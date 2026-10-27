"""Pre-publish fixes: fair housing, configurable plan limit, first-run alert in an exported copy. Sends nothing."""
import os, re, sys, shutil, subprocess, tempfile, yaml
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
import style, scout

def test_steer_note_and_rx():
    t = style.steer_note(); assert not style.check(t), style.check(t)
    for q in ["only safe areas", "find good schools", "no kids please", "adults only building"]:
        assert re.search(style.STEER_RX, q, re.I), q
    assert not re.search(style.STEER_RX, "2 beds under 3000 in 90001", re.I)

def test_assistance_animal_never_filters():
    C = {"match": {"exclude_no_pets": True}, "pets": {"service_animal": True}}
    assert not scout.pet_filter_on(C)
    assert scout.pet_filter_on({"match": {"exclude_no_pets": True}, "pets": {}})
    assert not scout.pet_filter_on({"match": {"exclude_no_pets": True}, "pets": {"esa_letter": True}})

def test_no_relay():
    for p in ["No Section 8", "adults only", "No kids", "vouchers not accepted"]: assert scout.NO_RELAY.search(p), p
    assert not scout.NO_RELAY.search("cats ok, dogs under 30 lbs")

def test_full_household_no_numbers_claimed():
    for t in (style.full_household(), style.full_household(10)): assert not style.check(t)
    assert "10" not in style.full_household()

def test_example_criteria():
    C = yaml.safe_load(open(os.path.join(HERE, "CRITERIA.example.yaml")))
    assert sum(s["type"] == "email" for s in C["sources"]) == 1
    assert C["match"]["price_max"] == C["price_tiers"]["stretch_max"]
    assert "exclude_no_pets" not in C["pets"]
    assert C["text_style"]["max_line_chars"] == 30 and C["message_style"]["max_line_chars"] == 30
    assert "missionary" not in str(C["scam_flags"])

def test_no_photon_price_claims():
    rx = re.compile(r"up to 10|\$0\b|costs nothing|free for 10|Free on Photon", re.I)
    for f in ["README.md", "SETUP.md", "PHOTON_FAQ.md", "COSTS.md", "SETUP_SCRIPT.md", "skill/SKILL.md", "notify.py", "style.py"]:
        bad = [ln for ln in open(os.path.join(HERE, f)) if rx.search(ln)]
        assert not bad, (f, bad[:2])

def test_first_run_alert_in_exported_copy():
    d = tempfile.mkdtemp()
    try:
        for n in os.listdir(HERE):
            if n in ("logs", "out", "inbox", "drafts", "node_modules", "state.json", "CRITERIA.yaml", "__pycache__"): continue
            (shutil.copytree if os.path.isdir(os.path.join(HERE, n)) else shutil.copy)(os.path.join(HERE, n), os.path.join(d, n))
        C = yaml.safe_load(open(os.path.join(d, "CRITERIA.example.yaml")))
        C["area"]["zips"] = ["90001", "90002", "90003"]; C["area"]["cities"] = ["Los Angeles"]
        C["sources"] += [{"name": f"Reader {i}", "type": "email", "dir": "./inbox"} for i in range(5)]; C["match"]["price_max"] = 5000   # old example: many sources on one inbox (was 0 alerts)
        yaml.safe_dump(C, open(os.path.join(d, "CRITERIA.yaml"), "w"))
        env = {k: v for k, v in os.environ.items() if k != "PHOTON_API_KEY"}
        run = lambda *a: subprocess.run([sys.executable, "-B", "scout.py", *a], cwd=d, env=env, capture_output=True, text=True, timeout=120)
        r = run("--seed"); assert "saved 0 current" in r.stderr, r.stderr[-400:]
        shutil.copy(os.path.join(HERE, "tests/fixtures/email_tracked/zillow_tracked.html"), os.path.join(d, "inbox"))
        r = run("--json", "--matches-only")
        assert re.search(r"== [1-9]\d* alert", r.stderr), r.stderr[-400:]
        assert "404" not in r.stderr
    finally: shutil.rmtree(d, ignore_errors=True)

if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"): f(); print("ok", k)
