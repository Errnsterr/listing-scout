"""Listing Scout Extra features (no AI). Shared by replies.py, notify.py and scout.py.
- Fine-tune the search: parse_change() reads a plain-words change; apply_change() writes CRITERIA (backup first).
- Your data stays put: purge_member(), purge_all(), prune_logs() (logs older than 30 days).
- Sleep mode: in_quiet() / quiet_hours() (per person; members.json "sleep": true).
- Still available?: gone_liked() picks shortlisted places gone ~24h that nobody was told about yet.
- Criteria hygiene: tradeoff(), near_misses(), hygiene_due(), suggest_change() (must-have vs nice-to-have).
Nothing here sends a text."""
import os, re, json, time, shutil, glob, yaml
_SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC
OUT = os.path.join(HERE, "out")
load = lambda f, d: json.load(open(f)) if os.path.exists(f) else d
DEFAULT_QUIET = {"start": 22, "end": 7}   # 10 PM to 7 AM local; only used by people who turn Sleep mode on
LOG_DAYS = 30

# ---------- Fine-tune the search ----------
INTENT = r"^(please )?(change|add|include|remove|drop|take out|raise|lower|increase|decrease|go up|go down|bump|set|make it|budget|max)\b"

def _money(s, frac, k):
    v = float(s.replace(",", "") + (frac or ""))
    return int(round(v * 1000 if (k or v < 100) else v))

def parse_change(text, C):
    """-> None (not a change), {"unclear": True}, or {"desc": one short line, "kind": ..., "value": ...}.
    Never guesses: anything it can't read cleanly is 'unclear' and the bot asks."""
    t = (text or "").strip().lower()
    m = re.search(r"\b(?:max|at most|no more than|cap(?: it)?(?: at)?|limit(?: it)?(?: to)?)\s+(\d{1,2})\s+(?:texts?|alerts?|messages?)\s+(?:a|per)\s+day\b", t)
    if m:   # Daily cap (off by default): extras wait for one evening text
        n = int(m.group(1))
        return {"desc": f"cap alerts at {n} a day.", "kind": "daily_cap", "value": n} if 1 <= n <= 20 else {"unclear": True}
    if re.search(r"\b(text|send) (me )?(every(thing| home| listing)?|all) (right away|instantly|as (it|they) (come|post))\b|\binstant alerts\b", t) and (C.get("mode") or "").startswith("buy"):
        return {"desc": "text every home right away.", "kind": "pace", "value": "instant"}
    if re.search(r"\b(just|only) (the )?(evening|nightly) roundup\b|\bone text (a|per) (day|night)\b", t) and (C.get("mode") or "").startswith("buy"):
        return {"desc": "send one evening roundup.", "kind": "pace", "value": "evening"}
    if re.search(r"\bstandouts?\b.*\b(right away|instantly|now)\b", t) and (C.get("mode") or "").startswith("buy"):
        return {"desc": "text standouts right away.", "kind": "pace", "value": "standouts"}
    if re.search(r"\b(no (daily )?(cap|limit)|remove the (daily )?(cap|limit)|send (them|alerts) all)\b", t) and (C.get("daily_cap") or 0) > 0:
        return {"desc": "send every alert right away.", "kind": "daily_cap", "value": 0}
    zips = [str(z) for z in (C.get("area") or {}).get("zips") or []]
    m = re.search(r"\b(add|include)\s+(?:zip\s+)?(\d{5})\b", t)
    if m:
        z = m.group(2)
        return {"unclear": True} if z in zips else {"desc": f"add {z} to the search.", "kind": "zip_add", "value": z}
    m = re.search(r"\b(remove|drop|take out)\s+(?:zip\s+)?(\d{5})\b", t)
    if m:
        z = m.group(2)
        return {"desc": f"take {z} off the search.", "kind": "zip_remove", "value": z} if z in zips and len(zips) > 1 else {"unclear": True}
    m = re.search(r"(stretch|target|budget|up to|max(?:imum)?|go up|raise|lower|go down)\D{0,20}\$?(\d[\d,]*)(\.\d+)?\s*(k)?\b", t)
    if m and not re.search(r"\bbeds?\b", t):
        v = _money(m.group(2), m.group(3), m.group(4))
        if not 300 <= v <= 50_000_000: return {"unclear": True}
        T = C.get("price_tiers") or {}
        if "stretch" in t:
            if v < T.get("target_max", 0): return {"unclear": True}
            return {"desc": f"set your stretch to ${v:,}.", "kind": "stretch_max", "value": v}
        return {"desc": f"set your target to ${v:,}.", "kind": "target_max", "value": v}
    m = re.search(r"\b(\d)\s*\+?\s*(?:bed|beds|br|bedrooms?)\b", t)
    if m and re.search(r"\b(fine|ok|okay|works|is good|minimum|min|at least|instead|too)\b", t):
        n = int(m.group(1))
        return {"desc": f"make it {n}+ beds.", "kind": "beds_min", "value": n} if 1 <= n <= 8 else {"unclear": True}
    if re.search(INTENT, t) and re.search(r"\b(search|zips?|budget|price|rent|area|beds?|target|stretch|cit(y|ies))\b", t):
        return {"unclear": True}
    return None

