"""
hukut_scraper.py
----------------
Scraper for Hukut Nepal (hukut.com)
"""

import requests
import time
import logging
import re
import os
from typing import List, Optional
from bs4 import BeautifulSoup, Tag

from base_scraper import BaseScraper


# ── Category → Hukut department URL map ──────────────────────────
HUKUT_CATEGORY_URLS = {
    "laptop":     "/laptops",
    "notebook":   "/laptops",
    "macbook":    "/laptops",
    "phone":      "/mobiles",
    "mobile":     "/mobiles",
    "smartphone": "/mobiles",
    "iphone":     "/mobiles",
    "tablet":     "/tablets",
    "ipad":       "/tablets",
    "monitor":    "/monitors",
    "tv":         "/televisions",
    "television": "/televisions",
    "camera":     "/cameras",
    "dslr":       "/cameras",
    "printer":    "/printers",
    "router":     "/networking",
    "keyboard":   "/keyboards-mice",
    "mouse":      "/keyboards-mice",
    "mousepad":   "/keyboards-mice",
    "headphone":  "/headphones",
    "earphone":   "/headphones",
    "earbuds":    "/headphones",
    "speaker":    "/speakers",
    "smartwatch": "/smart-watches",
    "watch":      "/smart-watches",
    "powerbank":  "/power-banks",
    "power bank": "/power-banks",
    "ssd":        "/storage",
    "hdd":        "/storage",
    "pendrive":   "/storage",
    "ram":        "/ram",
}


