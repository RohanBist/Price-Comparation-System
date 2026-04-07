"""
daraz_scraper.py
----------------
Scraper for Daraz Nepal (daraz.com.np)
"""

import time
import re
import os
import json
import hashlib
import urllib.parse
import requests
from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

from base_scraper import BaseScraper


# ── Daraz price extraction constants ──────────────────────────────────────────

MIN_PRICE = 200        # Lowered from 2000 to catch cheaper items
MAX_PRICE = 500_000

_CURRENCY_PREFIX = r"(?:Rs\.?|NPR|रु)\s*"
_PRICE_NUMBER    = r"([\d]{1,3}(?:,[\d]{3})*|[\d]+)"

PRICE_RE = re.compile(
    r"(?<!\d)" + _CURRENCY_PREFIX + _PRICE_NUMBER + r"(?![\d,])",
    re.IGNORECASE,
)

# Patterns to identify non-price numbers (review counts, ratings, etc.)
_REVIEW_PATTERNS = [
    re.compile(r"\(\s*\d+\s*reviews?\)", re.I),
    re.compile(r"\b\d+\s*reviews?\b", re.I),
    re.compile(r"\b\d+\s*ratings?\b", re.I),
    re.compile(r"\b\d+\s*sold\b", re.I),
    re.compile(r"rated\s*\d+", re.I),
]

# Numbers that are likely NOT prices (review counts, ratings, etc.)
SMALL_NUMBER_THRESHOLD = 50  # keyboards/mice can be Rs. 200-500, don't skip them

# Price class tokens
_PRICE_CLASS_TOKENS    = {"price", "prc", "sale", "offer", "amount", "cost", "final", "current"}
_OLD_PRICE_CLASS_TOKENS = {"original", "old", "was", "mrp", "market", "del", "strike", "through", "crossed"}

# EMI detection tokens
_EMI_CLASS_TOKENS = {"emi", "installment", "instalment", "monthly", "month",
                     "per-month", "permonth", "easy-pay", "easypay", "flexi"}
_EMI_TEXT_TOKENS  = {"/month", "/mo", "per month", "/pm", "emi", "installment",
                     "instalment", "monthly payment", "easy monthly"}


