"""Heads-ups: welcome lines, the one-time first-alert note, proven sites, Android help. Run: python3 tests/test_headsups.py"""
import os, sys, json, copy, time, shutil, tempfile, importlib.util, subprocess
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(HERE); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "tests"))
import yaml, style
CF = next(f for f in ("CRITERIA.yaml", "tests/fixtures/CRITERIA.test.yaml") if os.path.exists(f)); C = yaml.safe_load(open(CF))
SAMPLE = next(f for f in ("tests/sample_alerts.json", "tests/fixtures/sample_alerts.test.json") if os.path.exists(f))
NOTE = "Quick note on that one."
def box(shadow=False, members=None):
    d = tempfile.mkdtemp(); [shutil.copy(f, d) for f in ("notify.py", "scout.py", "style.py", "features.py")]
    os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs"); c = copy.deepcopy(C)
    c["recipients"] = [{"name": "Alex", "role": "owner", "phone_last4": "0000"}, {"name": "Sarah", "role": "co_decider", "phone_last4": "1111"}]
    c.update(paused=False, daily_cap=0, shadow=shadow, quiet_hours={"start": 0, "end": 0}); c.pop("mode", None)
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w")); json.dump(members or {}, open(f"{d}/out/members.json", "w"))
    os.environ["SCOUT_CRITERIA"] = f"{d}/CRITERIA.yaml"; os.environ.pop("PHOTON_API_KEY", None)
    spec = importlib.util.spec_from_file_location(f"nt{time.time_ns()}", f"{d}/notify.py"); n = importlib.util.module_from_spec(spec); spec.loader.exec_module(n)
    n.recipients = lambda: [{"name": "Alex", "role": "owner", "phone": "+10000000001", "line_last4": "0000"},
                            {"name": "Sarah", "role": "co_decider", "phone": "+10000000002", "line_last4": "0000"}]
    n.features.in_quiet = lambda C_: False; n.record_numbered = lambda q: None
    return d, n
def alerts(n, d, i):
    json.dump([{"reason": "new", "was": None, "market": None, "l": {**json.load(open(SAMPLE))[0]["l"], "id": f"h:{i}"}}], open(f"{d}/a.json", "w"))
    ob = f"{d}/outbox.json"
    if os.path.exists(ob): o = json.load(open(ob)); o["last_sent"] = 0; json.dump(o, open(ob, "w"))
    sys.argv = ["notify.py", "alerts", f"{d}/a.json", "--send"]; n.main()
def test_every_new_line_passes_check():
    for t in (style.first_alert_note(), style.owner_welcome("Sam", 10), *([style.owner_welcome("Sam", 10, True, "home")] if "kind" in style.owner_welcome.__code__.co_varnames else []),
              style.member_welcome("Kim", "Sam", ["2+ beds"], replies=True, card=True), style.member_welcome("Kim", "Sam", ["x"], "home"),
              style.capabilities(True, []), style.capabilities(False, ["Zillow"]), style.capabilities(True, ["Zillow", "Redfin", "HotPads"]),
              style.how_replies_work("Sam", android=True), style.how_replies_work(None, android=False)):
        assert style.check(t) == [], (style.check(t), t)
def test_welcome_lines_and_trims():
    for t in (style.owner_welcome("Sam", 10), style.member_welcome("Kim", "Sam", ["2+ beds"], replies=True, card=True)):
        assert "Not listed yet is normal." in t and "A home may show up twice." in t and "Soon I'll send" not in t
    assert "I'll text when a new one fits." not in style.owner_welcome("Sam", 10)
    if "kind" in style.owner_welcome.__code__.co_varnames:   # template welcome budget (live install has 2 extra shared-search lines)
        assert len(style.member_welcome("Kim", "Sam", ["2+ beds"], replies=True, card=True).split("\n\n")) <= 16
