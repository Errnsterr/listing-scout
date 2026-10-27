#!/usr/bin/env python3
"""listing-scout: simple listing alerts to your criteria.
Usage: python3 src/scout.py [--criteria CRITERIA.yaml] [--state state.json] [--dry-run] [--all]
Fetches each source, parses listings, filters, dedupes (id+price), stores state,
prints formatted text messages (one per alert, separated by '---'). Never sends anything.
Unknown fields are printed as 'unknown' — nothing is invented."""
import argparse, json, re, os, sys, time, html, glob, email, statistics, urllib.request, urllib.parse, hashlib
html_mod = html
from email import policy
from datetime import datetime, date
import yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) listing-scout/1.0 (personal home search, low frequency)"
U = "unknown"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")

def num(s):
    if s is None: return None
    k = re.fullmatch(r"\s*\$?\s?(\d{1,3}(?:\.\d{1,2})?)\s?[kK]\s*", str(s))   # '$30K', '1.8K', '$2.12K' = the number x 1000
    if k: return round(float(k.group(1)) * 1000, 2)
    m = re.search(r"[\d,]+(?:\.\d+)?", str(s))
    return float(m.group().replace(",", "")) if m else None

# ---------- parsers ----------
def parse_appfolio(src):
    base = re.match(r"https?://[^/]+", src["url"]).group()
    soup = BeautifulSoup(get(src["url"]), "html.parser")
    out = []
    for it in soup.select("div.js-listing-item"):
        a = it.select_one("a[href*='/listings/detail/']")
        if not a: continue
        uid = a["href"].rstrip("/").split("/")[-1]
        facts = {dt.get_text(strip=True).lower(): dd.get_text(" ", strip=True)
                 for dt, dd in zip(it.select("dt.detail-box__label"), it.select("dd.detail-box__value"))}
        bb = facts.get("bed / bath", "")
        beds = num(re.search(r"([\d.]+)\s*bd", bb).group(1)) if re.search(r"([\d.]+)\s*bd", bb) else None
        baths = num(re.search(r"([\d.]+)\s*ba", bb).group(1)) if re.search(r"([\d.]+)\s*ba", bb) else None
        if beds is None and re.search(r"studio", bb, re.I): beds = 0
        addr = it.select_one(".js-listing-address")
        img = it.select_one("img.js-listing-image")
        pet = it.select_one(".js-listing-pet-policy")
        out.append(dict(
            id=f"appfolio:{uid}", source=src["name"], url=base + a["href"],
            title=(it.select_one(".js-listing-title") or a).get_text(" ", strip=True),
            address=addr.get_text(" ", strip=True) if addr else None,
            price=num(facts.get("rent")), beds=beds, baths=baths, sqft=num(facts.get("square feet")),
            available=facts.get("available"),
            pets_raw=pet.get_text(" ", strip=True).replace("Pet Policy:", "").strip() if pet else None,
            text=it.get_text(" ", strip=True), photo=img.get("data-original") if img else None,
            photo_alt=img.get("alt") if img else None, showing_url=None, listed_on=None,
            apply_url=(base + ap["href"]) if (ap := it.select_one("a[href*='/listings/rental_applications/new']")) and ap.get("href", "").startswith("/") else None))
    return out

def parse_tenantturner(src):
    out = []
    for d in json.loads(get(src["url"])):
        addr = ", ".join(x for x in [d.get("address"), d.get("city"), f"{d.get('state','')} {d.get('zip','')}".strip()] if x)
        out.append(dict(
            id=f"tt:{d['id']}", source=src["name"], url=src.get("site") or d.get("btnUrl"),
            title=d.get("title"), address=addr, price=num(d.get("rentAmount")),
            beds=num(d.get("beds")), baths=num(d.get("baths")), sqft=None,
            available=d.get("dateAvailable"), pets_raw=d.get("acceptPets") or None,
            text=f"{d.get('title','')} {d.get('description','')} {d.get('propertyType','')}",
            photo=d.get("photo"), photo_alt=None, showing_url=d.get("btnUrl"),
            listed_on=d.get("dateActivated"), ptype_raw=d.get("propertyType")))
    return out

PORTALS = {"zillow": "Zillow", "redfin": "Redfin", "hotpads": "HotPads", "craigslist": "Craigslist",
           "realtor.com": "Realtor.com", "zumper": "Zumper", "rent.com": "Rent.com", "trulia": "Trulia"}
# Listing links: direct portal URLs AND the click trackers real alert emails use (Zillow, Redfin, HotPads /pad).
LISTING_HREF = re.compile(r"homedetails|/home/|/rental|/listing|/apartments?/|/pad\b|/b/|/property|"
                          r"click\.mail\.zillow\.com|redmail\d*\.redfin\.com|(?:email|click|links?)\.[\w.]*hotpads\.com|hotpads\.com/|"
                          r"realestateandhomes-detail|(?:click|links?|email|e|t)\.[\w.]*realtor\.com|realtor\.com/", re.I)
AMT = r"(\d{1,3}(?:\.\d{1,2})?\s?[kK]\b|\d{1,3}(?:,\d{3})+|\d{3,6})"   # shared price amount: '$4,350', '$4350', '$30K', '$1.8K'
PRICE = re.compile(r"\$\s?" + AMT + r"(?!\d)")
WAS = re.compile(r"(?:was|from|previously|reduced from|orig(?:inally)?)\s*:?\s*\$\s?[\d,]{3,}|\$\s?[\d,]{3,}\s*(?:→|->|to)\s*(?=\$)|<s>.*?</s>|<del>.*?</del>", re.I)
ADDR = re.compile(r"\b\d+[A-Za-z]? (?:[A-Z]|\d+(?:st|nd|rd|th)\b)[^,$|\n]{2,60}?,\s*[A-Za-z .]{3,40},\s*[A-Z]{2}(?:\s*\d{5})?")

def email_files(d):
    return sorted(f for f in glob.glob(os.path.join(d, "*")) if os.path.isfile(f) and not os.path.basename(f).startswith("."))

def _email_body(f):
    raw = open(f, "rb").read(); body = raw.decode("utf-8", "replace"); sender = ""
    if f.endswith(".eml"):
        msg = email.message_from_bytes(raw, policy=policy.default)
        sender = str(msg.get("From", ""))
        part = msg.get_body(preferencelist=("html", "plain"))
        body = part.get_content() if part else body
    m = re.match(r"\s*<!-- from: (.*?) \|", body)   # header line written by the alert-pull routine / fetch_inbox.py
    if m: sender = sender or m.group(1)
    return sender, body

def _card_id(portal, blob, addr):
    """Stable id: Zillow zpid or Redfin home id found anywhere in the card (hrefs decoded, img src, text);
    else normalized street address + unit; else None (caller falls back to a content hash)."""
    blob = urllib.parse.unquote(urllib.parse.unquote(blob))
    z = re.search(r"(\d{6,})_zpid|zpid[=:/\"' ]+(\d{6,})", blob, re.I)
    if z: return f"email:Zillow:{z.group(1) or z.group(2)}"
    r = re.search(r"redfin\.com/[^\s\"'<>]*?/home/(\d{4,})|/home/(\d{4,})", blob, re.I)
    if r and portal == "Redfin": return f"email:Redfin:{r.group(1) or r.group(2)}"
    ak = addr_key(addr)
    if ak: return f"email:addr:{ak.replace(' ', '-')}"
    return None

def _n(rx, t):
    m = re.search(rx, t, re.I); return num(m.group(1)) if m else None

STATUS = [("sold", r"\bsold\b"), ("pending", r"\bpending\b|under contract|contingent"), ("coming_soon", r"coming soon"),
          ("back_on_market", r"back on (the )?market"), ("price_cut", r"price (cut|drop|reduced|change)|reduced\b|\bnew price\b"),
          ("new", r"\bnew( listing)?\b|just listed")]

def buy_facts(t):
    """For-sale facts from one alert card; anything missing stays None (never guessed)."""
    hoa = re.search(r"HOA(?: dues| fee)?s?\s*:?\s*\$\s?([\d,]+)\s*(?:/\s*mo|per month|monthly|/month)?", t, re.I)
    no_hoa = re.search(r"\bno HOA\b|HOA:?\s*(?:none|\$0\b)", t, re.I)
    lot = re.search(r"([\d,.]+)\s*(acres?|ac)\b|([\d,]+)\s*(?:sq\.?\s*ft\.?|sqft)\s*lot|lot(?: size)?:?\s*([\d,]+)\s*(?:sq\.?\s*ft|sqft)", t, re.I)
    lot_s = None
    if lot:
        if lot.group(1): lot_s = f"{lot.group(1)} acre" + ("" if lot.group(1) in ("1", "1.0") else "s")
        else: lot_s = f"{num(lot.group(3) or lot.group(4)):,.0f} sq ft lot"
    st = next((name for name, rx in STATUS if re.search(rx, t, re.I)), None)
    oh = re.search(r"open house:?\s*((?:mon|tue|wed|thu|fri|sat|sun)\w*,?\s*(?:\w{3,9}\.? \d{1,2},?\s*)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(?:-|–|to)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm))", t, re.I)
    return {"hoa": 0 if no_hoa else (num(hoa.group(1)) if hoa else None),
            "sqft_buy": _n(r"([\d,]{3,6})\s*(?:sq\.?\s*ft\.?|sqft)(?!\s*lot)", t),
            "lot": lot_s, "year_built": _n(r"(?:built(?: in)?|year built:?)\s*((?:18|19|20)\d\d)", t),
            "dom": _n(r"(\d{1,4})\s*days? on (?:market|zillow|redfin|realtor\.com)", t),
            "status": st, "open_house": re.sub(r"\s+", " ", oh.group(1)).strip() if oh else None,
            "home_type_raw": next((k for k in ("townhome", "townhouse", "condo", "single family", "house") if k in t.lower()), None)}

