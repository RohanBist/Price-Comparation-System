"""
debug_sastodeal.py
------------------
Probe Sastodeal search page to find real selectors.

    python debug_sastodeal.py
"""

import time, re
from base_scraper import build_driver
from bs4 import BeautifulSoup

driver = build_driver()
URL = "https://www.sastodeal.com/catalogsearch/result/?q=laptop"

try:
    print(f"Loading: {URL}")
    driver.get(URL)

    # Wait up to 20s for price to appear
    from selenium.webdriver.support.ui import WebDriverWait
    try:
        WebDriverWait(driver, 20).until(lambda d: "Rs." in d.page_source or "रु" in d.page_source)
        print("✓ Price text found in DOM")
    except:
        print("✗ No price after 20s")

    # Scroll
    for i in range(3):
        driver.execute_script(f"window.scrollTo(0, {(i+1)*800});")
        time.sleep(0.8)

    src  = driver.page_source
    soup = BeautifulSoup(src, "html.parser")

    print(f"Title  : {driver.title}")
    print(f"URL    : {driver.current_url}")
    print(f"Length : {len(src):,}")

    price_re = re.compile(r"(Rs\.?\s*[\d,]+|रु\s*[\d,]+)", re.IGNORECASE)

    print("\n═══ Price-bearing leaf elements (up to 15) ═══")
    found = 0
    for el in soup.find_all(True):
        text = el.get_text(strip=True)
        if price_re.search(text) and len(text) < 300:
            children = [c for c in el.children if hasattr(c, 'name') and c.name]
            if len(children) <= 3:
                cls = " | ".join(el.get("class", []))
                print(f"  <{el.name} class='{cls}'> {text[:150]}")
                found += 1
        if found >= 15:
            break

    print("\n═══ Unique <li> / <div> / <article> classes (potential cards) ═══")
    seen = set()
    for el in soup.find_all(["li", "article"]):
        cls = tuple(el.get("class", []))
        if cls and cls not in seen:
            seen.add(cls)
            print(f"  {el.name}.{' '.join(cls)}")

finally:
    driver.quit()
    print("\n✓ Done.")
