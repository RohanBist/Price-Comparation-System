"""
main.py
-------
Electronics Price Comparison System.

Run:
    python main.py
    python main.py "gaming mouse"
"""

import sys
import os
import json
import textwrap
import re
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(__file__))

from base_scraper import build_driver
from daraz_scraper import DarazScraper
from hukut_scraper import HukutScraper
from difflib import SequenceMatcher

LINE = "=" * 62


def print_results(store_name: str, results: List[dict]) -> None:
    print("\n" + LINE)
    print(f"  Scraping {store_name}...")
    print(LINE)

    if not results:
        print("  ✗  No results returned.")
        return

    for i, p in enumerate(results, 1):
        name_w = textwrap.fill(p.get("name", ""), width=52, subsequent_indent="        ")
        price = p.get("price") or 0
        link = p.get("link", "")
        print(
            f"  {i:>2}. {name_w}\n"
            f"      Price : Rs. {price:,}\n"
            f"      Link  : {link}\n"
        )


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (s or "").lower())).strip()


def query_tokens(q: str):
    return [t for t in re.split(r"\W+", (q or "").lower()) if t and len(t) >= 3]


def name_similarity(a: str, b: str) -> float:
    try:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    except Exception:
        return 0.0


def token_jaccard(a: str, b: str) -> float:
    aset = set([t for t in re.split(r"\W+", (a or "").lower()) if t and len(t) >= 3])
    bset = set([t for t in re.split(r"\W+", (b or "").lower()) if t and len(t) >= 3])
    if not aset or not bset:
        return 0.0
    inter = aset & bset
    union = aset | bset
    return len(inter) / len(union)


def is_relevant(prod: dict, q: str) -> bool:
    name = normalize_text(prod.get("name", ""))
    tokens = query_tokens(q)
    if not tokens:
        return True
    name_tokens = set(re.split(r"\W+", name))
    for t in tokens:
        if t in name_tokens:
            return True
    # fuzzy fallback
    score = name_similarity(name, q)
    if score >= float(os.environ.get("MATCH_NAME_SIM", "0.45")):
        return True
    if token_jaccard(name, q) >= 0.25:
        return True
    return False


def filter_results(results: List[dict], q: str) -> List[dict]:
    out = [r for r in results if is_relevant(r, q)]
    if not out and results:
        return results[:5]
    return out


def find_matches(a_list: List[dict], b_list: List[dict]) -> Tuple[List[Tuple[dict, dict, float, int]], List[dict], List[dict]]:
    MATCH_NAME_SIM = float(os.environ.get("MATCH_NAME_SIM", "0.45"))
    MATCH_PRICE_REL = float(os.environ.get("MATCH_PRICE_REL", "0.20"))
    MATCH_PRICE_ABS = int(os.environ.get("MATCH_PRICE_ABS", "5000"))

    matches = []
    used_b = set()

    for i, a in enumerate(a_list):
        best_j = None
        best_score = 0.0
        for j, b in enumerate(b_list):
            if j in used_b:
                continue
            ns = name_similarity(a.get("name", ""), b.get("name", ""))
            tj = token_jaccard(a.get("name", ""), b.get("name", ""))
            score = max(ns, tj)
            if score > best_score:
                best_score = score
                best_j = j

        if best_j is not None and best_score >= MATCH_NAME_SIM:
            b = b_list[best_j]
            p1 = a.get("price") or 0
            p2 = b.get("price") or 0
            if p1 is None:
                p1 = 0
            if p2 is None:
                p2 = 0
            avg = (p1 + p2) / 2 if (p1 and p2) else max(p1, p2)
            abs_diff = abs(p1 - p2)
            rel = abs_diff / avg if avg else 1.0

            # price proximity check
            if (rel <= MATCH_PRICE_REL) or (abs_diff <= MATCH_PRICE_ABS):
                matches.append((a, b, best_score, abs_diff))
                used_b.add(best_j)

    unmatched_a = [x for x in a_list if not any(x is m[0] for m in matches)]
    unmatched_b = [x for idx, x in enumerate(b_list) if idx not in used_b]
    return matches, unmatched_a, unmatched_b


