"""
check_sites.py
--------------
Tests which Nepali e-commerce sites are reachable BEFORE
we write a scraper for them. Runs fast with plain requests.

    python check_sites.py
"""

import requests, time

SITES = [
    ("Daraz",       "https://www.daraz.com.np/catalog/?q=laptop"),
    ("Sastodeal",   "https://www.sastodeal.com/catalogsearch/result/?q=laptop"),
    ("Hukut",       "https://www.hukut.com/search?q=laptop"),
    ("Gyapu",       "https://www.gyapu.com/search/result?search=laptop"),
    ("Nepali Cart", "https://www.nepalicart.com/search?q=laptop"),
    ("Hamrobazar",  "https://hamrobazar.com/search?q=laptop"),
    ("Oliz Store",  "https://olizstore.com/?s=laptop"),
    ("Click2Nepal", "https://click2nepal.com/?s=laptop"),
    ("Techsathi",   "https://www.techsathi.com/price-in-nepal?q=laptop"),
    ("SYS Tech",    "https://systech.com.np/?s=laptop"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    )
}

print(f"\n{'Site':<15} {'Status':>7}  {'Time':>6}  {'Size':>10}  Result")
print("─" * 65)

reachable = []
for name, url in SITES:
    t0 = time.time()
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        elapsed = time.time() - t0
        size    = len(r.content)
        status  = r.status_code
        note    = "✓ REACHABLE" if status == 200 else f"HTTP {status}"
        if status == 200:
            reachable.append((name, url, size))
    except requests.Timeout:
        elapsed, size, status, note = time.time()-t0, 0, 0, "✗ TIMEOUT"
    except requests.ConnectionError as e:
        elapsed, size, status, note = time.time()-t0, 0, 0, f"✗ CONN ERROR"
    except Exception as e:
        elapsed, size, status, note = time.time()-t0, 0, 0, f"✗ {e}"

    print(f"{name:<15} {status:>7}  {elapsed:>5.1f}s  {size:>10,}  {note}")

print("\n" + "─" * 65)
print(f"Reachable sites ({len(reachable)}):")
for name, url, size in reachable:
    print(f"  • {name:<15} {size:>10,} bytes  {url}")
