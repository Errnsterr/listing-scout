"""Extra features: 30-character lines, address over link, Take a break, Sleep mode, Still available?,
One home one text, Fine-tune the search, We found it, Your data stays put. Temp copies only; never sends."""
import os, sys, json, copy, shutil, subprocess, tempfile, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import yaml, style, features, scout as sc
SAMPLES = "tests/sample_alerts.json" if os.path.exists("tests/sample_alerts.json") else "tests/fixtures/sample_alerts.test.json"
CRIT = "CRITERIA.yaml" if os.path.exists("CRITERIA.yaml") else "tests/fixtures/CRITERIA.test.yaml"
os.environ.setdefault("SCOUT_CRITERIA", os.path.abspath(CRIT))   # notify.py reads it at import
C = yaml.safe_load(open(CRIT)); sc.CFG.update(C); A = json.load(open(SAMPLES))
for a in A: a["l"].setdefault("flags", [])
ok = lambda m: not style.check(m)

def sandbox(members=None, shortlist=None):
    d = tempfile.mkdtemp(); [shutil.copy(os.path.join(HERE, "src", f) if str(f).endswith(".py") else f, d) for f in ("replies.py", "style.py", "notify.py", "scout.py", "features.py")]
    os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs"); c = copy.deepcopy(C); c["replies"] = True
    c["recipients"] = [{"name": "Alex", "role": "owner"}, {"name": "Sarah", "role": "co_decider"}]
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))
    json.dump([{"id": "a", "where": "Maple St"}, {"id": "b", "where": "Oak Ave"}], open(f"{d}/out/last_numbered.json", "w"))
    json.dump(members or {"Sarah": {"joined": "x"}}, open(f"{d}/out/members.json", "w"))
    if shortlist is not None: json.dump(shortlist, open(f"{d}/out/shortlist.json", "w"))
    run = lambda who, t: subprocess.run([sys.executable, "replies.py", "--as", who, "--text", t], cwd=d, capture_output=True, text=True,
                                        env={**os.environ, "SCOUT_CRITERIA": f"{d}/CRITERIA.yaml"}).stdout
    return d, run

# ---------- formatting ----------
def test_every_line_fits_30():
    assert style.MAX == 30
    assert style.check("This line has thirty-one chars.")                      # 31: flagged
    assert not style.check("This line is exactly 30 chars.")
    msgs = [sc.render(A[:1], C), sc.render(A[:3], C), sc.snapshot([a for a in A if a["l"]["match"]], 10, C),
            style.member_welcome("Josephine", "Bartholomew", sc.reflect(C), replies=True, card=True), style.owner_invite_intro("Josephine"),
            style.sleep_offer("2:14 AM"), style.gone_note("Santa Isabel"), style.change_ask("Add 78745 to the search."), style.data_note()]
    for m in msgs:
        assert ok(m), (m, style.check(m))
        L = m.split("\n")
        for i, ln in enumerate(L):
            if style.URL.fullmatch(ln) or (i + 1 < len(L) and style.URL.fullmatch(L[i + 1])): continue
            assert len(ln) <= 30, ln
    assert all(len(x) <= 30 for x in sc.reflect(C))
    try: style.text([["This sentence is longer than thirty."]]); assert False
    except style.StyleError: pass

def test_quotes_stay_exempt():
    t = style.relay("Sarah", "Maple St", "this is a long verbatim note that runs well past thirty characters")
    assert ok(t) and "well past thirty characters\"" in t

def test_address_labels_link():
    import re
    t3 = sc.render(A[:3], C); L3 = t3.split("\n")   # roundup: "N. street", short facts, then its own link
    for i, ln in enumerate(L3):
        if ln.startswith("http"):
            l_ = next(a["l"] for a in A if a["l"].get("url") == ln)
            h = next(x for x in reversed(L3[:i]) if re.fullmatch(r"\d\. .+", x))
            assert h.split(". ", 1)[1] == sc.street_line(l_) and L3.index(h) >= i - 3, (h, ln)
    assert "not listed yet" not in t3 and ok(t3)
    snap = sc.snapshot([a for a in A if a["l"]["match"]], 10, C)   # snapshot = every match, in the roundup entry
    M = sc.rank([a for a in A if a["l"]["match"]], C)
    for i, a in enumerate(M, 1):
        blk = snap.split(f"\n{i}. ", 1)[1].split("\n\n", 1)[0]
        assert blk.startswith(sc.street_line(a["l"]) or "") and (not a["l"].get("url") or a["l"]["url"] in blk), (i, blk)
    assert "not listed yet" not in snap.split("right now:", 1)[-1].split("\n\n", 2)[-1] and ok(snap)
    for t in (sc.render(A[:1], C),):
        L = t.split("\n")
        for i, ln in enumerate(L):
            if ln.startswith("http") and (i == 0 or not L[i - 1].endswith(":")):
                assert L[i - 1] and not L[i - 1].startswith("http") and i >= 1, (L[i - 1], ln)
                assert L[i - 1] in t and (L[i - 1] == sc.street_line(next(a["l"] for a in A if a["l"].get("url") == ln)) or "Address" in L[i - 1])
    l = copy.deepcopy(A[0]["l"]); l["address"] = "12345 Northwest Military Highway Boulevard, City, CA 90000"
    t = sc.render([{"reason": "new", "was": None, "market": None, "l": l}], C)
    assert "Hwy Blvd" in t and ok(t)                          # long street: short suffixes, kept whole, still labels the link

