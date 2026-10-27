#!/usr/bin/env python3
"""Pull new Zillow / Redfin / HotPads saved-search alert emails from the bot's AgentMail inbox into ./inbox.
Runs at the top of every run_loop.sh cycle. Needs AGENTMAIL_API_KEY in the environment (never written to disk).
Same contract as the 'pull site alert emails' routine:
- ids in out/fetched_ids.txt (one message id per line; the only id file),
- a welcome/verify-style subject is skipped ONLY if the body shows no listing (price + listing link),
- every skip is logged to logs/email_skips.log,
- out/routine_heartbeat.txt is written every run (notify.py emailwatch flags it after the plan interval + 3h).
Reads every page of the inbox listing (not just the newest 50). Sends nothing."""
import os, re, sys, json, time, urllib.request, urllib.parse, yaml
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
API = "https://api.agentmail.to/v0"
DOMAINS = ("zillow.com", "redfin.com", "hotpads.com", "trulia.com", "rent.com", "apartments.com", "realtor.com", "move.com", "zumper.com")   # realtor.com mail may also come from move.com mailers (unverified)
SKIP = re.compile(r"verif|welcome|one-time code|confirm your|password|sign in|log in", re.I)
LISTING = re.compile(r"\$\s?\d{1,3}(?:,\d{3})+|\$\s?\d{4}", re.I)
LINK = re.compile(r"homedetails|/home/|/pad\b|click\.mail\.zillow\.com|redmail\d*\.redfin\.com|hotpads\.com/", re.I)
IDS = os.path.join("out", "fetched_ids.txt")

def get(path, key):
    r = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {key}"})
    return json.load(urllib.request.urlopen(r, timeout=30))

def skip_log(why, frm, subj):
    os.makedirs("logs", exist_ok=True)
    with open(os.path.join("logs", "email_skips.log"), "a") as f: f.write(f"{time.strftime('%F %T %Z')}\t{why}\t{frm}\t{subj[:120]}\n")

def main():
    os.makedirs("out", exist_ok=True); os.makedirs("inbox", exist_ok=True)
    key = os.environ.get("AGENTMAIL_API_KEY")
    if not key: print("fetch_inbox: AGENTMAIL_API_KEY not set; skipped"); return 0
    inbox = (yaml.safe_load(open("CRITERIA.yaml")).get("alert_inbox") or "").strip()
    if not inbox: print("fetch_inbox: no alert_inbox in CRITERIA.yaml; skipped"); return 0
    old_json = os.path.join("out", "fetched_ids.json")   # one-time migration from the older format
    seen = set(l.strip() for l in open(IDS)) if os.path.exists(IDS) else set()
    if os.path.exists(old_json): seen |= set(json.load(open(old_json))); os.unlink(old_json)
    q, msgs, token = urllib.parse.quote(inbox), [], None
    for _ in range(20):   # up to 2,000 messages; stops at the first page with nothing new
        page = get(f"/inboxes/{q}/messages?limit=100" + (f"&page_token={urllib.parse.quote(token)}" if token else ""), key)
        got = page.get("messages") or []; msgs += got
        token = page.get("next_page_token")
        if not token or all((m.get("message_id") or m.get("id")) in seen for m in got): break
    n = 0
    for m in msgs:
        mid = m.get("message_id") or m.get("id")
        if not mid or mid in seen: continue
        frm = str(m.get("from") or "").lower(); subj = m.get("subject") or ""
        if not any(d in frm for d in DOMAINS): seen.add(mid); continue   # not a listing site: ignored quietly
        full = get(f"/inboxes/{q}/messages/{urllib.parse.quote(str(mid))}", key)
        body, ext = (full.get("html"), "html") if full.get("html") else (full.get("text") or full.get("extracted_text"), "txt")
        seen.add(mid)
        if not body: skip_log("empty body", frm, subj); continue
        if SKIP.search(subj) and not (LISTING.search(body) and LINK.search(body)):
            skip_log("account email, no listings in body", frm, subj); continue
        safe = re.sub(r"[^\w.-]", "_", str(mid))[:80]
        open(os.path.join("inbox", f"{safe}.{ext}"), "w").write(f"<!-- from: {frm} | subject: {subj} -->\n" + body); n += 1
    open(IDS, "w").write("".join(f"{i}\n" for i in sorted(seen)))
    print(f"fetch_inbox: {n} new alert email(s) saved")
    return 0

def heartbeat():
    os.makedirs("out", exist_ok=True); open(os.path.join("out", "routine_heartbeat.txt"), "w").write(time.strftime("%F %T %Z") + " fetch_inbox.py\n")

if __name__ == "__main__":
    import signal   # overall 60 s deadline so a slow API never stalls the loop
    def _late(*_): raise TimeoutError("60 s deadline")
    signal.signal(signal.SIGALRM, _late); signal.alarm(60)
    try: rc = main()
    except Exception as e: print(f"fetch_inbox: error {type(e).__name__}: {str(e)[:120]}"); sys.exit(0)   # never block the loop
    if os.environ.get("AGENTMAIL_API_KEY"): heartbeat()   # only when this script is the sync (else the routine writes it)
    sys.exit(rc)
