import re
import logging
from typing import Optional, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def build_driver() -> webdriver.Chrome:

    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")

    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
            """
        }
    )

    return driver


class BaseScraper:

    STORE_NAME: str = "Unknown Store"

    def __init__(self, driver=None):

        self.driver = driver
        self.logger = logging.getLogger(self.__class__.__name__)

    # --------------------------------------------

    def clean_price(self, raw: str) -> Optional[int]:

        if not raw:
            return None

        text = str(raw)

        # Find the first continuous group of digits (with optional commas)
        m = re.search(r"(\d[\d,]*)", text)
        if not m:
            self.logger.warning("Could not parse price: %s", raw)
            return None

        num = m.group(1).replace(",", "")
        try:
            return int(num)
        except ValueError:
            self.logger.warning("Could not parse price after cleanup: %s", num)
            return None

    # --------------------------------------------

    def format_product(self, name, price, link, image=None, query=None):
        if not name or price is None or not link:
            return None

        name_lower = name.lower()
        query_lower = query.lower().strip() if query else ""

        # ── Category page flag — detect and strip BEFORE building tokens ──
        is_category_page = "__category_page__" in query_lower
        if is_category_page:
            query_lower = query_lower.replace("__category_page__", "").strip()

        # ── Query tokens (words ≥ 3 chars) ──────────────────────────────
        query_tokens = [t for t in re.split(r"\W+", query_lower) if len(t) >= 3]

        # ── FIX: On category pages, skip ALL filtering except hard-ban ──
        if is_category_page:
            always_ban = {
                "laptop": [
                    "laptop bag", "laptop stand", "laptop sleeve", "laptop case",
                    "laptop cover", "laptop cooling", "laptop cooler",
                    "laptop keyboard cover", "laptop adapter", "laptop hub",
                    "laptop charger", "laptop cable", "laptop dock",
                ],
                "phone": [
                    "phone case", "phone cover", "phone stand",
                    "phone holder", "phone charger",
                ],
            }
            
            category = None
            if any(w in query_lower for w in ["laptop", "notebook", "macbook"]):
                category = "laptop"
            elif any(w in query_lower for w in ["phone", "mobile", "iphone", "redmi",
                                                 "samsung", "xiaomi", "realme", "oppo",
                                                 "vivo", "oneplus", "smartphone"]):
                category = "phone"
            
            if category:
                for phrase in always_ban.get(category, []):
                    if phrase in name_lower:
                        self.logger.debug(f"Hard-banned accessory phrase on category page: {name}")
                        return None
            
            self.logger.debug(f"Category page: accepting product: {name}")
            return {
                "name": name.strip(),
                "price": price,
                "store": self.STORE_NAME,
                "link": link.strip(),
                "image": image
            }

        # ── CRITICAL FIX: First, detect if this product is an ACCESSORY ──
        # Comprehensive list of accessory indicators (words that clearly indicate an accessory)
        HARD_ACCESSORY_INDICATORS = [
            # Cases and covers
            "case", "cover", "back cover", "flip cover", "backcase", "bumper", 
            "frame", "pouch", "skin", "wrap", "shell", "wallet", "folio",
            # Screen protection (IMPORTANT for your example)
            "protector", "tempered", "screen guard", "screen protector", "glass protector",
            "hydrogel", "uv glass", "curved glass", "membrane", "privacy", 
            "full glue", "uv light", "tempered glass", "screen film", "anti spy",
            # Charging accessories
            "charger", "adapter", "cable", "charging cable", "data cable", "fast charger",
            "car charger", "wireless charger", "charging pad", "charging dock",
            # Stands and holders
            "stand", "holder", "mount", "grip", "pop socket", "phone ring", "kickstand",
            # Audio accessories
            "earbuds", "headphones", "headset", "earphones", "airpods", "bluetooth headset",
            # Other accessories
            "power bank", "battery case", "lens", "tripod", "selfie stick",
            # Material indicators (often accessories)
            "silicone", "tpu", "pc", "polycarbonate", "leather", "fabric", "carbon fiber",
        ]
        
        # Accessory patterns (if these appear, it's almost certainly an accessory)
        accessory_patterns = [
            r"case\s+for", r"cover\s+for", r"protector\s+for", r"for\s+\w+\s+\w+\s*case",
            r"back\s+cover", r"flip\s+cover", r"tempered\s+glass", r"screen\s+protector",
            r"charging\s+cable", r"fast\s+charger", r"phone\s+stand", r"phone\s+holder",
            r"hydrogel", r"uv\s+glass", r"curved\s+glass", r"full\s+glue", r"privacy\s+film",
            r"screen\s+film", r"membrane", r"unbreakable", r"shockproof", r"military\s+grade",
            r"with\s+uv\s+light", r"glass\s+screen", r"liquid\s+glass", r"nano\s+glass",
        ]
        
        # Check if this is an accessory product
        is_definitely_accessory = False
        
        # Check HARD accessory indicators
        for indicator in HARD_ACCESSORY_INDICATORS:
            if indicator in name_lower:
                is_definitely_accessory = True
                self.logger.debug(f"Found accessory indicator '{indicator}' in: {name}")
                break
        
        # Check accessory patterns
        if not is_definitely_accessory:
            for pattern in accessory_patterns:
                if re.search(pattern, name_lower):
                    is_definitely_accessory = True
                    self.logger.debug(f"Found accessory pattern '{pattern}' in: {name}")
                    break
        
        # Special check for products that list multiple phone models (like "for Infinix Hot 60 / Hot 60i / Hot 60 Pro")
        # This is a clear indicator of a universal accessory that fits multiple phones
        if not is_definitely_accessory:
            # Count how many phone models are listed in the name
            phone_models = re.findall(r'\b(?:hot|note|redmi|galaxy|poco|k|pro|ultra|max|plus|prime)\s*\d+[a-z]*\b', name_lower, re.I)
            if len(phone_models) >= 2:
                is_definitely_accessory = True
                self.logger.debug(f"Found multiple phone models in name: {name}")
        
        # Check for "for" pattern followed by a phone model
        if not is_definitely_accessory:
            for_pattern = re.search(r'\bfor\b.*\b(?:hot|note|redmi|galaxy|infinix|tecno|samsung|xiaomi|realme|oppo|vivo|oneplus)\b', name_lower)
            if for_pattern:
                is_definitely_accessory = True
                self.logger.debug(f"Found 'for' with phone brand: {name}")

        # ── Category detection from query ────────────────────────────────
        category = None
        if any(w in query_lower for w in ["laptop", "notebook", "macbook"]):
            category = "laptop"
        elif any(w in query_lower for w in ["phone", "mobile", "iphone", "redmi",
                                             "samsung", "xiaomi", "realme", "oppo",
                                             "vivo", "oneplus", "smartphone", "infinix",
                                             "tecno", "poco", "iqoo"]):
            category = "phone"
        elif any(w in query_lower for w in ["tablet", "ipad"]):
            category = "tablet"
        elif any(w in query_lower for w in ["camera", "dslr", "mirrorless"]):
            category = "camera"
        elif any(w in query_lower for w in ["tv", "television", "smart tv"]):
            category = "tv"
        
        # ── CRITICAL: Filter accessories based on category ──
        # If we're searching for a phone and this is clearly an accessory, REJECT it immediately
        if category == "phone" and is_definitely_accessory:
            self.logger.debug(f"Filtered phone accessory: {name}")
            return None
        
        if category == "laptop" and is_definitely_accessory:
            self.logger.debug(f"Filtered laptop accessory: {name}")
            return None

        # ── Accessory intent detection (for when user is searching for accessories) ──
        accessory_keywords = [
            "adapter", "charger", "cable", "case", "cover", "protector",
            "tempered", "keyboard", "mouse", "mousepad", "earbuds", "buds",
            "headphone", "headset", "watch", "band", "speaker", "cooler",
            "cooling", "ram", "ssd", "hdd", "hard drive", "dock", "hub",
            "stand", "bag", "sleeve", "tripod", "lens", "memory card",
            "screen protector", "power bank", "router", "wifi", "printer",
            "ink", "toner", "monitor", "webcam", "microphone",
            "back cover", "backcase", "flip cover", "pouch", "skin", "tempered glass",
            "screen guard", "charging cable", "data cable", "fast charger",
            "car charger", "wireless charger", "charging pad",
            "phone stand", "phone holder", "pop socket", "phone grip", "phone ring",
            "hydrogel", "uv glass", "curved glass", "full glue", "privacy", "membrane"
        ]
        is_accessory_search = any(word in query_lower for word in accessory_keywords)

        # ── If searching for an accessory, we're more lenient ──
        if is_accessory_search:
            if query_tokens and not any(tok in name_lower for tok in query_tokens):
                self.logger.debug(f"Filtered (no token match): {name}")
                return None
            return {
                "name": name.strip(),
                "price": price,
                "store": self.STORE_NAME,
                "link": link.strip(),
                "image": image
            }

        # ── Non-accessory searches: apply category filtering ─────────────
        category_accessories = {
            "laptop": [
                "case", "cover", "sleeve", "bag", "stand", "cooler",
                "cooling pad", "keyboard cover", "screen protector",
                "adapter", "charger", "cable", "dock", "hub",
                "thermal paste", "thermal pad", "skin", "sticker"
            ],
            "phone": [
                "case", "cover", "screen protector", "tempered glass",
                "charger", "cable", "adapter", "earbuds", "airpods",
                "watch", "band", "power bank", "back cover", "flip cover",
                "pouch", "skin", "screen guard", "data cable", "fast charger",
                "car charger", "wireless charger", "phone stand", "phone holder",
                "hydrogel", "uv glass", "curved glass", "full glue", "privacy",
                "membrane", "unbreakable", "shockproof"
            ],
            "tablet": [
                "case", "cover", "stylus", "keyboard case",
                "screen protector", "stand", "charger"
            ],
            "camera": [
                "bag", "tripod", "lens filter", "memory card",
                "battery", "cleaning kit", "strap"
            ],
            "tv": [
                "wall mount", "hdmi cable", "remote cover",
                "soundbar", "streaming stick"
            ]
        }

        if category:
            banned = category_accessories.get(category, [])

            primary_device_indicators = {
                "laptop": {
                    "brands": ["hp", "dell", "lenovo", "asus", "acer", "msi", "apple",
                               "macbook", "huawei", "lg", "toshiba", "samsung", "razer",
                               "microsoft", "surface", "gigabyte", "alienware"],
                    "model_patterns": [
                        r"\b(core\s*i[3579]|ryzen\s*[3579]|celeron|pentium|snapdragon)\b",
                        r"\b\d{2,3}[a-z]{0,2}\s*(inch|\")\b",
                        r"\b(intel|amd)\b",
                        r"\bgen\b",
                        r"\bssd\b.{0,20}\blaptop\b|\blaptop\b.{0,20}\bssd\b",
                    ]
                },
                "phone": {
                    "brands": ["apple", "samsung", "xiaomi", "redmi", "realme", "oppo",
                               "vivo", "oneplus", "huawei", "nokia", "motorola", "poco",
                               "iqoo", "infinix", "tecno"],
                    "model_patterns": [
                        r"\b\d+\s*(gb|tb)\b",
                        r"\b\d+mp\b",
                        r"\b5g\b",
                        r"\b(?:hot|note|redmi|galaxy|poco|k|pro|ultra|max|plus)\s*\d+\b",
                    ]
                },
                "tablet": {
                    "brands": ["apple", "samsung", "xiaomi", "lenovo", "huawei"],
                    "model_patterns": [r"\b\d+\s*(gb|tb)\b"]
                },
                "camera": {
                    "brands": ["canon", "nikon", "sony", "fujifilm", "panasonic",
                               "olympus", "leica", "gopro"],
                    "model_patterns": [r"\b\d+mp\b", r"\b4k\b"]
                },
                "tv": {
                    "brands": ["samsung", "lg", "sony", "tcl", "hisense", "xiaomi",
                               "panasonic", "philips"],
                    "model_patterns": [r"\b\d{2,3}\s*(inch|\")\b", r"\b4k\b", r"\boled\b"]
                },
            }

            indicators = primary_device_indicators.get(category, {})
            device_brands = indicators.get("brands", [])
            device_patterns = indicators.get("model_patterns", [])

            product_is_primary_device = (
                any(brand in name_lower for brand in device_brands) or
                any(re.search(pat, name_lower) for pat in device_patterns) or
                (
                    category == "laptop" and
                    any(word in name_lower for word in ["ryzen", "intel", "i3", "i5", "i7", "i9"]) and
                    any(word in name_lower for word in ["gb", "ssd", "ram"])
                )
            )

            always_ban = {
                "laptop": [
                    "laptop bag", "laptop stand", "laptop sleeve", "laptop case",
                    "laptop cover", "laptop cooling", "laptop cooler",
                    "laptop keyboard cover", "laptop adapter", "laptop hub",
                    "laptop charger", "laptop cable", "laptop dock",
                ],
                "phone": [
                    "phone case", "phone cover", "phone stand",
                    "phone holder", "phone charger", "back cover",
                    "flip cover", "screen protector", "tempered glass",
                ],
            }
            for phrase in always_ban.get(category, []):
                if phrase in name_lower:
                    self.logger.debug(f"Hard-banned accessory phrase: {name}")
                    return None

            # For phone category, if it's an accessory (even if not caught earlier), filter it
            if category == "phone":
                # Check against an extended accessory word list
                phone_accessory_words = [
                    "case", "cover", "protector", "tempered", "hydrogel", "membrane",
                    "screen guard", "glass", "film", "shield", "armor", "bumper",
                    "back cover", "flip cover", "pouch", "skin", "wrap"
                ]
                for word in phone_accessory_words:
                    if word in name_lower:
                        self.logger.debug(f"Filtered phone accessory (word match): {name}")
                        return None

            if not product_is_primary_device:
                for word in banned:
                    if word in name_lower:
                        self.logger.debug(f"Filtered category accessory: {name}")
                        return None

        # ── Relevance: at least one query token must appear in name ──────
        # But skip if it's an accessory (already filtered)
        if query_tokens and not is_definitely_accessory:
            if category == "phone":
                # Extract model numbers from query
                query_numbers = [t for t in query_tokens if t.isdigit()]
                query_brands = [t for t in query_tokens if t in ["infinix", "tecno", "samsung", "xiaomi", "redmi", "realme", "oppo", "vivo", "oneplus"]]
                query_model_words = [t for t in query_tokens if t not in query_numbers and t not in query_brands]
                
                has_brand = any(brand in name_lower for brand in query_brands) if query_brands else True
                has_model_number = any(num in name_lower for num in query_numbers) if query_numbers else False
                has_model_word = any(word in name_lower for word in query_model_words) if query_model_words else False
                
                # For a phone product, we need at least brand AND (model number OR model word)
                if not (has_brand and (has_model_number or has_model_word)):
                    self.logger.debug(f"Filtered (weak phone match): {name}")
                    return None
            else:
                if not any(tok in name_lower for tok in query_tokens):
                    self.logger.debug(f"Filtered (no token match): {name}")
                    return None

        return {
            "name": name.strip(),
            "price": price,
            "store": self.STORE_NAME,
            "link": link.strip(),
            "image": image
        }
    def scrape_products(self, query: str) -> List[dict]:

        raise NotImplementedError(
            f"{self.__class__.__name__} must implement scrape_products()"
        )