# ---------- 1. Take a break ----------
def test_stop_is_instant_and_silent():
    d, run = sandbox()
    o = run("Sarah", "STOP"); assert "--> to Sarah" not in o and "Sarah turned off texts." in o

def test_owner_removal_asks_first_and_deletes_replies():
    d, run = sandbox(shortlist={"a": {"where": "Maple St", "price": "$1", "likes": ["Sarah"], "pass": [], "tour": [], "notes": [["Sarah", "love it", "t"]]}})
    o = run("Alex", "remove Sarah"); assert "Take Sarah off the search?" in o and "just say yes" not in o
    assert json.load(open(f"{d}/out/shortlist.json"))["a"]["notes"]             # nothing changed before the yes
    o = run("Alex", "no"); assert "Okay, nothing changed." in o
    run("Alex", "remove Sarah"); o = run("Alex", "yes")
    assert "Sarah is off the search." in o and "You're off the search now." in o
    S = json.load(open(f"{d}/out/shortlist.json"))["a"]; M = json.load(open(f"{d}/out/members.json"))
    assert S["notes"] == [] and S["likes"] == [] and M["Sarah"].get("left") and "joined" not in M["Sarah"]
    assert "--> to Sarah" not in run("Alex", "love Maple St")                       # never texted again

# ---------- 2. Sleep mode ----------
def test_quiet_hours():
    assert features.in_quiet(C, 2) and features.in_quiet(C, 23) and not features.in_quiet(C, 7) and not features.in_quiet(C, 14)
    assert features.wake_label(C) == "7 AM"

def test_sleep_offer_then_yes():
    d, run = sandbox({"Sarah": {"joined": "x", "pending": {"type": "sleep"}}})
    o = run("Sarah", "yes"); assert "Sleep mode is on." in o and "Night finds come at 7 AM." in o
    assert json.load(open(f"{d}/out/members.json"))["Sarah"]["sleep"] is True
    o = run("Sarah", "sleep mode off"); assert "Sleep mode is off." in o
    m = style.sleep_offer("2:14 AM"); assert "2:14 AM" in m and m.endswith("Want me to?") and ok(m)

def test_sleep_declined_is_quiet():
    d, run = sandbox({"Sarah": {"joined": "x", "pending": {"type": "sleep"}}})
    o = run("Sarah", "no thanks"); assert "--> to" not in o and not json.load(open(f"{d}/out/members.json"))["Sarah"].get("sleep")

# ---------- 3. Still available? ----------
def test_gone_only_liked_after_a_day():
    now = time.time()
    S = {"a": {"gone_since": now - 25 * 3600}, "b": {"gone_since": now - 25 * 3600}, "c": {"gone_since": now - 3600}}
    SL = {"a": {"where": "Maple St", "likes": ["Sarah"]}, "b": {"where": "Oak Ave", "likes": [], "pass": ["Alex"]},
          "c": {"where": "Elm St", "likes": ["Alex"]}}
    assert features.gone_liked(S, SL, now) == [{"id": "a", "where": "Maple St"}]
    SL["a"]["gone_told"] = "x"; assert features.gone_liked(S, SL, now) == []
    t = style.gone_note("Maple St"); assert "no longer listed" in t and "rented" not in t.lower() and ok(t)
    assert style.check("It was rented.")                                          # never 'rented'

# ---------- 4. One home, one text ----------
def test_cross_source_dedupe():
    S = {"pm:1": {"addr": "12 maple", "price": 3900, "gone_since": None}}
    l = {"id": "email:Zillow:9", "price": 3900}
    assert sc.cross_source(l, S, "12 maple") == ("skip", "pm:1")
    assert sc.cross_source(dict(l, price=4100), S, "12 maple") == ("skip", "pm:1")
    assert sc.cross_source(dict(l, price=3800), S, "12 maple") == ("lower", "pm:1", 3900)   # lower: the price-drop promise
    assert sc.cross_source(l, S, None) is None                                                  # no address: alert, never guess
    S["pm:1"]["gone_since"] = 1; assert sc.cross_source(l, S, "12 maple") is None                # gone: relist logic handles it

