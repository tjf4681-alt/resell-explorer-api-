
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx, re, urllib.parse, asyncio, os
from bs4 import BeautifulSoup

app = FastAPI(title="Resell Explorer Live API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16; SM-F936N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

SITE_CONFIG = {
    "eBay": {
        "url": lambda q: "https://www.ebay.com/sch/i.html?_nkw=" + urllib.parse.quote(q) + "&_sop=15",
        "parser": "ebay",
    },
    "Amazon": {
        "url": lambda q: "https://www.amazon.com/s?k=" + urllib.parse.quote(q),
        "parser": "amazon",
    },
    "네이버쇼핑": {
        "url": lambda q: "https://search.shopping.naver.com/search/all?query=" + urllib.parse.quote(q),
        "parser": "generic",
    },
    "번개장터": {
        "url": lambda q: "https://m.bunjang.co.kr/search/products?q=" + urllib.parse.quote(q),
        "parser": "generic",
    },
    "중고나라": {
        "url": lambda q: "https://web.joongna.com/search/" + urllib.parse.quote(q),
        "parser": "generic",
    },
    "TCGplayer": {
        "url": lambda q: "https://www.tcgplayer.com/search/all/product?q=" + urllib.parse.quote(q) + "&view=grid",
        "parser": "generic",
    },
    "Mercari JP": {
        "url": lambda q: "https://jp.mercari.com/search?keyword=" + urllib.parse.quote(q),
        "parser": "generic",
    },
    "RockAuto": {
        "url": lambda q: "https://www.google.com/search?q=" + urllib.parse.quote("site:rockauto.com " + q),
        "parser": "google",
    },
    "Partsouq": {
        "url": lambda q: "https://www.google.com/search?q=" + urllib.parse.quote("site:partsouq.com " + q),
        "parser": "google",
    },
}

KRW_RATE = {
    "USD": float(os.getenv("USD_KRW", "1355.25")),
    "JPY": float(os.getenv("JPY_KRW", "8.65041")),
    "KRW": 1.0,
}

PRICE_PATTERNS = [
    ("KRW", re.compile(r"(?:₩|KRW\s*)\s*([\d,]+)")),
    ("USD", re.compile(r"(?:US\s*)?\$\s*([\d,]+(?:\.\d+)?)")),
    ("JPY", re.compile(r"¥\s*([\d,]+)")),
]

def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def parse_price_text(text):
    text = clean(text)
    for currency, pat in PRICE_PATTERNS:
        m = pat.search(text)
        if m:
            n = float(m.group(1).replace(",", ""))
            return currency, n, text
    return None, None, text

def to_krw(currency, value):
    if value is None or currency not in KRW_RATE:
        return None
    return int(round(value * KRW_RATE[currency]))

def parse_ebay(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for li in soup.select("li.s-item"):
        title_el = li.select_one(".s-item__title")
        price_el = li.select_one(".s-item__price")
        link_el = li.select_one("a.s-item__link")
        if not title_el or not link_el:
            continue
        title = clean(title_el.get_text(" ", strip=True))
        if not title or "Shop on eBay" in title:
            continue
        price_text = clean(price_el.get_text(" ", strip=True) if price_el else "")
        cur, val, raw = parse_price_text(price_text)
        out.append({
            "site": "eBay",
            "title": title,
            "price": raw or "가격 확인 필요",
            "priceKRW": to_krw(cur, val),
            "condition": clean((li.select_one(".SECONDARY_INFO") or {}).get_text(" ", strip=True) if li.select_one(".SECONDARY_INFO") else ""),
            "link": link_el.get("href", ""),
        })
        if len(out) >= 30:
            break
    return out

def parse_amazon(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in soup.select('[data-component-type="s-search-result"]'):
        title_el = card.select_one("h2 span")
        link_el = card.select_one("h2 a")
        if not title_el:
            continue
        title = clean(title_el.get_text(" ", strip=True))
        whole = card.select_one(".a-price-whole")
        frac = card.select_one(".a-price-fraction")
        price_text = ""
        if whole:
            price_text = "$" + clean(whole.get_text("", strip=True)).rstrip(".")
            if frac:
                price_text += "." + clean(frac.get_text("", strip=True))
        cur, val, raw = parse_price_text(price_text)
        out.append({
            "site": "Amazon",
            "title": title,
            "price": raw or "가격 확인 필요",
            "priceKRW": to_krw(cur, val),
            "condition": "New",
            "link": urllib.parse.urljoin("https://www.amazon.com", link_el.get("href", "")) if link_el else "",
        })
        if len(out) >= 30:
            break
    return out

def parse_generic(html, source, base_url):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()

    # JSON-LD products first
    for script in soup.select('script[type="application/ld+json"]'):
        txt = script.string or script.get_text()
        if not txt:
            continue
        try:
            import json
            data = json.loads(txt)
        except Exception:
            continue

        stack = data if isinstance(data, list) else [data]
        for obj in stack:
            if not isinstance(obj, dict):
                continue
            if obj.get("@type") != "Product":
                continue
            title = clean(obj.get("name", ""))
            offers = obj.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            p = offers.get("price")
            cur = offers.get("priceCurrency")
            krw = None
            if p is not None and cur in KRW_RATE:
                try:
                    krw = to_krw(cur, float(str(p).replace(",", "")))
                except Exception:
                    pass
            link = obj.get("url") or base_url
            key = (title, str(p), link)
            if title and key not in seen:
                seen.add(key)
                out.append({
                    "site": source,
                    "title": title,
                    "price": (f"{cur} {p}" if p else "가격 확인 필요"),
                    "priceKRW": krw,
                    "condition": "",
                    "link": link,
                })
            if len(out) >= 30:
                return out

    # Fallback visible links + nearby price
    for a in soup.select("a[href]"):
        title = clean(a.get_text(" ", strip=True))
        if len(title) < 6:
            continue
        block = clean(a.parent.get_text(" ", strip=True) if a.parent else title)
        cur, val, raw = parse_price_text(block)
        if val is None:
            continue
        link = urllib.parse.urljoin(base_url, a.get("href", ""))
        key = (title[:120], raw, link)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "site": source,
            "title": title[:180],
            "price": raw,
            "priceKRW": to_krw(cur, val),
            "condition": "",
            "link": link,
        })
        if len(out) >= 30:
            break
    return out

def parse_google(html, source):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select("a"):
        h = a.select_one("h3")
        if not h:
            continue
        title = clean(h.get_text(" ", strip=True))
        href = a.get("href", "")
        if not title or not href:
            continue
        out.append({
            "site": source,
            "title": title,
            "price": "가격 확인 필요",
            "priceKRW": None,
            "condition": "",
            "link": href,
        })
        if len(out) >= 20:
            break
    return out

async def fetch_one(site, q):
    cfg = SITE_CONFIG[site]
    url = cfg["url"](q)

    try:
        async with httpx.AsyncClient(
            headers=UA,
            timeout=18.0,
            follow_redirects=True
        ) as client:
            r = await client.get(url)

        if r.status_code != 200:
            return {
                "site": site,
                "ok": False,
                "status": r.status_code,
                "items": [],
                "message": f"HTTP {r.status_code}",
            }

        if cfg["parser"] == "ebay":
            items = parse_ebay(r.text)
        elif cfg["parser"] == "amazon":
            items = parse_amazon(r.text)
        elif cfg["parser"] == "google":
            items = parse_google(r.text, site)
        else:
            items = parse_generic(r.text, site, str(r.url))

        return {
            "site": site,
            "ok": True,
            "status": r.status_code,
            "items": items,
            "message": "ok",
        }

    except Exception as e:
        return {
            "site": site,
            "ok": False,
            "status": 0,
            "items": [],
            "message": str(e)[:180],
        }

@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "Resell Explorer Live API",
        "search_endpoint": "/search?q=RTX%205090&sites=eBay,Amazon",
        "supported_sites": list(SITE_CONFIG.keys()),
    }

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    sites: str = "",
):
    selected = [s for s in sites.split(",") if s in SITE_CONFIG] if sites else list(SITE_CONFIG.keys())

    results = await asyncio.gather(*(fetch_one(site, q) for site in selected))

    items = []
    logs = []

    for r in results:
        if r["ok"]:
            logs.append(f"[{r['site']}] {len(r['items'])}건 수집")
            items.extend(r["items"])
        else:
            logs.append(f"[{r['site']}] 실패/제약: {r['message']}")

    # Put rows with KRW value first, cheapest first.
    items.sort(
        key=lambda x: (
            x.get("priceKRW") is None,
            x.get("priceKRW") if x.get("priceKRW") is not None else 10**18
        )
    )

    return {
        "ok": True,
        "query": q,
        "sites": selected,
        "count": len(items),
        "items": items,
        "logs": logs,
        "fx": KRW_RATE,
    }
