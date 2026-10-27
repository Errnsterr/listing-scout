#!/usr/bin/env python3
"""Deliver listing-scout alerts via Photon (Stable / Spectrum).
Credentials: PHOTON_API_KEY env var = the Project secret (never printed, never stored in files).
Project ID comes from CRITERIA.yaml (photon.project_id) or env PHOTON_PROJECT_ID.
Recipients must already be Users in the Photon project (dashboard /users). Their full phone number
is looked up from Photon's Users list at send time by last 4 digits.

Nothing is sent unless --send is given.
  python3 src/notify.py check                  # read-only: auth + users + plan; resolve each recipient
  python3 src/notify.py alerts FILE [--send]   # FILE = `scout.py --json` output; bundles within the hour
  NEW_USER_PHONE=+1... python3 src/notify.py add_user "Name" --confirm
                                           # adds a household member as a Photon project user (shared line).
                                           # Number comes ONLY from env NEW_USER_PHONE (secure form); prints last 4 only.
  python3 src/notify.py welcome "Name" [--card] [--send]  # merged test + welcome (owner vs household wording); --card attaches out/Listing-Scout-<Name>.vcf
  python3 src/notify.py emailwatch [--send]    # owner only: unreadable alert email / email sync stalled (plan interval + 3h) / a site quiet 48h
  python3 src/notify.py snapshot [--send]      # end of setup: "what's out there right now" (counts by tier + top 3), once, owner only
  python3 src/notify.py firstday [--send]      # fallback one-time note (after 6 PM; skipped if the snapshot or any alert went out)
  python3 src/notify.py seeded                 # record the quiet first run time
  python3 src/notify.py morning [--send]       # Sleep mode: held overnight finds at wake time + the one-time offer
  python3 src/notify.py gone [--send]          # Still available?: liked places gone ~24h -> "no longer listed"
"""
import time, os, sys, json, time, base64, subprocess, tempfile, urllib.request, urllib.error, yaml, importlib.util
_SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC
C = yaml.safe_load(open(os.environ.get("SCOUT_CRITERIA", os.path.join(HERE, "CRITERIA.yaml"))))
for _r in C.get("recipients") or []:   # "co-decider" / "Co Decider" -> "co_decider"
    if _r.get("role"): _r["role"] = __import__("re").sub(r"[\s-]+", "_", str(_r["role"]).strip().lower())
PID = os.environ.get("PHOTON_PROJECT_ID") or C.get("photon", {}).get("project_id")
sys.path.insert(0, _SRC)
import style, features
KIND = "home" if C.get("mode") == "buy" else "rental"
REPLIES = bool(C.get("replies"))   # 'decide together' stays hidden until a live round trip is verified

def api(path):
    key = os.environ.get("PHOTON_API_KEY") or sys.exit("Missing env PHOTON_API_KEY (Project secret).")
    req = urllib.request.Request(f"https://spectrum.photon.codes/projects/{PID}/{path}",
        headers={"User-Agent": "listing-scout/1.0", "Authorization": "Basic " + base64.b64encode(f"{PID}:{key}".encode()).decode()})
    return json.load(urllib.request.urlopen(req, timeout=30))["data"]

def recipients():
    if C.get("shadow") and not os.environ.get("PHOTON_API_KEY"):   # proof run / tests without Photon: names only, no numbers
        return [{**r, "phone": "", "line_last4": ""} for r in C["recipients"]]
    users = api("users/")["users"]
    out = []
    for r in C["recipients"]:
        l4 = r.get("phone_last4")
        u = next((u for u in users if l4 and (u.get("phoneNumber") or "").endswith(l4)), None)
        if not u: print(f"skip {r['name']}: not a Photon project user yet (add at /users)"); continue
        out.append({**r, "phone": u["phoneNumber"], "line_last4": (u.get("assignedPhoneNumber") or "")[-4:]})
    return out

CHANNEL_TTL = 3600   # re-check a person's channel at most once an hour before sends
SENDLOG = os.path.join(HERE, "logs", "sends.jsonl")
for _d in ("out", "logs"): os.makedirs(os.path.join(HERE, _d), exist_ok=True)   # exported copies ship without these

def _warn(msg): print("WARNING: " + msg, file=sys.stderr)

