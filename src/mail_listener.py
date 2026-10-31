#!/usr/bin/env python3
"""Listing Scout instant listener (v1.2.15, staged). Plain Python, no AI, sends nothing.
Watches one AgentMail inbox (default ern@agentmail.to) over AgentMail's WebSocket for
message.received, fetches the full message by REST, and routes it exactly like the
'pull site alert emails' routine:
  rental alert  -> <root>/inbox/<site>-<id>.txt
  buy-test alert (Realtor.com sender, or a 'Buy Test' saved search) -> <buytest>/inbox/<site>-<id>.txt only
  ids -> <root>/out/fetched_ids.txt (shared with the routine), lines -> <root>/logs/email_skips.log
On start (and after every reconnect) a catch-up poll lists the inbox for anything missed.
Alerts older than LS_CATCHUP_HOURS (default 24) are marked seen and skipped (stale rule).
Key: AGENTMAIL_API_KEY from env (never printed). Usage:
  mail_listener.py            run forever (auto-reconnect, backoff 2s..5min)
  mail_listener.py --check    read-only: connect + subscribe + count messages; writes nothing
  mail_listener.py --once     catch-up poll only, then exit"""
import os, re, sys, json, time, fcntl, asyncio, urllib.request, urllib.parse, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "vendor"))
ROOT = os.environ.get("LS_ROOT", os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE)   # src/ (repo) or flat install
BUYTEST = os.environ.get("LS_BUYTEST", os.path.join(os.path.dirname(os.path.abspath(ROOT)), "listing-scout-buytest"))
INBOX = os.environ.get("LS_LISTEN_INBOX", "ern@agentmail.to")
API = os.environ.get("LS_AGENTMAIL_API", "https://api.agentmail.to/v0")
WS = os.environ.get("LS_AGENTMAIL_WS", "wss://ws.agentmail.to/v0")
STALE_H = float(os.environ.get("LS_CATCHUP_HOURS", "24"))
SITES = (("zillow.com", "zillow"), ("redfin.com", "redfin"), ("hotpads.com", "hotpads"), ("realtor.com", "realtor"),
         ("move.com", "realtor"), ("trulia.com", "trulia"), ("rent.com", "rent"), ("apartments.com", "apartments"), ("zumper.com", "zumper"))
BUY_SITES = {"realtor"}                     # Realtor.com alerts exist only for the buy test
BUY_SEARCH = re.compile(r"buy\s*test", re.I)  # saved-search name, e.g. 'Buy Test - 92660', "Your 'Buy Test 1' Search"
SKIP = re.compile(r"verif|welcome|one-time code|confirm your|confirmation:|email changed|has been modified|email (?:address )?(?:was |has been )?(?:changed|updated)|password|sign in|log in", re.I)
LISTING = re.compile(r"\$\s?\d{1,3}(?:,\d{3})+|\$\s?\d{4}|\$\s?\d+(?:\.\d+)?\s?[KM]\b", re.I)
LINK = re.compile(r"homedetails|/home/|/pad\b|click\.mail\.zillow\.com|redmail\d*\.redfin\.com|hotpads\.com/|realtor\.com", re.I)

DETAIL = re.compile(r"hotpads\.com/\d+-[a-z0-9-]+|zillow\.com/homedetails/|redfin\.com/[A-Z]{2}/\S*/home/\d+|realtor\.com/realestateandhomes-detail/", re.I)   # a listing page link

def _key():
    k = os.environ.get("AGENTMAIL_API_KEY")
    if not k: raise SystemExit("mail_listener: AGENTMAIL_API_KEY not set")
    return k

def get(path, key, timeout=30):
    r = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {key}"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))

def p(*parts): return os.path.join(ROOT, *parts)

def log(msg):
    os.makedirs(p("logs"), exist_ok=True)
    with open(p("logs", "mail_listener.log"), "a") as f: f.write(f"{time.strftime('%F %T %Z')} {msg}\n")

def skip_log(kind, frm, subj, dest):   # same shape as the routine's lines
    os.makedirs(p("logs"), exist_ok=True)
    with open(p("logs", "email_skips.log"), "a") as f:
        f.write(f"{time.strftime('%F %T %Z')} | {kind} | {frm} | {subj[:160]} | {dest}\n")

class Ids:
    """out/fetched_ids.txt, shared with the routine. Re-read under a lock before every decision; append-only."""
    def __init__(self): os.makedirs(p("out"), exist_ok=True); self.f = p("out", "fetched_ids.txt")
    def __enter__(self):
        self.lk = open(p("out", ".fetched_ids.lock"), "w"); fcntl.flock(self.lk, fcntl.LOCK_EX); return self
    def __exit__(self, *a): fcntl.flock(self.lk, fcntl.LOCK_UN); self.lk.close()
    def seen(self):
        return set(norm_id(l) for l in open(self.f)) if os.path.exists(self.f) else set()
    def add(self, mid):
        with open(self.f, "a") as f: f.write(f"{norm_id(mid)}\n")

