"""
Safe migration: add `image` column to `products` table if it does not exist.
This script uses the project's `db.get_connection()` function. Run it like:

    python scripts/add_products_image_column.py

It will check INFORMATION_SCHEMA and perform ALTER TABLE only when necessary.
"""
import sys
import os
import logging

# Ensure project root is on sys.path so `import db` (project module) works
PRJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PRJ_ROOT not in sys.path:
    sys.path.insert(0, PRJ_ROOT)

import db

logger = logging.getLogger("migration")
logging.basicConfig(level=logging.INFO)

def ensure_image_column():
    conn = None
    cur = None
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        # Check if column exists in the current database/schema
        cur.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            ("products", "image"),
        )
        row = cur.fetchone()
        if row and row[0] > 0:
            logger.info("Column 'image' already exists on 'products'. Nothing to do.")
            return 0

        logger.info("Adding 'image' column to 'products' table...")
        # Use a permissive column type to store image URLs or base64 if desired
        cur.execute("ALTER TABLE products ADD COLUMN image TEXT NULL")
        conn.commit()
        logger.info("Added 'image' column successfully.")
        return 0
    except Exception as e:
        logger.exception("Migration failed: %s", e)
        return 2
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    sys.exit(ensure_image_column())
