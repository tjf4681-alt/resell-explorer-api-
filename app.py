
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx, re, urllib.parse, asyncio, os
from bs4 import BeautifulSoup

app = FastAPI(title="Resell Explorer Live API v2", version="2.0.0")
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

USD_KRW = float(os.getenv("USD_KRW", "1355.25"))
JPY_KRW = float(os.getenv("JPY_KRW", "8.65041"))
PHP_KRW = float(os.getenv("PHP_KRW", "23.70"))

FX = {"KRW":1.0, "USD":USD_KRW, "JPY":JPY_KRW, "PHP":PHP_KRW}

# mode:
# direct = open the marketplace search URL directly and generic-parse it
# ebay/amazon = dedicated parsers
# google = search Google for site:domain + query, parse results/snippets
SITE_CONFIG = {
    # 국내 종합/가격비교
    "네이버쇼핑": {"group":"국내 종합/가격비교","mode":"direct","url":lambda q:"https://search.shopping.naver.com/search/all?query="+urllib.parse.quote(q)},
    "쿠팡": {"group":"국내 종합/가격비교","mode":"google","domain":"coupang.com"},
    "11번가": {"group":"국내 종합/가격비교","mode":"google","domain":"11st.co.kr"},
    "G마켓": {"group":"국내 종합/가격비교","mode":"google","domain":"gmarket.co.kr"},
    "옥션": {"group":"국내 종합/가격비교","mode":"google","domain":"auction.co.kr"},
    "SSG닷컴": {"group":"국내 종합/가격비교","mode":"google","domain":"ssg.com"},
    "롯데ON": {"group":"국내 종합/가격비교","mode":"google","domain":"lotteon.com"},
    "다나와": {"group":"국내 종합/가격비교","mode":"google","domain":"danawa.com"},
    "에누리": {"group":"국내 종합/가격비교","mode":"google","domain":"enuri.com"},
    "GS SHOP": {"group":"국내 종합/가격비교","mode":"google","domain":"gsshop.com"},
    "CJ온스타일": {"group":"국내 종합/가격비교","mode":"google","domain":"cj온스타일.com"},
    "현대H몰": {"group":"국내 종합/가격비교","mode":"google","domain":"hmall.com"},

    # 국내 중고/리셀
    "번개장터": {"group":"국내 중고/리셀","mode":"direct","url":lambda q:"https://m.bunjang.co.kr/search/products?q="+urllib.parse.quote(q)},
    "중고나라": {"group":"국내 중고/리셀","mode":"direct","url":lambda q:"https://web.joongna.com/search/"+urllib.parse.quote(q)},
    "헬로마켓": {"group":"국내 중고/리셀","mode":"google","domain":"hellomarket.com"},
    "KREAM": {"group":"국내 중고/리셀","mode":"google","domain":"kream.co.kr"},

    # 패션/신발
    "무신사": {"group":"패션/신발","mode":"google","domain":"musinsa.com"},
    "29CM": {"group":"패션/신발","mode":"google","domain":"29cm.co.kr"},
    "ABC마트": {"group":"패션/신발","mode":"google","domain":"abcmart.a-rt.com"},
    "폴더": {"group":"패션/신발","mode":"google","domain":"folderstyle.com"},
    "슈마커": {"group":"패션/신발","mode":"google","domain":"shoemarker.co.kr"},

    # PC/전자
    "컴퓨존": {"group":"PC/전자","mode":"google","domain":"compuzone.co.kr"},
    "아이코다": {"group":"PC/전자","mode":"google","domain":"icoda.co.kr"},
    "조이젠": {"group":"PC/전자","mode":"google","domain":"joyzen.co.kr"},
    "샵다나와": {"group":"PC/전자","mode":"google","domain":"shop.danawa.com"},
    "Newegg": {"group":"PC/전자","mode":"google","domain":"newegg.com"},
    "B&H Photo": {"group":"PC/전자","mode":"google","domain":"bhphotovideo.com"},

    # 자동차부품
    "현대모비스 부품": {"group":"자동차부품","mode":"google","domain":"mobis-as.com"},
    "Partsouq": {"group":"자동차부품","mode":"google","domain":"partsouq.com"},
    "RockAuto": {"group":"자동차부품","mode":"google","domain":"rockauto.com"},
    "eBay Motors": {"group":"자동차부품","mode":"google","domain":"ebay.com"},
    "Amazon Automotive": {"group":"자동차부품","mode":"google","domain":"amazon.com"},

    # 카드/컬렉터
    "TCGplayer": {"group":"카드/컬렉터","mode":"direct","url":lambda q:"https://www.tcgplayer.com/search/all/product?q="+urllib.parse.quote(q)+"&view=grid"},
    "Cardmarket": {"group":"카드/컬렉터","mode":"google","domain":"cardmarket.com"},
    "COMC": {"group":"카드/컬렉터","mode":"google","domain":"comc.com"},
    "Goldin": {"group":"카드/컬렉터","mode":"google","domain":"goldin.co"},
    "Fanatics Collect": {"group":"카드/컬렉터","mode":"google","domain":"fanaticscollect.com"},
    "Mercari JP": {"group":"카드/컬렉터","mode":"direct","url":lambda q:"https://jp.mercari.com/search?keyword="+urllib.parse.quote(q)},
    "Yahoo Auctions JP": {"group":"카드/컬렉터","mode":"google","domain":"auctions.yahoo.co.jp"},
    "SNKRDUNK": {"group":"카드/컬렉터","mode":"google","domain":"snkrdunk.com"},

    # 해외 종합
    "eBay": {"group":"해외 종합","mode":"ebay","url":lambda q:"https://www.ebay.com/sch/i.html?_nkw="+urllib.parse.quote(q)+"&_sop=15"},
    "Amazon": {"group":"해외 종합","mode":"amazon","url":lambda q:"https://www.amazon.com/s?k="+urllib.parse.quote(q)},
    "AliExpress": {"group":"해외 종합","mode":"google","domain":"aliexpress.com"},
    "Walmart": {"group":"해외 종합","mode":"google","domain":"walmart.com"},
    "Rakuten JP": {"group":"해외 종합","mode":"google","domain":"rakuten.co.jp"},
    "Mercari US": {"group":"해외 종합","mode":"google","domain":"mercari.com"},

    # 필리핀
    "Shopee PH": {"group":"필리핀","mode":"google","domain":"shopee.ph"},
    "Lazada PH": {"group":"필리핀","mode":"google","domain":"lazada.com.ph"},
    "Carousell PH": {"group":"필리핀","mode":"google","domain":"carousell.ph"},
}