# ---------- 5. Fine-tune the search ----------
def test_parse_change():
    P = lambda t: features.parse_change(t, C)
    assert P("add 78745")["desc"] == "add 78745 to the search."
    assert P("go up to 4,500")["value"] == 4500 and P("stretch to 5.5k")["kind"] == "stretch_max"
    assert P("3 beds is fine")["value"] == 3
    assert P("change the area")["unclear"] and P("love the kitchen") is None and P("yes") is None
    for ch in (P("add 78745"), P("go up to 4,500")): assert ok(style.change_ask(ch["desc"].capitalize()))

def test_change_readback_then_apply_only_on_yes():
    d, run = sandbox()
    o = run("Alex", "add 78745"); assert "Got it:" in o and "Add 78745 to the search." in o and "Want me to make that change?" in o
    o = run("Alex", "yes"); assert "Done, the search is updated." in o and "would back up and update CRITERIA" in o
    o = run("Alex", "change the area"); assert "I'm not sure what to change." in o

def test_co_decider_suggestion_goes_to_owner_verbatim():
    d, run = sandbox()
    o = run("Sarah", "can we go up to 4,500?")
    assert "--> to Alex" in o and '"can we go up to 4,500?"' in o and "Set your target to $4,500." in o and "Alex gets the final say." in o
    o = run("Sarah", "yes"); assert "make that change" not in o and "Done, the search" not in o    # only the owner's yes applies it
    o = run("Alex", "yes"); assert o.count("Done, the search is updated.") == 2

def test_apply_change_writes_backup():
    d = tempfile.mkdtemp(); p = f"{d}/C.yaml"
    open(p, "w").write('area:\n  zips: ["00001","00002"]   # mine\nbeds_min: 2   # keep\nprice_tiers: {target_max: 3000, stretch_max: 3500}\n')
    features.OUT = d
    bak = features.apply_change({"kind": "zip_add", "value": "78745"}, p); assert os.path.exists(bak)
    features.apply_change({"kind": "target_max", "value": 4000}, p)
    y = yaml.safe_load(open(p)); raw = open(p).read()
    assert y["area"]["zips"] == ["00001", "00002", "78745"] and y["price_tiers"] == {"target_max": 4000, "stretch_max": 4000} and "# keep" in raw
    features.OUT = os.path.join(features.HERE, "out")

# ---------- 6. We found it ----------
def test_found_by_co_decider_goes_to_owner():
    d, run = sandbox()
    o = run("Sarah", "we found it!")
    assert "--> to Alex" in o and '"we found it!"' in o and "Want me to wrap up the search?" in o and "Congrats" not in o
    o = run("Alex", "yes"); assert o.count("Congrats on the new place!") == 2 and "clear our search data" in o
    assert os.path.exists(f"{d}/out/search_ended.json")
    o = run("Alex", "yes"); assert "Done, it's all cleared." in o and "LISTENER_STOP" in o and "CLOSE_SAVED_SEARCHES" in o

# ---------- 7. Your data stays put ----------
def test_data_note_and_purge_asks_first():
    d, run = sandbox(shortlist={"a": {"where": "Maple St", "notes": [["Sarah", "x", "t"]], "likes": [], "pass": [], "tour": []}})
    assert "Replies stay while we search." in run("Sarah", "what do you keep")
    o = run("Alex", "delete everything"); assert "Delete all the search data?" in o and os.path.exists(f"{d}/out/shortlist.json")
    o = run("Alex", "yes"); assert "Done, it's all deleted." in o and not os.path.exists(f"{d}/out/shortlist.json")
    assert json.load(open(f"{d}/out/members.json"))["Sarah"] == {"joined": "x"}      # only the flags that keep STOP honored

def test_leave_deletes_their_replies():
    d, run = sandbox(shortlist={"a": {"where": "Maple St", "notes": [["Sarah", "x", "t"], ["Alex", "y", "t"]], "likes": ["Sarah"], "pass": [], "tour": []}})
    run("Sarah", "leave"); S = json.load(open(f"{d}/out/shortlist.json"))["a"]
    assert S["notes"] == [["Alex", "y", "t"]] and S["likes"] == []

def test_logs_kept_30_days():
    d = tempfile.mkdtemp(); os.makedirs(f"{d}/logs")
    for n, age in (("old.log", 31), ("new.log", 2), ("loop.pid", 99)):
        open(f"{d}/logs/{n}", "w").write("x"); t = time.time() - age * 86400; os.utime(f"{d}/logs/{n}", (t, t))
    assert features.prune_logs(root=d) == ["old.log"] and sorted(os.listdir(f"{d}/logs")) == ["loop.pid", "new.log"]



# ---------- relay acks (live bug 2026-10-26: role "co-decider" emptied the relay list) ----------
def _crit(d, recips):
    c = yaml.safe_load(open(f"{d}/CRITERIA.yaml")); c["recipients"] = recips; yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))

def test_hyphen_role_still_relays_and_acks_by_name():
    d, run = sandbox(members={"Sarah": {"joined": "x"}})
    _crit(d, [{"name": "Alex", "role": "owner"}, {"name": "Sarah", "role": "co-decider"}])
    o = run("Alex", "love Maple St")
    assert "--> to Sarah:" in o and "Passed that to Sarah.\n" in o and "everyone" not in o

