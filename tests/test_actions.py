"""The listing's own apply link (rent) / agent link (buy): parsed only when labeled, cleaned of tokens, skipped when opaque,
shown for people to tap, never followed by the bot. SYNTHETIC fixtures in tests/fixtures/email_actions. Sends nothing."""
import os, sys, copy, glob, socket, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); os.chdir(HERE)
import yaml, scout as sc, style
FX = "tests/fixtures/email_actions"
RENT = yaml.safe_load(open("CRITERIA.example.yaml"))
BUY = yaml.safe_load(open("tests/fixtures/CRITERIA.buy.test.yaml")) if os.path.exists("tests/fixtures/CRITERIA.buy.test.yaml") else None
P = lambda f: sc.parse_email_file(os.path.join(FX, f))

def test_apply_link_cleaned_and_opaque_skipped():
    a, b = P("zillow_rent_apply.html")
    assert a["apply_url"] == "https://www.zillow.com/rental-manager/apply/synth-90000777/"   # tracker unwrapped, token dropped
    assert "rtoken" not in a["url"] and b["apply_url"] is None                                # opaque tracker: no line, never guessed
    assert all(not (l.get("apply_url") or "").count("homeloans") for l in P("zillow_rent_apply.html"))   # loan ad ignored

def test_text_render_apply():
    (l,) = P("zillow_rent_apply.txt"); assert l["apply_url"] == "https://www.zillow.com/rental-manager/apply/synth-55demo/"

def test_agent_link_buy():
    (l,) = P("redfin_buy_agent.html")
    assert l["agent_url"] == "https://www.redfin.com/CA/Exampleville/12-Fake-Ln-90001/home/7000123/tour" and l["apply_url"] is None

def test_clean_rules():
    c = sc.clean_action_url
    assert c("https://redmail3.redfin.com/u/click?_t=abc") is None                     # opaque
    assert c("https://www.zillow.com/homeloans/apply/?x=1") is None                     # not the listing's
    assert c("https://evil.example/apply") is None and c("http://www.zillow.com/a/") is None
    assert c("https://www.zillow.com/routing/email/x/" + "A" * 45 + "/") is None        # token-shaped path
    assert c("https://www.zillow.com/apply/abc/?rtoken=1#f") == "https://www.zillow.com/apply/abc/"

def _render(l, C):
    sc.CFG.clear(); sc.CFG.update(C); l = sc.classify(dict(l, flags=[]), C)
    return sc.render([{"reason": "new", "was": None, "market": None, "l": l}], C)

def test_render_lines_and_style():
    a, b = P("zillow_rent_apply.html")
    t = _render(a, RENT); assert "Apply link from the listing:\nhttps://www.zillow.com/rental-manager/apply/synth-90000777/" in t
    assert not style.check(t) and "Agent link" not in t
    assert "Apply link" not in _render(b, RENT)                                          # no link, no line
    if BUY:
        (l,) = P("redfin_buy_agent.html"); t = _render(l, BUY)
        assert "Agent link from the listing:\nhttps://www.redfin.com/CA/Exampleville/12-Fake-Ln-90001/home/7000123/tour" in t
        assert not style.check(t) and "Apply link" not in t

def test_bot_never_follows_apply_or_agent_links():
    """Parsing and rendering never open a URL (no network at all), and no code path fetches these fields."""
    def boom(*a, **k): raise AssertionError("network used")
    o1, o2 = urllib.request.urlopen, socket.create_connection
    urllib.request.urlopen = socket.create_connection = boom; sc_get = sc.get; sc.get = boom
    try:
        for f in sorted(glob.glob(FX + "/*")):
            for l in sc.parse_email_file(f): _render(l, RENT); BUY and _render(l, BUY)
    finally: urllib.request.urlopen, socket.create_connection, sc.get = o1, o2, sc_get
    for f in glob.glob("*.py") + glob.glob("*.mjs"):
        src = open(f).read()
        for key in ("apply_url", "agent_url"):
            for line in src.splitlines():
                if key in line: assert not any(w in line for w in ("get(l[", "urlopen", "requests.", "fetch(", "click")), (f, line)

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} action-link tests passed")
