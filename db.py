# db.py - Fixed version
"""
CSV-based storage for products and prices
"""

import csv
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Use absolute paths to avoid confusion
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.csv')
PRICES_FILE = os.path.join(DATA_DIR, 'prices.csv')
PRICE_HISTORY_FILE = os.path.join(DATA_DIR, 'price_history.csv')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def _ensure_csv_files():
    """Create CSV files with headers if they don't exist"""
    # Products file
    if not os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['product_id', 'product_name', 'image'])
            logger.info(f"Created {PRODUCTS_FILE}")
    
    # Prices file
    if not os.path.exists(PRICES_FILE):
        with open(PRICES_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['price_id', 'product_id', 'store_name', 'price', 'product_url', 'scraped_at'])
            logger.info(f"Created {PRICES_FILE}")
    
    # Price history file
    if not os.path.exists(PRICE_HISTORY_FILE):
        with open(PRICE_HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['product_id', 'store_name', 'price', 'date', 'price_change', 'change_percent'])
            logger.info(f"Created {PRICE_HISTORY_FILE}")

def read_products() -> List[Dict]:
    """Read all products from CSV"""
    _ensure_csv_files()
    products = []
    try:
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    products.append(row)
        else:
            logger.warning(f"Products file not found: {PRODUCTS_FILE}")
    except Exception as e:
        logger.error(f"Error reading products: {e}")
    return products

def read_prices() -> List[Dict]:
    """Read all prices from CSV"""
    _ensure_csv_files()
    prices = []
    try:
        if os.path.exists(PRICES_FILE):
            with open(PRICES_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    prices.append(row)
        else:
            logger.warning(f"Prices file not found: {PRICES_FILE}")
    except Exception as e:
        logger.error(f"Error reading prices: {e}")
    return prices

def _next_id(items: List[Dict], id_field: str) -> int:
    """Get next available ID"""
    if not items:
        return 1
    max_id = 0
    for item in items:
        try:
            val = int(item.get(id_field, 0))
            if val > max_id:
                max_id = val
        except (ValueError, TypeError):
            continue
    return max_id + 1

def write_product(product_id: int, name: str, image: str = ''):
    """Write a new product to CSV"""
    _ensure_csv_files()
    try:
        with open(PRODUCTS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([product_id, name, image])
        logger.debug(f"Added product: {product_id} - {name[:50]}")
    except Exception as e:
        logger.error(f"Error writing product: {e}")

def update_product_image(product_id: int, image: str):
    """Update product image"""
    products = read_products()
    updated = False
    for p in products:
        if int(p['product_id']) == product_id:
            p['image'] = image
            updated = True
            break
    
    if updated:
        try:
            with open(PRODUCTS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['product_id', 'product_name', 'image'])
                for p in products:
                    writer.writerow([p['product_id'], p['product_name'], p['image']])
        except Exception as e:
            logger.error(f"Error updating product image: {e}")

def write_price(price_id: int, product_id: int, store: str, price: float, url: str, scraped_at: str):
    """Write a new price record"""
    _ensure_csv_files()
    
    # Add to prices file
    try:
        with open(PRICES_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([price_id, product_id, store, price, url, scraped_at])
        logger.debug(f"Added price: {product_id} - {store} - Rs.{price}")
        
        # Also update price history
        _update_price_history(product_id, store, price, scraped_at)
        
    except Exception as e:
        logger.error(f"Error writing price: {e}")

def _update_price_history(product_id: int, store: str, price: float, scraped_at: str):
    """Update price history with change calculation"""
    try:
        # Get previous price for this product and store
        prices = read_prices()
        product_prices = [
            p for p in prices 
            if int(p['product_id']) == product_id and p['store_name'] == store
        ]
        
        if len(product_prices) >= 2:
            # Sort by date
            product_prices.sort(key=lambda x: x['scraped_at'])
            prev_price = float(product_prices[-2]['price'])
            current_price = price
            price_change = current_price - prev_price
            change_percent = (price_change / prev_price) * 100 if prev_price > 0 else 0
            
            # Add to price history
            with open(PRICE_HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([product_id, store, current_price, scraped_at, price_change, change_percent])
            
            # Log significant changes
            if abs(change_percent) >= 10:
                logger.info(f"Significant price change for product {product_id}: {change_percent:.1f}%")
                
    except Exception as e:
        logger.error(f"Error updating price history: {e}")

# Initialize CSV files on import
_ensure_csv_files()