def apply_change(ch, crit_path):
    """Write one approved change to CRITERIA, keeping comments where the line is simple. Backup first."""
    os.makedirs(OUT, exist_ok=True)
    bak = os.path.join(OUT, f"CRITERIA.backup-{time.strftime('%Y%m%d-%H%M%S')}.yaml"); shutil.copy(crit_path, bak)
    raw = open(crit_path).read(); C = yaml.safe_load(raw); k, v = ch["kind"], ch["value"]
    if k == "pace":
        new, n = re.subn(r"^(pace:\s*)\w+", lambda m: m.group(1) + str(v), raw, count=1, flags=re.M)
        if not n: new = raw.rstrip("\n") + f"\npace: {v}                  # buy: standouts | evening | instant\n"
    elif k == "daily_cap":
        new, n = re.subn(r"^(daily_cap:\s*)\d+", lambda m: m.group(1) + str(v), raw, count=1, flags=re.M)
        if not n: new = raw.rstrip("\n") + f"\ndaily_cap: {v}                     # 0 = off (instant); N = at most N alert texts a day, extras in one evening text\n"
    elif k in ("must_have", "nice_to_have", "exclude_no_pets", "baths_min"):   # criteria hygiene (structured YAML edit)
        M = C.setdefault("match", {}); nice = [x for x in M.get("nice_to_have") or [] if x != v]
        if k == "exclude_no_pets": M["exclude_no_pets"] = bool(v)
        elif k == "baths_min": M["baths_min"] = v
        elif v == "garage": M["garage_min"] = 1 if k == "must_have" else 0
        elif v == "layout": M["layout_any"] = LAYOUTS if k == "must_have" else []
        if v in ("garage", "layout"): M["nice_to_have"] = nice + ([v] if k == "nice_to_have" else [])
        new = yaml.safe_dump(C, sort_keys=False)
    elif k in ("zip_add", "zip_remove"):
        zs = [str(z) for z in C["area"].get("zips") or []]
        zs = zs + [v] if k == "zip_add" else [z for z in zs if z != v]
        new, n = re.subn(r"^(\s*zips:\s*)\[[^\]\n]*\]", lambda m: m.group(1) + json.dumps(zs, separators=(",", ":")), raw, count=1, flags=re.M)
        if not n: C["area"]["zips"] = zs; new = yaml.safe_dump(C, sort_keys=False)
    else:
        key = "beds_min" if k == "beds_min" else k
        new, n = re.subn(rf"^(\s*{key}:\s*)\d+", lambda m: m.group(1) + str(v), raw, count=1, flags=re.M)
        if not n:
            new, n = re.subn(rf"({key}:\s*)\d+", lambda m: m.group(1) + str(v), raw, count=1)
        if not n:
            (C if key == "beds_min" else C["price_tiers"])[key] = v; new = yaml.safe_dump(C, sort_keys=False)
        if k == "stretch_max" and "price_max:" in new:   # light filters cap at the stretch tier
            new = re.sub(r"(price_max:\s*)\d+", lambda m: m.group(1) + str(v), new, count=1)
        if k == "target_max" and (C.get("price_tiers") or {}).get("stretch_max", 0) < v:   # keep stretch >= target
            new = re.sub(r"(stretch_max:\s*)\d+", lambda m: m.group(1) + str(v), new, count=1)
    yaml.safe_load(new)   # never write a broken file
    open(crit_path, "w").write(new)
    return bak

