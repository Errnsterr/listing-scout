"""Run: python3 -m pytest -q tests  (or python3 tests/test_style.py)
Checks every end-user template and today's sample alerts for style problems:
lone words, two sentences on one line, long lines, links not alone, list numbers alone."""
import os, sys, json, copy, yaml
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); os.chdir(HERE)
import style, importlib.util
spec = importlib.util.spec_from_file_location("scout", os.path.join(HERE, "scout.py"))
sc = importlib.util.module_from_spec(spec); sys.argv = ["x"]; spec.loader.exec_module(sc)
REAL = os.path.exists("CRITERIA.yaml") and os.path.exists("tests/sample_alerts.json")
C = yaml.safe_load(open("CRITERIA.yaml" if REAL else "tests/fixtures/CRITERIA.test.yaml"))
SAMPLES = "tests/sample_alerts.json" if REAL else "tests/fixtures/sample_alerts.test.json"
sc.CFG.update(C)

def samples():
    A = json.load(open(SAMPLES))       # owner copy: live data; template: synthetic fixture
    for a in A: a["l"].setdefault("flags", [])
    M = [a for a in A if a["l"]["match"]]
    out = {f"alert:{a['l']['id']}": sc.render([a], C) for a in A}
    d = copy.deepcopy(M[0]); d["reason"] = "price_drop"; d["was"] = 4095
    out["price_drop"] = sc.render([d], C)
    out["bundle_matches"] = sc.render(M, C)
    out["bundle_all"] = sc.render(A[:6], C)
    return out

def templates():
    return {"owner_welcome": style.owner_welcome("Jordan", 619, True), "first_day": style.first_day(619),
            "member_welcome": style.member_welcome("Alex", "Jordan", sc.reflect(C)),
            "member_welcome_replies": style.member_welcome("Alex", "Jordan", sc.reflect(C), replies=True),
            "invite": style.invite("Alex"), "hint": style.hint_target_not_allowed("Alex", "1234"),
            "nudge": style.owner_nudge("Alex")}

def test_all_clean():
    bad = {k: p for k, v in {**templates(), **samples()}.items() if (p := style.check(v))}
    assert not bad, json.dumps(bad, indent=1)

def test_never_wraps():
    try:
        style.text([["This sentence is far too long to fit on one line of a text."]])
        assert False, "should have raised"
    except style.StyleError: pass
    for name, t in templates().items():
        for ln in t.split("\n"):
            assert len(ln) <= style.MAX + 3 or style.URL.fullmatch(ln), (name, ln)

def test_welcome_exact():
    assert style.owner_welcome("Sam", 10, True) == ("Hi Sam!\n\nIt's Listing Scout.\n\n"
        "Tap the card to save me.\n\nI'm watching 10 places.\n\n"
        "Quiet days mean nothing fit.\n\nAlways see a place first.\n\nNot listed yet is normal.\n\nA home may show up twice.\n\n"
        "Text STOP anytime to stop.\n\nSpot a bug, just let me know.\n\nDid this come through okay?")
    assert not hasattr(style, "welcome") and not hasattr(style, "test_text")   # legacy templates removed

def test_checker_catches_problems():
    assert style.check("When a place fits you get\nmore texts")          # sentence spans lines
    assert style.check("One sentence. Two sentences.")                   # two sentences
    assert style.check("See https://example.com now")                    # link not alone
    assert style.check("First sentence.\nSecond sentence.")             # no blank line after sentence
    assert style.check("2. Text it: Hi Listing Scout, I'm in.")          # text after colon on same line
    assert style.check("2. Text it:\nHi Listing Scout, I'm in.")        # blank line needed after a colon
    assert style.check("Joining takes 2 minutes:\n1. Tap it.")          # intro needs blank line
    assert not style.check("Pets: not listed yet")       # fact label exception

def test_colon_rendering():
    t = style.invite("Sam", line="+15550001234")
    assert t.endswith("Tap the number to say hi:\n\n(555) 000-1234") and "http" not in t and "sms:" not in t   # plain, forwardable, no URLs
    assert "Any text works, like \"hi\"." in style.hint_target_not_allowed("Sam", "1234")
    assert style.check("Alex on Main:\n\"Love it\"")              # quote needs a blank line after the colon
    assert not style.check("Pets: not listed yet")      # fact labels stay on one line




def test_numbered_steps_have_blank_lines():
    import style
    m = style.invite("Ana", line="+15550001234")
    assert "card" not in m.lower()                                     # one tap + Send; the welcome carries the card
    assert style.check("Steps:\n\n1. Do this.\n2. Do that.")
    assert not style.check(m)

