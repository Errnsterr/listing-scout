#!/usr/bin/env python3
"""Still listed? A once-a-day, polite check of each email-sourced place's clean link (v1.2.9).

  python3 src/gonecheck.py              # dry run: check and report, change nothing
  python3 src/gonecheck.py --apply      # also mark clear 'gone' places (run by the loop at most once a day)

One plain GET per place (no cookies, no retries), spaced out. A place is marked gone ONLY on a clear signal:
404/410, a redirect to a search or off-market page, or the page itself saying off market / no longer available /
rented. A 403, 429, 5xx, block page, captcha or timeout is UNKNOWN: never gone, and never worked around.
Gone places come off the shortlist and the reply-by-number lists; every change is logged in logs/gonecheck.log.
It never texts anyone and never edits state.json: marks live in out/link_gone.json (not 'gone_since'), so the
'Still available?' text (notify.py gone) and relist alerts never fire on them, and the loop's own writes can't race it."""
import os, sys, json, re, time, random, urllib.request, urllib.error, urllib.parse
_SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC
sys.path.insert(0, _SRC)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
GAP = (4.0, 7.0)          # seconds between requests, randomized: polite
TIMEOUT = 12
HOSTS = ("www.zillow.com", "www.redfin.com", "hotpads.com", "www.hotpads.com")
LISTING = {"www.zillow.com": re.compile(r"^/(homedetails/|apartments/[^/]+/[^/]+/[A-Za-z0-9]+/?$|b/)"),
           "www.redfin.com": re.compile(r"/(home|apartment)/\d+"),
           "hotpads.com": re.compile(r"/pad(/|$)"), "www.hotpads.com": re.compile(r"/pad(/|$)")}
BLOCK = re.compile(r"captcha|px-captcha|press (&|and) hold|access to this page has been denied|are you a human|unusual traffic|request blocked|cf-chl|attention required", re.I)
GONE_TEXT = re.compile(r"\bno longer available\b|\bthis (?:home|property|listing|unit|rental) is off[- ]market\b|\bstatus:?\s*off[- ]market\b|"
                       r"\b(?:has been|was|is now|is) rented\b|\bthis (?:home|rental|unit|listing) (?:is|was) (?:no longer|not) (?:listed|available)\b", re.I)

def visible_text(body):
    """What a person sees: no scripts, styles, JSON blobs or tags (site code carries template strings like
    'Sorry, {address} is no longer available.' on every page)."""
    t = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", " ", body or "")
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)

def classify_response(status, location, body, url):
    """-> ('gone', why) | ('live', why) | ('unknown', why). Pure; tests call it directly."""
    host = urllib.parse.urlparse(url).netloc.lower()
    if status in (404, 410): return "gone", f"HTTP {status}"
    if status in (301, 302, 303, 307, 308):
        if not location: return "unknown", f"HTTP {status} without a destination"
        dest = urllib.parse.urljoin(url, location); p = urllib.parse.urlparse(dest)
        if p.netloc.lower() not in HOSTS: return "unknown", f"redirect off-site ({p.netloc})"
        if re.search(r"off[-_]?market|not[-_]?available|sold", p.path + "?" + p.query, re.I): return "gone", "redirect to an off-market page"
        rx = LISTING.get(p.netloc.lower())
        if rx and not rx.search(p.path): return "gone", "redirect to a search page"
        return "follow", dest
    if status == 200:
        if BLOCK.search(body or ""): return "unknown", "block or captcha page"
        vis = visible_text(body)
        if GONE_TEXT.search(vis) and "{" not in GONE_TEXT.search(vis).group(0): return "gone", "page says it's off market or rented"
        return "live", "listed"
    return "unknown", f"HTTP {status}"

def _get(url):
    class _No(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k): return None
    op = urllib.request.build_opener(_No())
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "en-US"})
    try:
        r = op.open(req, timeout=TIMEOUT)
        return r.status, r.headers.get("Location"), r.read(400000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.headers.get("Location") if e.headers else None), ""
    except Exception as e:
        return None, None, type(e).__name__

def check(url, get=_get):
    """Follow up to 4 same-site redirects, one plain GET each."""
    for _ in range(4):
        st, loc, body = get(url)
        if st is None: return "unknown", f"no answer ({body})"
        verdict, why = classify_response(st, loc, body, url)
        if verdict != "follow": return verdict, why
        url = why
    return "unknown", "too many redirects"

GONE_FILE = os.path.join(HERE, "out", "link_gone.json")
def load_gone():
    try: return json.load(open(GONE_FILE))
    except Exception: return {}