# ---------- Criteria hygiene (must-have vs nice-to-have; confirm-first) ----------
LAYOUTS = ["first_floor", "single_story", "two_story_townhome"]
THING = {"garage": "a garage", "layout": "ground floor", "price": "price", "beds": "beds", "baths": "baths", "pets": "pet rules"}

def tradeoff(pool, thing):
    """-> (as_must_have, as_nice_to_have) counted from real current listings, or None if it can't be counted."""
    if not pool or thing not in ("garage", "layout"): return None
    base = [l for l in pool if not [m for m in l.get("misses", []) if m != thing]]
    ok = (lambda l: l.get("garage") == "yes") if thing == "garage" else (lambda l: l.get("layout") not in (None, "unknown", "upper unit"))
    return sum(1 for l in base if ok(l)), len(base)

def near_misses(pool):
    """{thing: count} of in-area places that missed on exactly one thing (area misses excluded)."""
    out = {}
    for l in pool or []:
        m = l.get("misses") or []
        if len(m) == 1 and m[0] != "area": out[m[0]] = out.get(m[0], 0) + 1
    return out

def suggest_change(thing, pool, C):
    """A Fine-tune change dict for loosening one thing, or None. Only from real data; never guesses a number."""
    if thing in ("garage", "layout"): return {"desc": "make a garage a nice-to-have." if thing == "garage" else "make ground floor optional.", "kind": "nice_to_have", "value": thing}
    if thing == "pets": return {"desc": "keep places that say no pets.", "kind": "exclude_no_pets", "value": False}
    if thing == "baths": return {"desc": "allow any number of baths.", "kind": "baths_min", "value": 0}
    if thing == "beds" and C.get("beds_min", 1) > 1:
        n = C["beds_min"] - 1; return {"desc": f"make it {n}+ beds.", "kind": "beds_min", "value": n}
    if thing == "price":
        ps = [l["price"] for l in pool or [] if l.get("misses") == ["price"] and l.get("price")]
        if ps:
            v = int(-(-min(ps) // 100) * 100); return {"desc": f"set your stretch to ${v:,}.", "kind": "stretch_max", "value": v}
    return None

def tighten_change(pool, C):
    """Most useful nice-to-have to promote when there are too many matches, from real counts; None if none helps."""
    best = None
    for t in (C.get("match") or {}).get("nice_to_have") or []:
        c = tradeoff(pool, t)
        if c and c[0] < c[1] and (best is None or c[0] < best[1]): best = (t, c[0])
    return best and {"desc": f"make {THING[best[0]]} a must-have.", "kind": "must_have", "value": best[0]}

def pulse_due(H, now, last_alert_ts):
    """Quiet-week pulse: once after 7 days with no alert texts, then not again until another quiet week.
    Skipped if a hygiene check-in went out in the last day (one text, not two)."""
    week = 7 * 86400; H.setdefault("started", now)
    if now - H.get("last_checkin", 0) < 86400: return False
    return now - max(last_alert_ts or 0, H.get("last_pulse", 0), H["started"]) >= week

def pace_split(queue, pace, C):
    """Buy pace: 'standouts' = strong matches within target price (new, price cut, back on market) now, the rest tonight;
    'evening' = everything tonight; 'instant' = everything now."""
    if pace == "instant": return queue, []
    if pace == "evening": return [], queue
    T = (C.get("price_tiers") or {}).get("target_max")
    def standout(a):
        l = a["l"]
        return bool(l.get("match")) and a.get("reason") in ("new", "price_drop", "relist", "relist_lower") and \
            l.get("price") is not None and T is not None and l["price"] <= T and l.get("beds") is not None
    return [a for a in queue if standout(a)], [a for a in queue if not standout(a)]

def cap_split(queue, cap, texts_today):
    """Daily cap on alert TEXTS: -> (send_now, hold_for_evening). cap 0 = off (instant, the default)."""
    if not cap or texts_today < cap: return queue, []
    return [], queue

def hygiene_due(H, now, matches_today, today):
    """Update the hygiene record and return which check-in is due: 'near_miss', 'loosen', 'tighten' or None.
    First run only starts the clocks (nothing is sent on day one). One check-in per week at most."""
    H.setdefault("started", now); H.setdefault("last_match", now); H.setdefault("days", {})
    if matches_today: H["last_match"] = now
    H["days"][today] = H["days"].get(today, 0) + matches_today
    H["days"] = dict(sorted(H["days"].items())[-14:])
    week = 7 * 86400
    if now - max(H.get("last_checkin", 0), H["started"]) < week: return None
    recent = list(H["days"].values())[-7:]
    if len(recent) >= 7 and sum(recent) / 7 > 5: return "tighten"
    if now - H["last_match"] >= week: return "loosen"
    return "near_miss"

# ---------- Your data stays put ----------
def purge_member(name):
    """On leave or removal: delete this person's replies and likes; keep only a 'left' flag so they're never texted."""
    first = name.split()[0]
    sl = os.path.join(OUT, "shortlist.json"); S = load(sl, {})
    for v in S.values():
        v["notes"] = [n for n in v.get("notes", []) if n[0] != first]
        for k in ("likes", "pass", "tour"): v[k] = [x for x in v.get(k, []) if x != first]
    if os.path.exists(sl): json.dump(S, open(sl, "w"), indent=1)
    mf = os.path.join(OUT, "members.json"); M = load(mf, {})
    old = M.get(name, {})
    M[name] = {k: old[k] for k in ("left", "stopped") if k in old} or {"left": time.strftime("%F %T %Z")}
    M[name].setdefault("left", time.strftime("%F %T %Z")); M[name]["paused"] = True
    json.dump(M, open(mf, "w"), indent=1)

DATA_FILES = ("shortlist.json", "last_numbered.json", "last_sent.json", "gone_pending.json", "alerts.json", "sample.json", "outage_pending.json")

def purge_all(keep_members=True, everything=False):
    """'Delete everything' (owner asked, then said yes). Replies, shortlists, queues and logs go.
    keep_members keeps only joined/stopped/left flags so STOP is still honored. everything=True (finish line)
    also removes members.json, state.json and CRITERIA backups. CRITERIA.yaml itself stays (the owner's settings)."""
    gone = []
    for f in DATA_FILES:
        p = os.path.join(OUT, f)
        if os.path.exists(p): os.remove(p); gone.append(f)
    for p in [os.path.join(HERE, "outbox.json")] + glob.glob(os.path.join(HERE, "logs", "*.log")) + glob.glob(os.path.join(HERE, "logs", "*.err")):
        if os.path.exists(p): os.remove(p); gone.append(os.path.basename(p))
    # v1.2.11: automatic backups hold the same data, so they go too (local and the encrypted off-box copy)
    import shutil
    try: _mir = json.load(open(os.path.join(HERE, "selfheal.local.json"))).get("mirror")
    except Exception: _mir = None
    for p in [os.path.join(HERE, "backups", "auto")] + ([os.path.join(_mir, "listing-scout-backups", os.path.basename(os.path.abspath(HERE)))] if _mir else []):
        if os.path.isdir(p): shutil.rmtree(p, ignore_errors=True); gone.append("backups")
    mf = os.path.join(OUT, "members.json")
    if everything:
        for p in [mf, os.path.join(HERE, "state.json")] + glob.glob(os.path.join(OUT, "CRITERIA.backup-*.yaml")):
            if os.path.exists(p): os.remove(p); gone.append(os.path.basename(p))
    elif keep_members and os.path.exists(mf):
        M = load(mf, {}); json.dump({n: {k: v[k] for k in ("joined", "stopped", "left", "paused", "sleep") if k in v} for n, v in M.items()}, open(mf, "w"), indent=1)
    return gone

def prune_logs(days=LOG_DAYS, root=HERE):
    """Logs are kept 30 days (approved policy). Deletes only files under logs/ older than that."""
    cut, gone = time.time() - days * 86400, []
    for p in glob.glob(os.path.join(root, "logs", "*")):
        if os.path.isfile(p) and not p.endswith((".pid", ".lock", "lifecycle.json")) and os.path.getmtime(p) < cut:
            os.remove(p); gone.append(os.path.basename(p))
    return gone

# ---------- Sleep mode ----------
def quiet_hours(C):
    q = C.get("quiet_hours") or {}
    return int(q.get("start", DEFAULT_QUIET["start"])), int(q.get("end", DEFAULT_QUIET["end"]))

DEFAULT_TZ = "America/Los_Angeles"
def tz_name(C): return (C or {}).get("timezone") or DEFAULT_TZ

def local_now(C, ts=None):
    """The search's own clock (CRITERIA timezone), never the bot computer's clock."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.fromtimestamp(time.time() if ts is None else ts, ZoneInfo(tz_name(C)))

def local_hour(C, ts=None): return local_now(C, ts).hour
def local_str(C, fmt="%F %T %Z", ts=None): return local_now(C, ts).strftime(fmt)

ROUTINE_HOURS = {"lean": 12, "standard": 2, "hands_on": 1}   # how often the inbox-reader routine runs per plan (docs/COSTS.md)
def email_stale_limit(C):
    """Seconds before 'email sync stalled' is worth a note: routine interval + 3h drift. api pull runs every loop.
    inbox_routine_minutes (if set) overrides the plan's interval."""
    C = C or {}
    if C.get("inbox_pull") == "api": return 3 * 3600
    m = C.get("inbox_routine_minutes")
    iv = int(m) * 60 if m else ROUTINE_HOURS.get(C.get("plan_mode") or "lean", 12) * 3600
    return iv + 3 * 3600

def in_quiet(C, hour=None, ts=None):
    s, e = quiet_hours(C); h = local_hour(C, ts) if hour is None else hour
    return (h >= s or h < e) if s > e else (s <= h < e)

def wake_label(C):
    e = quiet_hours(C)[1]
    return f"{(e % 12) or 12} {'AM' if e < 12 else 'PM'}"

# ---------- Still available? ----------
GONE_AFTER = 24 * 3600   # ride out feed blips

def gone_liked(S_state, shortlist, now=None):
    """Shortlisted places (someone liked or asked to tour) gone from every feed for ~24h, not yet told."""
    now = now or time.time(); out = []
    for lid, v in shortlist.items():
        if not (v.get("likes") or v.get("tour")) or v.get("gone_told"): continue
        rec = S_state.get(lid) or {}
        if rec.get("gone_since") and now - rec["gone_since"] >= GONE_AFTER: out.append({"id": lid, "where": v["where"]})
    return out

ENDED = os.path.join(OUT, "search_ended.json")
def search_ended(): return os.path.exists(ENDED)


# ---------- Make it better (feedback). GATE: nothing is ever auto-queued or built. ----------
# Every item lands as status 'pending_review' and stays there until the owner explicitly approves it
# (review_feedback.py --approve ID). Approval only marks it; any fix and any "You asked, it's fixed"
# text are done by hand. No code path here sends a text or queues work.
import re as _re
FEEDBACK = os.path.join(HERE, "out", "feedback.jsonl")
_FB = _re.compile(r"^\s*(?:(?:i\s+(?:found|have|got)\s+an?\s+)?(?:bug|idea|suggestion|feature\s+request|feedback)\s*(?:report)?\s*[:,\-\u2013\u2014!.]\s*\S"
                  r"|(?:bug|idea|suggestion)\s+(?:report\s+)?(?:for\s+(?:you|the\s+bot)|about|with|in)\b"
                  r"|report\s+a\s+bug\b|(?:something(?:'|\u2019)?s|something\s+is|this\s+is|the\s+bot\s+is|scout\s+is)\s+(?:broken|not\s+working|buggy)\b"
                  r"|suggestion\s+\S)", _re.I)

def is_feedback(text):
    """Only clear openers count ('bug, the link didn't open', 'idea: ...', 'suggestion ...', 'something's broken').
    Anything unsure returns False, so the text is handled as a normal reply/relay."""
    return bool(text and _FB.search(text))

def feedback_payload(words, last_kind):
    """Only the person's exact words, the VERSION, and the kind of last text. No names, phones, addresses or criteria."""
    v = open(os.path.join(HERE, "VERSION")).read().strip() if os.path.exists(os.path.join(HERE, "VERSION")) else "?"
    return {"words": words, "version": v, "last_text": last_kind or "unknown"}

def record_feedback(payload, path=None):
    path = path or FEEDBACK
    os.makedirs(os.path.dirname(path), exist_ok=True)
    item = {"id": time.strftime("%Y%m%d-%H%M%S"), "ts": time.strftime("%F %T %Z"), **payload, "status": "pending_review"}
    with open(path, "a") as f: f.write(json.dumps(item) + "\n")
    return item

def feedback_items(path=None):
    path = path or FEEDBACK
    if not os.path.exists(path): return []
    return [json.loads(l) for l in open(path) if l.strip()]
