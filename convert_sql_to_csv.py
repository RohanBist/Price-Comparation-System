# convert_sql_to_csv.py
"""
Convert MySQL dump to CSV files for your CSV-based system
Run this once to migrate your existing data
"""

import csv
import re
from datetime import datetime
import os

def parse_sql_inserts(sql_file):
    """Parse INSERT statements from SQL file"""
    with open(sql_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract products insert
    products_pattern = r"INSERT INTO `products` \(.*?\) VALUES\n\((.*?)\);"
    products_matches = re.findall(products_pattern, content, re.DOTALL)
    
    products = []
    for match in products_matches:
        # Parse each product row (simplified - you might need to handle escaped quotes)
        rows = re.findall(r'\(([^)]+)\)', match, re.DOTALL)
        for row in rows:
            # Split by comma but respect quotes
            parts = []
            current = ''
            in_quotes = False
            for char in row:
                if char == "'" and not in_quotes:
                    in_quotes = True
                    current += char
                elif char == "'" and in_quotes:
                    in_quotes = False
                    current += char
                elif char == ',' and not in_quotes:
                    parts.append(current.strip())
                    current = ''
                else:
                    current += char
            if current:
                parts.append(current.strip())
            
            if len(parts) >= 6:
                products.append({
                    'product_id': parts[0].strip("'"),
                    'product_name': parts[1].strip("'"),
                    'category': parts[2].strip("'") if parts[2] != 'NULL' else '',
                    'description': parts[3].strip("'") if parts[3] != 'NULL' else '',
                    'created_at': parts[4].strip("'") if parts[4] != 'NULL' else '',
                    'image': parts[5].strip("'") if parts[5] != 'NULL' else ''
                })
    
    # Extract prices insert
    prices_pattern = r"INSERT INTO `prices` \(.*?\) VALUES\n((?:\([^)]+\),?\n?)+);"
    prices_match = re.search(prices_pattern, content, re.DOTALL)
    
    prices = []
    if prices_match:
        rows = re.findall(r'\(([^)]+)\)', prices_match.group(1))
        for row in rows:
            parts = [p.strip() for p in row.split(',')]
            if len(parts) >= 6:
                prices.append({
                    'price_id': parts[0].strip("'"),
                    'product_id': parts[1].strip("'"),
                    'store_name': parts[2].strip("'") if parts[2] != 'NULL' else '',
                    'price': parts[3].strip("'"),
                    'product_url': parts[4].strip("'") if parts[4] != 'NULL' else '',
                    'scraped_at': parts[5].strip("'") if parts[5] != 'NULL' else ''
                })
    
    return products, prices

def save_to_csv(products, prices, data_dir='data'):
    """Save products and prices to CSV files"""
    
    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Save products
    products_file = os.path.join(data_dir, 'products.csv')
    with open(products_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['product_id', 'product_name', 'image'])
        for p in products:
            writer.writerow([
                p['product_id'],
                p['product_name'],
                p.get('image', '')
            ])
    print(f"Saved {len(products)} products to {products_file}")
    
    # Save prices
    prices_file = os.path.join(data_dir, 'prices.csv')
    with open(prices_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['price_id', 'product_id', 'store_name', 'price', 'product_url', 'scraped_at'])
        for p in prices:
            writer.writerow([
                p['price_id'],
                p['product_id'],
                p['store_name'],
                p['price'],
                p['product_url'],
                p['scraped_at']
            ])
    print(f"Saved {len(prices)} price records to {prices_file}")
    
    # Create price_history.csv for trend tracking
    price_history_file = os.path.join(data_dir, 'price_history.csv')
    with open(price_history_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['product_id', 'store_name', 'price', 'date', 'price_change', 'change_percent'])
        
        # Calculate price changes per product
        from collections import defaultdict
        product_prices = defaultdict(list)
        
        for p in prices:
            product_prices[int(p['product_id'])].append({
                'price': float(p['price']),
                'store': p['store_name'],
                'date': p['scraped_at']
            })
        
        for pid, price_list in product_prices.items():
            # Sort by date
            price_list.sort(key=lambda x: x['date'])
            
            # Calculate changes between consecutive records
            for i in range(1, len(price_list)):
                prev_price = price_list[i-1]['price']
                curr_price = price_list[i]['price']
                change = curr_price - prev_price
                change_percent = (change / prev_price) * 100 if prev_price > 0 else 0
                
                writer.writerow([
                    pid,
                    price_list[i]['store'],
                    curr_price,
                    price_list[i]['date'],
                    change,
                    change_percent
                ])
    
    print(f"Created price history file with calculated trends")

if __name__ == "__main__":
    # Convert your SQL file
    sql_file = "price_comparison_ai (1).sql"
    products, prices = parse_sql_inserts(sql_file)
    save_to_csv(products, prices)
    print("\n✅ Migration complete! Your CSV files are ready in the 'data' folder.")