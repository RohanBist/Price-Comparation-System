"""
Export the entire `prices` table to CSV for backup.
Usage:
    python scripts/export_prices_backup.py
Outputs to `scripts/prices_backup_<timestamp>.csv`.
"""
import os
import sys
import csv
from datetime import datetime

# ensure project root on path
PRJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PRJ_ROOT not in sys.path:
    sys.path.insert(0, PRJ_ROOT)

import db


def export_prices():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM prices")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()

    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_path = os.path.join(os.path.dirname(__file__), f'prices_backup_{ts}.csv')
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for r in rows:
            # convert datetimes to isoformat
            out = []
            for v in r:
                if hasattr(v, 'isoformat'):
                    out.append(v.isoformat())
                else:
                    out.append(v)
            writer.writerow(out)
    print(f'Exported {len(rows)} rows to {out_path}')

if __name__ == '__main__':
    export_prices()
