"""
db_utils.py
-----------
CSV-backed utilities replacing MySQL queries.
Products and prices are stored in data/products.csv and data/prices.csv.
"""

import os
import re
import json
import logging
import difflib
import tempfile
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

import db

logger = logging.getLogger(__name__)

PENDING_FILE = os.path.join(os.path.dirname(__file__), "pending_inserts.jsonl")


# ── Helper functions ────────────────────────────────────────────────────────────

def extract_model_tokens(text: str) -> set:
    """Extract all numeric model tokens from text (e.g. {'3050'} from 'RTX 3050 Ti')."""
    matches = re.findall(r"\b(\d+)\b", text)
    return set(matches)


# ── Save / lookup ────────────────────────────────────────────────────────────

def save_product_and_price(result: Dict) -> Optional[int]:
    try:
        return _save_csv(result)
    except Exception as exc:
        logger.exception("CSV save failed, enqueueing: %s", exc)
        try:
            _enqueue_pending(result)
        except Exception:
            logger.exception("Failed to enqueue pending save")
        return None


def _save_csv(result: Dict) -> Optional[int]:
    name      = result.get("name")
    store     = result.get("store")
    price     = result.get("price")
    link      = result.get("link")
    image     = result.get("image", "")

    if not name or price is None:
        return None

    products = db.read_products()
    prices   = db.read_prices()

    # Find existing product by URL first, then by name
    product_id = None
    if link:
        for p in prices:
            if p.get("product_url") == link:
                product_id = int(p["product_id"])
                break
    if not product_id and name:
        for p in products:
            if p.get("product_name") == name:
                product_id = int(p["product_id"])
                break

    if not product_id:
        product_id = db._next_id(products, "product_id")
        db.write_product(product_id, name, image)
    elif image:
        db.update_product_image(product_id, image)

    price_id = db._next_id(prices, "price_id")
    db.write_price(price_id, product_id, store, float(price), link or "", datetime.now().isoformat())

    try:
        flush_pending()
    except Exception:
        pass

    return product_id


# ── Pending queue ─────────────────────────────────────────────────────────────

def _enqueue_pending(obj: Any) -> None:
    with open(PENDING_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, default=str, ensure_ascii=False) + "\n")


def flush_pending() -> int:
    if not os.path.exists(PENDING_FILE):
        return 0
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="pending_flush_", dir=os.path.dirname(PENDING_FILE))
    os.close(tmp_fd)
    success_count = 0
    remaining = []
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception as exc:
        logger.exception("Failed to read pending file: %s", exc)
        return 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        try:
            _save_csv(item)
            success_count += 1
        except Exception as exc:
            logger.debug("Flush attempt failed: %s", exc)
            remaining.append(item)
    try:
        if remaining:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                for it in remaining:
                    fh.write(json.dumps(it, default=str, ensure_ascii=False) + "\n")
            os.replace(tmp_path, PENDING_FILE)
        else:
            try:
                os.remove(PENDING_FILE)
            except Exception:
                pass
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception as exc:
        logger.exception("Failed to rewrite pending file: %s", exc)
    logger.info("flush_pending: %d flushed, %d remain", success_count, len(remaining))
    return success_count


# ── Price history ─────────────────────────────────────────────────────────────

def get_price_history(product_id: int) -> List[Tuple[str, float]]:
    try:
        prices = db.read_prices()
        rows = [
            (p["scraped_at"], float(p["price"]))
            for p in prices
            if int(p["product_id"]) == product_id
        ]
        rows.sort(key=lambda x: x[0])
        return rows
    except Exception as exc:
        logger.exception("CSV history read failed: %s", exc)
        return []


# ── Recommendations ───────────────────────────────────────────────────────────