UNDISCLOSED = re.compile(r"\(?\s*(?:undisclosed|address not (?:disclosed|listed))\s*address\)?\s*,\s*([A-Za-z .]{3,40}),\s*([A-Z]{2})\b(?:\s*(\d{5}))?", re.I)
URL_RE = re.compile(r"https?://[^\s)<>\"']+")
PRICE_RANGE = re.compile(r"^\s*\$\s?([\d,]{3,})\s*[-\u2013]\s*\$\s?([\d,]{3,})\s*/\s*mo\b", re.I)   # Redfin buildings: '$2,702-$3,953/mo'
NAMED_PLACE = re.compile(r"^\s*([A-Za-z0-9][^,$|\n(]{1,60}),\s*([A-Za-z .]{3,40}),\s*([A-Z]{2})\s+(\d{5})\b")   # 'Example Villas, Vista del Sol, CA 90001'
PRICE_LINE = re.compile(r"^\s*(?:from\s+)?\$\s?" + AMT + r"(?:\s*/\s*mo\b|\+?\s*$)", re.I)

# ---------- the listing's own apply / agent link (shown, never followed) ----------
# Only a link whose own label says so, inside that listing's card. Trackers are unwrapped only when the real
# target is in the link itself; query strings (tokens) are dropped; anything opaque or token-shaped is skipped.
APPLY_LABEL = re.compile(r"^\s*apply(?: now| online| for this (?:home|rental|unit))?\s*$", re.I)
AGENT_LABEL = re.compile(r"^\s*(?:contact (?:the )?(?:listing )?agent|request (?:a )?tour|ask a question|schedule a tour|message (?:the )?agent)\s*$", re.I)
ACTION_HOSTS = re.compile(r"^(?:www\.)?(?:zillow|redfin|realtor|hotpads|trulia|apartments)\.com$", re.I)
ACTION_BAD = re.compile(r"homeloans|prequal|mortgage|support|unsubscribe|notifications|feedback|/routing/|/click|login|signin|~~", re.I)

def clean_action_url(href):
    """Plain public URL for a listing's apply/agent link, or None (never invented, never fetched)."""
    if not href: return None
    u = urllib.parse.urlparse(href.strip())
    q = urllib.parse.parse_qs(u.query)
    tgt = next((q[k][0] for k in ("target", "u", "url", "redirect") if q.get(k) and q[k][0].startswith("http")), None)
    if tgt: u = urllib.parse.urlparse(urllib.parse.unquote(tgt))
    if u.scheme != "https" or not ACTION_HOSTS.match(u.netloc or ""): return None   # opaque tracker or another site: skip
    path = u.path or "/"
    if ACTION_BAD.search(path) or any(len(seg) >= 40 for seg in path.split("/")): return None   # token-shaped path: skip
    return f"https://{u.netloc.lower()}{path}"

def action_links(pairs):
    """pairs = [(label, href)] from one card -> {'apply_url':..., 'agent_url':...} (clean links only)."""
    out = {"apply_url": None, "agent_url": None}
    for label, href in pairs:
        k = "apply_url" if APPLY_LABEL.match(label or "") else "agent_url" if AGENT_LABEL.match(label or "") else None
        if k and not out[k]: out[k] = clean_action_url(href)
    return out

def _text_pairs(seg):
    """Plain-text render: a label line followed (within 2 lines) by its '(URL)' line."""
    pairs = []
    for k, x in enumerate(seg):
        if APPLY_LABEL.match(x) or AGENT_LABEL.match(x):
            u = next((m for y in seg[k + 1:k + 3] for m in URL_RE.findall(y)), None)
            if u: pairs.append((x.strip(), u))
    return pairs

IMG_PRICE = re.compile(r"^\s*\[image:[^\]]*\]\s*\(https?://[^)\s]*\)\s*(?=\$)")
SIMILAR = re.compile(r"^\s*(?:related to your search|nearby similar homes|similar homes|recommended for you)\s*$", re.I)
TRACKER = re.compile(r"redmail\d*\.|click\.mail\.|/u/click|/a/click|/f/a/|~~|[?&](?:_t|_e|_m|rtoken|zuid|token)=", re.I)

def _parse_text_cards(body, portal, fname):
    """Plain-text alert (e.g. a text render of a Zillow 'New Rental Match'): one card per '$X/mo' line.
    Beds/baths/sqft/address are read from the lines after the price, up to the next price line or footer."""
    body = html.unescape(body)   # '&middot;' etc. in text renders
    L = [IMG_PRICE.sub("", x) for x in body.split("\n")]   # Redfin: '[image: New Listing] (URL) $1,349,000' -> '$1,349,000'
    cut = next((k for k, x in enumerate(L) if SIMILAR.match(x)), len(L))   # 'Nearby similar homes' aren't saved-search matches
    L = L[:cut]; out, ids = [], set()
    msgid = (re.search(r"message_id\s+(\w+)", body) or re.search(r"(\d{5,})", fname) or re.match("()", "")).group(1)
    starts = [i for i, x in enumerate(L) if PRICE_LINE.match(x) or PRICE_RANGE.match(x)]
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(L)
        seg = L[i:end]
        stop = next((k for k, x in enumerate(seg) if re.search(r"see (latest|all|more) (search )?results|^\s*zillow, inc\.|unsubscribe|^\s*©", x, re.I)), len(seg))
        seg = seg[:stop]; t = " ".join(y for x in seg for y in [re.sub(r"\(\s*\)", "", URL_RE.sub("", x)).strip()] if y)
        bdr = re.search(r"(\d+)\s*[-\u2013]\s*(\d+)\s*(?:bd|bds|beds?|br)\b", t, re.I); bar = re.search(r"(\d+(?:\.\d)?)\s*[-\u2013]\s*(\d+(?:\.\d)?)\s*(?:ba|baths?)\b", t, re.I)
        bd = None if bdr else re.search(r"(\d+(?:\.\d)?)\s*(?:bd|bds|beds?|br)\b", t, re.I); ba = None if bar else re.search(r"(\d+(?:\.\d)?)\s*(?:ba|baths?)\b", t, re.I)
        sq = re.search(r"([\d,]{3,})\s*sq\.?\s*ft", t, re.I)
        und = UNDISCLOSED.search(t); ad = None if und else next((m.group() for x in seg for m in [ADDR.search(x)] if m), None)
        if not (ad or und):   # building name instead of a street number: 'Example Villas, Vista del Sol, CA 90001'
            ad = next((m.group().strip() for x in seg for m in [NAMED_PLACE.match(URL_RE.sub("", x))] if m), None)
        if not (bd or ba or bdr or bar or ad or und): continue
        pre = [u for x in L[max(0, i - 8):i] for u in URL_RE.findall(x)]   # tracked link nearest the card (just above the price)
        inside = [u for x in seg for u in URL_RE.findall(x)]
        res = next((URL_RE.findall(L[k - 1] if k else "") or URL_RE.findall(L[k - 2] if k > 1 else "") for k, x in enumerate(L)
                    if re.search(r"see latest search results", x, re.I)), [])
        link = (pre[-1:] or inside[:1] or res[:1] or [None])[0]
        rg = PRICE_RANGE.match(L[i])
        price = None if rg else num(PRICE_LINE.match(L[i]).group(1)); beds = num(bd.group(1)) if bd else None
        zr = _card_id(portal, " ".join(seg) + " " + body if len(starts) == 1 else " ".join(L[max(0, i - 8):end]), None)
        if zr: lid = zr
        elif ad and addr_key(ad): lid = f"email:addr:{addr_key(ad).replace(' ', '-')}"
        else: lid = f"email:{portal}:m{msgid}-{int(price) if price else 'x'}-{int(beds) if beds is not None else 'x'}-{sq.group(1).replace(',', '') if sq else 'x'}"
        if lid in ids: continue
        ids.add(lid)
        city = und.group(1).strip() if und else None
        wp = re.search(r"(?:was|from|previously)\s*:?\s*\$\s?([\d,]{3,})", t, re.I)
        out.append(dict(buy_facts(t), **action_links(_text_pairs(seg)), id=lid, source=portal, url=_clean_link(lid, link), title=t[:120], address=ad, city=city,
            zip=(und.group(3) if und and und.group(3) else None), state=(und.group(2) if und else None),
            price=price, beds=beds, baths=num(ba.group(1)) if ba else None, sqft=num(sq.group(1)) if sq else None,
            available=None, pets_raw=None, text=t, photo=None, photo_alt=None, showing_url=None, listed_on=None,
            email_was_price=num(wp.group(1)) if wp else None, email_file=fname,
            price_range=[num(rg.group(1)), num(rg.group(2))] if rg else None,   # a building's unit range: shown as a range, never one made-up price
            beds_range=[num(bdr.group(1)), num(bdr.group(2))] if bdr else None, baths_range=[num(bar.group(1)), num(bar.group(2))] if bar else None))
    return out

