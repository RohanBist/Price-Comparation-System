# fix_csv_setup.py
"""Quick script to set up CSV files properly"""

import os
import csv
from datetime import datetime

def create_csv_files():
    """Create CSV files with proper headers"""
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Create products.csv
    products_file = 'data/products.csv'
    if not os.path.exists(products_file):
        with open(products_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['product_id', 'product_name', 'image'])
        print(f"✓ Created {products_file}")
    else:
        print(f"✓ {products_file} already exists")
    
    # Create prices.csv
    prices_file = 'data/prices.csv'
    if not os.path.exists(prices_file):
        with open(prices_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['price_id', 'product_id', 'store_name', 'price', 'product_url', 'scraped_at'])
        print(f"✓ Created {prices_file}")
    else:
        print(f"✓ {prices_file} already exists")
    
    # Create price_history.csv
    history_file = 'data/price_history.csv'
    if not os.path.exists(history_file):
        with open(history_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['product_id', 'store_name', 'price', 'date', 'price_change', 'change_percent'])
        print(f"✓ Created {history_file}")
    else:
        print(f"✓ {history_file} already exists")
    
    print("\n✅ CSV files are ready!")

def check_pending_inserts():
    """Check and process pending inserts"""
    pending_file = 'pending_inserts.jsonl'
    
    if os.path.exists(pending_file):
        print(f"\nFound {pending_file} with pending data")
        
        # Count pending items
        with open(pending_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            pending_count = len([l for l in lines if l.strip()])
        
        print(f"  {pending_count} pending items found")
        
        # Ask if we should process them
        response = input("\nDo you want to process pending inserts? (y/n): ")
        if response.lower() == 'y':
            from db_utils import flush_pending
            processed = flush_pending()
            print(f"  Processed {processed} items")
    else:
        print("\n✓ No pending inserts found")

if __name__ == "__main__":
    print("=" * 50)
    print("CSV Setup and Fix")
    print("=" * 50)
    
    create_csv_files()
    check_pending_inserts()
    
    print("\n" + "=" * 50)
    print("Next steps:")
    print("1. Run: python app.py")
    print("2. Search for products (e.g., laptop)")
    print("3. Check if results appear")
    print("=" * 50)