def norm_id(mid):
    """One form for fetched_ids.txt: the bare message id. 'am:<id>' (older routine lines) counts as the same id."""
    m = str(mid).strip()
    if m.startswith("am:"): m = m[3:].strip()
    if m.startswith("<") and m.endswith(">"): m = m[1:-1].strip()   # v1.2.16: '<id>' and 'id' are the same message
    return m

def site_of(frm):
    frm = frm.lower()
    for d, s in SITES:
        if d in frm: return s
    return None

def route(frm, subj, body):
    """-> ('rental'|'buy', site) or (None, reason)."""
    s = site_of(frm)
    if not s: return None, "not a listing site"
    if not body: return None, "empty body"
    if SKIP.search(subj) and not (LISTING.search(body) and LINK.search(body)):
        return None, "account email, no listings in body"
    if not ((LISTING.search(body) and LINK.search(body)) or DETAIL.search(body)):   # v1.2.15b: a real alert always shows a price + listing link; else it would parse to 0 homes and trip emailwatch
        return None, "no listings in body"
    if s in BUY_SITES or BUY_SEARCH.search(subj) or BUY_SEARCH.search(body): return "buy", s
    return "rental", s

def search_name(body):
    m = BUY_SEARCH.search(body or "")
    if not m: return ""
    return re.split(r"[(<\n'\"]", body[m.start():m.start() + 40])[0].strip()

def safe_id(mid): return re.sub(r"[^\w.-]", "_", str(mid)).strip("_.")[:80]