# ---------- HotPads plain-text alerts ----------
# Real HotPads alerts (2026-10-26): each card is price, [New!], beds, [building name], street, 'City, ST zip'
# (or one 'street, City, ST zip' line), then '(https://hotpads.com/<slug>/pad?...)Contact (...) View listing (...)'.
# The card's link comes AFTER its text, so cards are split on that link line, never on price lines
# ('$1,797+/mo' and 'Call for price' cards have no plain '$X/mo' line).
HP_ANCHOR = re.compile(r"^\s*\((https?://(?:www\.)?hotpads\.com/[^)\s]+)\)\s*Contact\b", re.I)
HP_PRICE = re.compile(r"^\s*(?:from\s+)?\$\s?" + AMT + r"\+?\s*(?:/\s*mo\b|$)", re.I)   # '$4,350/mo', '$30K/mo', 'from $1.8K'
HP_BEDS = re.compile(r"^\s*(studio|\d+)(?:\s+to\s+(\d+))?\s+beds?\b|^\s*studio\s*$", re.I)
HP_CITY = re.compile(r"^\s*([A-Za-z .'-]{3,40}),\s*([A-Z]{2})\s+(\d{5})\s*$")
HP_STREET = re.compile(r"^\s*\d[\d./]*[A-Za-z]?\s+\S.*$")

def hotpads_url(u):
    """Plain listing link: https://hotpads.com/<slug>/.../pad, no nid/utm query. None for non-listing pages."""
    p = urllib.parse.urlparse(u or "")
    if not re.fullmatch(r"(?:www\.)?hotpads\.com", p.netloc or "", re.I) or not re.search(r"/pad/?$", p.path or ""): return None
    return f"https://hotpads.com{p.path}"

def _parse_hotpads_text(body, fname):
    L = html.unescape(body).split("\n")
    cut = next((k for k, x in enumerate(L) if re.match(r"\s*see all homes\b", x, re.I)), len(L))
    L = L[:cut]; out, ids, prev = [], set(), 0
    for i, x in enumerate(L):
        m = HP_ANCHOR.match(x)
        if not m: continue
        seg = [re.sub(r"^\[image[^\]]*\]\s*(?:total price)?\s*", "", y.strip(), flags=re.I) for y in L[prev:i] if y.strip()]; prev = i + 1
        st = next((k for k, y in enumerate(seg) if HP_PRICE.match(y) or re.match(r"call for (?:price|pricing)$", y, re.I)), None)
        url = hotpads_url(m.group(1))
        if st is None or not url: continue
        seg = seg[st:]
        pm = HP_PRICE.match(seg[0]); price = num(pm.group(1)) if pm else None
        bm = next((HP_BEDS.match(y) for y in seg if HP_BEDS.match(y)), None)
        beds = beds_max = None
        if bm:
            lo = (bm.group(1) or "studio").lower(); beds = 0.0 if lo == "studio" else num(lo)
            beds_max = num(bm.group(2)) if bm.group(2) else beds
        addr = city = state = zp = None
        for k, y in enumerate(seg):
            one = ADDR.fullmatch(y)
            cm = HP_CITY.match(y)
            if one and HP_STREET.match(y):
                addr = y; cm = HP_CITY.match(y.split(",", 1)[1])
            elif cm and k and HP_STREET.match(seg[k - 1]) and not HP_BEDS.match(seg[k - 1]) and not HP_PRICE.match(seg[k - 1]):
                addr = f"{seg[k - 1]}, {y}"
            if cm:
                city, state, zp = cm.group(1).strip(), cm.group(2), cm.group(3); break
        ak = addr_key(addr)
        lid = f"email:addr:{ak.replace(' ', '-')}" if ak else "email:HotPads:" + urllib.parse.urlparse(url).path.strip("/").replace("/", "-")
        if lid in ids: continue
        ids.add(lid); t = " ".join(seg)
        out.append(dict(buy_facts(t), apply_url=None, agent_url=None, id=lid, source="HotPads", url=url, title=t[:120], address=addr, city=city,
            zip=zp, state=state, price=price, beds=beds, beds_max=beds_max, baths=None, sqft=None,
            available=None, pets_raw=None, text=t, photo=None, photo_alt=None, showing_url=None, listed_on=None,
            email_was_price=None, email_file=fname))
    return out

def _clean_link(lid, link):
    """Zillow zpid known -> plain homedetails link (no tracker, no account token like rtoken/zuid in what we text people)."""
    m = re.fullmatch(r"email:Zillow:(\d{6,})", lid or "")
    if m: return f"https://www.zillow.com/homedetails/{m.group(1)}_zpid/"
    if link and re.search(r"//(?:www\.)?hotpads\.com/", link, re.I):   # only a /pad listing page, never /user/searches etc.
        return hotpads_url(link)
    if link and TRACKER.search(link):   # a tracker carries account tokens: unwrap to a plain public page if it's inside, else none
        return clean_action_url(link)
    return link

def parse_email_file(f):
    """One alert email -> list of listing dicts. Reads cards (price, beds, baths, address); missing fields stay None."""
    sender, body = _email_body(f)
    portal = next((v for k, v in PORTALS.items() if k in sender.lower()), None) or \
             next((v for k, v in PORTALS.items() if k in body[:5000].lower()), "Email alert")
    body = re.sub(r"</?cursor_untrusted_data\w*[^>]*>", "", body)   # wrapper tags from a tool's text render
    if not re.search(r"<(?:a|div|table|td|tr|p|html|body|span|img)\b", body, re.I):   # plain text / text render
        if portal == "HotPads" and any(HP_ANCHOR.match(x) for x in body.split("\n")):
            return _parse_hotpads_text(body, os.path.basename(f))
        return _parse_text_cards(body, portal, os.path.basename(f))
    soup = BeautifulSoup(body, "html.parser")
    for t in soup.find_all(["s", "del", "strike"]): t.insert_before(" was ")
    cards, out, ids = [], [], set()
    for a in soup.find_all("a", href=True):
        if not LISTING_HREF.search(a["href"]): continue
        blk = a
        while blk is not None and not PRICE.search(blk.get_text(" ", strip=True)): blk = blk.parent
        if blk is None or blk.name in ("[document]", "html", "body"): continue
        pr = lambda e: set(PRICE.findall(e.get_text(" ", strip=True)))
        while blk.parent is not None and blk.parent.name not in ("[document]", "html", "body") and pr(blk.parent) == pr(blk) \
                and len(blk.parent.find_all("a", href=LISTING_HREF)) <= len(blk.find_all("a", href=LISTING_HREF)) + 3:
            blk = blk.parent   # grow to the whole card (beds/address often sit beside the priced link)
        # too big (holds 2+ cards)? then this link isn't inside a single card
        if len(set(PRICE.findall(WAS.sub(" ", blk.get_text(" ", strip=True))))) > 2 and len(ADDR.findall(blk.get_text(" ", strip=True))) > 1: continue
        if any(blk is c for c in cards): continue
        if any(c in blk.descendants for c in cards): continue
        cards = [c for c in cards if c not in list(blk.descendants)] + [blk]
    for blk in cards:
        t = blk.get_text(" ", strip=True)
        clean = WAS.sub(" ", t)
        pm = PRICE.search(clean) or PRICE.search(t)
        was = re.search(r"(?:was|from|previously|reduced from|orig(?:inally)?)\s*:?\s*\$\s?([\d,]{3,})", t, re.I)
        bd = re.search(r"(\d+(?:\.\d)?)\s*(?:bd|bds|beds?|br)\b", t, re.I)
        beds = num(bd.group(1)) if bd else (0 if re.search(r"\bstudio\b", t, re.I) else None)
        ba = re.search(r"(\d+(?:\.\d)?)\s*(?:ba|baths?)\b", t, re.I)
        ad = ADDR.search(blk.get_text("\n", strip=True))   # one line per element, so the street isn't glued to '2 bd'
        els = ([blk] if blk.name in ("a", "img") else []) + blk.find_all(["a", "img"])
        hrefs = [x.get("href") or "" for x in els if x.name == "a"]
        attrs = " ".join(str(v) for x in els for v in x.attrs.values())
        zr = _card_id(portal, attrs + " " + t, None)
        if not (bd or ba or ad or zr): continue   # a price alone ('Prices from $3,000') isn't a listing card
        lid = _card_id(portal, attrs + " " + t, ad.group() if ad else None) or \
              ("email:%s:h%s" % (portal, hashlib.sha1(" ".join(t.split()).encode()).hexdigest()[:12]))
        if lid in ids: continue
        ids.add(lid)
        link = next((h for h in hrefs if LISTING_HREF.search(h)), None)
        bf = buy_facts(t)
        bf.update(action_links([(x.get_text(" ", strip=True), x.get("href") or "") for x in els if x.name == "a"]))
        out.append(dict(bf, id=lid, source=portal, url=_clean_link(lid, link), title=t[:120], address=ad.group() if ad else None,
            price=num(pm.group(1)) if pm else None, beds=beds,
            baths=num(ba.group(1)) if ba else None, sqft=None, available=None, pets_raw=None,
            text=t, photo=None, photo_alt=None, showing_url=None, listed_on=None,
            email_was_price=num(was.group(1)) if was else None, email_file=os.path.basename(f)))
    return out