def test_no_one_got_it_means_no_ack():
    d, run = sandbox()
    _crit(d, [{"name": "Alex", "role": "owner"}])
    o = run("Alex", "love Maple St")
    assert "Passed that" not in o and "WARNING" in o

def test_two_others_named_when_they_fit():
    d, run = sandbox(members={"Sam": {"joined": "x"}, "Jo": {"joined": "x"}})
    _crit(d, [{"name": "Alex", "role": "owner"}, {"name": "Sam", "role": "co_decider"}, {"name": "Jo", "role": "co_decider"}])
    o = run("Alex", "love Maple St"); assert "Passed that to Sam and Jo." in o

def test_two_others_long_names_say_everyone():
    d, run = sandbox(members={"Sarah": {"joined": "x"}, "Maximiliana": {"joined": "x"}})
    _crit(d, [{"name": "Alex", "role": "owner"}, {"name": "Sarah", "role": "co_decider"}, {"name": "Maximiliana", "role": "co_decider"}])
    o = run("Alex", "love Maple St"); assert "Passed that to everyone." in o

def test_left_member_not_counted_in_ack():
    d, run = sandbox(members={"Sarah": {"joined": "x", "left": True}})
    _crit(d, [{"name": "Alex", "role": "owner"}, {"name": "Sarah", "role": "co_decider"}])
    o = run("Alex", "love Maple St"); assert "Passed that" not in o

# ---------- channels: reactions sent as text + per-person channel ----------
def test_reaction_text_is_parsed_not_relayed():
    for t in ['Liked “Maple St”', 'Loved "Maple St"', 'Emphasized “Maple St”', 'Laughed at “Maple St”',
              'Disliked “Maple St”', 'Questioned “Maple St”', 'Reacted 😀 to “Maple St”']:
        assert style.parse_reaction(t) and style.parse_reaction(t)[0] != "remove", t
    assert style.parse_reaction('Removed a like from “Maple St”')[0] == "remove"
    for t in ["I liked it", "loved the kitchen", "liked Maple St", "yes"]: assert style.parse_reaction(t) is None, t
    d, run = sandbox()
    o = run("Sarah", 'Loved “Maple St 2 bed townhome”')
    assert "Sarah loved Maple St" in o and '"Loved' not in o and "Passed that" not in o
    sl = f"{d}/out/shortlist.json"; assert not os.path.exists(sl) or "Sarah" not in open(sl).read()   # not a like/pass decision
    o = run("Sarah", 'Disliked “Oak Ave”'); assert "Sarah disliked Oak Ave" in o and not os.path.exists(sl)
    assert run("Sarah", "Removed a heart from “Maple St”").strip() == "reaction removed; dropped silently"

def test_reaction_never_a_command():
    d, run = sandbox()
    for t in ['Liked “stop”', 'Loved “pause”', 'Liked “we found it”', 'Emphasized “delete everything”']:
        o = run("Alex", t); assert "-->" in o and "Sarah" in o
        M = json.load(open(f"{d}/out/members.json"))
        assert not any(v.get("stopped") or v.get("paused") or v.get("pending") for v in M.values()), (t, M)

def test_reaction_plain_word_for_android():
    d, run = sandbox(members={"Sarah": {"joined": "x", "channel": "sms"}})
    o = run("Alex", 'Liked "Oak Ave"'); assert "Alex liked Oak Ave" in o and "👍" not in o
    for m in (style.reaction("Sarah", "❤️", "loved", "Maple St"), style.reaction("Josephine", "😂", "laughed at", "Maple St", True)):
        assert ok(m) and all(len(x) <= 30 for x in m.split("\n")), m

def test_channel_plain_format():
    import notify
    t, card = notify.for_channel(style.member_welcome("Sarah", "Alex", sc.reflect(C), card=True), "x.vcf", "sms")
    assert card is None and style.SAVE_LINE in t and "card" not in t and ok(t)
    t2, _ = notify.for_channel(sc.render(A[:1], C), None, "rcs")
    assert "🏡" not in t2 and not style._EMOJI.search(t2) and ok(t2) and "\n\n\n" not in t2
    t3, c3 = notify.for_channel(sc.render(A[:1], C), "x.vcf", "imessage"); assert c3 == "x.vcf" and t3 == sc.render(A[:1], C)
    r = style.plain(style.relay("Alex", "Maple St", "love it 😍\nso much 🏡")); assert '"love it 😍\nso much 🏡"' in r   # member words verbatim
    a, b = style.owner_invite_intro("Sarah"), style.owner_invite_intro("Sarah", "sms")
    assert "More, then the arrow" in a and "Forward" in b and "More" not in b and ok(b)