def get_recommendations(query: str, limit: int = 20, price_hint: float = None) -> List[Dict]:
    import math
    try:
        products = db.read_products()
        prices   = db.read_prices()

        if not products:
            return []

        ids   = [int(p["product_id"]) for p in products]
        names = [p.get("product_name") or "" for p in products]
        images = {int(p["product_id"]): p.get("image", "") for p in products}

        q = query or ""
        scores = []

        # TF-IDF with sklearn if available, else difflib fallback
        use_sklearn = False
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            use_sklearn = True
        except Exception:
            pass

        if use_sklearn:
            try:
                vect = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
                tfidf = vect.fit_transform(names)
                qv = vect.transform([q])
                sim = cosine_similarity(qv, tfidf).ravel()
                
                q_model_tokens = extract_model_tokens(q)
                important_tokens = [t for t in re.split(r"\W+", q.lower()) if len(t) >= 4]
                
                for idx, s in enumerate(sim):
                    pname = names[idx]
                    name_lower = pname.lower()
                    name_model_tokens = extract_model_tokens(name_lower)

                    # 🔥 STRICT MODEL CHECK - if query has model numbers, product must contain ALL of them
                    if q_model_tokens:
                        if not q_model_tokens.issubset(name_model_tokens):
                            continue

                    # 🔥 STRICT KEYWORD CHECK for brand/model
                    if important_tokens:
                        if not any(tok in name_lower for tok in important_tokens):
                            continue

                    if s and s > 0.01:
                        scores.append((float(s), ids[idx], pname))
            except Exception:
                scores = []

        if not scores:
            ql = q.lower()
            q_model_tokens = extract_model_tokens(ql)
            important_tokens = [t for t in re.split(r"\W+", ql) if len(t) >= 4]
            
            for pid, pname in zip(ids, names):
                name_lower = (pname or "").lower()
                name_model_tokens = extract_model_tokens(name_lower)

                # 🔥 STRICT MODEL CHECK - if query has model numbers, product must contain ALL of them
                if q_model_tokens:
                    if not q_model_tokens.issubset(name_model_tokens):
                        continue  # ❌ skip products missing required model numbers

                # 🔥 STRICT KEYWORD CHECK for brand/model
                if important_tokens:
                    if not any(tok in name_lower for tok in important_tokens):
                        continue

                score = difflib.SequenceMatcher(a=ql, b=name_lower).ratio()
                for w in ql.split():
                    if w and w in name_lower:
                        score += 0.1
                if score > 0.18:
                    scores.append((float(score), pid, pname))

        if not scores:
            return []

        scores.sort(reverse=True)
        candidate_slice = scores[:max(limit * 3, limit)]
        candidate_ids = [pid for _, pid, _ in candidate_slice]

        # Build latest price map from CSV
        price_map: Dict[int, float] = {}
        url_map: Dict[int, str] = {}
        popularity_map: Dict[int, int] = {}
        for p in prices:
            pid = int(p["product_id"])
            if pid not in candidate_ids:
                continue
            popularity_map[pid] = popularity_map.get(pid, 0) + 1
            # Keep the latest price row (largest scraped_at)
            if pid not in price_map or p["scraped_at"] > url_map.get(f"_ts_{pid}", ""):
                try:
                    price_map[pid] = float(p["price"])
                    url_map[pid] = p.get("product_url", "")
                    url_map[f"_ts_{pid}"] = p["scraped_at"]
                except Exception:
                    pass

        # Price scoring
        price_metrics = []
        for _, pid, _ in candidate_slice:
            pr = price_map.get(pid)
            if pr is None or pr <= 0:
                metric = 0.0
            else:
                if price_hint and price_hint > 0:
                    metric = max(0.0, 1.0 - min(1.0, abs(pr - price_hint) / price_hint))
                else:
                    metric = 1.0 / (1.0 + math.log1p(pr))
            price_metrics.append(metric)

        pm_min = min(price_metrics) if price_metrics else 0.0
        pm_max = max(price_metrics) if price_metrics else 0.0
        if pm_max - pm_min < 1e-12:
            norm_metrics = [1.0] * len(price_metrics)
        else:
            norm_metrics = [(v - pm_min) / (pm_max - pm_min) for v in price_metrics]

        combined = [
            (0.75 * float(s) + 0.25 * norm_metrics[i], float(s), pid, pname)
            for i, (s, pid, pname) in enumerate(candidate_slice)
        ]
        combined.sort(reverse=True)

        out = []
        for final_score, content_score, pid, pname in combined[:limit]:
            out.append({
                "product_id":     pid,
                "product_name":   pname,
                "score":          round(content_score, 4),
                "combined_score": round(final_score, 4),
                "latest_price":   price_map.get(pid),
                "product_url":    url_map.get(pid),
                "image":          images.get(pid, ""),
                "popularity":     popularity_map.get(pid, 0),
            })
        return out

    except Exception as exc:
        logger.exception("CSV recommendations failed: %s", exc)
        return []


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_latest_price_stats(product_id: int) -> Dict:
    try:
        prices = db.read_prices()
        # Latest price per store
        store_latest: Dict[str, float] = {}
        store_ts: Dict[str, str] = {}
        for p in prices:
            if int(p["product_id"]) != product_id:
                continue
            store = p["store_name"]
            ts = p["scraped_at"]
            if store not in store_ts or ts > store_ts[store]:
                store_ts[store] = ts
                store_latest[store] = float(p["price"])
        vals = list(store_latest.values())
        if not vals:
            return {"min": None, "max": None}
        return {"min": min(vals), "max": max(vals)}
    except Exception as exc:
        logger.exception("CSV stats failed: %s", exc)
        return {"min": None, "max": None}


def get_popularity_map(product_ids: list) -> dict:
    try:
        prices = db.read_prices()
        out: Dict[int, int] = {}
        for p in prices:
            pid = int(p["product_id"])
            if pid in product_ids:
                out[pid] = out.get(pid, 0) + 1
        return out
    except Exception as exc:
        logger.exception("CSV popularity failed: %s", exc)
        return {}


def get_product_price_trends(product_id: int) -> Dict:
    """Get price trends for a product"""
    return db.get_product_price_trends(product_id)


def get_products_on_sale(threshold_percent: int = 10) -> List[Dict]:
    """Get products with significant price drops"""
    try:
        products = db.read_products()
        prices = db.read_prices()
        
        on_sale = []
        for product in products:
            pid = int(product['product_id'])
            product_prices = [p for p in prices if int(p['product_id']) == pid]
            
            if len(product_prices) >= 2:
                product_prices.sort(key=lambda x: x['scraped_at'])
                latest_price = float(product_prices[-1]['price'])
                oldest_price = float(product_prices[0]['price'])
                
                if oldest_price > 0:
                    drop_percent = ((oldest_price - latest_price) / oldest_price) * 100
                    if drop_percent >= threshold_percent:
                        on_sale.append({
                            'product_id': pid,
                            'product_name': product['product_name'],
                            'current_price': latest_price,
                            'original_price': oldest_price,
                            'saving': oldest_price - latest_price,
                            'saving_percent': drop_percent,
                            'store': product_prices[-1]['store_name']
                        })
        
        return on_sale
    except Exception as exc:
        logger.exception("CSV on_sale query failed: %s", exc)
        return []