def parse_email(src):
    """Saved-search alert emails (.eml/.html/.txt in src['dir']). Writes out/email_parse.json per file
    (count + portal) so notify.py can flag a 0-listing email to the owner; the file is kept for review."""
    d = src.get("dir", "./inbox"); out, rep = [], {}
    for f in email_files(d):
        try: got = parse_email_file(f)
        except Exception as e: got = []; print(f"email parse error {os.path.basename(f)}: {type(e).__name__}", file=sys.stderr)
        sender, body = _email_body(f)
        portal = next((v for k, v in PORTALS.items() if k in (sender + body[:5000]).lower()), "Email alert")
        rep[os.path.basename(f)] = {"count": len(got), "portal": portal, "mtime": os.path.getmtime(f)}
        out += got
    if src.get("report"):   # only the live run (scout main) writes the report; tests never do
        os.makedirs("out", exist_ok=True); json.dump(rep, open(os.path.join("out", "email_parse.json"), "w"), indent=1)
    return out

PARSERS = {"appfolio": parse_appfolio, "tenantturner": parse_tenantturner, "email": parse_email}

# ---------- classify ----------
def has(text, words): return any(re.search(r"\b" + re.escape(w) + r"\b", text, re.I) for w in words or [])

def is_buy(C): return (C.get("mode") or "lease").startswith("buy")

def home_type(l):
    raw = (l.get("home_type_raw") or "") + " " + (l.get("title") or "")
    if re.search(r"townho(me|use)", raw, re.I): return "townhome"
    if re.search(r"\bcondo", raw, re.I): return "condo"
    if re.search(r"single[- ]family|\bhouse\b", raw, re.I): return "house"
    return None

def is_match_buy(l, C):
    """Buy mode light filters: area, price <= max, beds, baths, HOA max, home type. Unknowns are kept."""
    B = C.get("buy") or {}
    if not l.get("in_area") or l.get("status") in ("pending", "sold"): return False
    if l.get("beds") is not None and l["beds"] < C.get("beds_min", 0): return False
    if l.get("baths") is not None and l["baths"] < B.get("baths_min", 0): return False
    pmax = B.get("price_max") or (C.get("price_tiers") or {}).get("stretch_max")
    if pmax and l.get("price") is not None and l["price"] > pmax: return False
    if B.get("price_min") and l.get("price") is not None and l["price"] < B["price_min"]: return False
    if B.get("hoa_max") is not None and l.get("hoa") is not None and l["hoa"] > B["hoa_max"]: return False
    ht = home_type(l)
    if B.get("home_types") and ht and ht not in B["home_types"]: return False
    return True

def is_match(l, C):
    """Light filters (default): area + beds (unknown kept) + baths_min (unknown kept) + price <= max (unknown kept)
    + pets not explicitly disallowed. Garage/layout are only filters if match.garage_min / match.layout_any are set
    (older CRITERIA); otherwise they are shown in the alert as details, never invented."""
    need = C.get("match") or {}
    if not l.get("eligible"): return False
    b = l.get("baths")
    if b is not None and b < need.get("baths_min", (C.get("baths") or {}).get("ok", 0)): return False
    pmax = need.get("price_max", (C.get("price_tiers") or {}).get("stretch_max"))
    if pmax and l.get("price") is not None and l["price"] > pmax: return False
    if pmax and l.get("price") is None and l.get("price_range") and l["price_range"][0] > pmax: return False   # even the lowest unit is over
    if pet_filter_on(C) and str(l.get("pets", "")).startswith("no dogs") and "disagree" not in str(l.get("pets")): return False
    lay = l.get("layout", U)
    if need.get("layout_any") and lay in (U, "upper unit"): return False
    if need.get("garage_min", 0) > 0 and l.get("garage") != "yes": return False
    return True

NO_RELAY = re.compile(r"section\s*8|vouchers?|adults?\s*only|no (?:kids|children)|single professional|seniors?\s*only|christian|muslim|jewish|english only", re.I)

def assistance_animal(C):
    P = C.get("pets") or {}
    return bool(P.get("service_animal") or P.get("esa_letter"))

def pet_filter_on(C):
    """Fair housing: a service or assistance animal is never filtered on 'no pets' rules (not legal advice)."""
    return bool((C.get("match") or {}).get("exclude_no_pets", True)) and not assistance_animal(C)

def misses(l, C):
    """Which filters an in-area listing fails (unknowns never count as a miss). Used by the near-miss check-in."""
    if not l.get("in_area"): return ["area"]
    need, out = C.get("match") or {}, []
    if l.get("beds") is not None and l["beds"] < C["beds_min"]: out.append("beds")
    b = l.get("baths")
    if b is not None and b < need.get("baths_min", (C.get("baths") or {}).get("ok", 0)): out.append("baths")
    pmax = need.get("price_max", (C.get("price_tiers") or {}).get("stretch_max"))
    if pmax and l.get("price") is not None and l["price"] > pmax: out.append("price")
    if pet_filter_on(C) and str(l.get("pets", "")).startswith("no dogs") and "disagree" not in str(l.get("pets")): out.append("pets")
    if need.get("layout_any") and l.get("layout") in (U, "upper unit"): out.append("layout")
    if need.get("garage_min", 0) > 0 and l.get("garage") != "yes": out.append("garage")
    return out

def classify(l, C):
    t = " ".join(str(l.get(k) or "") for k in ("title", "text", "address"))
    K = C.get("keywords", {})
    zipm = (re.findall(r"\b(\d{5})(?:-\d{4})?\b", l.get("address") or "") or [None])[-1]
    l["zip"] = zipm
    area = C["area"]
    in_area = (l["zip"] in area["zips"]) if l["zip"] else any(c.lower() in t.lower() for c in area["cities"])
    l["neighborhood"] = next((n for n in area.get("neighborhoods", []) if n.lower() in t.lower()), None)
    # garage
    if has(t, K.get("garage_negative")): l["garage"] = "no"
    elif has(t, K.get("garage")): l["garage"] = "yes"
    else: l["garage"] = U
    # layout
    lay = []
    if has(t, K.get("first_floor")): lay.append("first floor")
    if has(t, K.get("single_story")): lay.append("single story")
    if has(t, K.get("townhome")): lay.append("townhome/2-story")
    upper = has(t, K.get("upper_negative"))
    l["layout"] = ", ".join(lay) if lay else ("upper unit" if upper else U)
    layout_ok = bool(lay) and not (upper and not lay)
    # pets
    p = (l.get("pets_raw") or "").lower()
    if not p: l["pets"] = U
    elif re.search(r"dogs? not allowed|no pets|pets not allowed", p): l["pets"] = "no dogs"
    elif "dog" in p: l["pets"] = "dogs ok"
    elif "cat" in p and "allowed" in p: l["pets"] = "cats only"
    else: l["pets"] = U if NO_RELAY.search(p) else l["pets_raw"]   # never repeat discriminatory ad wording
    # tier
    pr, T = l.get("price"), C["price_tiers"]
    l["tier"] = U if pr is None else ("TARGET" if pr <= T["target_max"] else "STRETCH" if pr <= T["stretch_max"] else "CURIOSITY")
    br_ = l.get("beds_range")
    beds_ok = (br_[1] >= C["beds_min"]) if (l.get("beds") is None and br_) else (l.get("beds") is None or l["beds"] >= C["beds_min"])   # unknown beds: kept, shown as not listed yet
    l["in_area"] = in_area
    l["eligible"] = in_area and beds_ok
    l["match"] = is_match_buy(l, C) if is_buy(C) else is_match(l, C)
    if is_buy(C): l["pets"] = "n/a"   # pets are a rental filter only
    l["ideal"] = l["match"] and (l.get("baths") or 0) >= C["baths"]["ideal"]
    # scam flags (phrases + photo/address mismatch); comps flag added later
    S, flags = C.get("scam_flags", {}), []
    if has(t, S.get("phrases")): flags.append("suspicious payment/deposit wording")
    if S.get("check_address_photo_mismatch") and l.get("photo_alt") and l.get("address"):
        n1, n2 = re.match(r"\s*(\d+)", l["photo_alt"]), re.match(r"\s*(\d+)", l["address"])
        if n1 and n2 and n1.group(1) != n2.group(1): flags.append("photo/address mismatch")
    l["flags"] = flags
    return l