def test_email_parser_fixture():
    """Synthetic Zillow-shaped alert (tests/fixtures/email). Real alert emails are still unverified."""
    L = sc.parse_email({"dir": "tests/fixtures/email", "name": "fixture"})
    assert [l["id"] for l in L] == ["email:Zillow:99000001", "email:Zillow:99000002"]
    a, b = L
    assert (a["price"], a["beds"], a["baths"], a["address"]) == (3750, 2, 2, "100 Example Ln, Los Angeles, CA 90001")
    assert (b["price"], b["beds"], b["baths"], b["address"]) == (4400, 2, 1, "200 Sample Ave APT 3, Los Angeles, CA 90002")
    c = sc.classify(dict(a), C)
    assert c["zip"] == "90001"   # parsing only; eligibility depends on each owner's area

def test_new_templates_clean():
    A = json.load(open(SAMPLES))
    for x in A: x["l"].setdefault("flags", [])
    M = [x for x in A if x["l"]["match"]]
    for t in [style.owner_welcome("Jordan", 619), style.owner_welcome("Jordan", 619, True), style.member_welcome("Sam", "Jordan", ["Los Angeles"]),
              style.first_day(619), sc.snapshot(M, 619, C), sc.snapshot([], 619, C), sc.snapshot(M[:1], 5, C)]:
        assert not style.check(t), (t, style.check(t))
    assert "I'm watching 619 places." in style.owner_welcome("Jordan", 619)
    assert "added you" not in style.owner_welcome("Jordan", 619)


def test_case_b_templates_clean():
    R = sc.reflect(C)
    ts = [style.member_welcome("Alex", "Jordan", R), style.member_welcome("Alex", "Jordan", R, replies=True),
          style.member_welcome("Sam", "Bartholomew-Johnson", R, "home", "in_the_know"),
          style.how_replies_work("Jordan"), style.how_replies_work(), style.member_prefs("Jordan"),
          style.owner_member_in("Alex"), style.owner_member_in("Alex", replies=True), style.owner_member_in("Sam", "in_the_know"),
          style.owner_nudge("Alex"), style.relay("Alex", "Main", "love the yard!"),
          style.relay("Bartholomew", "Northwest Military Highway Frontage", "x " * 200),
          style.mutual("Main"), style.mutual("Northwest Military Highway Frontage Road"), style.tour_note("Alex", "Main", True),
          style.saved("Northwest Military Highway Frontage Road"), style.passed_to("Jordan"), style.paused_text(True), style.paused_text(False),
          style.shortlist([("Main", "$3,895/mo", "you both like it")]), style.shortlist([]), style.which_one(),
          style.invite("Alex", "home")]
    for t in ts: assert not style.check(t), (t, style.check(t))
    assert all(len(x) <= style.MAX for x in R)
    assert "Northwest" in style.saved("Northwest Military Highway Frontage Road")   # street never lost
    assert "Your shared shortlist:" in style.shortlist([("Main", "$1", "")])
    assert "It's on your shortlist." in style.mutual("Main")

def test_relay_is_verbatim():
    raw = "no,   too far from work: honestly the kitchen looked tiny in photo 3, can we skip it?\n\nalso parking!!"
    t = style.relay("Alex", "Oak Ave", "  " + raw + "  ")
    assert t == 'Alex on Oak Ave:\n\n"' + raw + '"'     # exactly as written; only outer whitespace trimmed
    assert not style.check(t)                                   # their words are exempt from every style rule
    assert style.check("Alex on Main:\n\"x\"")                   # the bot's header still follows the colon rule
    assert style.check('Alex on Main and some very long street name that goes on:\n\n"x"')   # bot lines still checked

def test_generic_no_leaks():
    """Generic criteria must not render the owner's pets, garage or ESA wording."""
    G = copy.deepcopy(C); G.update(pets={"dog": None}, match={"layout_any": [], "garage_min": 0})
    A = json.load(open(SAMPLES))
    for a in A: a["l"].setdefault("flags", [])
    t = sc.render(A[:1], G) + sc.render(A[:3], G)
    for bad in ("ESA", "Pets:", "Garage:", "dog"): assert bad not in t, bad