def main(query: str) -> None:
    print("\n" + LINE)
    print("  Electronics Price Comparison System")
    print(f"  Searching for: '{query}'")
    print(LINE)

    # Run Hukut (fast, no browser)
    hukut_results = HukutScraper().scrape_products(query)

    # Run Daraz (needs browser)
    print("\n  Starting headless Chrome for Daraz...")
    driver = build_driver()
    print(f"  Driver created: {driver is not None}")
    daraz_results = []

    try:
        daraz_scraper = DarazScraper(driver)
        daraz_results = daraz_scraper.scrape_products(query)

        # if Daraz returned few results, attempt a couple of extra deeper scrapes
        display_total = int(os.environ.get("DISPLAY_TOTAL", "50"))
        desired_half = display_total // 2
        if len(daraz_results) < desired_half:
            extra_attempts = int(os.environ.get("DARAZ_EXTRA_ATTEMPTS", "2"))
            base_max = int(os.environ.get("DARAZ_MAX_SCROLLS", "4"))
            seen_links = set(p.get("link") for p in daraz_results if p.get("link"))
            for attempt in range(extra_attempts):
                os.environ["DARAZ_MAX_SCROLLS"] = str(base_max + (attempt + 1) * 4)
                print(f"  Daraz: extra scrape attempt {attempt+1} with max_scrolls={os.environ['DARAZ_MAX_SCROLLS']}")
                more = DarazScraper(driver).scrape_products(query)
                added = 0
                for p in more:
                    ln = p.get("link")
                    if not ln or ln in seen_links:
                        continue
                    seen_links.add(ln)
                    daraz_results.append(p)
                    added += 1
                    if len(daraz_results) >= desired_half:
                        break
                if added == 0:
                    break
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        print("  ✓ Browser closed.")

    # Apply per-query filtering (keeps fallback items if fully filtered out)
    daraz_results = filter_results(daraz_results, query)
    hukut_results = filter_results(hukut_results, query)

    # Find matches across full lists
    matches, daraz_unmatched, hukut_unmatched = find_matches(daraz_results, hukut_results)

    # Print matches
    if matches:
        print("\n" + LINE)
        print("  MATCHED PRODUCTS (Daraz ⇄ Hukut)")
        print(LINE)
        for i, (a, b, score, diff) in enumerate(matches, 1):
            cheaper = a if (a.get("price") or 0) <= (b.get("price") or 0) else b
            print(f"\n  {i}. {a.get('name','')[:80]}")
            print(f"      Daraz : Rs. {(a.get('price') or 0):,}  — {a.get('link','')}")
            print(f"      Hukut : Rs. {(b.get('price') or 0):,}  — {b.get('link','')}")
            avg = ((a.get('price') or 0) + (b.get('price') or 0)) / 2 if (a.get('price') and b.get('price')) else max(a.get('price') or 0, b.get('price') or 0)
            pct = (diff / avg * 100) if avg else 0
            print(f"      Price diff: Rs. {diff:,} ({pct:.1f}%); Recommended: Buy from {(cheaper.get('store') or 'store')}")
    else:
        print("\n  No close matches found between Daraz and Hukut for this query.")

    # Combined full set (Daraz first then Hukut) and cheapest summary
    full_sorted = (daraz_results + hukut_results)
    full_sorted = [p for p in full_sorted if p.get('price') is not None]
    full_sorted.sort(key=lambda x: x.get("price", 10**12))

    print_results("Daraz", daraz_results)
    print_results("Hukut", hukut_results)

    print("\n" + LINE)
    print("  SUMMARY")
    print(LINE)

    print(f"  Total products found : {len(daraz_results) + len(hukut_results)}")

    if full_sorted:
        cheapest = full_sorted[0]
        print(
            f"\n  Cheapest product:\n"
            f"  {cheapest.get('name','')[:60]}\n"
            f"  Rs. {cheapest.get('price',0):,} ({cheapest.get('store','unknown')})"
        )

    print(LINE)

    print("\n--- JSON Output (full: Daraz then Hukut) ---")
    all_results = daraz_results + hukut_results
    print(json.dumps(all_results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("\nEnter product to search: ").strip()
        if not query:
            print("Please enter a product name.")
            sys.exit()
    main(query)