def sdk_channel(phone):
    """Photon SDK check (@photon-ai/advanced-imessage addresses.isIMessageAvailable / get).
    Returns 'imessage' | 'sms' | 'rcs', or None if the check failed or isn't available. Read-only; sends nothing."""
    if not (phone and os.environ.get("PHOTON_API_KEY") and PID): return None
    try:
        p = subprocess.run(["node", os.path.join(_SRC, "photon_send.mjs"), "channel", phone],
                           env={**os.environ, "PHOTON_PROJECT_ID": PID}, capture_output=True, text=True, timeout=60)
        m = __import__("re").search(r"^channel: (imessage|sms|rcs)$", p.stdout, __import__("re").M)
        return m.group(1) if m else None
    except Exception: return None

def channel_of(r, refresh=False):
    """A person's channel. Saved per person in out/members.json. If the SDK check fails or isn't
    available, assume iMessage, log a warning, and never block sending."""
    m = member(r); ch = m.get("channel")
    if refresh or not ch or time.time() - m.get("channel_ts", 0) > CHANNEL_TTL:
        got = sdk_channel(r.get("phone"))
        if got:
            set_member(r["name"], channel=got, channel_ts=time.time(), channel_checked=time.strftime("%F %T %Z")); ch = got
        else:
            if r.get("phone") and os.environ.get("PHOTON_API_KEY"):
                _warn(f"channel check unavailable for {r['name']}; assuming {ch or 'imessage'}")
            ch = ch or "imessage"
    return ch

def for_channel(text, card, ch):
    """iMessage: as is. SMS/RCS: no emoji, no contact card (a 'save me' line instead)."""
    if ch == "imessage": return text, card
    t = style.plain(text)
    if card and style.SAVE_LINE not in t: t = style.text([[style.SAVE_LINE]]) + "\n\n" + t
    return t, None

def log_send(r, ch, ok, really, card, n):
    try:
        os.makedirs(os.path.dirname(SENDLOG), exist_ok=True)
        with open(SENDLOG, "a") as f:
            f.write(json.dumps({"ts": time.strftime("%F %T %Z"), "to": r["name"], "channel": ch, "ok": bool(ok),
                                "dry_run": not really, "card": bool(card), "chars": n}) + "\n")
    except OSError: pass

def send_parts(r, parts, really):
    """a roundup's texts, in order; stops at the first failure so nobody gets Part 2 without Part 1."""
    if isinstance(parts, str): parts = [parts]
    for t in parts:
        if not send(r, t, really): return False
    return True

def send(r, text, really, card=None):
    if style.check(text): _warn(f"style problems in a text to {r['name']}: {style.check(text)[:2]}")   # every text should come from style.py
    if C.get("shadow"):   # proof run: log the would-be text, send nothing (names only, never numbers)
        os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
        with open(os.path.join(HERE, "out", "shadow_texts.jsonl"), "a") as f:
            f.write(json.dumps({"ts": time.strftime("%F %T %Z"), "to": r["name"], "card": bool(card), "text": text, "style_ok": not style.check(text)}) + "\n")
        print(f"[SHADOW] logged a text for {r['name']} (not sent)"); return True
    ch = channel_of(r) if really else (member(r).get("channel") or "imessage")
    text, card = for_channel(text, card, ch)
    ok = _send(r, text, really, card, ch)
    log_send(r, ch, ok, really, card, len(text)); return ok

def _send(r, text, really, card, ch="imessage"):
    probs = style.check(text)
    if probs: print("style problems (fix before sending):", probs); return False
    tag = f"{r['name']} (***{r['phone'][-4:]}, line ***{r['line_last4']}, {ch})"
    if not really:
        print(f"[DRY RUN] would send to {tag}{' + contact card' if card else ''}:\n{text}\n"); return True
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f: f.write(text)
    env = {**os.environ, "PHOTON_PROJECT_ID": PID}
    for attempt in (1, 2, 3):   # Photon hiccup: quiet retries, no one is told
        p = subprocess.run(["node", os.path.join(_SRC, "photon_send.mjs"), "send", r["phone"], f.name, "--send"] + (["--card", card] if card else []),
                           env=env, capture_output=True, text=True, timeout=120)
        if p.returncode == 0 or "not allowed" in (p.stdout + p.stderr).lower(): break
        time.sleep(30 * attempt)
    os.unlink(f.name)
    ok = p.returncode == 0
    if ok and card: print("card: " + ("accepted by Photon" if "card sent" in p.stdout else "NOT confirmed"))
    print(f"sent: {tag}. Texts come from the number ending {r['line_last4']}." if ok else f"Not sent: {tag}. Nothing is wrong on their side.")
    if not ok:
        import re
        sec = os.environ.get("PHOTON_API_KEY") or "\0"
        err = (p.stderr + p.stdout).replace(sec, "[secret]")
        if "Target not allowed" in err:
            print(style.hint_target_not_allowed(r["name"], r["line_last4"]))
        else:
            print(re.sub(r"\+?\d{7,}", lambda m: "***" + m.group()[-4:], err)[-4000:])
    if not ok and ch != "imessage":
        print("  SMS/RCS delivery is UNVERIFIED on our Photon line; the owner may need to check with this person.")
    return ok

