"""
debug_hukut.py  —  find real selectors on Hukut search page
    python debug_hukut.py
"""

import re, time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    )
}

URL = "https://www.hukut.com/search?q=laptop"
print(f"Fetching: {URL}")
r   = requests.get(URL, headers=HEADERS, timeout=15)
src = r.text
soup = BeautifulSoup(src, "html.parser")

print(f"Status : {r.status_code}")
print(f"Length : {len(src):,} chars")
print(f"Title  : {soup.title.string if soup.title else 'N/A'}")

price_re = re.compile(r"(Rs\.?\s*[\d,]+|रु\s*[\d,]+)", re.IGNORECASE)

print("\n═══ Price-bearing leaf elements (up to 20) ═══")
found = 0
for el in soup.find_all(True):
    text = el.get_text(strip=True)
    if price_re.search(text) and 5 < len(text) < 300:
        children = [c for c in el.children if hasattr(c, "name") and c.name]
        if len(children) <= 3:
            cls = " | ".join(el.get("class", []))
            print(f"  <{el.name} class='{cls}'>  {text[:160]}")
            found += 1
    if found >= 20:
        break

print("\n═══ Unique <li> / <article> classes (potential product cards) ═══")
seen = set()
for el in soup.find_all(["li", "article"]):
    cls = tuple(el.get("class", []))
    if cls and cls not in seen:
        seen.add(cls)
        print(f"  {el.name}.{' '.join(cls)}")

print("\n═══ <a> tags containing price text ═══")
found = 0
for a in soup.find_all("a", href=True):
    text = a.get_text(strip=True)
    if price_re.search(text) and len(text) < 300:
        print(f"  href={a['href'][:80]}")
        print(f"  text={text[:120]}")
        found += 1
    if found >= 5:
        break