def comps_note(l, pool, C):
    """median $/listing among seen eligible listings with same beds in same city/zip prefix; needs >=3."""
    if l.get("price") is None or l.get("beds") is None: return None
    sim = [x["price"] for x in pool if x is not l and x.get("beds") == l["beds"] and x.get("price") and x.get("zip") and l.get("zip") and x["zip"][:4] == l["zip"][:4]]
    if len(sim) < 5: return None
    med = statistics.median(sim)
    pct = (l["price"] - med) / med * 100
    if pct <= -C.get("scam_flags", {}).get("below_comps_pct", 999): l["flags"].append(f"price {abs(pct):.0f}% below similar — verify before paying anything")
    return f"{'+' if pct>=0 else ''}{pct:.0f}% vs median ${med:,.0f} of {len(sim)} similar {int(l['beds'])}bd seen"

def addr_key(a):
    """normalize '241 Example Street - A, Los Angeles, CA 90001' == '241 Example Street Unit A, ...'"""
    if not a: return None
    parts = [p.strip() for p in a.lower().split(",")]
    if len(parts) < 3: return None
    st = " ".join(parts[:-2])
    st = re.sub(r"\b(street|st|avenue|ave|drive|dr|road|rd|lane|ln|place|pl|boulevard|blvd|unit|apt|way)\b", " ", st)
    toks = re.sub(r"[#\-.]", " ", st).split()
    return " ".join(toks) if toks and toks[0].isdigit() else None

def cross_source(l, S, ak):
    """A home already alerted under another id (e.g. a PM feed, then a Zillow email hours later).
    -> None (not seen: alert as new), ("skip", id) (same or higher price: attach quietly), ("lower", id, old_price).
    No address, or one we can't normalize, never matches: it alerts as usual (we never guess a match)."""
    if not ak: return None
    hit = next((k for k, v in S.items() if k != l["id"] and v.get("addr") == ak and not v.get("gone_since")), None)
    if not hit: return None
    old = S[hit].get("price")
    if l.get("price") is not None and old and l["price"] < old: return ("lower", hit, old)
    return ("skip", hit)

def merge_dupes(L, C):
    """Same unit listed by two feeds (e.g. AppFolio + TenantTurner) -> one alert, fields combined."""
    out, by = [], {}
    for l in L:
        k = addr_key(l.get("address"))
        if k and k in by:
            b = by[k]
            took_link = not b.get("url") and l.get("url")   # the link comes from this source, so "Via" must name it
            for f in ("url", "showing_url", "listed_on", "sqft", "photo", "ptype_raw", "apply_url", "agent_url"):
                b[f] = b.get(f) or l.get(f)
            if l["garage"] == "yes" and b["garage"] == U: b["garage"] = "yes"
            if b["layout"] == U: b["layout"] = l["layout"]
            if b["pets"] == U or l["pets"] != b["pets"]:
                b["pets"] = l["pets"] if b["pets"] == U else (b["pets"] if l["pets"] == U else f"{b['pets']} / {l['pets']} (feeds disagree)")
            if l["id"] != b["id"] and l["id"] not in b["also_ids"]: b["also_ids"].append(l["id"])   # never self, no repeats
            b["source"] = f"{l['source']} + {b['source']}" if took_link else b["source"] + f" + {l['source']}"   # first source = the one the link opens
            if l.get("price") and b.get("price") and l["price"] != b["price"]:
                lo, hi = sorted([(b["price"], b["source"].split(" + ")[0]), (l["price"], l["source"])])
                b["price"] = lo[0]; b.setdefault("alt_prices", []).append((hi[1], hi[0]))
            b["match"] = is_match_buy(b, C) if is_buy(C) else is_match(b, C)
            b["ideal"] = b["match"] and (b.get("baths") or 0) >= C["baths"]["ideal"]
            continue
        l["also_ids"] = []
        if k: by[k] = l
        out.append(l)
    return out

# ---------- message (calm style, approved 2026-10-26) ----------
NUMW = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine"}
TYPES = [("townhome", r"townho(me|use)"), ("house", r"single[- ]family|\bhouse\b|\bhome\b(?! ?owner)"),
         ("condo", r"\bcondo"), ("duplex", r"duplex|triplex|fourplex"), ("cottage", r"cottage"),
         ("ADU", r"\bADU\b"), ("apartment", r"apartment|\bapt\b")]

def ptype(l):
    t = f"{l.get('title','')} {l.get('ptype_raw') or ''}"
    for name, rx in TYPES:
        if re.search(rx, t, re.I): return name
    return None

def money(v): return f"${v:,.0f}"
def rng(r, f=lambda v: f"{v:g}"): return f"{f(r[0])}-{f(r[1])}"
def price_range_text(l, C):
    r = l.get("price_range"); return f"${r[0]:,.0f}-${r[1]:,.0f}{per(C)}" if r and l.get("price") is None else None
def beds_text(l):
    b, r = l.get("beds"), l.get("beds_range")
    if b is not None: return "Studio" if b == 0 else f"{int(b)} bed"
    return f"{rng(r)} bed" if r else None
def baths_text(l):
    b, r = l.get("baths"), l.get("baths_range")
    if b is not None: return f"{'%g' % b} bath"
    return f"{rng(r)} bath" if r else None

def tier_words(p, C):
    T = C["price_tiers"]
    if p is None: return None
    if p <= T["target_max"]: return "in your target range"
    if p < T["stretch_max"]: return "in your stretch range"
    if p == T["stretch_max"]: return "top of your stretch range"
    return "above your usual range"

def bb(l):
    s = ", ".join(x for x in [beds_text(l), baths_text(l)] if x)
    t = ptype(l)
    return f"{s} {t}".strip() if t else s

def own_spelling(name, C=None):
    """A city as the user spelled it in their search (e.g. 'Vista del Sol'), never the source's casing."""
    if not name: return name
    for c in ((C or CFG).get("area") or {}).get("cities") or []:
        if c.lower() == name.strip().lower(): return c
    return name

def area(l):
    city = re.search(r",\s*([A-Za-z .]+),\s*[A-Z]{2}\b", l.get("address") or "")
    name = l.get("neighborhood") or (city.group(1).strip() if city else l.get("city"))
    name = own_spelling(name)
    return ", ".join(x for x in [name, l.get("zip")] if x) or None

def avail(l):
    a = (l.get("available") or "").strip()
    if not a: return None
    if a.lower() == "now": return "available now"
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:T.*)?", a)   # ISO dates from feeds -> 12/1/26
    if m:
        y, mo, d = m.groups()
        if date(int(y), int(mo), int(d)) <= date.today(): return "available now"
        return f"available {int(mo)}/{int(d)}/{y[2:]}"
    return f"available {a}"

CFG = {}
def via_line(l):
    """'Via Redfin' / 'Via Tim Carr Group': the first source that carried it (never guessed)."""
    src = re.sub(r"\s*\(.*?\)", "", (l.get("source") or "").split(" + ")[0]).strip()
    if not src or src.lower().startswith("portal"): return None
    return style.fit(f"Via {src}", "Via a property manager" if " " in src else None) if len(f"Via {src}") > style.MAX else f"Via {src}"

