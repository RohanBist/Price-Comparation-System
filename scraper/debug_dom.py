"""
debug_dom.py
------------
Dumps the live rendered HTML from Daraz and Itti after JavaScript runs,
so we can find the real CSS selectors to use in our scrapers.

Run:
    python debug_dom.py
"""

import time
import os
from base_scraper import build_driver

driver = build_driver()

def dump_page(name, url, wait=8):
    print(f"\n{'='*60}")
    print(f"  {name}: {url}")
    print(f"{'='*60}")
    driver.get(url)
    time.sleep(wait)  # let JS fully render

    src = driver.page_source

    # Save full HTML for inspection
    fname = f"debug_{name.lower()}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"  Full HTML saved to: {os.path.abspath(fname)}")
    print(f"  Page title: {driver.title}")
    print(f"  HTML length: {len(src):,} chars")

    # Print first product-like elements
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(src, "html.parser")

    # Show all unique class names on div/li/article that contain a price-like string
    print("\n  --- Elements containing 'Rs' or price-like text ---")
    count = 0
    for el in soup.find_all(["div", "li", "article", "span"]):
        text = el.get_text(strip=True)
        if ("Rs" in text or "NPR" in text or "₨" in text) and len(text) < 300:
            classes = " ".join(el.get("class", []))
            tag = el.name
            print(f"    <{tag} class='{classes}'> → {text[:120]}")
            count += 1
            if count >= 15:
                break

    if count == 0:
        print("  No price elements found — page may still be loading or blocked.")
        # Print first 2000 chars of body
        body = soup.find("body")
        if body:
            print("\n  --- First 1500 chars of <body> ---")
            print(body.get_text(strip=True)[:1500])

try:
    dump_page("Daraz", "https://www.daraz.com.np/catalog/?q=laptop&sort=pricedesc", wait=10)
    dump_page("Itti",  "https://www.itti.com.np/?s=laptop&post_type=product", wait=10)
finally:
    driver.quit()
    print("\n✓ Browser closed.")