def write_atomic(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = os.path.join(os.path.dirname(path), "." + os.path.basename(path) + ".part")   # scout only reads *.txt/*.html
    with open(tmp, "w") as f: f.write(text)
    os.replace(tmp, path)

def _ts(m):
    t = m.get("timestamp") or m.get("created_at") or ""
    try: return datetime.datetime.fromisoformat(str(t).replace("Z", "+00:00")).timestamp()
    except Exception: return None

def handle(m, key, fetch=True):
    """Process one message summary/event. Returns the written path or None. Never sends anything."""
    mid = m.get("message_id") or m.get("id")
    if not mid: return None
    with Ids() as ids:
        if norm_id(mid) in ids.seen(): return None
        frm = str(m.get("from") or m.get("from_") or ""); subj = m.get("subject") or ""
        if not site_of(frm): ids.add(mid); return None   # not a listing site: ignored quietly (as fetch_inbox.py)
        ts = _ts(m)
        if ts and time.time() - ts > STALE_H * 3600:
            ids.add(mid); skip_log("skipped", frm, subj, f"stale catch-up (> {STALE_H:g} h old)"); return None
        full = get(f"/inboxes/{urllib.parse.quote(INBOX)}/messages/{urllib.parse.quote(str(mid))}", key) if fetch else m
        body = full.get("text") or full.get("extracted_text") or full.get("html") or ""
        kind, site = route(frm, subj, body)
        if not kind:
            ids.add(mid); skip_log("skipped", frm, subj, site); return None
        to = full.get("to") or m.get("to") or INBOX
        to = ", ".join(to) if isinstance(to, list) else str(to)
        recv = full.get("timestamp") or m.get("timestamp") or ""
        head = (f"<!-- from: {frm} | subject: {subj} -->\n"
                f"--- listener {time.strftime('%F %T %Z')} · received {recv} · message_id {mid}\n"
                f"From: {frm}\nTo: {to}\nSubject: {subj}\n\n")
        name = f"{site}-{safe_id(mid)}.txt"
        if kind == "buy":
            path = os.path.join(BUYTEST, "inbox", name); dest = f"buytest inbox/{name}" + (f" ({search_name(body)})" if search_name(body) else "")
        else:
            path = p("inbox", name); dest = f"inbox/{name}"
        write_atomic(path, head + body)
        ids.add(mid); skip_log("routed", frm, subj, dest + " [listener]")
        return path

def catch_up(key, quiet=False):
    q, token, n = urllib.parse.quote(INBOX), None, 0
    for _ in range(20):
        page = get(f"/inboxes/{q}/messages?limit=100" + (f"&page_token={urllib.parse.quote(token)}" if token else ""), key)
        got = page.get("messages") or []
        with Ids() as ids: seen = ids.seen()
        for m in got:
            try:
                if handle(m, key): n += 1
            except Exception as e: log(f"catch-up message error {type(e).__name__}: {str(e)[:120]}")
        token = page.get("next_page_token")
        if not token or all(norm_id(m.get("message_id") or m.get("id")) in seen for m in got): break
    if not quiet: log(f"catch-up: {n} saved")
    return n

def heartbeat():
    os.makedirs(p("out"), exist_ok=True)
    with open(p("out", "listener_heartbeat.txt"), "w") as f: f.write(time.strftime("%F %T %Z") + " mail_listener.py\n")

RESUMED = {"at": 0.0}   # v1.2.17: set when the box wakes from a pause (wall clock jumped past the monotonic clock)

def resumed(prev_wall, prev_mono, now_wall, now_mono, slack=20):
    """True when more wall time passed than this process could run: the VM was paused/snapshotted and resumed."""
    return (now_wall - prev_wall) - (now_mono - prev_mono) > slack

def mark_resume(jump):
    RESUMED["at"] = time.time(); log(f"box resumed after a pause (~{jump:.0f}s); catching up now")
    try: write_atomic(p("out", "resumed_at"), time.strftime("%F %T %Z") + "\n")   # loop_watchdog.py grace
    except Exception: pass

async def watchdog_job(every=60):
    import subprocess
    while True:
        await asyncio.sleep(every)
        try: await asyncio.to_thread(subprocess.run, [sys.executable, os.path.join(HERE, "loop_watchdog.py")],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
        except Exception as e: log(f"watchdog error {type(e).__name__}: {str(e)[:100]}")

async def side_jobs(key, every=60, poll_every=60, tick=5, ws_holder=None):
    """v1.2.17: a cheap list-call catch-up every minute, on its own task (v1.2.16 ran it after the watchdog, whose
    restarts could hold it for minutes). Ticks every 5 s; when the box resumes from a pause it polls at once and drops
    the (now dead) socket so it reconnects. The loop guard runs on a separate task. Never sends."""
    asyncio.get_running_loop().create_task(watchdog_job(every))
    w0, m0 = time.time(), time.monotonic(); t_poll = time.monotonic()
    while True:
        await asyncio.sleep(tick)
        w, m = time.time(), time.monotonic(); jump = (w - w0) - (m - m0)
        woke = resumed(w0, m0, w, m); w0, m0 = w, m
        if woke:
            mark_resume(jump)
            ws = (ws_holder or {}).get("ws")
            if ws is not None:
                try: await ws.close()
                except Exception: pass
        if woke or time.monotonic() - t_poll >= poll_every:
            t_poll = time.monotonic()
            try:
                n = await asyncio.to_thread(catch_up, key, True)
                if n: log(f"poll: {n} saved")
            except Exception as e: log(f"poll error {type(e).__name__}: {str(e)[:100]}")

async def run_forever(key):
    import websockets
    delay = 2
    holder = {}
    asyncio.get_running_loop().create_task(side_jobs(key, ws_holder=holder))
    while True:
        try:
            async with websockets.connect(WS, additional_headers={"Authorization": f"Bearer {key}"},
                                          ping_interval=30, ping_timeout=30, open_timeout=20) as ws:
                await ws.send(json.dumps({"type": "subscribe", "inbox_ids": [INBOX], "event_types": ["message.received"]}))
                log("connected; subscribing"); delay = 2; holder["ws"] = ws
                await asyncio.to_thread(catch_up, key)   # after subscribe, so nothing slips between poll and stream
                heartbeat()
                async for raw in ws:
                    heartbeat()
                    try: ev = json.loads(raw)
                    except Exception: continue
                    if ev.get("type") == "subscribed": log("subscribed"); continue
                    if ev.get("type") == "error": log(f"server error: {str(ev)[:160]}"); continue
                    if ev.get("event_type") == "message.received" and isinstance(ev.get("message"), dict):
                        msg = ev["message"]
                        if msg.get("inbox_id") not in (None, INBOX): continue
                        try:
                            path = await asyncio.to_thread(handle, msg, key)
                            if path: log(f"saved {os.path.basename(path)}")
                        except Exception as e: log(f"message error {type(e).__name__}: {str(e)[:120]}")
        except asyncio.CancelledError: raise
        except Exception as e:
            log(f"disconnected ({type(e).__name__}: {str(e)[:100]}); retry in {delay}s")
        await asyncio.sleep(delay); delay = min(delay * 2, 300)

async def check(key):
    """Read-only connectivity test. Writes nothing anywhere."""
    import websockets
    async with websockets.connect(WS, additional_headers={"Authorization": f"Bearer {key}"}, open_timeout=20) as ws:
        await ws.send(json.dumps({"type": "subscribe", "inbox_ids": [INBOX], "event_types": ["message.received"]}))
        ev = json.loads(await asyncio.wait_for(ws.recv(), 15))
    ok = ev.get("type") == "subscribed"
    q, token, total = urllib.parse.quote(INBOX), None, 0
    for _ in range(20):
        page = get(f"/inboxes/{q}/messages?limit=100" + (f"&page_token={urllib.parse.quote(token)}" if token else ""), key)
        total += len(page.get("messages") or []); token = page.get("next_page_token")
        if not token: break
    print(f"websocket: {'subscribed' if ok else 'unexpected reply: ' + str(ev.get('type'))} to {INBOX}")
    print(f"messages in {INBOX}: {total}")
    return 0 if ok else 1

def main(argv):
    key = _key()
    if "--check" in argv: return asyncio.run(check(key))
    if "--once" in argv: catch_up(key); return 0
    os.makedirs(p("logs"), exist_ok=True)
    with open(p("logs", "mail_listener.pid"), "w") as f: f.write(str(os.getpid()))
    asyncio.run(run_forever(key))

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