def test_channel_check_fails_open_and_logs(tmp_path=None):
    import notify, importlib
    d = tempfile.mkdtemp(); os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs")
    old = (notify.HERE, notify.SENDLOG); notify.HERE = d; notify.SENDLOG = f"{d}/logs/sends.jsonl"
    try:
        r = {"name": "Sarah", "phone": "+10000000000", "line_last4": "0000"}
        env = os.environ.pop("PHOTON_API_KEY", None)
        assert notify.channel_of(r, refresh=True) == "imessage"           # no SDK: assume iMessage, never block
        notify.sdk_channel = lambda p: "sms"; os.environ["PHOTON_API_KEY"] = "x"
        assert notify.channel_of(r, refresh=True) == "sms"
        assert json.load(open(f"{d}/out/members.json"))["Sarah"]["channel"] == "sms"
        os.environ.pop("PHOTON_API_KEY")
        assert notify.send(r, sc.render(A[:1], C), False) is True                     # dry run only
        L = [json.loads(x) for x in open(notify.SENDLOG)]
        assert L[-1]["channel"] == "sms" and L[-1]["dry_run"] and "phone" not in L[-1] and "0000000000" not in open(notify.SENDLOG).read()
        if env: os.environ["PHOTON_API_KEY"] = env
    finally:
        notify.HERE, notify.SENDLOG = old; importlib.reload(notify)

def test_join_saves_channel_in_sim_without_blocking():
    d, run = sandbox(members={"Sarah": {"invited_ts": 1}})
    o = run("Sarah", "hi"); assert "Hi Sarah!" in o and "Sarah is in." in o


# ---------- Make it better (feedback, gated) ----------
def test_feedback_triggers_and_no_collisions():
    for t in ("bug, the link didn't open", "idea: a map view", "suggestion add a pool filter", "something's broken", "Bug! no photos"):
        assert features.is_feedback(t), t
    for t in ("love the kitchen", "no, too far", "yes to Maple St", "pass", "tour it", "shortlist", "sleep mode", "pause",
              "add 78745 to the search", "the idea of a yard is nice", "Ideal spot", "debug", "suggestions?", "we found one", "help"):
        assert not features.is_feedback(t), t

def test_feedback_confirm_yes_records_pending_review_only():
    d, run = sandbox(); shutil.copy("VERSION", d)
    o = run("Sarah", "bug, the link didn't open")
    assert "Send it to the Scout team?" in o and ok(o.split("--> to Sarah:")[1].strip()) and not os.path.exists(f"{d}/out/feedback.jsonl")
    o = run("Sarah", "yes"); assert "Thanks, I passed it on." in o and "FEEDBACK_EMAIL" not in o
    L = [json.loads(x) for x in open(f"{d}/out/feedback.jsonl")]
    assert len(L) == 1 and L[0]["status"] == "pending_review" and L[0]["words"] == "bug, the link didn't open"
    assert set(L[0]) == {"id", "ts", "words", "version", "last_text", "status"} and L[0]["version"] == open("VERSION").read().strip()
    assert "Sarah" not in json.dumps(L[0]) and "Alex" not in json.dumps(L[0])

def test_feedback_no_or_silence_drops_it():
    d, run = sandbox()
    run("Sarah", "idea: a map view"); o = run("Sarah", "no"); assert "Okay, I won't send it." in o
    run("Sarah", "idea: a map view"); o = run("Sarah", "love the kitchen")   # anything else: lapses, handled as a relay
    assert 'Sarah on' in o or '"love the kitchen"' in o
    assert not os.path.exists(f"{d}/out/feedback.jsonl")

def test_feedback_email_only_when_configured():
    d, run = sandbox(); c = yaml.safe_load(open(f"{d}/CRITERIA.yaml")); c["feedback_email"] = "team@example.com"
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))
    run("Sarah", "suggestion add a pool filter"); o = run("Sarah", "yes")
    m = json.loads(o.split("FEEDBACK_EMAIL ")[1].splitlines()[0])
    assert m["to"] == "team@example.com" and m["body"] == {"words": "suggestion add a pool filter", "version": "?", "last_text": "welcome"}

def test_review_gate_and_fixed_draft():
    import importlib, review_feedback as rf
    tmp = tempfile.mkdtemp(); old = features.FEEDBACK; features.FEEDBACK = f"{tmp}/feedback.jsonl"
    try:
        it = features.record_feedback(features.feedback_payload("idea: map view", "alert"))
        try: rf.draft_fixed(it); assert False
        except ValueError: pass
        try: rf.main(["--fixed", it["id"]]); assert False   # can't skip approval
        except SystemExit: pass
        rf.main(["--approve", it["id"]]); rf.main(["--fixed", it["id"]])
        f = features.feedback_items()[0]; assert f["status"] == "fixed"
        assert ok(rf.draft_fixed(f)) and "You asked, it's fixed:" in rf.draft_fixed(f)
    finally: features.FEEDBACK = old