def candidates(S, links, G=None):
    """Email-sourced places we'd still show: eligible, not a duplicate, not already marked, with a clean link."""
    out = []
    for k, v in S.items():
        if not k.startswith("email:") or v.get("dup_of") or k in (G or {}) or not v.get("eligible"): continue
        u = links.get(k)
        if u and urllib.parse.urlparse(u).netloc.lower() in HOSTS: out.append((k, u))
    return out

def inbox_links():
    import yaml, glob, scout as sc
    C = yaml.safe_load(open(os.path.join(HERE, "CRITERIA.yaml"))); sc.CFG.update(C)
    sc.RESOLVE_LINKS = True; sc.RESOLVE_CACHE = os.path.join(HERE, "out", "link_cache.json")   # cached; no new lookups for known trackers
    links = {}
    for f in sorted(glob.glob(os.path.join(HERE, "inbox", "*"))):
        try:
            for l in sc.parse_email_file(f):
                if l.get("url"): links.setdefault(l["id"], l["url"])
        except Exception: pass
    return links

def drop_from_lists(ids, log):
    """Gone places come off the shortlist (moved to out/shortlist_gone.json, notes kept) and the reply-by-number lists."""
    out = os.path.join(HERE, "out")
    slf, slg = os.path.join(out, "shortlist.json"), os.path.join(out, "shortlist_gone.json")
    if os.path.exists(slf):
        SL = json.load(open(slf)); G = json.load(open(slg)) if os.path.exists(slg) else {}
        for i in [i for i in ids if i in SL]:
            G[i] = dict(SL.pop(i), removed=time.strftime("%F %T %Z")); log(f"shortlist: removed {i} ({G[i].get('where')})")
        json.dump(SL, open(slf, "w"), indent=1); json.dump(G, open(slg, "w"), indent=1)
    nf = os.path.join(out, "last_numbered.json")
    if os.path.exists(nf):
        N = json.load(open(nf)); keep = [x for x in N if x.get("id") not in ids]
        if len(keep) != len(N): log(f"reply list: removed {len(N) - len(keep)} gone place(s)"); json.dump(keep, open(nf, "w"), indent=1)
    lsf = os.path.join(out, "last_sent.json")
    if os.path.exists(lsf):
        d = json.load(open(lsf)); prev = d.get("prev") or []; keep = [x for x in prev if x.get("id") not in ids]
        if len(keep) != len(prev): d["prev"] = keep; json.dump(d, open(lsf, "w")); log(f"earlier reply list: removed {len(prev) - len(keep)} gone place(s)")

def main(argv=sys.argv[1:], get=_get, sleep=time.sleep):
    apply_ = "--apply" in argv; daily = "--daily" in argv
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True); os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
    mark = os.path.join(HERE, "out", "gonecheck.json")
    M = json.load(open(mark)) if os.path.exists(mark) else {}
    today = time.strftime("%F")
    if daily and M.get("last_day") == today: print("gone check already ran today"); return 0
    if daily: M["last_day"] = today; json.dump(M, open(mark, "w"), indent=1)   # claimed up front: never two runs in a day
    S = json.load(open(os.path.join(HERE, "state.json")))["listings"]
    G = load_gone(); todo = candidates(S, inbox_links(), G)
    logf = open(os.path.join(HERE, "logs", "gonecheck.log"), "a")
    def log(msg): logf.write(f"{time.strftime('%F %T %Z')} | {'apply' if apply_ else 'dry run'} | {msg}\n"); logf.flush()
    counts = {"checked": 0, "gone": 0, "unknown": 0, "live": 0}; by_site = {}; gone = []
    for n, (k, u) in enumerate(todo):
        if n: sleep(random.uniform(*GAP))
        verdict, why = check(u, get)
        site = urllib.parse.urlparse(u).netloc.lower().replace("www.", "")
        counts["checked"] += 1; counts[verdict] += 1
        by_site.setdefault(site, {"gone": 0, "unknown": 0, "live": 0})[verdict] += 1
        if verdict != "live": log(f"{verdict} | {k} | {site} | {why}")
        if verdict == "gone": gone.append((k, why))
    if apply_ and gone:
        for k, why in gone:
            G[k] = {"at": time.strftime("%F %T %Z"), "why": why}; log(f"marked gone | {k} | {why}")
        tmp = GONE_FILE + ".tmp"; json.dump(G, open(tmp, "w"), indent=1); os.replace(tmp, GONE_FILE)
        drop_from_lists({k for k, _ in gone}, log)
    if daily or apply_: M["last_day"] = today
    M["last"] = {"at": time.strftime("%F %T %Z"), "apply": apply_, **counts, "by_site": by_site}
    json.dump(M, open(mark, "w"), indent=1)
    print(json.dumps(M["last"], indent=1))
    return 0

if __name__ == "__main__": sys.exit(main())
