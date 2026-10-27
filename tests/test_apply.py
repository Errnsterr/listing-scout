"""Apply for me: text parsing, member scoping, the scam gate, plan contents, no SPI ever persisted, text style.
Runs on a temp copy with a temp profile path; never touches live state, never sends, never opens a link."""
import os, sys, json, copy, shutil, subprocess, tempfile, time, stat, glob
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import yaml, style
C = yaml.safe_load(open("CRITERIA.example.yaml"))
ok = lambda m: not style.check(m)
FAKE_SSN = "123-45-6789"
NOW = time.time()
L1 = {"id": "a", "where": "Maple St", "price": "$3,900/mo", "url": "https://www.zillow.com/homedetails/a/",
      "apply_url": "https://www.zillow.com/rental-manager/apply/synth-1/", "source": "Zillow", "sent_ts": NOW}
L2 = {"id": "b", "where": "Oak Ave", "price": "$4,100/mo", "url": "https://examplepm.com/listings/b",
      "apply_url": "https://examplepm.appfolio.com/apply/b", "source": "Example PM", "sent_ts": NOW}

def sandbox(profiles=None, numbered=(L1, L2)):
    d = tempfile.mkdtemp()
    for f in ("replies.py", "style.py", "notify.py", "scout.py", "features.py", "apply.py"): shutil.copy(os.path.join(HERE, "src", f), d)
    os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs"); c = copy.deepcopy(C); c["replies"] = True
    c["recipients"] = [{"name": "Alex", "role": "owner"}, {"name": "Sarah", "role": "co_decider"}]
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))
    json.dump(list(numbered), open(f"{d}/out/last_numbered.json", "w"))
    json.dump({"Sarah": {"joined": "x"}}, open(f"{d}/out/members.json", "w"))
    prof = f"{d}/cfg/apply_profile.json"; env = {**os.environ, "SCOUT_CRITERIA": f"{d}/CRITERIA.yaml", "LISTING_SCOUT_APPLY_PROFILE": prof}
    if profiles:
        os.environ["LISTING_SCOUT_APPLY_PROFILE"] = prof
        import importlib, apply as ap; importlib.reload(ap)
        for n, f in profiles.items(): ap.save_profile(n, f)
    run = lambda who, t: subprocess.run([sys.executable, "replies.py", "--as", who, "--text", t], cwd=d, capture_output=True, text=True, env=env).stdout
    plan = lambda rid: subprocess.run([sys.executable, "apply.py", "plan", rid], cwd=d, capture_output=True, text=True, env=env).stdout
    return d, run, plan, prof

PROF = {"employer": "Acme", "job_title": "Nurse", "monthly_income": 9000, "move_date": "2026-12-01", "occupants": 2,
        "ssn": FAKE_SSN, "date_of_birth": "1990-01-01", "drivers_license": "D1234567"}   # last three must be dropped

def reqs(d): return json.load(open(f"{d}/out/apply_requests.json")) if os.path.exists(f"{d}/out/apply_requests.json") else []

def test_parse_and_index():
    d, run, _, _ = sandbox({"Alex": PROF})
    o = run("Alex", "apply 2"); R = reqs(d)
    assert len(R) == 1 and R[0]["listing"]["id"] == "b" and R[0]["member"] == "Alex" and "APPLY_REQUEST" in o
    run("Alex", "Apply for it #1"); assert reqs(d)[-1]["listing"]["id"] == "a"
    o = run("Alex", "apply"); assert len(reqs(d)) == 2 and "Which place" in o        # two places, no context: ask
    o = run("Alex", "apply 9"); assert len(reqs(d)) == 2 and "apply 1 or apply 2" in o
    run("Alex", "I'd love to apply someday"); assert len(reqs(d)) == 2                # not a command

def test_single_place_no_index():
    d, run, _, _ = sandbox({"Alex": PROF}, numbered=(L1,))
    run("Alex", "apply"); assert reqs(d)[0]["listing"]["id"] == "a"

def test_member_scoping():
    d, run, _, _ = sandbox({"Alex": PROF})
    o = run("Sarah", "apply 1"); assert reqs(d) == [] and "own profile" in o and "to Alex" not in o   # no profile of her own
    o = run("Alex", "apply 1"); assert reqs(d)[0]["member"] == "Alex" and "to Sarah" not in o        # nobody else is texted

def test_profile_never_holds_spi():
    d, run, _, prof = sandbox({"Alex": PROF})
    raw = open(prof).read()
    assert FAKE_SSN not in raw and "1990-01-01" not in raw and "D1234567" not in raw
    assert stat.S_IMODE(os.stat(prof).st_mode) == 0o600
    import apply as ap
    try: ap.save_profile("Alex", {"employer": "SSN " + FAKE_SSN}); assert False
    except ValueError: pass

def test_gate():
    import apply as ap
    assert ap.gate(L1, C) == [] and ap.gate(L2, C) == []
    assert ap.gate(dict(L1, flags=["suspicious payment/deposit wording"]), C)
    assert ap.gate(dict(L1, desc="Pay a deposit before viewing by wire"), C)
    assert ap.gate(dict(L1, desc="Gift card accepted"), C)
    assert ap.gate(dict(L1, apply_url="https://rent-fast-apply.example/x"), C)          # host mismatch
    assert ap.gate(dict(L1, apply_url="http://www.zillow.com/apply/"), C)
    assert ap.gate(dict(L1, apply_url=None), C)
    assert ap.gate(dict(L1, sent_ts=NOW - 5 * 86400), C)                                   # stale
    assert ap.gate(dict(L1, desc="adults only building"), C)                                # fair housing