class DarazScraper(BaseScraper):

    STORE_NAME = "Daraz"
    BASE_URL   = "https://www.daraz.com.np"
    SEARCH_URL = BASE_URL + "/catalog/?q={q}"

    def scrape_products(self, query: str) -> List[dict]:
        # Simple on-disk cache to speed up repeated queries.
        cache_ttl = int(os.environ.get("DARAZ_CACHE_TTL", "300"))
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "scraper_cache")
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            pass

        key = hashlib.sha1(query.encode("utf-8")).hexdigest()
        cache_path = os.path.join(cache_dir, f"daraz_search_{key}.json")
        try:
            if os.path.exists(cache_path):
                mtime = os.path.getmtime(cache_path)
                if (time.time() - mtime) < cache_ttl:
                    with open(cache_path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        self.logger.debug("Daraz: returning %d cached products for query '%s'", len(data), query)
                        return data
        except Exception:
            pass

        q = urllib.parse.quote_plus(query)
        url = self.SEARCH_URL.format(q=q)
        self.logger.info("Daraz → %s", url)

        # Try HTTP first for speed
        try:
            http_first = os.environ.get("DARAZ_HTTP_FIRST", "1")
            if http_first and http_first != "0":
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                }
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code == 200 and resp.text:
                    try:
                        products = self._extract_products_from_html(resp.text, query)
                        if products:
                            self.logger.info("Daraz HTTP extractor: found %d products", len(products))
                            try:
                                with open(cache_path, "w", encoding="utf-8") as fh:
                                    json.dump(products, fh, ensure_ascii=False)
                            except Exception:
                                pass
                            return products
                    except Exception:
                        self.logger.debug("Daraz HTTP extractor failed, falling back to Selenium", exc_info=True)
        except Exception:
            pass

        # Use Selenium as fallback
        try:
            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Small delay for JavaScript rendering
            time.sleep(2)

            # Scroll to load more products
            for i in range(3):
                self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
                time.sleep(1)

        except TimeoutException:
            self.logger.warning("Daraz: timeout waiting for page load")
            return []
        except Exception as exc:
            self.logger.error("Daraz page error: %s", exc)
            return []

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        cards = self._find_product_cards(soup)

        self.logger.info("Daraz: found %d potential cards", len(cards))

        products: List[dict] = []
        seen_links = set()

        for card in cards:
            name = self._get_name(card)
            price = self._get_price(card)  # Using improved _get_price
            link = self._get_link(card)
            image = self._get_image(card)

            if not name or price is None or not link:
                continue

            if link in seen_links:
                continue

            seen_links.add(link)

            product = self.format_product(name, price, link, image, query)

            if product:
                products.append(product)

            if len(products) >= 10:
                break

        self.logger.info("Daraz: %d valid products", len(products))

        # Save to cache
        try:
            with open(cache_path, "w", encoding="utf-8") as fh:
                json.dump(products, fh, ensure_ascii=False)
        except Exception:
            pass

        return products

    def _find_product_cards(self, soup: BeautifulSoup) -> List:
        """Find product cards using multiple strategies"""
        cards = []
        
        # Strategy 1: Look for elements with data attributes
        cards = soup.select("[data-product-id], [data-item-id], [data-sku-simple]")
        if cards:
            self.logger.info("Found %d cards with data attributes", len(cards))
            return cards[:100]

        # Strategy 2: Look for common product card classes
        card_selectors = [
            ".product-card",
            ".item",
            ".product-item",
            ".pdp-product-card",
            "[class*='product-card']",
            "[class*='product-item']",
            "[class*='grid-item']",
            ".c1-box",
            ".c2-box",
        ]
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                self.logger.info("Found %d cards with selector: %s", len(cards), selector)
                return cards[:100]

        # Strategy 3: Look for elements with price text
        price_pattern = re.compile(r"Rs\.?\s*[\d,]+", re.I)
        for element in soup.find_all(["div", "li", "article"]):
            # Skip navigation elements
            classes = element.get("class", [])
            class_str = " ".join(classes) if classes else ""
            if any(x in class_str.lower() for x in ["nav", "header", "footer", "menu"]):
                continue
            
            # Check for image
            img = element.find("img")
            if not img:
                continue
            
            # Check for price
            text = element.get_text()
            if not price_pattern.search(text):
                continue
            
            # Check for link
            link = element.find("a", href=True)
            if not link:
                continue
            
            cards.append(element)
        
        if cards:
            self.logger.info("Found %d cards with image+price+link", len(cards))
            return cards[:100]

        return []

    def _get_price(self, card) -> Optional[int]:
        """
        Extract price from product card with improved filtering of non-price numbers.
        """
        
        def is_review_or_rating(text: str) -> bool:
            """Check if text is likely a review count or rating"""
            # Check for review patterns
            for pattern in _REVIEW_PATTERNS:
                if pattern.search(text):
                    return True
            
            # Check if it's a small number that might be a rating
            numbers = re.findall(r'\b\d+\b', text)
            for num in numbers:
                val = int(num)
                if val < SMALL_NUMBER_THRESHOLD:
                    # Check if it appears with rating-related words
                    if any(word in text.lower() for word in ['star', 'rating', 'review', 'rate']):
                        return True
            
            return False
        
        def is_emi_payment(text: str) -> bool:
            """Check if text is an EMI payment amount"""
            text_lower = text.lower()
            if any(token in text_lower for token in _EMI_TEXT_TOKENS):
                return True
            # Check for patterns like "Rs. 500/month"
            if re.search(r'Rs\.?\s*\d+\s*/\s*month', text_lower):
                return True
            return False
        
        def is_old_price_element(el) -> bool:
            """Check if element contains old/original price"""
            current = el
            for _ in range(4):
                if current is None or current.name in (None, "[document]"):
                    break
                if current.name in ("del", "s", "strike"):
                    return True
                cls = " ".join(current.get("class") or []).lower()
                if any(tok in cls for tok in _OLD_PRICE_CLASS_TOKENS):
                    return True
                current = getattr(current, "parent", None)
            return False
        
        def get_element_score(el) -> int:
            """Score element based on how likely it contains the actual price"""
            score = 0
            cls = " ".join(el.get("class") or []).lower()
            
            # High score for price-related classes
            if any(tok in cls for tok in _PRICE_CLASS_TOKENS):
                score += 100
            
            # Penalize old price classes
            if any(tok in cls for tok in _OLD_PRICE_CLASS_TOKENS):
                score -= 80
            
            # Penalize EMI classes
            if any(tok in cls for tok in _EMI_CLASS_TOKENS):
                score -= 150
            
            # ── NEW: Penalize discount/savings indicators ──────────────────
            _DISCOUNT_TOKENS = {"save", "saving", "savings", "discount", "off",
                                "you save", "cashback", "voucher"}
            if any(tok in cls for tok in _DISCOUNT_TOKENS):
                score -= 200
            
            # Boost for specific tags
            if el.name in ("ins", "strong", "b"):
                score += 30
            
            # ── NEW: Check parent element classes too ──────────────────────
            parent = getattr(el, "parent", None)
            if parent:
                parent_cls = " ".join(parent.get("class") or []).lower()
                if any(tok in parent_cls for tok in _PRICE_CLASS_TOKENS):
                    score += 50
                if any(tok in parent_cls for tok in _OLD_PRICE_CLASS_TOKENS):
                    score -= 60
                if any(tok in parent_cls for tok in _DISCOUNT_TOKENS):
                    score -= 200
            
            return score
        
        # Collect all price candidates
        candidates = []
        
        # Scan all elements that might contain prices
        for el in card.find_all(["span", "div", "p", "strong", "b", "ins", "em", "a", "li"]):
            text = el.get_text(" ", strip=True)
            # Collapse multiple spaces
            text = re.sub(r'\s+', ' ', text).strip()
            if not text:
                continue
            
            # Skip if it looks like a review or rating
            if is_review_or_rating(text):
                self.logger.debug(f"Daraz: skipping review/rating: {text}")
                continue
            
            # Skip if it's EMI payment
            if is_emi_payment(text):
                self.logger.debug(f"Daraz: skipping EMI payment: {text}")
                continue
            
            # Skip old price elements
            if is_old_price_element(el):
                self.logger.debug(f"Daraz: skipping old price element: {text}")
                continue
            
            # ── NEW: Skip elements whose text contains discount/savings language ──
            _DISCOUNT_TEXT_PATTERNS = [
                re.compile(r'\bsave\b', re.I),
                re.compile(r'\bsaving\b', re.I),
                re.compile(r'\bdiscount\b', re.I),
                re.compile(r'\bcashback\b', re.I),
                re.compile(r'you\s+save', re.I),
                re.compile(r'-\s*\d+\s*%'),        # "-8%" pattern
                re.compile(r'\d+\s*%\s*off', re.I),
            ]
            if any(p.search(text) for p in _DISCOUNT_TEXT_PATTERNS):
                self.logger.debug(f"Daraz: skipping discount element: {text}")
                continue
            
            # Find all price patterns in this element
            for match in PRICE_RE.finditer(text):
                price_str = match.group(1).replace(",", "")
                try:
                    price_val = int(price_str)
                    
                    # Filter out obviously wrong prices
                    if price_val < MIN_PRICE or price_val > MAX_PRICE:
                        self.logger.debug(f"Daraz: out-of-range candidate {price_val} — skipped")
                        continue
                    
                    score = get_element_score(el)
                    candidates.append((score, price_val, text))
                    
                except ValueError:
                    continue
        
        if candidates:
            # Sort by score desc, then price desc (highest price on tie = most likely real price)
            candidates.sort(key=lambda x: (-x[0], -x[1]))
            
            best_score, best_price, best_text = candidates[0]
            
            # ── NEW: Sanity check — if best price looks like a discount amount ──
            # If there's another candidate with score >= best and price > 10x best,
            # the "best" is likely a savings amount, not the real price
            for score, price, text in candidates[1:]:
                if score >= best_score - 30 and price > best_price * 5:
                    self.logger.debug(
                        f"Daraz: overriding suspicious low price {best_price} "
                        f"with {price} (score diff: {best_score - score})"
                    )
                    best_price = price
                    best_text = text
                    break
            
            self.logger.debug(f"Daraz: selected price {best_price} (score={best_score}) from: {best_text[:100]}")
            return best_price
        
        # Fallback: search entire card text but require currency symbol
        card_text = card.get_text(" ", strip=True)  # use space separator to prevent concatenation
        
        # Remove review/rating patterns first
        for pattern in _REVIEW_PATTERNS:
            card_text = pattern.sub(" ", card_text)
        
        # Only match prices WITH explicit currency prefix in fallback
        fallback_re = re.compile(
            r"(?:Rs\.?|NPR|रु)\s*([\d]{1,3}(?:,[\d]{3})*|[\d]+)(?![\d,])",
            re.IGNORECASE
        )
        
        fallback_prices = []
        for match in fallback_re.finditer(card_text):
            price_str = match.group(1).replace(",", "")
            try:
                price_val = int(price_str)
                if MIN_PRICE <= price_val <= MAX_PRICE:
                    # Check context to avoid EMI
                    context = card_text[max(0, match.start()-30):match.end()+30]
                    if not is_emi_payment(context):
                        fallback_prices.append(price_val)
            except ValueError:
                continue
        
        if fallback_prices:
            # Pick the LOWEST valid price (most likely the sale/current price)
            best_price = min(fallback_prices)
            self.logger.debug(f"Daraz: fallback selected {best_price}")
            return best_price
        
        self.logger.warning("Daraz: could not extract any price from card")
        return None

    def _get_name(self, card) -> Optional[str]:
        """Extract product name"""
        # Try title attribute
        a = card.select_one("a[title]")
        if a:
            title = a.get("title", "").strip()
            if title and len(title) > 3:
                return title[:200]
        
        # Try anchor text
        a = card.select_one("a")
        if a:
            text = a.get_text(" ", strip=True)
            # Collapse multiple spaces
            text = re.sub(r'\s+', ' ', text).strip()
            if text and len(text) > 5:
                # Remove price text if present
                text = re.sub(r"Rs\.?\s*[\d,]+.*", "", text)
                text = text.strip()
                if text:
                    return text[:200]
        
        # Try heading elements
        for tag in ["h2", "h3", "h4", "h5"]:
            el = card.select_one(tag)
            if el:
                text = el.get_text(" ", strip=True)
                # Collapse multiple spaces
                text = re.sub(r'\s+', ' ', text).strip()
                if text and len(text) > 3:
                    return text[:200]
        
        return None

    def _get_link(self, card) -> Optional[str]:
        """Extract product link"""
        a = card.select_one("a[href]")
        if not a:
            return None
        
        href = a.get("href", "").strip()
        if not href:
            return None
            
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/"):
            return self.BASE_URL + href
        
        return self.BASE_URL + "/" + href
    
    def _get_image(self, card) -> Optional[str]:
        """Extract product image"""
        img = card.select_one("img")
        if not img:
            return None
        
        for attr in ["src", "data-src", "data-lazy", "data-original", "data-uri"]:
            src = img.get(attr)
            if src and not src.startswith("data:"):
                if src.startswith("//"):
                    return "https:" + src
                elif src.startswith("/"):
                    return self.BASE_URL + src
                elif src.startswith("http"):
                    return src
        
        return None

    def _extract_products_from_html(self, html: str, query: str) -> List[dict]:
        """Extract products from HTML (simplified version)"""
        products = []
        soup = BeautifulSoup(html, "html.parser")
        
        # Look for product items
        for item in soup.find_all("div", class_=re.compile(r"product|item", re.I)):
            name_elem = item.find(class_=re.compile(r"title|name", re.I))
            if not name_elem:
                continue
            
            name = name_elem.get_text(" ", strip=True)
            name = re.sub(r'\s+', ' ', name).strip()
            if not name:
                continue
            
            # Try to get price
            price_elem = item.find(class_=re.compile(r"price", re.I))
            if price_elem:
                price_text = price_elem.get_text(" ", strip=True)
                price_text = re.sub(r'\s+', ' ', price_text).strip()
                price_match = PRICE_RE.search(price_text)
                if price_match:
                    price_str = price_match.group(1).replace(",", "")
                    try:
                        price = int(price_str)
                        if MIN_PRICE <= price <= MAX_PRICE:
                            # Get link
                            link_elem = item.find("a", href=True)
                            link = link_elem.get("href") if link_elem else None
                            if link:
                                if link.startswith("/"):
                                    link = self.BASE_URL + link
                                
                                products.append(self.format_product(name, price, link, None, query))
                    except ValueError:
                        continue
        
        return products[:10]