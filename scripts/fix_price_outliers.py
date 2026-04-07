"""
Fix obvious price outliers in the `prices` table by product.

This script is conservative and supports a dry-run mode (default). It looks for
prices that are extreme compared to the product's median price and attempts to
repair obvious concatenation errors by dividing by 10 repeatedly until the
value becomes reasonably close to the median.

Usage:
    python scripts/fix_price_outliers.py        # dry-run, shows proposed fixes
    python scripts/fix_price_outliers.py --apply   # apply fixes to DB

The script uses the project's `db.get_connection()` helper.
"""
import sys
import os
import math
import argparse

# ensure project root on path
PRJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PRJ_ROOT not in sys.path:
    sys.path.insert(0, PRJ_ROOT)

import db
import csv
from datetime import datetime, timezone


def get_all_product_ids(conn):
    cur = conn.cursor()
    cur.execute("SELECT product_id FROM products")
    rows = cur.fetchall()
    cur.close()
    return [r[0] for r in rows]


def fetch_prices_for_product(conn, pid):
    cur = conn.cursor()
    cur.execute("SELECT price_id, price, scraped_at FROM prices WHERE product_id=%s ORDER BY scraped_at ASC", (pid,))
    rows = cur.fetchall()
    cur.close()
    return rows


def propose_fix_for_value(value, median):
    """If value looks like a concatenation error (much larger than median),
    try dividing by 10 repeatedly until close to median. Return new value or None."""
    if value <= 0 or not math.isfinite(value):
        return None
    if median <= 0 or not math.isfinite(median):
        return None
    # only consider if value is much larger than median (e.g. >= 8x)
    if value < median * 8:
        return None
    v = value
    while v > median * 2 and v >= 10:
        v = v / 10.0
        # if v is now within 3x of median, stop
        if abs(v - median) / median < 3:
            return round(v, 2)
    return None


def run(dry_run=True):
    conn = db.get_connection()
    pids = get_all_product_ids(conn)
    total_changes = 0
    # audit CSV path
    audit_csv = os.path.join(os.path.dirname(__file__), 'outlier_fixes_applied.csv')
    audit_header = ['product_id','price_id','scraped_at','old_price','new_price','applied_at','note']
    # prepare audit file if applying
    if not dry_run:
        # ensure the CSV has a header if missing
        if not os.path.exists(audit_csv):
            with open(audit_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(audit_header)
    for pid in pids:
        rows = fetch_prices_for_product(conn, pid)
        if not rows:
            continue
        prices = [float(r[1]) for r in rows if r[1] is not None]
        if not prices:
            continue
        s = sorted(prices)
        mid = len(s) // 2
        median = s[mid] if len(s) % 2 == 1 else (s[mid-1] + s[mid]) / 2.0
        proposals = []
        for price_id, price, scraped_at in rows:
            try:
                p = float(price)
            except Exception:
                continue
            newp = propose_fix_for_value(p, median)
            if newp is not None and abs(newp - p) / p > 0.001:
                proposals.append((price_id, p, newp, scraped_at))
        if proposals:
            print(f"Product {pid}: median={median}, proposed fixes={len(proposals)}")
            for price_id, oldp, newp, ts in proposals:
                print(f"  price_id={price_id} ts={ts} {oldp} -> {newp}")
            if not dry_run:
                cur = conn.cursor()
                # append audit rows as we apply updates
                with open(audit_csv, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    for price_id, oldp, newp, ts in proposals:
                        cur.execute("UPDATE prices SET price=%s WHERE price_id=%s", (newp, price_id))
                        applied_at = datetime.now(timezone.utc).isoformat()
                        writer.writerow([pid, price_id, str(ts), oldp, newp, applied_at, 'auto-fix: divided by 10 until near median'])
                        total_changes += 1
                conn.commit()
    conn.close()
    print(f"Done. total_changes={total_changes}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Apply fixes to DB')
    args = ap.parse_args()
    run(dry_run=not args.apply)