def test_proven_sites_config_driven():
    assert "Sites are still warming up." in style.capabilities(sites=[])
    assert "Sites working so far:\n\nFoo." in style.capabilities(sites=["Foo"])
    assert "Foo, Bar and Baz." in style.capabilities(sites=["Foo", "Bar", "Baz"])
    d = tempfile.mkdtemp(); os.makedirs(f"{d}/out")
    json.dump({"Bar": {"first": "2026-01-02"}, "Foo": {"first": "2026-01-01"}}, open(f"{d}/out/sources_proven.json", "w"))
    assert style.proven_sites(d) == ["Foo", "Bar"] and style.proven_sites(tempfile.mkdtemp()) == []
    assert "slower" not in style.capabilities(sites=["Foo"])
    assert style.capabilities(sites=["Foo"]).endswith("The next step is always yours.\n\nBuilt by @errnsterr")
def test_android_only_when_asked():
    assert "Emoji may show as words." in style.how_replies_work("Sam", android=True)
    assert "Emoji" not in style.how_replies_work("Sam") and "Emoji" not in style.capabilities(sites=[])
def test_note_once_per_person_flag_before_send():
    d, n = box(); sent = []; seen_flag = []
    def snd(r, t, really, card=None):
        if t == style.first_alert_note(): seen_flag.append(bool(n.member(r).get("first_alert_note_sent")))
        sent.append((r["name"], t.startswith(NOTE))); return True
    n.send = snd
    alerts(n, d, 1); assert sent == [("Alex", False), ("Alex", True), ("Sarah", False), ("Sarah", True)], sent
    assert seen_flag == [True, True]   # saved before sending
    alerts(n, d, 2); assert [s for s in sent[4:] if s[1]] == [] and len(sent) == 6   # never twice
    d2, n2 = box(members={"Alex": {"first_alert_note_sent": "x"}, "Sarah": {"first_alert_note_sent": "x"}}); s2 = []
    n2.send = lambda r, t, really, card=None: s2.append(t.startswith(NOTE)) or True
    alerts(n2, d2, 3); assert s2 == [False, False]   # flag survives restarts (members.json)
def test_note_failed_alert_no_note():
    d, n = box(); sent = []
    n.send = lambda r, t, really, card=None: (sent.append((r["name"], t.startswith(NOTE))) or r["name"] != "Sarah")
    alerts(n, d, 1); assert ("Sarah", True) not in sent and ("Alex", True) in sent
def test_note_shadow_only_logs():
    if "shadow_texts" not in open("notify.py").read(): return   # install without shadow mode
    d = tempfile.mkdtemp(); [shutil.copy(f, d) for f in ("notify.py", "scout.py", "style.py", "features.py")]
    os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs"); c = copy.deepcopy(C); c.update(shadow=True, paused=False, daily_cap=0); c.pop("mode", None)
    c["recipients"] = [{"name": "Alex", "role": "owner", "phone_last4": "0000"}]; yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))
    json.dump([{"reason": "new", "was": None, "market": None, "l": json.load(open(SAMPLE))[0]["l"]}], open(f"{d}/a.json", "w"))
    env = {k: v for k, v in os.environ.items() if k != "PHOTON_API_KEY"}; env["SCOUT_CRITERIA"] = f"{d}/CRITERIA.yaml"
    o = subprocess.run([sys.executable, "notify.py", "alerts", "a.json", "--send"], cwd=d, capture_output=True, text=True, env=env)
    rows = [json.loads(x) for x in open(f"{d}/out/shadow_texts.jsonl")] if os.path.exists(f"{d}/out/shadow_texts.jsonl") else []
    assert [r["to"] for r in rows if NOTE in r["text"]] == ["Alex"], (rows, o.stdout, o.stderr)
def test_scout_records_each_proven_site():
    import test_email
    _, _, d = test_email.run_scout(["zillow_tracked.html", "redfin_tracked.html", "welcome_no_listings.html"])
    P = json.load(open(f"{d}/out/sources_proven.json")); assert set(P) == {"Zillow", "Redfin"}, P
    assert set(style.proven_sites(d)) == {"Zillow", "Redfin"}
if __name__ == "__main__":
    T = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in T: t()
    print(f"{len(T)} heads-up tests passed")