class HukutScraper(BaseScraper):

    STORE_NAME = "Hukut"
    BASE_URL   = "https://www.hukut.com"
    SEARCH_URL = BASE_URL + "/search?q={q}"

    def __init__(self, driver=None):

        super().__init__(driver)

        self.logger = logging.getLogger(self.__class__.__name__)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        })

    # ────────────────────────────────────────────────────────────────────

    def _get_category_url(self, query: str) -> Optional[str]:
        """Return a Hukut category URL if the query matches a known category."""
        q = query.lower().strip()
        for keyword, path in HUKUT_CATEGORY_URLS.items():
            if keyword in q:
                return self.BASE_URL + path
        return None

    # ----------------------------------------------------

    def scrape_products(self, query: str) -> List[dict]:

        category_url = self._get_category_url(query)
        if category_url:
            base_url = category_url
            effective_query = query + " __category_page__"
            self.logger.info("Hukut: using category URL %s for query '%s'", base_url, query)
        else:
            base_url = self.SEARCH_URL.format(q=requests.utils.quote(query))
            effective_query = query
            self.logger.info("Hukut → %s", base_url)

        products = []
        seen_links = set()

        try:
            max_pages = int(os.environ.get("HUKUT_MAX_PAGES", "1"))
        except Exception:
            max_pages = 1

        for page in range(1, max_pages + 1):
            if page == 1:
                url = base_url
            else:
                sep = '&' if '?' in base_url else '?'
                url = f"{base_url}{sep}page={page}"

            try:
                r = self.session.get(url, timeout=15)
                r.raise_for_status()
                self.logger.debug(f"Fetched URL: {url}, status: {r.status_code}")
            except requests.RequestException as exc:
                self.logger.debug("Hukut: stop pagination at page %s (%s)", page, exc)
                break

            soup = BeautifulSoup(r.text, "html.parser")
            cards = self._find_cards(soup)
            self.logger.info("Hukut: page %d → %d cards", page, len(cards))
            
            # Debug: print first card HTML if no cards found
            if len(cards) == 0:
                self.logger.debug("No cards found. Page title: %s", soup.title.string if soup.title else "No title")
                # Save HTML for debugging
                with open(f"hukut_debug_page_{page}.html", "w", encoding="utf-8") as f:
                    f.write(r.text)
                self.logger.debug("Saved HTML to hukut_debug_page_%d.html", page)

            any_new = False
            for card in cards:
                name = self._get_name(card)
                price = self._get_price(card)
                link = self._get_link(card)
                image = self._get_image(card)

                self.logger.debug(f"Product: name='{name}', price={price}, link='{link}'")
                
                if not name or price is None or not link:
                    continue
                if link in seen_links:
                    continue

                seen_links.add(link)
                any_new = True

                product = self.format_product(name, price, link, image, effective_query)
                if product:
                    products.append(product)
                    product['query'] = query
                    self.logger.debug(f"Added product: {product['name']}")
                else:
                    self.logger.debug(f"Filtered out by format_product: {name}")

                if len(products) >= 10:
                    break

            if not any_new:
                break
            if len(products) >= 10:
                break

            time.sleep(0.6)

        # Retry with search if category page returned nothing
        if not products and category_url:
            self.logger.info("Hukut: category URL returned nothing, retrying with search")
            fallback_url = self.SEARCH_URL.format(q=requests.utils.quote(query))
            try:
                r = self.session.get(fallback_url, timeout=15)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                cards = self._find_cards(soup)
                for card in cards:
                    name = self._get_name(card)
                    price = self._get_price(card)
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
            except Exception as exc:
                self.logger.warning("Hukut: fallback search also failed: %s", exc)

        self.logger.info("Hukut: %d valid products gathered", len(products))
        return products

    # ----------------------------------------------------

    def _find_cards(self, soup: BeautifulSoup) -> List:

        # First try the specific class combination
        cards = []
        for el in soup.find_all("div", class_=True):
            classes = el.get("class", [])
            if all(c in classes for c in ["group", "relative", "bg-white", "flex-col"]):
                cards.append(el)
        
        if cards:
            return cards[:100]
        
        # Fallback: look for any element containing image + price + link
        price_patterns = [
            r"Rs\.?\s*[\d,]+",
            r"NPR\s*[\d,]+",
            r"रु\s*[\d,]+",
            r"Rs\s*[\d,]+",
        ]
        price_regex = re.compile("|".join(price_patterns), re.IGNORECASE)
        
        candidate_cards = []
        
        for div in soup.find_all("div", recursive=True):
            classes = div.get("class", [])
            class_str = " ".join(classes) if classes else ""
            
            # Skip nav/header/footer
            if any(x in class_str.lower() for x in ["nav", "header", "footer", "menu"]):
                continue
            
            # Need image
            img = div.find("img")
            if not img:
                continue
            
            # Need price text
            text = div.get_text()
            if not price_regex.search(text):
                continue
            
            # Need link
            link = div.find("a", href=True)
            if not link:
                continue
            
            candidate_cards.append(div)
        
        if candidate_cards:
            self.logger.info("Hukut: found %d fallback cards", len(candidate_cards))
            return candidate_cards
        
        # Final fallback: any element with product-like structure
        for el in soup.find_all(["div", "li", "article"]):
            if el.find("img") and el.find("a", href=True):
                classes = el.get("class", [])
                class_str = " ".join(classes) if classes else ""
                # Skip generic layout elements
                if "container" in class_str or "wrapper" in class_str:
                    continue
                if el.find(text=price_regex):
                    candidate_cards.append(el)
        
        return candidate_cards

    # ----------------------------------------------------

    def _get_name(self, card: Tag) -> Optional[str]:

        # Try anchor with title
        a = card.find("a", href=True)
        if a:
            text = a.get_text(" ", strip=True)
            if text and len(text) > 3:
                # Remove price if present
                text = re.sub(r"Rs\.?\s*[\d,]+.*", "", text)
                text = text.strip()
                if text:
                    return text[:200]
        
        # Try heading elements
        for tag in ["h2", "h3", "h4"]:
            el = card.select_one(tag)
            if el:
                text = el.get_text(strip=True)
                if text and len(text) > 3:
                    return text[:200]
        
        # Try product name class patterns
        for cls in ["product-name", "productTitle", "item-title"]:
            el = card.select_one(f".{cls}")
            if el:
                text = el.get_text(strip=True)
                if text:
                    return text[:200]
        
        # Get first substantial text
        for el in card.find_all(["span", "div", "p"]):
            text = el.get_text(strip=True)
            if text and len(text) > 10 and len(text) < 200:
                # Skip if it looks like just a price
                if not re.match(r"^[\s\d,NRs.]+$", text):
                    return text[:200]
        
        return None

    # ----------------------------------------------------

    def _get_price(self, card: Tag) -> Optional[int]:
        
        def _pick_real_price(prices: list) -> Optional[int]:
            """
            Given a sorted list of price candidates, pick the real current price.
            Filters out values that look like discount amounts (< 15% of the max).
            """
            if not prices:
                return None
            if len(prices) == 1:
                return prices[0]
            
            max_p = max(prices)
            # Filter out anything that's less than 15% of the max price —
            # those are discount amounts / savings, not actual prices
            real_candidates = [p for p in prices if p >= max_p * 0.15]
            
            if not real_candidates:
                return min(prices)  # fallback if filter too aggressive
            
            return min(real_candidates)  # smallest of the real prices = sale price

        # More robust per-element scanning to avoid accidental concatenation
        candidates = []  # (int_value, element, raw_text)

        patterns = [
            r"Rs\.?\s*([\d,]+)",
            r"NPR\s*([\d,]+)",
            r"रु\s*([\d,]+)",
            r"Rs\s*([\d,]+)",
        ]

        # Words that indicate discount/savings amounts (should be excluded)
        exclude_words = ['save', 'saved', 'saving', 'discount', 'you save', 'you pay', 'offer']
        
        # Scan likely small text elements for explicit price mentions
        for el in card.find_all(['span', 'div', 'p', 'strong', 'b', 'ins', 'em', 'a', 'li', 'del']):
            text = el.get_text(strip=True)
            if not text:
                continue
            
            # Skip if this element contains discount/savings keywords
            text_lower = text.lower()
            if any(exclude_word in text_lower for exclude_word in exclude_words):
                continue
            
            for pattern in patterns:
                for m in re.finditer(pattern, text, re.IGNORECASE):
                    num = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
                    digits = re.sub(r"[^\d]", "", num)
                    if not digits:
                        continue
                    try:
                        val = int(digits)
                    except ValueError:
                        continue
                    candidates.append((val, el, text))

        if not candidates:
            # Final fallback: search entire card text, but exclude discount amounts
            text = card.get_text()
            
            # Check if the entire text contains discount keywords, if so, try to find actual price
            if any(exclude_word in text.lower() for exclude_word in exclude_words):
                # Try to find price that's not part of "Save Rs. X" pattern
                for pattern in patterns:
                    # Find all price matches
                    matches = list(re.finditer(pattern, text, re.IGNORECASE))
                    for match in matches:
                        price_str = match.group(1).replace(",", "")
                        try:
                            price_val = int(price_str)
                            # Check if this price is preceded by "save" or "discount"
                            start_pos = match.start()
                            context = text[max(0, start_pos-20):start_pos].lower()
                            if not any(exclude_word in context for exclude_word in exclude_words):
                                return price_val
                        except ValueError:
                            continue
                return None
            
            # Normal fallback without discount keywords
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    price_str = match.group(1).replace(",", "")
                    try:
                        return int(price_str)
                    except ValueError:
                        continue
            return None

        # Filter out candidates that come from elements with discount keywords in siblings/parent
        filtered_candidates = []
        for val, el, text in candidates:
            # Check the element's text again for discount keywords
            text_lower = text.lower()
            if any(exclude_word in text_lower for exclude_word in exclude_words):
                continue
            
            # Check parent and sibling texts
            parent = el.parent
            if parent:
                parent_text = parent.get_text(strip=True).lower()
                if any(exclude_word in parent_text for exclude_word in exclude_words):
                    # But only skip if the discount amount matches this price
                    # For example, "Save Rs. 6001" - we want to skip 6001 but not 52999
                    discount_pattern = r'save\s+rs\.?\s*(\d[\d,]*)'
                    discount_match = re.search(discount_pattern, parent_text, re.IGNORECASE)
                    if discount_match:
                        discount_amount = int(re.sub(r"[^\d]", "", discount_match.group(1)))
                        if val == discount_amount:
                            continue
            
            filtered_candidates.append((val, el, text))

        if not filtered_candidates:
            return None

        # IMPORTANT: Look for discounted/sale price indicators first
        sale_indicators = ['ins', 'span.sale-price', 'span.special-price', 'span.current-price', 'span.price']
        
        sale_candidates = []
        for val, el, text in filtered_candidates:
            # Check if element is a <ins> tag (typically shows current price)
            if el.name == 'ins':
                sale_candidates.append((val, el, text))
                continue
            
            # Check class names for sale indicators
            classes = ' '.join(el.get('class', [])).lower()
            if any(indicator in classes for indicator in ['sale', 'special', 'current', 'price']):
                # But exclude if it has 'old' or 'original' in class
                if not any(exclude in classes for exclude in ['old', 'original']):
                    sale_candidates.append((val, el, text))
                    continue
            
            # Check if element is inside a sale-price container
            parent = el.parent
            if parent:
                parent_classes = ' '.join(parent.get('class', [])).lower()
                if any(indicator in parent_classes for indicator in ['sale', 'special', 'current']):
                    sale_candidates.append((val, el, text))

        # If we found sale/discounted prices, use the smallest one (most discounted)
        if sale_candidates:
            # Get unique values to avoid duplicates
            unique_prices = list(set([c[0] for c in sale_candidates]))
            chosen_price = min(unique_prices)  # Take the smallest for discounted price
            try:
                self.logger.debug(f"Hukut sale candidates found: {unique_prices}")
                self.logger.debug(f"Hukut chosen sale price: {chosen_price}")
            except Exception:
                pass
            return chosen_price

        # Check for elements that might be original/strikethrough prices to exclude them
        original_indicators = ['del', 'strike', 'original', 'old-price']
        original_prices = []
        current_candidates = []

        for val, el, text in filtered_candidates:
            # Check if it's a strikethrough element (original price)
            if el.name == 'del':
                original_prices.append(val)
                continue
            
            # Check class for original price indicators
            classes = ' '.join(el.get('class', [])).lower()
            if any(indicator in classes for indicator in original_indicators):
                original_prices.append(val)
                continue
            
            # Otherwise it's a candidate for current price
            current_candidates.append((val, el, text))

        # If we have current candidates, use the smallest one (most discounted)
        if current_candidates:
            current_prices = list(set([c[0] for c in current_candidates]))
            
            if original_prices:
                filtered_prices = [p for p in current_prices if p not in original_prices]
                if filtered_prices:
                    # ── FIXED: pick smallest non-original price (actual sale price) ──
                    # But sanity check: if smallest is < 10% of largest, it's probably
                    # a discount amount, not the real price — use second smallest instead
                    filtered_prices.sort()
                    chosen_price = _pick_real_price(filtered_prices)
                    self.logger.debug(f"Hukut price after filtering original: {chosen_price}")
                    return chosen_price
            
            current_prices.sort()
            chosen_price = _pick_real_price(current_prices)
            self.logger.debug(f"Hukut chosen current price: {chosen_price}")
            return chosen_price

        # Fallback: all candidates
        all_prices = sorted(set([c[0] for c in filtered_candidates]))
        chosen_price = _pick_real_price(all_prices)
        self.logger.debug(f"Hukut chosen price (fallback): {chosen_price}")
        return chosen_price

    # ----------------------------------------------------

    def _get_link(self, card: Tag) -> Optional[str]:

        a = card.find("a", href=True)

        if not a:
            return None

        href = a.get("href", "").strip()

        if not href:
            return None
            
        if href.startswith("http"):
            return href

        if href.startswith("//"):
            return "https:" + href

        return self.BASE_URL + href

    # ----------------------------------------------------

    def _get_image(self, card: Tag) -> Optional[str]:

        img = card.find("img")

        if not img:
            return None

        # Try multiple attributes
        for attr in ["src", "data-src", "data-lazy", "data-original", "data-image"]:
            src = img.get(attr)
            if src and not src.startswith("data:"):
                if src.startswith("//"):
                    return "https:" + src
                elif src.startswith("/"):
                    return self.BASE_URL + src
                elif src.startswith("http"):
                    return src
        
        # Try style attribute
        style = img.get("style", "")
        bg_match = re.search(r'url\(["\']?([^"\')]+)["\']?\)', style)
        if bg_match:
            src = bg_match.group(1)
            if src.startswith("//"):
                return "https:" + src
            elif src.startswith("http"):
                return src
        
        return None