PRICE_RE = re.compile(
    r'(?:(?:₩|KRW)\s*([\d,]+)|(?:US\s*)?\$\s*([\d,]+(?:\.\d+)?)|¥\s*([\d,]+)|₱\s*([\d,]+(?:\.\d+)?))'
)

def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def extract_price(text):
    text = clean(text)
    m = PRICE_RE.search(text)
    if not m:
        return None, None, None
    if m.group(1):
        return "KRW", float(m.group(1).replace(",","")), m.group(0)
    if m.group(2):
        return "USD", float(m.group(2).replace(",","")), m.group(0)
    if m.group(3):
        return "JPY", float(m.group(3).replace(",","")), m.group(0)
    return "PHP", float(m.group(4).replace(",","")), m.group(0)

def krw(cur, val):
    if cur is None or val is None: return None
    return int(round(val * FX.get(cur,1)))

def google_url(domain, q):
    return "https://www.google.com/search?q=" + urllib.parse.quote(f'site:{domain} "{q}"')

def parse_google(html, site):
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for a in soup.select("a"):
        h3 = a.select_one("h3")
        if not h3: continue
        title = clean(h3.get_text(" ", strip=True))
        if not title: continue
        block = clean(a.parent.get_text(" ", strip=True) if a.parent else title)
        cur, val, raw = extract_price(block)
        href = a.get("href","")
        key=(title,href)
        if key in seen: continue
        seen.add(key)
        out.append({
            "site":site,"title":title,
            "price":raw or "가격 확인 필요",
            "priceKRW":krw(cur,val),
            "condition":"",
            "link":href
        })
        if len(out)>=15: break
    return out

def parse_generic(html, site, base):
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()

    # JSON-LD product offers first
    for script in soup.select('script[type="application/ld+json"]'):
        txt = script.string or script.get_text()
        if not txt: continue
        try:
            import json
            data = json.loads(txt)
        except Exception:
            continue
        objs = data if isinstance(data,list) else [data]
        for obj in objs:
            if not isinstance(obj,dict) or obj.get("@type")!="Product":
                continue
            title=clean(obj.get("name",""))
            offers=obj.get("offers") or {}
            if isinstance(offers,list): offers=offers[0] if offers else {}
            p=offers.get("price")
            cur=offers.get("priceCurrency")
            val=None
            try: val=float(str(p).replace(",","")) if p is not None else None
            except: pass
            link=obj.get("url") or base
            key=(title,link)
            if title and key not in seen:
                seen.add(key)
                out.append({
                    "site":site,"title":title,
                    "price":f"{cur} {p}" if p is not None else "가격 확인 필요",
                    "priceKRW":krw(cur,val),
                    "condition":"",
                    "link":link
                })
            if len(out)>=20: return out

    # Visible text fallback
    for a in soup.select("a[href]"):
        title=clean(a.get_text(" ",strip=True))
        if len(title)<6: continue
        block=clean(a.parent.get_text(" ",strip=True) if a.parent else title)
        cur,val,raw=extract_price(block)
        if val is None: continue
        href=urllib.parse.urljoin(base,a.get("href",""))
        key=(title[:140],href)
        if key in seen: continue
        seen.add(key)
        out.append({
            "site":site,"title":title[:180],
            "price":raw,"priceKRW":krw(cur,val),
            "condition":"","link":href
        })
        if len(out)>=20: break
    return out