def posted_line(l, now=None):
    """'Posted about 20 min ago' only when the source gives a real posting time (posted_ts, epoch seconds)."""
    ts = l.get("posted_ts")
    if not isinstance(ts, (int, float)) or ts <= 0: return None
    m = int(((now or time.time()) - ts) // 60)
    if m < 0 or m >= 24 * 60: return None
    if m < 60: return f"Posted about {max(m, 1)} min ago"
    h = m // 60; return f"Posted about {h} hour{'s' if h > 1 else ''} ago"

def buy_details(l, C):
    """For-sale details, one short line each; unknowns as 'X: not listed' (style.UNKNOWN). Never guessed."""
    known, unknown = [], []
    st = {"coming_soon": "Coming soon", "back_on_market": None, "price_cut": None, "new": None,
          "pending": "Pending", "sold": "Sold"}.get(l.get("status"))
    if st: known.append(st)
    if l.get("open_house"):
        oh = f"Open house {l['open_house']}"
        known.append(oh if len(oh) <= style.MAX else "Open house listed")
    h = l.get("hoa")
    if h is not None: known.append("No HOA" if h == 0 else f"HOA ${h:,.0f}/mo")
    if l.get("sqft_buy"): known.append(f"{l['sqft_buy']:,.0f} sq ft")
    if l.get("lot"): known.append("Lot " + l["lot"].replace(" sq ft lot", " sq ft"))
    if l.get("year_built"): known.append(f"Built {int(l['year_built'])}")
    if l.get("dom") is not None: known.append(f"{int(l['dom'])} days on market")
    for k, (src, p) in enumerate(l.get("alt_prices") or []):
        known.append(f"Also {money(p)} on {src}" if len(f"Also {money(p)} on {src}") <= style.MAX else "Another site lists it lower")
    if l.get("price") is None: unknown.insert(0, "price")
    if l.get("beds") is None: unknown.insert(0, "beds")
    if C.get("show_source", True):
        v = via_line(l); known.append(v) if v else None
    out = [k[0].upper() + k[1:] for k in known]
    return out + [f"{u[0].upper() + u[1:]}: {style.UNKNOWN}" for u in unknown]

def details(l, C=None):
    """Only what this person cares about: garage if they asked for one, pets if they have pets."""
    C = C or CFG
    if is_buy(C): return buy_details(l, C)
    C = C or CFG
    P = C.get("pets") or {}
    has_pet, esa = bool(P.get("dog") or P.get("cat") or assistance_animal(C)), assistance_animal(C)
    M = C.get("match") or {}
    nice = M.get("nice_to_have") or []
    want_garage = M.get("garage_min", 0) > 0 or "garage" in nice
    want_layout = bool(M.get("layout_any")) or "layout" in nice
    known, unknown = [], []
    g = l.get("garage")   # style keeps "X: value" for unknowns only, so known values read as plain words
    if want_garage: known.append("has a garage") if g == "yes" else known.append("no garage") if g == "no" else None   # shown only when stated
    if want_layout:   # first label only, so the line stays short; never guessed
        lay = (l.get("layout") or U).split(",")[0].strip()
        if lay != U: known.append({"first floor": "ground floor", "townhome/2-story": "townhome"}.get(lay, lay))
    a = avail(l); known.append(a) if a else None   # shown only when stated
    unknown += [k for k, f in (("rent", "price"), ("beds", "beds"), ("baths", "baths")) if l.get(f) is None and not l.get(f + "_range")]   # Ern's list: rent, beds, baths, pets
    for k, (src, p) in enumerate(l.get("alt_prices") or []):   # same home, another source, another price
        known.append(f"Also {money(p)}{'/mo' if (C.get('mode') != 'buy') else ''} on {src}" if len(f"Also {money(p)}/mo on {src}") <= style.MAX else f"Also {money(p)}{'/mo' if (C.get('mode') != 'buy') else ''} elsewhere")
    p = l["pets"]
    esa_s = ["Assistance animals may be ok", "Worth asking"] if esa else ["Worth asking"]   # one fact line each (fits style.check in a fact group)
    if not has_pet: pass
    elif p == "dogs ok": known.append("dogs allowed")
    elif p.startswith("no dogs"): known += ["no dogs listed"] + esa_s
    elif p == "cats only": known += ["cats only listed"] + esa_s
    elif p == U: unknown.append("pets")
    else: known.append(f"pets: {p.lower()}")
    if has_pet and "feeds disagree" in p: known[-1] = "pet rules differ by site"
    if C.get("show_source", True):
        v = via_line(l); known.append(v) if v else None
    pl = posted_line(l); known.insert(0, pl) if pl else None
    out = [k[0].upper() + k[1:] for k in known]
    for u in unknown:   # one line each, so every line stays short
        out.append(f"{u[0].upper() + u[1:]}: {style.UNKNOWN}")
    return out

def street(l):
    a = l.get("address") or ""
    return re.sub(r"\s+", " ", a.split(",")[0]).strip() or None

def market_words(l, pool, C):
    if l.get("price") is None or l.get("beds") is None or not l.get("zip"): return None
    sim = [x["price"] for x in pool if x is not l and x.get("beds") == l["beds"] and x.get("price") and (x.get("zip") or "")[:4] == l["zip"][:4]]
    if len(sim) < 8: return None
    pct = (l["price"] - statistics.median(sim)) / statistics.median(sim) * 100
    n = f"{int(l['beds'])}-beds"
    if pct <= -C.get("scam_flags", {}).get("below_comps_pct", 999):
        l["flags"].append("The price is much lower than similar places. Please see it in person before paying anything.")
    if abs(pct) < 5: return f"Priced like nearby {n}."
    if pct < -15: return f"Well below nearby {n}."
    if pct < 0: return f"A bit below nearby {n}."
    if pct > 15: return f"Well above nearby {n}."
    return f"A bit above nearby {n}."

GENTLE = {"suspicious payment/deposit wording": "The ad mentions paying or wiring money early. Worth seeing it in person first.",
          "photo/address mismatch": "The photo and address don't quite line up. Worth double-checking."}

def per(C): return "" if C.get("mode") == "buy" else "/mo"

def summary_block(a, C):
    l = a["l"]
    lines = [x for x in [bb(l), area(l)] if x]
    tw = tier_words(l.get("price"), C)
    if a["reason"] in ("price_drop", "relist_lower") and a.get("was"):
        lines.append(f"Now {money(l['price'])}{per(C)} (was {money(a['was'])})")
        if tw: lines.append(tw[0].upper() + tw[1:])
    elif l.get("price") is not None:
        lines.append(f"{money(l['price'])}{per(C)}")
        if tw: lines.append(tw[0].upper() + tw[1:])
    elif price_range_text(l, C):
        lines.append(price_range_text(l, C))
    return lines   # unknown rent goes last, with the other unknowns (details)

CAUTION = {"price": "It's far below similar places.", "suspicious payment/deposit wording": "It wants money before a tour.",
           "photo/address mismatch": "Photo and address don't match."}
def extras(a):
    """Market words, plus at most ONE gentle caution line (scam signals)."""
    l, out = a["l"], []
    if a.get("market"): out.append(a["market"])
    fl = ["price" if "lower than similar" in f or "below similar" in f else f for f in l["flags"]]
    fl = [f for f in fl if f in CAUTION]
    if len(fl) == 1: out.append(CAUTION[fl[0]])
    if fl: out.append("See it before paying anything.")   # the one caution close, every time
    return out

def links(l):
    out = [l["url"]] if l.get("url") else []   # no link, no line
    if l.get("showing_url") and l["showing_url"] != l.get("url"):
        out += ["Showing link from the listing:", l["showing_url"]]
    act = (l.get("agent_url"), "Agent link from the listing:") if is_buy(CFG) else (l.get("apply_url"), "Apply link from the listing:")
    if act[0] and act[0] not in (l.get("url"), l.get("showing_url")):
        out += [act[1], act[0]]   # shown for the person to tap; the bot never opens, applies or contacts
    return out

HEAD_BUY = {"new": "New home that fits", "price_drop": "A price came down", "relist": "Back on the market",
            "relist_lower": "Back, and lower", "current": "New home that fits"}
HEAD = {"new": "New place that fits", "price_drop": "A price came down", "relist": "Back on the market",
        "relist_lower": "Back, and lower", "current": "New place that fits"}
LABEL = {"price_drop": "A price came down", "relist": "Back on the market", "relist_lower": "Back, and lower"}   # roundup item labels = the single-alert headers

ABBR = {"avenue": "Ave", "drive": "Dr", "street": "St", "road": "Rd", "lane": "Ln", "boulevard": "Blvd", "place": "Pl",
        "court": "Ct", "circle": "Cir", "terrace": "Ter", "parkway": "Pkwy", "highway": "Hwy"}
def street_line(l):
    """The street address that labels the link: whole if it fits one line, else with short suffixes.
    Never cut mid-name; if it still doesn't fit, it stays whole (an address is a fact, not prose)."""
    st = street(l)
    if not st or len(st) <= style.MAX: return st
    return re.sub(r"\b(" + "|".join(ABBR) + r")\b", lambda m: ABBR[m.group(1).lower()], st, flags=re.I)

def where_block(l):
    """One address/link layout everywhere: the street address on its own line, its link alone right under."""
    st = street_line(l)
    if not st and l.get("city"):   # street undisclosed (e.g. Zillow '(undisclosed Address), Los Angeles, CA 90001'): city, then the unknown
        return style.Group([l["city"], "Address not shown"] + links(l))
    return style.Group([st or "Address not shown"] + links(l))
CLOSE = style.CLOSE

PART_MAX = 1500   # chars per text: under the common 1,600-char carrier cap for long SMS; iMessage itself has no smaller limit
def shown(alerts, C):
    """Every place a roundup shows, in shown order (reply numbers attach to exactly these). Nothing is left out."""
    if len(alerts) <= 1: return list(alerts)
    return rank(alerts, C)

def area_name(l):
    a = area(l)
    return a.split(",")[0].strip() if a else None

def fact_lines(l, C, split=None):
    """Roundup facts: '$X/mo, N bed, B bath' (baths only when known), then the area.
    Same shape for every entry in one text: all on one line, or (split) the area on its own line."""
    beds = beds_text(l)
    if beds and baths_text(l): beds += ", " + baths_text(l)
    pr = f"{money(l['price'])}{per(C)}" if l.get("price") is not None else price_range_text(l, C)
    ar = area_name(l)
    one = ", ".join(x for x in [pr, beds, ar] if x)
    if split is None: split = len(one) > style.MAX
    if not split: return [one] if one else []
    pb = ", ".join(x for x in [pr, beds] if x)
    if len(pb) > style.MAX: return [x for x in [pr, beds, ar] if x]   # a price range: price, beds, area, one per line
    return [x for x in [pb, ar] if x]

def needs_split(alerts, C):
    return any(len(", ".join(fact_lines(a["l"], C, split=False))) > style.MAX for a in alerts)

def render_parts(alerts, C, head=None):
    """one alert -> [single text]; several -> every place, numbered, split into 'Part i of n' texts
    only when one text would pass PART_MAX. A place's entry is never split across texts."""
    if len(alerts) == 1:
        a = alerts[0]; l = a["l"]
        G = style.Group
        sb = summary_block(a, C)
        blocks = [[head or (HEAD_BUY if is_buy(C) else HEAD)[a["reason"]]], G(sb), G(details(l, C))]
        if extras(a): blocks.append(extras(a))
        blocks += [where_block(l), [CLOSE]]
        return [style.text(blocks)]   # the one shared formatter (style.py)
    alerts = shown(alerts, C); total = len(alerts)
    kinds = {a["reason"] for a in alerts}
    noun = "homes" if is_buy(C) else "places"
    head = head or (f"{NUMW.get(total, total)} new {noun} today" if kinds <= {"new", "current"} else f"{NUMW.get(total, total)} updates today")
    entries = entries_for(alerts, C)
    return pack([[head]], entries, [[CLOSE]])

def entries_for(alerts, C):
    """The one roundup entry: 'N. address' / facts line / its own link (+ a label or caution line if any)."""
    out = []; sp = needs_split(alerts, C)
    for i, a in enumerate(alerts, 1):
        l = a["l"]
        lab = LABEL.get(a["reason"])
        st = street_line(l) or (area_name(l) or "Address not shown")
        b = [f"{i}. {st}"] + ([lab] if lab else []) + fact_lines(l, C, sp)
        e = [style.Group(b + [l["url"]] if l.get("url") else b)]
        cau = [x for x in extras(a) if x not in (a.get("market"),)]
        if cau: e.append(cau)
        out.append(e)
    return out

def pack(lead, entries, tail):
    """lead blocks, every entry, tail blocks; split into 'Part i of n' texts only past PART_MAX, never inside an entry."""
    def build(groups, n):
        out = []
        for k, g in enumerate(groups, 1):
            bl = ([[f"Part {k} of {n}"]] if n > 1 else []) + (list(lead) if k == 1 else [])
            for e in g: bl += e
            if k == n: bl += list(tail)
            out.append(style.text(bl))
        return out
    def size(g, first, n):
        bl = ([[f"Part {n} of {n}"]] if n > 1 else []) + (list(lead) if first else [])
        for e in g: bl += e
        return len(style.text(bl + list(tail)))
    n = 1
    while True:
        groups, cur = [], []
        for e in entries:
            if cur and size(cur + [e], not groups, n) > PART_MAX: groups.append(cur); cur = []
            cur.append(e)
        groups.append(cur)
        if len(groups) == n: break
        n = len(groups)
    return build(groups, n)

def render(alerts, C, head=None):
    """the whole message as one string (parts joined); senders use render_parts()."""
    return "\n\n".join(render_parts(alerts, C, head))

def _join(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]

def reflect(C):
    """The shared search in plain words, one short line each (member welcome, setup step 1)."""
    out = []
    cities = C["area"].get("cities") or []
    rest = list(cities)   # every city, never dropped: split across lines if needed
    while rest:
        k = len(rest)
        while k > 1 and len(_join(rest[:k]) if k == len(rest) else ", ".join(rest[:k]) + ",") > style.MAX: k -= 1
        out.append(_join(rest[:k]) if k == len(rest) else ", ".join(rest[:k]) + ","); rest = rest[k:]
    out.append(f"{C['beds_min']}+ bed" + ("s" if C["beds_min"] != 1 else ""))
    T = C["price_tiers"]; per_ = per(C)
    out += [f"Up to ${T['target_max']:,}{per_}", f"Stretch to ${T['stretch_max']:,}{per_}"]
    m = C.get("match") or {}
    lay = {"first_floor": "ground floor", "single_story": "single story", "two_story_townhome": "townhome"}
    L = [lay.get(x, x) for x in m.get("layout_any") or []]
    if m.get("garage_min", 0) > 0: out.append("A garage")
    if L:
        t = L[0] if len(L) == 1 else ", ".join(L[:-1]) + " or " + L[-1]
        if len(t) <= style.MAX: out.append(t[0].upper() + t[1:])
        else: out += [L[0][0].upper() + L[0][1:]] + [f"Or {x}" for x in L[1:]]   # one whole option per line
    if is_buy(C):   # buy: HOA max and home types are the only other filters
        B = C.get("buy") or {}
        if B.get("hoa_max") is not None: out.append(f"HOA up to ${B['hoa_max']:,}/mo")
        ht = B.get("home_types") or []
        if ht and len(ht) < 3:
            t = " or ".join(ht); out.append((t[0].upper() + t[1:]) if len(t) <= style.MAX else ht[0].capitalize())
        return out
    P = C.get("pets") or {}
    pet = P.get("dog") or P.get("cat")
    if pet:
        t = f"The {pet}" + (" (assistance)" if assistance_animal(C) else "")
        if len(t) <= style.MAX: out.append(t)
        else:   # one whole thought per line: the pet, then its ESA letter
            out.append(f"The {pet}" if len(f"The {pet}") <= style.MAX else "A pet")
            if assistance_animal(C): out.append("An assistance animal")
    return out

TIER_KEY = {"in your target range": "target", "in your stretch range": "stretch",
            "top of your stretch range": "stretch", "above your usual range": "above"}
def rank(matches, C):
    """Best fits first: ideal baths, then lowest price."""
    ideal = (C.get("baths") or {}).get("ideal", 2)
    return sorted(matches, key=lambda a: ((a["l"].get("baths") or 0) < ideal, a["l"].get("price") or 1e9))

def snapshot_parts(matches, n_checked, C, top=None, header="What's out there now"):
    """End-of-setup snapshot from the quiet first run: real counts, then every current match as the roundup entry."""
    G = style.Group
    M = rank(matches, C)
    cnt = {}
    for a in M:
        k = TIER_KEY.get(tier_words(a["l"].get("price"), C), "unknown"); cnt[k] = cnt.get(k, 0) + 1
    lab = {"target": "in your target range", "stretch": "in your stretch range",
           "above": "above your usual range", "unknown": "with rent not listed yet"}
    lead = [[header], [f"I checked {n_checked:,} places."]]
    tail = [["From here, I'll stay quiet.", "I'll text when a new one fits."]]
    if not M: return [style.text(lead + [["Nothing fits today."]] + tail)]
    lead.append(G([f"{len(M)} fit your search right now:"] +
                  [f"{cnt[k]} {lab[k]}" for k in ("target", "stretch", "above", "unknown") if k in cnt]))
    lead.append([f"Here they all are:" if len(M) > 1 else "Here it is:"])
    return pack(lead, entries_for(M, C), tail)

def snapshot(matches, n_checked, C, top=None, header="What's out there now"):
    return "\n\n".join(snapshot_parts(matches, n_checked, C, top, header))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--criteria", default="CRITERIA.yaml"); ap.add_argument("--state", default="state.json")
    ap.add_argument("--dry-run", action="store_true", help="don't save state"); ap.add_argument("--all", action="store_true", help="print every eligible listing, ignore state")
    ap.add_argument("--seed", action="store_true", help="quiet first run: save everything as seen, print nothing")
    ap.add_argument("--json", action="store_true", help="emit alerts as JSON for notify.py")
    ap.add_argument("--bundle", action="store_true", help="render all alerts as one numbered text")
    ap.add_argument("--sample", action="store_true", help="also save current matches to out/sample.json (proof-of-life sample)")
    ap.add_argument("--matches-only", action="store_true", help="only MATCH listings")
    a = ap.parse_args()
    for _d in ("out", "logs", "inbox"): os.makedirs(_d, exist_ok=True)   # exported copies ship without these
    C = yaml.safe_load(open(a.criteria))
    st = json.load(open(a.state)) if os.path.exists(a.state) else {"listings": {}}
    S, now, today = st["listings"], time.time(), date.today().isoformat()
    allL, report = [], []
    for src in C["sources"]:
        if src.get("enabled") is False or src["type"] not in PARSERS:
            report.append((src["name"], "skipped", src.get("note", src["type"]))); continue
        if re.search(r"SUBDOMAIN|CUSTOMER_ID|YOUR_|EXAMPLE", str(src.get("url", ""))):
            report.append((src["name"], "skipped", "placeholder URL; add your own")); continue
        try:
            got = [classify(l, C) for l in PARSERS[src["type"]](dict(src, report=not a.dry_run) if src["type"] == "email" else src)]
            if src["type"] == "email" and got and not a.dry_run and not os.path.exists(os.path.join("out", "email_proven.json")):   # first real alert parsed
                os.makedirs("out", exist_ok=True)
                json.dump({"first": time.strftime("%F %T %Z"), "source": got[0]["source"], "count": len(got)}, open(os.path.join("out", "email_proven.json"), "w"))
            if src["type"] == "email" and got and not a.dry_run:   # per-site proof for "Sites working so far" (style.proven_sites)
                _pf = os.path.join("out", "sources_proven.json"); _pd = json.load(open(_pf)) if os.path.exists(_pf) else {}
                _new = {l.get("source") for l in got if l.get("source") and l.get("source") not in _pd}
                if _new: os.makedirs("out", exist_ok=True); _pd.update({n: {"first": time.strftime("%F %T %Z")} for n in _new}); json.dump(_pd, open(_pf, "w"), indent=1)
            allL += got
            report.append((src["name"], "ok", f"{len(got)} listings, {sum(l['eligible'] for l in got)} in-area 2bd+, {sum(l['match'] for l in got)} MATCH"))
            if not got and st.get("health", {}).get(src["name"], {}).get("last_count", 0) > 0: raise RuntimeError("0 listings (page may have changed)")
            st.setdefault("health", {})[src["name"]] = {"last_count": len(got)}
        except Exception as e:
            report.append((src["name"], "ERROR", str(e)[:120]))
            h = st.setdefault("health", {}).setdefault(src["name"], {})
            h.setdefault("failing_since", now)   # quiet retries every run; owner told once after a day
            if now - h["failing_since"] > 86400 and not h.get("told") and not a.dry_run:
                h["told"] = True
                json.dump({"source": src["name"], "since": __import__("features").local_str(C, "%a %-I:%M %p", h["failing_since"])},
                          open(os.path.join(os.path.dirname(os.path.abspath(a.state)), "out", "outage_pending.json"), "w"))
        time.sleep(1)
    _ids = set(); allL = [l for l in allL if not (l["id"] in _ids or _ids.add(l["id"]))]   # two sources reading one inbox: same listing once
    allL = merge_dupes(allL, C)
    for l in allL: l["also_ids"] = [x for x in l.get("also_ids", []) if x != l["id"]]   # never 'seen' via its own id (was: 0 alerts after an empty first run)
    msgs, seen_ids, offm = [], set(), []
    for l in allL:
        seen_ids.add(l["id"]); seen_ids.update(l.get("also_ids", []))
        prev = S.get(l["id"])   # read BEFORE marking other ids seen (same email twice must still alert)
        for oid in l.get("also_ids", []):
            if oid != l["id"]: S.setdefault(oid, {"first_seen": today, "price_history": []}).update(last_seen=today, gone_since=None)
        ak = addr_key(l.get("address"))
        if prev is None and ak:   # relisted under a new id: same street address, gone a while
            old = next((k for k, v in S.items() if v.get("addr") == ak and v.get("gone_since")), None)
            if old: prev = dict(S[old])
        dup = cross_source(l, S, ak) if prev is None else None   # One home, one text (across runs and sources)
        if dup:
            S[dup[1]].setdefault("also_ids", []); S[dup[1]]["also_ids"] = sorted(set(S[dup[1]]["also_ids"]) | {l["id"]})
            if dup[0] == "skip":   # same home, same or higher price: attach the new source quietly
                S[l["id"]] = {"first_seen": today, "price_history": [[today, l.get("price")]] if l.get("price") else [], "price": l.get("price"),
                              "last_seen": today, "gone_since": None, "eligible": l["eligible"], "addr": ak, "dup_of": dup[1]}
                continue
            prev = {"price": dup[2], "price_history": [], "first_seen": today}   # lower elsewhere: a normal price-drop alert
        if prev is None and l.get("email_was_price") and l.get("price") and l["email_was_price"] > l["price"]:
            prev = {"price": l["email_was_price"], "price_history": [], "first_seen": today}   # the alert email itself says 'was $X'
        reason = None
        if l.get("status") in ("pending", "sold"):   # buy: never a new alert; a shortlisted home gets one calm note (notify.py offmarket)
            offm.append({"id": l["id"], "also_ids": l.get("also_ids", []) + ([dup[1]] if dup else []), "status": l["status"],
                         "where": street(l) or "a saved home"})
            S[l["id"]] = dict(prev or {"first_seen": today, "price_history": []}, last_seen=today, gone_since=None, status=l["status"], addr=ak)
            continue
        if prev is None and l.get("status") == "back_on_market": reason = "relist"
        elif prev is None: reason = "new"
        elif prev.get("gone_since") and (now - prev["gone_since"]) / 86400 >= C.get("relist_after_days", 3) \
                and l.get("price") is not None and prev.get("price") and l["price"] < prev["price"]: reason = "relist_lower"
        elif l.get("price") is not None and prev.get("price") and l["price"] < prev["price"]: reason = "price_drop"
        elif prev.get("gone_since") and (now - prev["gone_since"]) / 86400 >= C.get("relist_after_days", 3): reason = "relist"
        was_price = prev.get("price") if prev else None   # read before rec.update() below overwrites it (rec is prev)
        rec = prev or {"first_seen": today, "price_history": []}
        if l.get("price") is not None and (not rec["price_history"] or rec["price_history"][-1][1] != l["price"]):
            rec["price_history"].append([today, l["price"]])
        rec.update(price=l.get("price"), last_seen=today, gone_since=None, eligible=l["eligible"], addr=ak)
        S[l["id"]] = rec
        if not l["eligible"] or (reason is None and not a.all): continue
        a_ = {"l": l, "reason": reason or "current", "was": was_price}
        if C.get("market_context", True):
            a_["market"] = market_words(l, [x for x in allL if x["eligible"]], C)
        if a.matches_only and not l["match"]: continue
        msgs.append(a_)
    for k, v in S.items():
        if k not in seen_ids and not v.get("gone_since") and not k.startswith("email:"): v["gone_since"] = now
    if not a.dry_run:
        json.dump(st, open(a.state, "w"), indent=1)
        if offm:   # pending/sold events for notify.py offmarket (only people who shortlisted the home hear about it)
            of = os.path.join("out", "offmarket.json"); os.makedirs("out", exist_ok=True)
            old = json.load(open(of)) if os.path.exists(of) else []
            json.dump(old + [e for e in offm if e["id"] not in {o["id"] for o in old}], open(of, "w"), indent=1)
        os.makedirs("out", exist_ok=True)   # criteria hygiene: today's in-area pool (trade-off counts, near misses)
        json.dump([{k: l.get(k) for k in ("id", "price", "beds", "baths", "garage", "layout", "pets", "match")} | {"misses": misses(l, C)}
                   for l in allL if l.get("in_area")], open(os.path.join("out", "pool.json"), "w"))
    print("== SOURCES ==", file=sys.stderr)
    for r in report: print(" | ".join(r), file=sys.stderr)
    msgs.sort(key=lambda m: (not m["l"]["match"], m["l"].get("price") or 1e9))
    print(f"== {len(msgs)} alert(s), {sum(m['l']['match'] for m in msgs)} MATCH ==", file=sys.stderr)
    if a.seed or a.sample:   # proof of life: save real current matches for notify.py sample
        os.makedirs("out", exist_ok=True)
        json.dump([{"reason": "current", "was": None, "market": m.get("market"),
                    "l": {k: v for k, v in m["l"].items() if k != "text"}} for m in msgs if m["l"]["match"]],
                  open(os.path.join("out", "sample.json"), "w"), indent=1)
    if a.seed:
        print(f"quiet first run: saved {len(seen_ids)} current listings; nothing to send", file=sys.stderr); return
    if a.json:   # for notify.py (bundles within the hour)
        print(json.dumps([{"reason": m["reason"], "was": m["was"], "market": m.get("market"),
                           "l": {k: v for k, v in m["l"].items() if k != "text"}} for m in msgs]))
    elif a.bundle and len(msgs) > 1:
        print(render(msgs, C))
    else:
        print("\n---\n".join(render([m], C) for m in msgs))

if __name__ == "__main__": main()