LIFE = os.path.join(HERE, "logs", "lifecycle.json")
def life():
    return json.load(open(LIFE)) if os.path.exists(LIFE) else {}
def save_life(d): json.dump(d, open(LIFE, "w"), indent=1)
def n_places():
    st = os.path.join(HERE, "state.json")
    return len(json.load(open(st))["listings"]) if os.path.exists(st) else 0
def card_for(r):
    f = os.path.join(HERE, "out", f"Listing-Scout-{r['name'].replace(chr(39)+'s', 's').replace(' ', '-')}.vcf")
    return f if os.path.exists(f) else None
def is_owner(r): return r.get("role") == "owner" or r["name"] == C["recipients"][0]["name"]
def sample_text():
    """Proof of life: 'what's out there right now' snapshot from the quiet first run
    (out/sample.json = every current MATCH, written by scout.py --seed or --sample). Real data only."""
    sp = importlib.util.spec_from_file_location("scout", os.path.join(_SRC, "scout.py"))
    sc = importlib.util.module_from_spec(sp); sp.loader.exec_module(sc)
    f = os.path.join(HERE, "out", "sample.json")
    A = json.load(open(f)) if os.path.exists(f) else []
    if not A: return None
    for a in A: a["l"].setdefault("flags", [])
    return sc.snapshot_parts(A, n_places(), C)   # list of texts (Part i of n only if long)

SUFFIX = r"\s+(Avenue|Ave|Drive|Dr|Street|St|Road|Rd|Lane|Ln|Boulevard|Blvd|Way|Place|Pl|Court|Ct|Circle|Cir|Terrace|Ter)\.?$"
def short_where(l):
    import re
    st = (l.get("address") or "").split(",")[0].strip()
    st = re.sub(r"^\s*[\d\-A-Za-z]*\d[\w\-]*\s+", "", st)            # drop house number like 308-A2
    st = re.sub(r"\s+-\s*.*$", "", st)                              # AppFolio "Example Street - Unit C" / "Sample Ave - C"
    st = re.sub(r"\s+(Unit|Apt|#)\s*\S+$", "", st, flags=re.I)
    st = re.sub(SUFFIX, "", st, flags=re.I).strip()
    return st or (l.get("zip") or "that one")