def parse_ebay(html):
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for li in soup.select("li.s-item"):
        t=li.select_one(".s-item__title")
        p=li.select_one(".s-item__price")
        a=li.select_one("a.s-item__link")
        if not t or not a: continue
        title=clean(t.get_text(" ",strip=True))
        if not title or "Shop on eBay" in title: continue
        pt=clean(p.get_text(" ",strip=True) if p else "")
        cur,val,raw=extract_price(pt)
        out.append({
            "site":"eBay","title":title,
            "price":raw or pt or "가격 확인 필요",
            "priceKRW":krw(cur,val),
            "condition":clean((li.select_one(".SECONDARY_INFO") or {}).get_text(" ",strip=True) if li.select_one(".SECONDARY_INFO") else ""),
            "link":a.get("href","")
        })
        if len(out)>=30: break
    return out

def parse_amazon(html):
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for card in soup.select('[data-component-type="s-search-result"]'):
        t=card.select_one("h2 span")
        a=card.select_one("h2 a")
        if not t: continue
        title=clean(t.get_text(" ",strip=True))
        whole=card.select_one(".a-price-whole")
        frac=card.select_one(".a-price-fraction")
        pt=""
        if whole:
            pt="$"+clean(whole.get_text("",strip=True)).rstrip(".")
            if frac: pt+="."+clean(frac.get_text("",strip=True))
        cur,val,raw=extract_price(pt)
        out.append({
            "site":"Amazon","title":title,
            "price":raw or pt or "가격 확인 필요",
            "priceKRW":krw(cur,val),
            "condition":"New",
            "link":urllib.parse.urljoin("https://www.amazon.com",a.get("href","")) if a else ""
        })
        if len(out)>=30: break
    return out

async def fetch_site(site,q):
    cfg=SITE_CONFIG[site]
    try:
        if cfg["mode"]=="google":
            url=google_url(cfg["domain"],q)
        else:
            url=cfg["url"](q)
        async with httpx.AsyncClient(headers=UA,timeout=18.0,follow_redirects=True) as c:
            r=await c.get(url)
        if r.status_code!=200:
            return {"site":site,"ok":False,"items":[],"message":f"HTTP {r.status_code}"}
        if cfg["mode"]=="ebay":
            items=parse_ebay(r.text)
        elif cfg["mode"]=="amazon":
            items=parse_amazon(r.text)
        elif cfg["mode"]=="google":
            items=parse_google(r.text,site)
        else:
            items=parse_generic(r.text,site,str(r.url))
        return {"site":site,"ok":True,"items":items,"message":"ok"}
    except Exception as e:
        return {"site":site,"ok":False,"items":[],"message":str(e)[:160]}

@app.get("/")
async def root():
    return {
        "ok":True,
        "service":"Resell Explorer Live API v2",
        "supported_count":len(SITE_CONFIG),
        "groups":sorted(set(v["group"] for v in SITE_CONFIG.values()))
    }

@app.get("/health")
async def health():
    return {"ok":True,"supported_count":len(SITE_CONFIG)}

@app.get("/sites")
async def sites():
    return {
        "count":len(SITE_CONFIG),
        "sites":[{"name":k,"group":v["group"]} for k,v in SITE_CONFIG.items()]
    }

@app.get("/search")
async def search(q:str=Query(...,min_length=1), sites:str=""):
    requested=[s for s in sites.split(",") if s]
    selected=[s for s in requested if s in SITE_CONFIG] if requested else list(SITE_CONFIG.keys())

    # Avoid hammering everything at once; batch concurrency.
    sem=asyncio.Semaphore(8)
    async def guarded(site):
        async with sem:
            return await fetch_site(site,q)

    results=await asyncio.gather(*(guarded(s) for s in selected))
    items=[]
    logs=[]
    for r in results:
        if r["ok"]:
            items.extend(r["items"])
            logs.append(f"[{r['site']}] {len(r['items'])}건")
        else:
            logs.append(f"[{r['site']}] 실패/제약: {r['message']}")

    items.sort(key=lambda x:(x.get("priceKRW") is None,x.get("priceKRW") or 10**18))

    return {
        "ok":True,
        "query":q,
        "requested_sites":requested,
        "searched_sites":selected,
        "searched_count":len(selected),
        "count":len(items),
        "items":items,
        "logs":logs,
        "fx":FX
    }
