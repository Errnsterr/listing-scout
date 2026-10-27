#!/usr/bin/env python3
"""Apply for me: the gate and the hand-off plan. Sends nothing, submits nothing, pays nothing, contacts no one.
A member texts "apply" (or "apply 2"); src/replies.py records it in out/apply_requests.json.
The bot then runs:
  python3 src/apply.py plan <request_id>      # gate + plan -> out/apply_plans/<id>.json (prints a short summary)
  python3 src/apply.py pending [--send]       # open requests; expires >24 h ones (one text to that member, live only with --send)
  python3 src/apply.py mark <id> in_progress|handled|expired|declined   # plan sets waiting
  python3 src/apply.py profile --check NAME   # which profile fields are filled (names only, never values)
and does the rest itself in its browser, stopping at the review page for the owner's yes.
NEVER stored here or anywhere: SSN, date of birth, driver's license number, bank numbers, ID or pay stub files."""
import os, sys, re, json, time
from urllib.parse import urlparse
_SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC
OUT = os.path.join(HERE, "out")
REQ = os.path.join(OUT, "apply_requests.json")
PLANS = os.path.join(OUT, "apply_plans")
PROFILE = os.environ.get("LISTING_SCOUT_APPLY_PROFILE", os.path.expanduser("~/.config/listing-scout/apply_profile.json"))
FRESH_HOURS = 72   # older than this since the alert: ask the owner first (it may be gone)

# The only fields a profile may hold (non-sensitive). Anything else is dropped on save.
PROFILE_FIELDS = ("employer", "job_title", "monthly_income", "current_address", "current_landlord_ref",
                  "previous_addresses", "previous_landlord_refs", "move_date", "occupants", "pets", "vehicles",
                  "emergency_contact_name")
VAULT_FIELDS = ("full_name", "address", "phone", "email")            # filled from the Grok Bot vault, never copied here
OWNER_STEPS = ("ssn", "date_of_birth", "id_upload", "paystub_upload", "id_verification_selfie",
               "credit_check_consent", "e_signature", "phone_code", "captcha")
FORBIDDEN = re.compile(r"ssn|social|security.?number|dob|birth|license|licence|passport|bank|routing|account.?num|tax.?id|itin|paystub|pay.?stub|document|upload", re.I)
SSN_RX = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")
# Apply pages that commonly sit on a platform host, not the listing's own domain.
PLATFORMS = ("zillow.com", "redfin.com", "hotpads.com", "trulia.com", "apartments.com", "appfolio.com", "rentcafe.com",
             "buildium.com", "managebuilding.com", "rentmanager.com", "entrata.com", "yardi.com", "realpage.com")
UPFRONT_RX = re.compile(r"wire|western union|gift ?card|zelle|venmo|cash ?app|crypto|bitcoin|deposit (before|to hold)|pay (before|to) (see|view|tour)|before (a )?(viewing|showing|tour)|keys will be mailed|out of the country|overseas", re.I)

load = lambda f, d: json.load(open(f)) if os.path.exists(f) else d

def base(host):
    parts = (host or "").lower().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host or ""

def load_profiles():
    return load(PROFILE, {}).get("profiles", {})

def has_profile(name):
    p = load_profiles().get(name) or {}
    return any(p.get(k) for k in PROFILE_FIELDS)