def _sc():
    sp = importlib.util.spec_from_file_location("scout", os.path.join(_SRC, "scout.py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
def record_numbered(alerts):
    """Which places were in the latest text, in order (replies attach to these). Clears relay contexts."""
    mf = os.path.join(HERE, "out", "members.json")
    if os.path.exists(mf):
        M = json.load(open(mf))
        for v in M.values(): v.pop("context", None)
        json.dump(M, open(mf, "w"), indent=1)
    lf = os.path.join(HERE, "out", "last_numbered.json")
    prev = json.load(open(lf)) if os.path.exists(lf) else []
    json.dump({"ts": time.time(), "prev": prev}, open(os.path.join(HERE, "out", "last_sent.json"), "w"))
    json.dump([{"id": a["l"]["id"], "where": short_where(a["l"]),
                "price": (f"${a['l']['price']:,.0f}" + ("" if C.get("mode") == "buy" else "/mo")) if a["l"].get("price") else "rent not listed",
                **{k: a["l"].get(k) for k in ("url", "apply_url", "source", "flags") if a["l"].get(k)}, "sent_ts": time.time()}   # apply.py gate reads these
               for a in alerts], open(os.path.join(HERE, "out", "last_numbered.json"), "w"), indent=1)
def household_other(r):
    """Name of the other decider for a shared search, or None (solo owner / in the know)."""
    if not C.get("replies"): return None
    R = [x for x in C["recipients"] if x.get("phone_last4")]
    roles = {x["name"]: x.get("role", "owner" if i == 0 else "co_decider") for i, x in enumerate(R)}
    if roles.get(r["name"]) not in ("owner", "co_decider"): return None
    others = [n for n, ro in roles.items() if n != r["name"] and ro in ("owner", "co_decider")]
    return others[0].split()[0] if len(others) == 1 else ("everyone" if others else None)
def member(r):
    f = os.path.join(HERE, "out", "members.json")
    return (json.load(open(f)) if os.path.exists(f) else {}).get(r["name"], {})
def set_member(name, **kw):
    f = os.path.join(HERE, "out", "members.json"); M = json.load(open(f)) if os.path.exists(f) else {}
    M.setdefault(name, {}).update(kw); json.dump(M, open(f, "w"), indent=1)
def paused(r):
    f = os.path.join(HERE, "out", "members.json")
    m = json.load(open(f)).get(r["name"], {}) if os.path.exists(f) else {}
    import features
    return bool(m.get("paused") or m.get("stopped") or m.get("left") or features.search_ended())   # STOP / left / wrapped up: never texted

def add_user(name, confirm):
    import re, base64 as b64
    phone = os.environ.get("NEW_USER_PHONE", "").strip()
    if not re.fullmatch(r"\+[1-9]\d{6,14}", phone):
        sys.exit("Set NEW_USER_PHONE (E.164, e.g. +1...) from the secure form. Nothing was changed.")
    if not confirm:
        sys.exit(f"Dry run: would add {name} (***{phone[-4:]}) as a shared Photon user. Re-run with --confirm after the owner says yes.")
    key = os.environ.get("PHOTON_API_KEY") or sys.exit("Missing env PHOTON_API_KEY.")
    lim = (C.get("photon") or {}).get("user_limit")   # the owner's plan limit (photon.codes/pricing); unset = no local check
    try:   # say so before trying, only if the owner set their plan's limit
        n = len(json.load(urllib.request.urlopen(urllib.request.Request(f"https://spectrum.photon.codes/projects/{PID}/users/", headers={
            "User-Agent": "listing-scout/1.0", "Authorization": "Basic " + b64.b64encode(f"{PID}:{key}".encode()).decode()}), timeout=30)) or [])
        if lim and n >= int(lim): sys.exit(f"Your search already has {n} people, your Photon plan's limit (photon.codes/pricing). Nothing was changed.")
    except (urllib.error.URLError, ValueError, TypeError): pass
    first, *rest = name.split()
    body = json.dumps({"type": "shared", "phoneNumber": phone, "firstName": first, "lastName": " ".join(rest) or None}).encode()
    req = urllib.request.Request(f"https://spectrum.photon.codes/projects/{PID}/users/", data=body, method="POST", headers={
        "User-Agent": "listing-scout/1.0", "Content-Type": "application/json",
        "Authorization": "Basic " + b64.b64encode(f"{PID}:{key}".encode()).decode()})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        sys.exit(f"Photon didn't add {name} (HTTP {e.code}). Nothing is wrong on their side. Check your plan's limits: photon.codes/pricing.")
    u = d.get("data") or {}
    line = (u.get("assignedPhoneNumber") or "")[-4:]
    print(f"{name} is added. Their texts will come from the number ending {line}.")
    print(f"Next: add to CRITERIA.yaml recipients -> name: {name}, channel: imessage, phone_last4: \"{phone[-4:]}\"")

def main():
    a = sys.argv[1:]; really = "--send" in a
    if not a: sys.exit(__doc__)
    if a[0] == "check":
        print("project:", api("")["name"], "| plan:", api("billing/subscription")["tier"], "| iMessage:", api("imessage/")["type"])
        for r in recipients():
            p = subprocess.run(["node", os.path.join(_SRC, "photon_send.mjs"), "check", r["phone"]],
                               env={**os.environ, "PHOTON_PROJECT_ID": PID}, capture_output=True, text=True, timeout=90)
            print(f"{r['name']}: line ***{r['line_last4']} ->", "reachable via SDK" if p.returncode == 0 else "SDK lookup failed")
    elif a[0] == "outage":   # a source down > 1 day: tell the owner once, gently
        f = os.path.join(HERE, "out", "outage_pending.json")
        if os.path.exists(f):
            d = json.load(open(f)); owner = recipients()[0]
            t = style.listener_note() if d.get("source") == "Reply listener" else style.outage_note(d["source"], d["since"])
            if send(owner, t, "--send" in a) and "--send" in a: os.unlink(f)
    elif a[0] == "add_user":
        add_user(a[1], "--confirm" in a)
    elif a[0] == "welcome":   # merged test + welcome; owner and household member get different wording
        owner = C["recipients"][0]["name"].split()[0]
        for r in recipients():
            if r["name"].lower() == a[1].lower():
                card = card_for(r) if ("--card" in a or not is_owner(r)) else None   # members always get their card with the welcome
                if "--card" in a and not card: print("no contact card yet: run python3 src/make_contact.py first"); return
                first = r["name"].split()[0]
                t = style.owner_welcome(first, n_places(), bool(card), KIND) if is_owner(r) else style.member_welcome(first, owner, _sc().reflect(C), KIND, r.get("role", "co_decider"), REPLIES, bool(card))
                if send(r, t, really, card) and really and not is_owner(r):   # for the one-time owner nudge
                    f = os.path.join(HERE, "out", "members.json"); M = json.load(open(f)) if os.path.exists(f) else {}
                    M.setdefault(r["name"], {}).setdefault("invited_ts", time.time()); json.dump(M, open(f, "w"), indent=1)
    elif a[0] in ("snapshot", "sample"):   # proof of life, once, at the end of setup (owner only)
        L = life()
        if L.get("snapshot_sent") and "--again" not in a and not (len(a) > 1 and not a[1].startswith("--")):
            print("snapshot already sent once; nothing sent"); return
        t = sample_text()
        if not t: print("no seed data yet (run scout.py --seed); nothing sent"); return
        who = a[1] if len(a) > 1 and not a[1].startswith("--") else None   # notify.py snapshot "Name" for a new member
        r = next((r for r in recipients() if (r["name"].lower() == who.lower() if who else is_owner(r))), None)
        if r and send_parts(r, t, really) and really:
            A = json.load(open(os.path.join(HERE, "out", "sample.json"))); record_numbered(_sc().rank(A, C))   # every match shown, every number maps
            L["snapshot_sent"] = time.strftime("%F %T %Z"); save_life(L)
    elif a[0] == "firstday":  # one-time, capped: only if seeded, nothing sent since, after 6 PM local, never twice
        L = life(); ob = json.load(open(os.path.join(HERE, "outbox.json"))) if os.path.exists(os.path.join(HERE, "outbox.json")) else {}
        why = ("already sent" if L.get("firstday_sent") else "the snapshot already went out" if L.get("snapshot_sent") else "not seeded yet" if not L.get("seeded_at") else
               "an alert already went out" if ob.get("last_sent", 0) > L.get("seeded_ts", 0) else
               "too early (waits until 6 PM)" if features.local_hour(C) < 18 and "--now" not in a else None)
        if why: print(f"first-day note: {why}; nothing sent"); return
        t = style.first_day(n_places())
        oks = [send(r, t, really) for r in recipients() if r.get("mode") != "digest"]
        if really and oks and all(oks): L["firstday_sent"] = time.strftime("%F %T %Z"); save_life(L)
    elif a[0] == "nudge":     # one time: tell the owner if a member hasn't replied OK within ~24h
        f = os.path.join(HERE, "out", "members.json"); M = json.load(open(f)) if os.path.exists(f) else {}
        own = next((r for r in recipients() if is_owner(r)), None)
        for name, v in M.items():
            if v.get("invited_ts") and not v.get("joined") and not v.get("nudged") and time.time() - v["invited_ts"] > 24 * 3600 and own:
                if send(own, style.owner_nudge(name.split()[0]), really) and really:
                    v["nudged"] = time.strftime("%F %T %Z"); json.dump(M, open(f, "w"), indent=1)
    elif a[0] == "seeded":    # record the quiet first run (called by the install command)
        L = life(); L.update(seeded_at=time.strftime("%F %T %Z"), seeded_ts=time.time()); save_life(L); print("seed recorded")
    elif a[0] == "emailwatch":   # owner only: unreadable alert email, alert-email sync stalled, a site quiet 48h
        if not C.get("alert_inbox"): return
        wf = os.path.join(HERE, "logs", "email_watch.json")
        w = json.load(open(wf)) if os.path.exists(wf) else {}
        rep_f = os.path.join(HERE, "out", "email_parse.json")
        rep = json.load(open(rep_f)) if os.path.exists(rep_f) else {}
        now, notes = time.time(), []
        for fn, d in sorted(rep.items()):   # 1. an inbox email that parsed to 0 listings (file kept in inbox/ for review)
            if d.get("count") == 0 and fn not in w.get("zero_told", []):
                notes.append(("zero", fn, style.email_zero_note(d.get("portal", "alert"))))
        hb = os.path.join(HERE, "out", "routine_heartbeat.txt")   # 2. alert-email sync heartbeat (routine or fetch_inbox.py)
        w.setdefault("hb_watch_since", now)
        age = now - (os.path.getmtime(hb) if os.path.exists(hb) else w["hb_watch_since"])
        if age <= features.email_stale_limit(C): w.pop("hb_told", None)   # plan routine interval + 3h drift; only a real outage warns
        elif not w.get("hb_told"): notes.append(("hb", None, style.routine_stale_note(int(age // 60))))
        sites = w.setdefault("sites", {})   # 3. a site that has sent alerts goes quiet for 48h (told once per quiet spell)
        for fn, d in rep.items():
            p = d.get("portal")
            if p in ("Zillow", "Redfin", "HotPads") and (d.get("count", 0) > 0 or p in sites):
                s_ = sites.setdefault(p, {}); s_["last"] = max(s_.get("last", 0), d.get("mtime", 0))
        for p, s_ in sites.items():
            if now - s_.get("last", now) < 48 * 3600: s_.pop("told", None)
            elif not s_.get("told"): notes.append(("site", p, style.site_quiet_note(p)))
        if notes and not features.in_quiet(C):
            own = next((r for r in recipients() if is_owner(r)), None)
            for kind, key, t in notes:
                if own and send(own, t, really) and really:
                    if kind == "zero": w.setdefault("zero_told", []).append(key)
                    elif kind == "hb": w["hb_told"] = True
                    else: sites[key]["told"] = True
        if really or not os.path.exists(wf): json.dump(w, open(wf, "w"), indent=1)
    elif a[0] == "alerts":
        if C.get("paused"):
            print("alerts paused (CRITERIA.yaml paused: true); nothing sent"); return
        spec = importlib.util.spec_from_file_location("scout", os.path.join(_SRC, "scout.py"))
        sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
        obf = os.path.join(HERE, "outbox.json")
        ob = json.load(open(obf)) if os.path.exists(obf) else {"queue": [], "last_sent": 0}
        new = json.load(open(a[1]))
        for x in new: x["l"].setdefault("flags", [])
        ob["queue"] += new
        today = time.strftime("%F")
        if ob.get("day") != today: ob["day"], ob["texts_today"] = today, 0
        pace = (C.get("pace") or "standouts") if KIND == "home" else "instant"   # pace is a buy-mode setting; rentals stay instant
        if ob["queue"] and pace in ("standouts", "evening"):   # buy default: standouts now, the rest in one evening roundup
            now_q, held_q = features.pace_split(ob["queue"], pace, C)
            if held_q: ob.setdefault("evening", []).extend(held_q); ob["queue"] = now_q; print(f"pace {pace}: {len(held_q)} held for the evening roundup")
        if ob["queue"]:   # Daily cap (off unless the owner said yes to one): extras wait for one evening text
            now_q, held_q = features.cap_split(ob["queue"], int(C.get("daily_cap") or 0), ob.get("texts_today", 0))
            if held_q: ob.setdefault("evening", []).extend(held_q); ob["queue"] = now_q; print(f"daily cap reached; {len(held_q)} held for the evening text")
        # First new find goes out right away; finds that follow within the cooldown are bundled into the next text.
        # Sends are tracked per person: if one person's send fails, only that person is retried (next loop pass).
        cool = int(C.get("bundle_cooldown_min", 60)) * 60
        akey = lambda x: f"{x['l'].get('id')}|{x.get('reason')}|{x['l'].get('price')}"
        dl = ob.setdefault("delivered", {})
        retry = any(dl.values())
        if ob["queue"] and (retry or time.time() - ob["last_sent"] >= cool):
            oks = []
            for r in recipients():
                q = [x for x in ob["queue"] if akey(x) not in dl.get(r["name"], [])]
                if r.get("tiers"):   # per-person preference, e.g. tiers: [target]
                    q = [x for x in q if (sc.tier_words(x["l"].get("price"), C) or "").split()[-2:][0] in r["tiers"]]
                if not q: continue
                if r.get("mode") == "digest" or paused(r):   # digest people get a daily summary; paused people get nothing
                    continue
                m = member(r)
                if m.get("sleep") and features.in_quiet(C):   # Sleep mode: hold overnight finds (price drops too) until wake time
                    ob.setdefault("held", {}).setdefault(r["name"], []).extend(q); print(f"holding {len(q)} for {r['name']} (sleep mode)")
                    if really: dl.setdefault(r["name"], []).extend(akey(x) for x in q)
                    continue
                ok1 = send_parts(r, sc.render_parts(q, C), really); oks.append(ok1)
                if ok1 and (really or C.get("shadow")) and not m.get("first_alert_note_sent"):   # one-time heads-up, once per person
                    set_member(r["name"], first_alert_note_sent=time.strftime("%F %T %Z"))   # flag saved BEFORE sending: never twice
                    send(r, style.first_alert_note(), really)   # shadow mode: send() only logs it
                if ok1 and really: dl.setdefault(r["name"], []).extend(akey(x) for x in q)
                if ok1 and really and features.in_quiet(C) and not m.get("sleep_offered") and not m.get("late_at"):
                    set_member(r["name"], late_at=features.local_str(C, "%-I:%M %p"))   # Sleep mode is offered once, in the morning
            ok = all(oks) if oks else True
            if really and ok:
                record_numbered(sc.shown(ob["queue"], C))
                ob = {"queue": [], "last_sent": time.time(), "held": ob.get("held", {}), "evening": ob.get("evening", []),
                      "day": ob.get("day"), "texts_today": ob.get("texts_today", 0) + 1, "delivered": {}}
            elif really:
                print(f"{oks.count(False)} send(s) failed; next pass retries only those people")
        else:
            print(f"holding {len(ob['queue'])} alert(s) to bundle (cooldown {cool // 60} min after the last text)")
        if really: json.dump(ob, open(obf, "w"), indent=1)
    elif a[0] == "morning":   # Sleep mode: send held finds as one bundle at wake time; offer Sleep mode once after a late alert
        if features.in_quiet(C): print("still quiet hours; nothing sent"); return
        spec = importlib.util.spec_from_file_location("scout", os.path.join(_SRC, "scout.py"))
        sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
        obf = os.path.join(HERE, "outbox.json"); ob = json.load(open(obf)) if os.path.exists(obf) else {"queue": [], "last_sent": 0}
        for r in recipients():
            held = ob.get("held", {}).get(r["name"]) or []
            if held and not paused(r) and send_parts(r, sc.render_parts(held, C), really) and really:
                record_numbered(sc.shown(held, C))   # replies by number attach to this bundle, like every other send
                ob["held"].pop(r["name"], None); json.dump(ob, open(obf, "w"), indent=1)
            m = member(r)
            if m.get("late_at") and not m.get("sleep_offered") and not paused(r):
                if send(r, style.sleep_offer(m["late_at"]), really) and really:
                    set_member(r["name"], sleep_offered=time.strftime("%F %T %Z"), pending={"type": "sleep"})
    elif a[0] == "evening":   # Daily cap: everything held today goes out as one text after 6 PM (never during Sleep hours)
        obf = os.path.join(HERE, "outbox.json"); ob = json.load(open(obf)) if os.path.exists(obf) else {}
        ev = ob.get("evening") or []
        if not ev or ((features.local_hour(C) < 18 or features.in_quiet(C)) and "--now" not in a): print("evening: nothing to send yet"); return
        sc = _sc(); oks = [send_parts(r, sc.render_parts(ev, C, head=style.evening_bundle_intro(len(ev), KIND)), really) for r in recipients() if not paused(r) and r.get("mode") != "digest"]
        if really and oks and all(oks): record_numbered(sc.shown(ev, C)); ob["evening"] = []; json.dump(ob, open(obf, "w"), indent=1)
    elif a[0] == "offmarket":   # buy: a shortlisted home went pending/sold -> one calm note, only to the people who shortlisted it
        of = os.path.join(HERE, "out", "offmarket.json"); slf = os.path.join(HERE, "out", "shortlist.json")
        ev = json.load(open(of)) if os.path.exists(of) else []; SL = json.load(open(slf)) if os.path.exists(slf) else {}
        left = []
        for e in ev:
            k = next((i for i in [e["id"]] + e.get("also_ids", []) if i in SL), None)
            if not k or SL[k].get("offmarket_told"): continue   # nobody shortlisted it: say nothing
            who = set(SL[k].get("likes", [])) | set(SL[k].get("tour", []))
            R = [r for r in recipients() if r["name"] in who and not paused(r)]
            oks = [send(r, style.off_market(SL[k].get("where") or e["where"], e["status"]), really) for r in R]
            if really and oks and all(oks): SL[k]["offmarket_told"] = time.strftime("%F %T %Z")
            elif oks: left.append(e)
        if really: json.dump(SL, open(slf, "w"), indent=1) if SL else None; json.dump(left, open(of, "w"), indent=1)
    elif a[0] == "pulse":     # Quiet-week pulse: one calm note with a real count after 7 silent days
        hf = os.path.join(HERE, "out", "hygiene.json"); H = json.load(open(hf)) if os.path.exists(hf) else {}
        obf = os.path.join(HERE, "outbox.json"); ob = json.load(open(obf)) if os.path.exists(obf) else {}
        if not features.pulse_due(H, time.time(), ob.get("last_sent", 0)):
            if not os.path.exists(hf): json.dump(H, open(hf, "w"), indent=1)
            print("pulse: not a quiet week yet; nothing sent"); return
        n = n_places() or None   # real count from the last check, or no count line at all
        R = [r for r in recipients() if not paused(r) and not member(r).get("no_checkins") and r.get("role", "owner" if is_owner(r) else "co_decider") in ("owner", "co_decider")]
        oks = [send(r, style.quiet_week(n), really) for r in R]
        if really and oks and all(oks): H["last_pulse"] = time.time(); json.dump(H, open(hf, "w"), indent=1)
    elif a[0] == "firstweek": # once, 4+ days after going live, owner only: an open door into Make it better (gated)
        L = life(); own = next((r for r in recipients() if is_owner(r)), None)
        if L.get("firstweek_sent") or not L.get("seeded_ts") or time.time() - L["seeded_ts"] < 4 * 86400 or not own or paused(own) or member(own).get("no_checkins") or features.in_quiet(C):
            print("first-week ask: not now; nothing sent"); return
        if send(own, style.first_week_ask(), really) and really:
            set_member(own["name"], pending={"type": "feedback_open"}); L["firstweek_sent"] = time.strftime("%F %T %Z"); save_life(L)
    elif a[0] == "hygiene":   # Criteria hygiene: weekly near-miss check-in / volume nudge, owner only, confirm-first
        if C.get("checkins") is False or C.get("paused"): print("check-ins off; nothing sent"); return
        hf = os.path.join(HERE, "out", "hygiene.json"); H = json.load(open(hf)) if os.path.exists(hf) else {}
        pf, af = os.path.join(HERE, "out", "pool.json"), os.path.join(HERE, "out", "alerts.json")
        pool = json.load(open(pf)) if os.path.exists(pf) else []
        n_today = sum(1 for x in (json.load(open(af)) if os.path.exists(af) else []) if x.get("l", {}).get("match"))
        due = features.hygiene_due(H, time.time(), n_today, time.strftime("%F"))
        own = next((r for r in recipients() if is_owner(r)), None); t = ch = None
        if due == "near_miss":
            nm = features.near_misses(pool)
            if nm:
                thing, n = max(nm.items(), key=lambda kv: kv[1]); ch = features.suggest_change(thing, pool, C)
                if ch: t = style.near_miss_ask(n, thing, ch["desc"][0].upper() + ch["desc"][1:])
        elif due == "loosen":
            nm = features.near_misses(pool); thing = max(nm.items(), key=lambda kv: kv[1])[0] if nm else None
            ch = thing and features.suggest_change(thing, pool, C)
            if ch: t = style.loosen_ask(ch["desc"][0].upper() + ch["desc"][1:])
        elif due == "tighten":
            ch = features.tighten_change(pool, C)
            if ch: t = style.tighten_ask(ch["desc"][0].upper() + ch["desc"][1:])
        if due and not t: H["last_checkin"] = time.time()   # nothing real to suggest: stay quiet a week
        if t and own and not paused(own) and not member(own).get("no_checkins") and send(own, t, really) and really:
            set_member(own["name"], pending={"type": "change", "change": ch, "by": own["name"]}); H["last_checkin"] = time.time()
        if not t: print(f"hygiene: {due or 'not due'}; nothing sent")
        if really or not os.path.exists(hf): json.dump(H, open(hf, "w"), indent=1)
    elif a[0] == "gone":      # Still available?: only places someone liked, gone ~24h; never 'rented'
        st = os.path.join(HERE, "state.json"); slf = os.path.join(HERE, "out", "shortlist.json")
        S = json.load(open(st))["listings"] if os.path.exists(st) else {}; SL = json.load(open(slf)) if os.path.exists(slf) else {}
        todo = features.gone_liked(S, SL)
        if not todo: print("no liked places gone; nothing sent"); return
        R = [r for r in recipients() if r.get("role", "owner" if is_owner(r) else "co_decider") in ("owner", "co_decider") and not paused(r)]
        for g in todo:
            oks = [send(r, style.gone_note(g["where"]), really) for r in R]
            if really and oks and all(oks):
                SL[g["id"]]["gone_told"] = time.strftime("%F %T %Z"); json.dump(SL, open(slf, "w"), indent=1)

if __name__ == "__main__": main()
