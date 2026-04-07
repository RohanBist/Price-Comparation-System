"""
app.py
------
Flask backend for PriceNepal.
Exposes a REST API that runs the scrapers and returns JSON.

Run:
    pip install flask flask-cors
    python app.py
"""

import sys
import os
import json
import threading
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

# Make scraper folder importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scraper"))

from base_scraper import build_driver
from daraz_scraper import DarazScraper
from hukut_scraper import HukutScraper
from db_utils import save_product_and_price, get_recommendations, get_price_history, get_latest_price_stats, get_popularity_map
import db

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)  # Allow frontend to call the API from any origin

# ── Simple in-memory cache to avoid re-scraping same query ──
_cache: dict = {}
_cache_lock = threading.Lock()


def run_scrapers(query: str) -> list:
    """Run all scrapers concurrently and return merged sorted results."""
    results = []
    errors  = []

    # --- Hukut ---
    try:
        hukut = HukutScraper()
        results.extend(hukut.scrape_products(query))
    except Exception as e:
        errors.append(f"Hukut error: {e}")

    # --- Daraz ---
    driver = None
    try:
        driver = build_driver()
        daraz = DarazScraper(driver)
        results.extend(daraz.scrape_products(query))
    except Exception as e:
        errors.append(f"Daraz error: {e}")
    finally:
        if driver:
            driver.quit()

    # ── NEW: Relevance filter ──────────────────────────────────────────
    query_tokens = [t.lower() for t in query.strip().split() if t]

    def relevance_score(product_name: str) -> float:
        name = product_name.lower()
        matched = sum(1 for t in query_tokens if t in name)
        return matched / len(query_tokens) if query_tokens else 0

    # Keep only results that match ALL query tokens (strict),
    # fall back to majority match if strict returns nothing
    strict = [r for r in results if relevance_score(r.get("name", "")) == 1.0]
    results = strict if strict else [r for r in results if relevance_score(r.get("name", "")) >= 0.6]

    # Attach relevance score to each result for frontend use
    for r in results:
        r["relevance"] = relevance_score(r.get("name", ""))
    # ──────────────────────────────────────────────────────────────────

    # Sort by price ascending (relevance filter already ensures they're all matching)
    results.sort(key=lambda x: x.get("price", 0))
    return results, errors


def save_results_to_db(results: list):
    """Persist scraped results to DB where possible."""
    saved = []
    for r in results:
        try:
            pid = save_product_and_price(r)
            r['product_id'] = pid
            saved.append(r)
        except Exception as e:
            # don't break on DB failures
            print(f"DB save error: {e}")
    return saved



# ════════════════════════════════════════════
#  API ROUTES
# ════════════════════════════════════════════

@app.route("/api/search")
def api_search():
    """
    GET /api/search?q=<query>

    Returns JSON:
    {
        "query": "...",
        "count": 12,
        "results": [
            { "name": "...", "price": 42999, "store": "Daraz", "link": "..." },
            ...
        ],
        "errors": []
    }
    """
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({"error": "Missing query parameter ?q="}), 400

    # Check cache
    with _cache_lock:
        if query.lower() in _cache:
            cached = _cache[query.lower()]
            cached["cached"] = True
            return jsonify(cached)

    results, errors = run_scrapers(query)

    # Persist scraped results (best-effort)
    save_results_to_db(results)

    # Enrich results with popularity (number of saved observations) where possible
    try:
        product_ids = [r.get('product_id') for r in results if r.get('product_id')]
        pop_map = get_popularity_map(product_ids)
        for r in results:
            pid = r.get('product_id')
            # Prefer popularity by product_id when available
            pcount = int(pop_map.get(pid, 0)) if pid else 0
            # Fallback: if no product_id or popularity is zero, try counting by product_url
            if (not pid or pcount == 0) and r.get('link'):
                try:
                    prices = db.read_prices()
                    pcount = sum(1 for p in prices if p.get("product_url") == r.get("link"))
                except Exception:
                    pass
            r['popularity'] = pcount
            # rating: if the scraper didn't provide an explicit rating, compute
            # a simple proxy rating from popularity so the 'Ratings' sort does
            # have an effect immediately. This is a lightweight heuristic and
            # can be replaced when true ratings are scraped/stored.
            try:
                import math
                if r.get('rating') is not None:
                    r['rating'] = float(r.get('rating'))
                else:
                    # proxy: map popularity to 1..5 scale using log
                    r['rating'] = round(min(5.0, 1.0 + math.log10(max(1, pcount)) * 0.8), 2)
            except Exception:
                r['rating'] = None
    except Exception:
        pass

    response = {
        "query":   query,
        "count":   len(results),
        "results": results,
        "errors":  errors,
        "cached":  False,
    }

    # Store in cache
    with _cache_lock:
        _cache[query.lower()] = response

    return jsonify(response)


@app.route('/api/history')
def api_history():
    pid = request.args.get('product_id')
    if not pid:
        return jsonify({'error': 'Missing product_id'}), 400
    try:
        pid_i = int(pid)
    except ValueError:
        return jsonify({'error': 'Invalid product_id'}), 400

    data = get_price_history(pid_i)
    return jsonify({'product_id': pid_i, 'history': data})


@app.route('/api/recommendations')
def api_recommendations():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'recommendations': []})
    # optional price hint (used to prefer items near a given price)
    price_hint = request.args.get('price')
    try:
        price_hint_val = float(price_hint) if price_hint else None
    except Exception:
        price_hint_val = None
    # optional limit for how many recommendations to return (default higher)
    limit = request.args.get('limit')
    try:
        limit_val = int(limit) if limit else None
    except Exception:
        limit_val = None

    recs = get_recommendations(q, limit=limit_val or 20, price_hint=price_hint_val)
    return jsonify({'recommendations': recs})


@app.route('/api/save_price', methods=['POST'])
def api_save_price():
    """Save a single product price observation posted from the frontend.

    Expects JSON body with keys: name, price, store, link, image (optional).
    Returns {product_id: <id>} on success.
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({'error': 'Missing JSON body'}), 400
    # normalize keys
    result = {
        'name': payload.get('name') or payload.get('product_name'),
        'price': payload.get('price') or payload.get('latest_price') or payload.get('p'),
        'store': payload.get('store') or payload.get('store_name'),
        'link': payload.get('link') or payload.get('product_url'),
        'image': payload.get('image')
    }
    try:
        pid = save_product_and_price(result)
        return jsonify({'product_id': pid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/stores")
def api_stores():
    """Return list of supported stores."""
    return jsonify({
        "stores": ["Daraz", "Hukut"]
    })


@app.route("/api/health")
def api_health():
    """Health check."""
    return jsonify({"status": "ok", "service": "PriceNepal API"})


# ════════════════════════════════════════════
#  SERVE FRONTEND
# ════════════════════════════════════════════

@app.route("/")
@app.route("/<path:page>")
def index(page="index"):
    return render_template("index.html")


# ════════════════════════════════════════════

if __name__ == "__main__":
    print("\n  PriceNepal API running at http://localhost:5000")
    print("  Search endpoint: http://localhost:5000/api/search?q=laptop\n")
    app.run(debug=True, port=5000)