def test_welcome_mentions_feedback_once_receipt_last():
    m = style.owner_welcome("Alex", 620, True)
    assert m.count(style.FEEDBACK_LINE) == 1 and m.rstrip().endswith(style.RECEIPT) and ok(m)
    m = style.member_welcome("Sarah", "Alex", sc.reflect(C), replies=True, card=True)   # member: feedback line trimmed for the 18+ line
    assert style.FEEDBACK_LINE not in m and style.AGE_LINE in m and m.rstrip().endswith(style.RECEIPT) and ok(m)
    for m in (style.feedback_ask("bug, x"), style.feedback_sent(), style.feedback_dropped()): assert ok(m)


# ---------- light filters + criteria hygiene ----------
def _l(**k):
    l = dict(id="t", source="t", url="https://x.example/1", title="", text="", address="1 A St, Los Angeles, CA 90002", price=3600, beds=2, baths=2,
             sqft=None, available=None, pets_raw=None, photo=None, photo_alt=None, showing_url=None, listed_on=None); l.update(k); return l
def _LC():
    c = copy.deepcopy(C); c["beds_min"] = 2; c["area"] = {"cities": ["Los Angeles"], "zips": ["90002"]}; c["match"] = {"baths_min": 1, "price_max": 5000, "exclude_no_pets": True, "nice_to_have": ["garage", "layout"], "layout_any": [], "garage_min": 0}; return c
def test_light_filters():
    c = _LC()
    assert sc.classify(_l(), c)["match"]                                   # garage/layout unknown: still a match
    assert sc.classify(_l(beds=None, baths=None, price=None), c)["match"]  # unknowns kept
    assert not sc.classify(_l(price=5100), c)["match"] and sc.misses(sc.classify(_l(price=5100), c), c) == ["price"]
    assert not sc.classify(_l(baths=0.5), c)["match"]
    assert not sc.classify(_l(pets_raw="No pets"), c)["match"]
    assert not sc.classify(_l(address="1 A St, Ogdenville, CA 00009"), c)["match"]
def test_nice_to_have_lines():
    c = _LC(); sc.CFG.clear(); sc.CFG.update(c)
    t = sc.render([{"l": sc.classify(_l(), c), "reason": "new", "was": None}], c)
    assert "Garage" not in t and "Layout" not in t and ok(t), t   # shown only when the listing states them
    t = sc.render([{"l": sc.classify(_l(title="townhouse attached garage"), c), "reason": "new", "was": None}], c)
    assert "Has a garage" in t and "Townhome" in t and ok(t), t
    sc.CFG.clear(); sc.CFG.update(C)
def test_hygiene_texts():
    for m in (style.must_or_nice_q("garage"), style.must_or_nice_q("layout"), style.tradeoff_text((3, 12)), style.tradeoff_text(None),
              style.near_miss_ask(4, "price", "Set your stretch to $5,200."), style.near_miss_ask(1, "layout", "Make ground floor optional."), style.loosen_ask("Make a garage a nice-to-have."),
              style.tighten_ask("Make a garage a must-have.")):
        assert ok(m), (m, style.check(m)); assert "reply" not in m.lower()
    assert "about 3 fit" in style.tradeoff_text((3, 12)) and "can't count" in style.tradeoff_text(None)
def test_hygiene_counts_real_only():
    pool = [dict(garage="yes", layout="unknown", misses=[]), dict(garage="unknown", layout="first floor", misses=[]), dict(garage="no", layout="unknown", misses=["price"], price=5200)]
    assert features.tradeoff(pool, "garage") == (1, 2) and features.tradeoff([], "garage") is None and features.tradeoff(pool, "price") is None
    assert features.near_misses(pool) == {"price": 1}
    assert features.suggest_change("price", pool, C)["value"] == 5200
    assert features.suggest_change("garage", pool, C)["kind"] == "nice_to_have"
    for t in ("garage", "layout", "pets", "baths", "beds", "price"):   # every possible change line fits in 30
        ch = features.suggest_change(t, pool, C)
        if ch: assert len(ch["desc"]) <= style.MAX, ch
    assert all(len(f"make {w} a must-have.") <= style.MAX for w in features.THING.values())
def test_hygiene_schedule():
    H = {}; d = 86400
    assert features.hygiene_due(H, 0, 0, "d0") is None              # day one: clocks start, nothing sent
    assert features.hygiene_due(H, 3 * d, 1, "d3") is None
    assert features.hygiene_due(H, 8 * d, 0, "d8") == "near_miss"
    H = {}; features.hygiene_due(H, 0, 0, "d0"); assert features.hygiene_due(H, 8 * d, 0, "d8") in ("loosen",)
    H = {}; [features.hygiene_due(H, i * d, 8, f"d{i}") for i in range(8)]; assert features.hygiene_due(H, 8 * d, 8, "d8") == "tighten"