def save_profile(name, fields):
    """Keeps only PROFILE_FIELDS; refuses anything that looks like an SSN. chmod 600. Returns the field names kept."""
    clean = {k: v for k, v in fields.items() if k in PROFILE_FIELDS and not FORBIDDEN.search(k)}
    if SSN_RX.search(json.dumps(clean)): raise ValueError("looks like an SSN; never stored")
    os.makedirs(os.path.dirname(PROFILE), exist_ok=True)
    d = load(PROFILE, {}); d.setdefault("profiles", {})[name] = clean
    fd = os.open(PROFILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: json.dump(d, f, indent=1)
    os.chmod(PROFILE, 0o600)
    return sorted(clean)

def gate(L, C=None):
    """Return a list of plain-words reasons to stop and ask the owner. Empty = OK to start filling."""
    C = C or {}
    why = []
    words = " ".join(str(L.get(k) or "") for k in ("where", "text", "desc", "description"))
    phrases = (C.get("scam_flags") or {}).get("phrases") or []
    if L.get("flags"): why.append("scam check flagged it: " + "; ".join(L["flags"]))
    if any(p.lower() in words.lower() for p in phrases) or UPFRONT_RX.search(words):
        why.append("asks for payment up front or by wire or gift card")
    try:
        sys.path.insert(0, _SRC); import scout
        if scout.NO_RELAY.search(words): why.append("listing has wording we never relay (fair housing)")
    except Exception: pass
    au = L.get("apply_url")
    if not au: why.append("no apply link from the listing")
    else:
        u = urlparse(au); h = u.hostname or ""
        lh = urlparse(L.get("url") or "").hostname or ""
        if u.scheme != "https": why.append("apply link is not https")
        elif base(h) != base(lh) and base(h) not in PLATFORMS:
            why.append(f"apply link host ({h}) doesn't match the listing ({lh or 'no listing link'})")
    ts = L.get("sent_ts")
    if not ts or time.time() - ts > FRESH_HOURS * 3600: why.append("listing may not be fresh anymore")
    return why

def build_plan(req, C=None):
    L = req["listing"]; prof = load_profiles().get(req["member"]) or {}
    why = gate(L, C)
    return {"request_id": req["id"], "member": req["member"], "made": time.strftime("%F %T %Z"),
            "listing": {k: L.get(k) for k in ("id", "where", "price", "url", "apply_url", "source")},
            "status": "stop_and_ask_owner" if why else "ready_to_fill", "stop_reasons": why,
            "from_profile": sorted(k for k in PROFILE_FIELDS if prof.get(k)),   # field NAMES only; values stay in the profile file
            "missing_profile_fields": sorted(k for k in PROFILE_FIELDS if not prof.get(k)),
            "from_vault": list(VAULT_FIELDS), "fee_card": "vault card, only after the owner's yes for this application",
            "owner_provides": list(OWNER_STEPS),
            "owner_provides_how": "SSN and date of birth: a use-once Secure Form each time. ID and pay stubs: attach in the Grok Bot app. "
                                  "Selfie ID checks, credit consent, e-signature, phone codes, captchas: the owner does these.",
            "fee": L.get("fee") or "not listed yet",
            "rules": ["fill only on the listing's own apply page", "stop at the review page",
                      "show the owner what was filled and the fee", "submit and pay only after an explicit yes for this application",
                      "never email, call or message the landlord or agent", "never store SSN, DOB, ID numbers or documents"]}

EXPIRE_HOURS = 24
DONE = ("handled", "expired", "declined")
MARKS = DONE + ("in_progress",)   # in_progress: the member said yes; never expires

def _crit():
    import yaml
    cp = os.environ.get("SCOUT_CRITERIA", os.path.join(HERE, "CRITERIA.yaml"))
    return yaml.safe_load(open(cp)) if os.path.exists(cp) else {}

def _ts(r):
    return r.get("ts") or (time.mktime(time.strptime(r["asked"][:19], "%Y-%m-%d %H:%M:%S")) if r.get("asked") else 0)

def pending(send=False, now=None):
    """Lists open requests (id, member last-4, listing id, age). Expires ones older than 24 h and texts
    style.apply_expired() to that member only (live only with --send; otherwise prints). Returns the open list."""
    now = now or time.time(); R = load(REQ, [])
    C = _crit(); last4 = {x.get("name"): x.get("phone_last4") or "----" for x in C.get("recipients") or []}
    open_, expired = [], []
    for r in R:
        if r.get("status") in DONE: continue
        if r.get("status", "new") in ("new", "waiting") and now - _ts(r) > EXPIRE_HOURS * 3600:
            r["status"] = "expired"; r["closed"] = time.strftime("%F %T %Z"); expired.append(r)
        else: open_.append(r)
    if expired:
        json.dump(R, open(REQ, "w"), indent=1)
        sys.path.insert(0, _SRC); import style
        for r in expired:
            t = style.apply_expired(r["listing"].get("where", ""))
            if send:
                import notify
                live = {x["name"]: x for x in notify.recipients()}
                if r["member"] in live: notify.send(live[r["member"]], t, True)
                else: print(f"WARNING: not texting {r['member']}: not a live Photon user")
            else: print(f"--> to {r['member']}:\n{t}\n")
            print(f"EXPIRED {r['id']}")
    for r in open_:
        age = int((now - _ts(r)) // 60)
        print(f"{r['id']}  member ..{last4.get(r['member'], '----')}  listing {r['listing'].get('id')}  {age} min  {r.get('status', 'new')}" + (f" ({r['gate']})" if r.get("gate") else ""))
    if not open_ and not expired: print("none")
    return open_

def mark(rid, status):
    if status not in MARKS: print(f"status must be one of {MARKS}"); return 1
    R = load(REQ, []); r = next((x for x in R if x["id"] == rid), None)
    if not r: print("no such apply request"); return 1
    r["status"] = status; r["closed" if status in DONE else "started"] = time.strftime("%F %T %Z"); json.dump(R, open(REQ, "w"), indent=1)
    print(f"{rid} {status}"); return 0

def main(a):
    if a[:1] == ["pending"]: pending("--send" in a); return 0
    if a[:1] == ["mark"] and len(a) == 3: return mark(a[1], a[2])
    if a[:1] == ["plan"]:
        R = load(REQ, []); req = next((r for r in R if r["id"] == a[1]), None)
        if not req: print("no such apply request"); return 1
        import yaml
        cp = os.environ.get("SCOUT_CRITERIA", os.path.join(HERE, "CRITERIA.yaml"))
        C = yaml.safe_load(open(cp)) if os.path.exists(cp) else {}
        plan = build_plan(req, C)
        os.makedirs(PLANS, exist_ok=True); json.dump(plan, open(os.path.join(PLANS, req["id"] + ".json"), "w"), indent=1)
        req["status"] = "waiting"; req["gate"] = plan["status"]; json.dump(R, open(REQ, "w"), indent=1)
        print(f"{plan['status']}: {plan['listing']['where']}" + ("".join("\n- " + w for w in plan["stop_reasons"])))
        return 0
    if a[:2] == ["profile", "--check"]:
        n = a[2]; p = load_profiles().get(n) or {}
        print(f"{n}: filled {sorted(k for k in PROFILE_FIELDS if p.get(k))}; missing {sorted(k for k in PROFILE_FIELDS if not p.get(k))}"); return 0
    print(__doc__); return 0

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