def test_plan_contents_and_no_spi_on_disk():
    d, run, plan, prof = sandbox({"Alex": PROF})
    run("Alex", "apply 1"); rid = reqs(d)[0]["id"]
    o = plan(rid); assert o.startswith("ready_to_fill")
    P = json.load(open(f"{d}/out/apply_plans/{rid}.json"))
    assert P["status"] == "ready_to_fill" and P["member"] == "Alex"
    for k in ("ssn", "date_of_birth", "id_upload", "id_verification_selfie", "credit_check_consent", "e_signature", "phone_code", "captcha"):
        assert k in P["owner_provides"]
    assert "employer" in P["from_profile"] and "Acme" not in json.dumps(P)               # names only, never values
    assert set(P["from_vault"]) == {"full_name", "address", "phone", "email"}
    assert any("explicit yes" in r for r in P["rules"]) and any("never email" in r for r in P["rules"])
    for f in glob.glob(f"{d}/**/*", recursive=True):                                        # grep every output
        if os.path.isfile(f) and not f.endswith(".py"):
            s = open(f, errors="ignore").read(); assert FAKE_SSN not in s and "1990-01-01" not in s and "D1234567" not in s, f

def test_plan_stops_on_scam():
    d, run, plan, _ = sandbox({"Alex": PROF}, numbered=(dict(L1, flags=["suspicious payment/deposit wording"]),))
    run("Alex", "apply"); rid = reqs(d)[0]["id"]
    assert plan(rid).startswith("stop_and_ask_owner") and reqs(d)[0]["status"] == "waiting" and reqs(d)[0]["gate"] == "stop_and_ask_owner"

def test_texts_style():
    for m in (style.apply_ack("Maple St"), style.apply_ack("1234 Extraordinarily Longname Boulevard"), style.apply_need_profile(), style.apply_no_place()):
        assert ok(m), (m, style.check(m))

def _with_reqs(d, rs): json.dump(rs, open(f"{d}/out/apply_requests.json", "w"))
pend = lambda d, *a: subprocess.run([sys.executable, "apply.py", *a], cwd=d, capture_output=True, text=True,
                                    env={**os.environ, "SCOUT_CRITERIA": f"{d}/CRITERIA.yaml"}).stdout

def test_pending_lists_and_silent_when_none():
    d, *_ = sandbox()
    assert pend(d, "pending").strip() == "none"
    c = yaml.safe_load(open(f"{d}/CRITERIA.yaml")); c["recipients"][0]["phone_last4"] = "4321"; yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))
    _with_reqs(d, [{"id": "r1", "member": "Alex", "listing": L1, "ts": time.time() - 600, "status": "new"}])
    o = pend(d, "pending"); assert "r1" in o and "..4321" in o and "listing a" in o and "10 min" in o and "-->" not in o

def test_mark():
    d, *_ = sandbox()
    _with_reqs(d, [{"id": "r1", "member": "Alex", "listing": L1, "ts": time.time(), "status": "new"}])
    assert "r1 handled" in pend(d, "mark", "r1", "handled") and reqs(d)[0]["status"] == "handled"
    assert pend(d, "pending").strip() == "none"
    assert "must be one of" in pend(d, "mark", "r1", "submitted") and "no such" in pend(d, "mark", "zz", "handled")

def test_expire_texts_only_that_member_once():
    d, *_ = sandbox()
    _with_reqs(d, [{"id": "old", "member": "Sarah", "listing": L2, "ts": time.time() - 25 * 3600, "status": "new"},
                   {"id": "new", "member": "Alex", "listing": L1, "ts": time.time(), "status": "new"}])
    o = pend(d, "pending")
    assert "--> to Sarah" in o and "--> to Alex" not in o and "EXPIRED old" in o and "I didn't apply to Oak Ave." in o
    assert {r["id"]: r["status"] for r in reqs(d)} == {"old": "expired", "new": "new"}
    assert "--> to" not in pend(d, "pending")                                  # second run: no repeat text
    for w in ("Oak Ave", "1234 Extraordinarily Longname Boulevard", ""): assert ok(style.apply_expired(w))

def test_waiting_and_in_progress():
    d, run, plan, _ = sandbox({"Alex": PROF})
    run("Alex", "apply 1"); rid = reqs(d)[0]["id"]; plan(rid)
    assert reqs(d)[0]["status"] == "waiting" and "waiting (ready_to_fill)" in pend(d, "pending")
    assert "in_progress" in pend(d, "mark", rid, "in_progress") and reqs(d)[0]["status"] == "in_progress"
    R = reqs(d); R[0]["ts"] = time.time() - 48 * 3600; _with_reqs(d, R)
    o = pend(d, "pending"); assert "-->" not in o and "in_progress" in o and reqs(d)[0]["status"] == "in_progress"   # never expires
    R[0]["status"] = "waiting"; _with_reqs(d, R)
    o = pend(d, "pending"); assert "EXPIRED" in o and reqs(d)[0]["status"] == "expired"                              # waiting does

def test_buy_mode_and_in_the_know_have_no_apply():
    d, run, _, _ = sandbox({"Alex": PROF})
    c = yaml.safe_load(open(f"{d}/CRITERIA.yaml")); c["mode"] = "buy"; yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))
    run("Alex", "apply 1"); assert reqs(d) == []
    assert "Apply" not in style.capabilities(True, [], False) and "Apply" not in style.how_replies_work("Sarah", apply_=False)
    assert "apply" not in style.owner_welcome("Alex", 3, False, "home")

if __name__ == "__main__":


    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"): f(); n += 1
    print(f"{n} apply tests passed")