def test_hygiene_apply_change():
    d = tempfile.mkdtemp(); p = f"{d}/c.yaml"; c = _LC(); yaml.safe_dump(c, open(p, "w"))
    old = features.OUT; features.OUT = d
    features.apply_change({"kind": "must_have", "value": "garage"}, p); y = yaml.safe_load(open(p))
    assert y["match"]["garage_min"] == 1 and "garage" not in y["match"]["nice_to_have"]
    features.apply_change({"kind": "nice_to_have", "value": "garage"}, p); y = yaml.safe_load(open(p))
    assert y["match"]["garage_min"] == 0 and "garage" in y["match"]["nice_to_have"]
    features.OUT = old

def test_confirm_answers():
    import replies
    for t in ("please don't", "please no", "ok no", "no thanks", "not yet", "yes but no", "please", "Yes, don\u2019t", "maybe", "ok but wait"):
        assert replies.answer(t) != "yes", t
    for t in ("please don't", "please no", "ok no", "no thanks", "not yet", "yes but no"): assert replies.answer(t) == "no", t
    for t in ("yes", "Yes please", "sure", "do it", "ok", "Okay!", "yes, do it"): assert replies.answer(t) == "yes", t
def test_negated_reply_changes_nothing():
    for t in ("please don't", "please no", "ok no", "no thanks", "not yet", "yes but no"):
        d, run = sandbox(); M = json.load(open(f"{d}/out/members.json")); M["Alex"] = {"pending": {"type": "change", "change": {"desc": "make it 3+ beds.", "kind": "beds_min", "value": 3}, "by": "Alex"}}
        json.dump(M, open(f"{d}/out/members.json", "w")); o = run("Alex", t)
        assert "would back up" not in o and "Done, the search" not in o, (t, o)
    for t in ("yes", "yes please", "sure", "do it", "ok"):
        d, run = sandbox(); M = json.load(open(f"{d}/out/members.json")); M["Alex"] = {"pending": {"type": "change", "change": {"desc": "make it 3+ beds.", "kind": "beds_min", "value": 3}, "by": "Alex"}}
        json.dump(M, open(f"{d}/out/members.json", "w")); o = run("Alex", t)
        assert "would back up" in o and "Done, the search" in o, (t, o)

def _pend(d, who, p):
    M = json.load(open(f"{d}/out/members.json")); M.setdefault(who, {})["pending"] = p; json.dump(M, open(f"{d}/out/members.json", "w"))
PENDS = {"feedback": {"type": "feedback", "payload": {"words": "idea: map", "version": "x", "last_text": "alert"}},
         "purge": {"type": "purge"},
         "change": {"type": "change", "change": {"desc": "make it 3+ beds.", "kind": "beds_min", "value": 3}, "by": "Alex"}}
def test_stop_beats_pending():
    for word in ("STOP", "cancel", "Unsubscribe"):
        for k, p in PENDS.items():
            who = "Sarah" if k == "feedback" else "Alex"
            d, run = sandbox(); _pend(d, who, p); o = run(who, word)
            M = json.load(open(f"{d}/out/members.json"))
            assert "pending" not in M[who] and M[who].get("stopped") and M[who].get("paused"), (word, k, M)
            assert "would back up" not in o and "Done" not in o and "Thanks, I passed" not in o and "deleted" not in o.lower(), (word, k, o)
            assert f"--> to {who}" not in o, (word, k, o)                       # no reply to the person who stopped
            assert not os.path.exists(f"{d}/out/feedback.jsonl"), (word, k)
def test_delete_needs_word_yes():
    for t in ("k", "ok", "\U0001F44D", "sure"):
        d, run = sandbox(); _pend(d, "Alex", {"type": "purge"}); o = run("Alex", t); assert "it's all deleted" not in o, (t, o)
    for t in ("yes", "yes please", "do it", "go ahead"):
        d, run = sandbox(); _pend(d, "Alex", {"type": "purge"}); o = run("Alex", t); assert "it's all deleted" in o, (t, o)

def test_stop_with_punctuation():
    for word in ("stop?", "stop,", "STOP \U0001F6D1", "stop please", "Quit now!"):
        for k, p in PENDS.items():
            who = "Sarah" if k == "feedback" else "Alex"
            d, run = sandbox(); _pend(d, who, p); o = run(who, word); M = json.load(open(f"{d}/out/members.json"))
            assert "pending" not in M[who] and M[who].get("stopped") and M[who].get("paused"), (word, k, M)
            assert f"--> to {who}" not in o and "would back up" not in o and not os.path.exists(f"{d}/out/feedback.jsonl"), (word, k, o)
    for t in ("we should end the search soon?", "I might quit looking at Maple", "the end unit looks nice"):
        d, run = sandbox(); run("Sarah", t); M = json.load(open(f"{d}/out/members.json"))
        assert not M["Sarah"].get("stopped"), t