def test_decide_together_is_offered_once_not_instructed():
    off = style.member_welcome("Alex", "Jordan", ["Los Angeles"])
    assert "decide together" not in off.lower() and "tell me" not in off.lower()   # flag off: no promise
    on = style.member_welcome("Alex", "Jordan", ["Los Angeles"], replies=True)
    for l in ["We can decide together here.", "Tell me what you think of one.", "I'll share it with Jordan.",
              style.STOP_LINE]: assert l in on
    assert "I'll keep a shared shortlist." not in on   # trimmed: the owner's text and help cover the shortlist
    assert on.count("Reply") == 0 and on.endswith(style.RECEIPT)   # only the receipt
    assert "Jordan said you'd stop by." in on and "Here's what we're looking for:" in on
    assert "You get Jordan's alerts too." in on
    o = style.owner_member_in("Alex", replies=True)
    assert "I'll share it with Alex." in o and "Reply" not in o
    assert "decide together" not in style.owner_member_in("Alex").lower()
    assert "decide together" not in style.owner_member_in("Sam", "in_the_know", True).lower()
    A = json.load(open(SAMPLES))
    for x in A: x["l"].setdefault("flags", [])
    for t in [sc.render(A[:1], C), sc.render(A[:2], C), sc.snapshot([a for a in A if a["l"]["match"]], 10, C)]:
        assert "Reply" not in t and "tell" not in t.lower(), t           # no reply instructions in alerts/snapshots
    sn = sc.snapshot([a for a in A if a["l"]["match"]], 10, C)
    assert sn.endswith("From here, I'll stay quiet.\n\nI'll text when a new one fits.")
    assert "Reply" not in style.relay("Alex", "Main", "love it")
    assert style.passed_to("Jordan") == "Passed that to Jordan."
    assert "help" not in sc.render(A[:1], C)

def test_unknowns_last_and_one_wording():
    assert style.check("Has a garage\nPets: not listed yet\nAvailable now")    # unknown not last
    assert style.check("Pets: not listed")                                                  # wrong wording
    assert not style.check("Has a garage\nPets: not listed yet")
    A = json.load(open(SAMPLES))
    for x in A: x["l"].setdefault("flags", [])
    x = copy.deepcopy(A[0]); x["l"]["price"] = None; x["l"]["available"] = None
    t = sc.render([x], C); assert not style.check(t), (t, style.check(t))
    assert "Rent: not listed yet" in t



def test_sms_links_encode_and_are_exempt():
    from urllib.parse import unquote
    j = style.join_link("+1 (555) 000-1234")
    assert j == "sms:+15550001234&body=hi"
    assert unquote(j.split("&body=")[1]) == "hi"
    inv = style.invite("Alex", line="+15550001234"); assert not style.check(inv)
    o = style.owner_invite_link(inv)
    assert o.startswith("sms:&body=") and unquote(o[len("sms:&body="):]) == inv
    assert not any(c in o[4:] for c in " \n'\",")                     # fully percent-encoded
    assert not style.check("Tap this:\n\n" + "sms:&body=" + "x" * 300)   # long links: own line, exempt from MAX

def test_member_welcome_with_card_matches_owner():
    w = style.member_welcome("Alex", "Jordan", ["Sample City"], card=True)
    assert "Tap the card to save me." in w and "Tap the card to save me." in style.owner_welcome("Jordan", 10, True)
    assert w.endswith(style.RECEIPT) and not style.check(w)

def test_public_copy_fixes():
    # member welcome tells people how to stop; help names STOP and leave; honest privacy; calm outage
    for kind in ("rental", "home"):
        w = style.member_welcome("Alex", "Jordan", ["Los Angeles"], kind=kind, replies=True)
        assert style.STOP_LINE in w and style.SAFETY_LINE in w and not style.check(w)
        assert (style.BUY_LINE in w) == (kind == "home")
    h = style.how_replies_work("Jordan"); assert "STOP turns texts off." in h and "Leave takes you off." in h
    for o in (True, False):
        c = style.capabilities(o); assert not style.check(c) and "STOP" in c and "landlords" in c
        assert ("change the search" in c) == o
    assert "Only Photon sees the texts." in style.data_note() and "Nothing leaves" not in style.data_note()
    out = style.outage_note("Example PM", "Mon 1:05 PM"); assert "isn't loading" not in out and not style.check(out)
    assert "A few days in." in style.first_week_ask() and style.CHECKINS_LINE in style.first_week_ask()
    assert style.CHECKINS_LINE in style.quiet_week(5) and style.CHECKINS_LINE in style.quiet_week(None)
    for on in (True, False): assert not style.check(style.checkins_set(on))
    assert "rentals" not in style.invite("Alex", "home") and "homes" in style.invite("Alex")

if __name__ == "__main__":   # runs every test_* (no pytest needed)
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} tests passed")
