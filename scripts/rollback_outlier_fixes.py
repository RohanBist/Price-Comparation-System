"""
Rollback runner for outlier fixes recorded in `scripts/outlier_fixes_applied.csv`.
This script will read the CSV and revert the `prices.price` values back to
`old_price` for the listed `price_id`s.

Usage:
    python scripts/rollback_outlier_fixes.py   # dry-run (shows actions)
    python scripts/rollback_outlier_fixes.py --apply  # perform restores

The script is conservative and will only update rows whose current price matches
`new_price` in the CSV (to avoid stomping unrelated edits). It prints a summary
and (if --apply) commits the changes.
"""
import os
import sys
import csv
import argparse
from datetime import datetime

PRJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PRJ_ROOT not in sys.path:
    sys.path.insert(0, PRJ_ROOT)

import db

CSV_PATH = os.path.join(os.path.dirname(__file__), 'outlier_fixes_applied.csv')


def read_csv():
    if not os.path.exists(CSV_PATH):
        print('Audit CSV not found:', CSV_PATH)
        return []
    out = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                price_id = int(r['price_id'])
                old_price = float(r['old_price'])
                new_price = float(r['new_price'])
                out.append((price_id, old_price, new_price))
            except Exception:
                continue
    return out


def run(apply=False):
    rows = read_csv()
    if not rows:
        print('No entries to rollback.')
        return
    conn = db.get_connection()
    cur = conn.cursor()
    to_apply = []
    for price_id, old_price, new_price in rows:
        # check current price
        cur.execute('SELECT price FROM prices WHERE price_id=%s', (price_id,))
        r = cur.fetchone()
        if not r:
            print(f'price_id {price_id} not found, skipping')
            continue
        cur_price = float(r[0])
        if abs(cur_price - new_price) > 1e-6:
            print(f'price_id {price_id} current price {cur_price} != expected new_price {new_price}, skipping')
            continue
        to_apply.append((price_id, old_price))

    print(f'Prepared {len(to_apply)} rollbacks.')
    if not apply:
        for pid, oldp in to_apply:
            print(f'Would restore price_id={pid} to {oldp}')
        cur.close()
        conn.close()
        return

    # apply
    applied = 0
    for pid, oldp in to_apply:
        cur.execute('UPDATE prices SET price=%s WHERE price_id=%s', (oldp, pid))
        applied += 1
    conn.commit()
    cur.close()
    conn.close()
    print(f'Applied {applied} rollbacks.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Apply rollbacks')
    args = ap.parse_args()
    run(apply=args.apply)