# ---------- source line, posted time, quiet-week pulse, daily cap, first-week ask ----------
def test_via_and_posted():
    l = _l(source="Redfin"); assert sc.via_line(l) == "Via Redfin"
    assert sc.via_line(_l(source="Tim Carr Group (TenantTurner) + Zillow")) == "Via Tim Carr Group"
    assert sc.posted_line(_l()) is None                                      # no time from the source: no line
    assert sc.posted_line(_l(posted_ts=1000), now=1000 + 20 * 60) == "Posted about 20 min ago"
    assert sc.posted_line(_l(posted_ts=1000), now=1000 + 3 * 3600) == "Posted about 3 hours ago"
    assert sc.posted_line(_l(posted_ts=1000), now=1000 + 2 * 86400) is None
    c = _LC(); sc.CFG.clear(); sc.CFG.update(c)
    t = sc.render([{"l": sc.classify(_l(source="Redfin", posted_ts=time.time() - 600), c), "reason": "new", "was": None}], c)
    assert "Via Redfin" in t and "Posted about 10 min ago" in t and ok(t), t
    sc.CFG.clear(); sc.CFG.update(C)
def test_pulse_schedule():
    d = 86400; H = {"started": 0}
    assert not features.pulse_due(H, 6 * d, 0) and features.pulse_due(H, 7 * d, 0)
    assert not features.pulse_due(H, 9 * d, 5 * d)                           # an alert went out 4 days ago
    H["last_pulse"] = 7 * d; assert not features.pulse_due(H, 10 * d, 0) and features.pulse_due(H, 14 * d, 0)
    H["last_checkin"] = 14 * d - 3600; assert not features.pulse_due(H, 14 * d, 0)   # one text, not two
    for m in (style.quiet_week(312), style.quiet_week(None)): assert ok(m), (m, style.check(m))
    assert "312" in style.quiet_week(312) and "checked" not in style.quiet_week(None)
def test_daily_cap():
    assert features.cap_split([1, 2], 0, 99) == ([1, 2], [])                 # off by default
    assert features.cap_split([1, 2], 3, 2) == ([1, 2], []) and features.cap_split([1, 2], 3, 3) == ([], [1, 2])
    ch = features.parse_change("max 3 texts a day", C); assert ch["kind"] == "daily_cap" and ch["value"] == 3, ch
    assert features.parse_change("no daily cap", dict(C, daily_cap=3))["value"] == 0
    assert ok(style.change_ask("Cap alerts at 3 a day.")) and ok(style.evening_bundle_intro(4))
    d = tempfile.mkdtemp(); p = f"{d}/c.yaml"; open(p, "w").write("beds_min: 2\n"); old = features.OUT; features.OUT = d
    features.apply_change(ch, p); assert yaml.safe_load(open(p))["daily_cap"] == 3
    features.apply_change({"kind": "daily_cap", "value": 0}, p); assert yaml.safe_load(open(p))["daily_cap"] == 0
    features.OUT = old
def test_first_week_ask():
    for m in (style.first_week_ask(), style.first_week_glad(), style.listener_note()): assert ok(m), (m, style.check(m))
    d, run = sandbox(); _pend(d, "Alex", {"type": "feedback_open"}); o = run("Alex", "all good")
    assert "Glad it's working well." in o and not os.path.exists(f"{d}/out/feedback.jsonl")
    d, run = sandbox(); _pend(d, "Alex", {"type": "feedback_open"}); o = run("Alex", "the links open slowly")
    assert "Send it to the Scout team?" in o and not os.path.exists(f"{d}/out/feedback.jsonl"), o   # gated: asks first, saves nothing yet
    M = json.load(open(f"{d}/out/members.json")); assert M["Alex"]["pending"]["type"] == "feedback"
    d, run = sandbox(); _pend(d, "Alex", {"type": "feedback_open"}); o = run("Alex", "STOP")
    M = json.load(open(f"{d}/out/members.json")); assert M["Alex"].get("stopped") and "pending" not in M["Alex"]

def test_what_can_you_do_and_checkin_optout():
    d, run = sandbox(); o = run("Sarah", "what can you do")
    assert "Text STOP anytime to stop." in o and "end my search" not in o   # same list for everyone; owner-only lines only for the owner
    oa = run("Alex", "What can you do?"); assert "change to the search" in oa and "Text end my search to end." in oa
    o = run("Alex", "no check-ins"); M = json.load(open(f"{d}/out/members.json"))
    assert M["Alex"].get("no_checkins") and not M["Alex"].get("stopped") and "no more check-ins" in o
    o = run("Alex", "stop check-ins"); M = json.load(open(f"{d}/out/members.json"))
    assert not M["Alex"].get("stopped") and M["Alex"].get("no_checkins")   # not mistaken for STOP
    o = run("Alex", "check-ins on"); M = json.load(open(f"{d}/out/members.json"))
    assert "no_checkins" not in M["Alex"] and "back on" in o
    o = run("Sarah", "privacy"); assert "Only Photon sees the texts." in o and "Nothing leaves" not in o

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} feature tests passed")
