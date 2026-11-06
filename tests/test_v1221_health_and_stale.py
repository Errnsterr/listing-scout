"""v1.2.21: a recovered Photon timeout must not keep health not OK, and nothing older than 4 hours is texted.
Temp copies only. No network, no sends, no real phone numbers."""
import os, sys, json, time, copy, shutil, tempfile, subprocess, datetime, importlib.util, io, contextlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); sys.path.insert(0, os.path.join(HERE, "tests"))
os.chdir(HERE)
import scout as sc, style, yaml
import test_mail_listener as T
FX = os.path.join(HERE, "tests", "fixtures")
C0 = yaml.safe_load(open(os.path.join(FX, "CRITERIA.test.yaml")))
SAMPLE = json.load(open(os.path.join(FX, "sample_alerts.test.json")))[0]
PHOTON = "a recent text was not accepted by Photon"
FAIL = "Not sent: Kathleen (***1111, line ***2222, imessage). Nothing is wrong on their side.\n"
OKLN = "sent: Kathleen (***1111, line ***2222, imessage). Texts come from the number ending 2222.\n"
HOUR = 3600

def _iso(hours_ago):
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")

def test_photon_recovered_is_ok_and_ongoing_is_not():
    def run(log):
        d = tempfile.mkdtemp(); os.makedirs(f"{d}/logs"); os.makedirs(f"{d}/out"); os.makedirs(f"{d}/inbox")
        shutil.copy("src/health.py", f"{d}/health.py")
        y = yaml.safe_load(open("CRITERIA.example.yaml")); y["sources"] = []; y["replies"] = False
        yaml.safe_dump(y, open(f"{d}/CRITERIA.yaml", "w")); json.dump({"listings": {}}, open(f"{d}/state.json", "w"))
        open(f"{d}/logs/loop.log", "w").write(time.strftime("%F %T %Z") + " ok mode=lean 0 alerts\n")
        open(f"{d}/logs/notify.log", "w").write(log)
        return subprocess.run([sys.executable, "health.py"], cwd=d, capture_output=True, text=True).stdout
    noise = "send timed out; will retry next pass\n"
    assert PHOTON not in run(FAIL + noise + OKLN), "a timeout that then went through must not keep health not OK"
    assert PHOTON not in run(FAIL + OKLN + OKLN)                         # 7:08 fail, then 7:08 and 7:09 sent
    assert PHOTON in run(OKLN + FAIL)                                    # a later miss is still failing
    assert PHOTON in run(FAIL)                                           # no successful send after the failure
    assert PHOTON not in run("x" * 4000 + "\n" + FAIL + noise + OKLN)    # both still inside the window

def test_age_window_boundary():
    import features, mail_listener as L
    assert features.alert_max_hours() == 4 and L.stale_hours() == 4
    assert not sc.listing_stale({"alert_ts": 1000}, now=1000 + 4 * HOUR)       # 4 hours on the dot is still timely
    assert sc.listing_stale({"alert_ts": 1000}, now=1000 + 4 * HOUR + 1)
    assert not sc.listing_stale({})                                            # a live page fetch has no clock
    recent = {"timestamp": _iso(1)}
    assert not L.msg_is_stale(recent, now=L.msg_ts(recent) + HOUR)
    ts = L.msg_ts({"timestamp": "2026-01-01T00:00:00Z"})
    assert not L.msg_is_stale({"timestamp": "2026-01-01T00:00:00Z"}, now=ts + 4 * HOUR)
    assert L.msg_is_stale({"timestamp": "2026-01-01T00:00:00Z"}, now=ts + 4 * HOUR + 1)
    assert not L.msg_is_stale({})

def test_catchup_skips_old_and_keeps_recent():
    L, root, _ = T.fresh(ts=_iso(5))
    assert L.catch_up("k") == 0 and T.files(root) == []
    log = open(os.path.join(root, "logs", "email_skips.log")).read()
    assert "skipped for age" in log and "stale catch-up" in log
    ids = open(os.path.join(root, "out", "fetched_ids.txt")).read()
    assert "r1@hotpads" in ids                                          # marked seen, so it is not pulled again
    n = log.count("skipped for age")
    assert L.catch_up("k") == 0 and open(os.path.join(root, "logs", "email_skips.log")).read().count("skipped for age") == n
    L2, root2, _ = T.fresh(ts=_iso(1))
    assert L2.catch_up("k") == 3 and len(T.files(root2)) == 3           # timely rentals still saved
    assert "skipped for age" not in open(os.path.join(root2, "logs", "email_skips.log")).read()

def _box(names=("3021665",)):
    d = tempfile.mkdtemp()
    for x in ("out", "logs", "inbox"): os.makedirs(os.path.join(d, x))
    paths = []
    for n in names:
        dest = os.path.join(d, "inbox", f"hotpads-{n}.txt")
        shutil.copy(os.path.join(FX, "hotpads_text", f"hotpads_{n}.txt"), dest); paths.append(dest)
    C = copy.deepcopy(C0); C["beds_min"] = 2; C.setdefault("match", {})["price_max"] = 5000
    C["sources"] = [{"name": "alerts", "type": "email", "dir": "inbox"}]
    yaml.safe_dump(C, open(os.path.join(d, "CRITERIA.yaml"), "w"))
    return d, paths, C

def _scout(d, *extra):
    p = subprocess.run([sys.executable, os.path.join(HERE, "src", "scout.py"), "--json", "--matches-only", *extra],
                       cwd=d, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-800:]
    alerts = json.loads(p.stdout) if "--seed" not in extra else []
    st = json.load(open(os.path.join(d, "state.json")))
    return alerts, st, p.stderr

def _age(paths, hours):
    old = time.time() - hours * HOUR
    for p in paths: os.utime(p, (old, old))

def test_body_received_line_is_not_the_clock_and_listener_header_is():
    p = os.path.join(tempfile.mkdtemp(), "a.txt")
    open(p, "w").write("--- 1. received 2020-01-01T00:00:00Z · message_id old\n")
    assert time.time() - sc.alert_landed_ts(p) < 60                      # fixture 'received' lines are not a clock
    old = _iso(8)
    open(p, "w").write(f"--- listener 2026-11-06 08:10:00 UTC · received {old} · message_id aged\nbody\n")
    os.utime(p, None)                                                    # file mtime is now; the header is 8h ago
    assert time.time() - sc.alert_landed_ts(p) > 7 * HOUR

def test_scout_skips_stale_mail_and_still_texts_timely():
    fresh, paths, C = _box()
    alerts, _, err = _scout(fresh)
    assert alerts and all(a["reason"] == "new" for a in alerts), err[-400:]
    ids = [a["l"]["id"] for a in alerts]
    t = sc.render(alerts[:1], C)
    assert "skipped" not in t.lower() and not style.check(t), style.check(t)   # timely wording unchanged
    stale, spaths, _ = _box()
    _age(spaths, 8)
    got, st, err = _scout(stale)
    assert got == [], err[-400:]
    assert "skipped for age" in err and "skipped for age" in open(os.path.join(stale, "logs", "match.log")).read()
    for i in ids:
        assert st["listings"][i].get("stale_skipped"), i               # seen, so the next pass cannot text it
    n = err.count("skipped for age")
    got2, _, err2 = _scout(stale)
    assert got2 == [] and err2.count("skipped for age") == 0           # not retried
    # catch-up wrote the file just now, but the listener header says the mail landed 8h ago
    late, lpaths, _ = _box()
    body = open(lpaths[0]).read()
    open(lpaths[0], "w").write(f"--- listener now · received {_iso(8)} · message_id late\n" + body)
    got, st, err = _scout(late)
    assert got == [] and "skipped for age" in err, err[-400:]
    assert any(v.get("stale_skipped") for v in st["listings"].values())

def test_held_release_past_window_is_skipped_for_good():
    d, paths, _ = _box(("3021702", "3021665"))
    _scout(d, "--seed")
    st = json.load(open(os.path.join(d, "state.json")))
    for k in ("email:addr:1562-testwood7", "email:addr:2238-testwood10"): st["listings"][k]["held_review"] = True
    json.dump(st, open(os.path.join(d, "state.json"), "w"))
    _age(paths, 8)
    got, st, err = _scout(d)
    assert got == [], err[-400:]
    rec = st["listings"]["email:addr:1562-testwood7"]
    assert rec.get("held_skipped") and rec.get("stale_skipped") and rec.get("held_review")
    assert "skipped for age" in err
    n = open(os.path.join(d, "logs", "match.log")).read().count("skipped for age")
    got2, st2, _ = _scout(d)
    assert got2 == [] and st2["listings"]["email:addr:1562-testwood7"].get("held_skipped")
    assert open(os.path.join(d, "logs", "match.log")).read().count("skipped for age") == n

def _notify():
    d = tempfile.mkdtemp()
    for f in ("notify.py", "scout.py", "style.py", "features.py"): shutil.copy(os.path.join(HERE, "src", f), d)
    os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs")
    c = copy.deepcopy(C0); c["recipients"] = [{"name": "Alex", "role": "owner"}, {"name": "Sarah", "role": "co_decider"}]
    c.update(paused=False, daily_cap=0, replies=False); c["quiet_hours"] = {"start": 0, "end": 0}
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w")); json.dump({}, open(f"{d}/out/members.json", "w"))
    os.environ["SCOUT_CRITERIA"] = f"{d}/CRITERIA.yaml"
    spec = importlib.util.spec_from_file_location(f"nt{time.time_ns()}", f"{d}/notify.py")
    n = importlib.util.module_from_spec(spec); spec.loader.exec_module(n)
    n.recipients = lambda: [{"name": "Alex", "role": "owner", "phone": "", "line_last4": "0000"},
                            {"name": "Sarah", "role": "co_decider", "phone": "", "line_last4": "0000"}]
    n.features.in_quiet = lambda C_: False
    n.record_numbered = lambda q: None
    n.member = lambda r: {"first_alert_note_sent": "test"}
    return d, n

def _item(i, addr, hours):
    x = copy.deepcopy(SAMPLE)
    x["l"] = dict(x["l"], id=f"t:{i}", address=addr, alert_ts=time.time() - hours * HOUR)
    x["queued_at"] = x["l"]["alert_ts"]
    return x

def _call(n, *args):
    buf = io.StringIO(); sys.argv = ["notify.py", *args]
    with contextlib.redirect_stdout(buf): n.main()
    return buf.getvalue()

def test_notify_queue_hold_and_evening_skip_stale_keep_timely_text():
    fresh, stale = _item(1, "100 Example St Unit 4, Los Angeles, CA 90001", 0.5), _item(2, "9 Old Pier Rd, Los Angeles, CA 90001", 8)
    d, n = _notify(); sent = []
    n.send = lambda r, t, really, card=None: sent.append((r["name"], t)) or True
    f = f"{d}/a.json"; json.dump([fresh], open(f, "w"))
    alone = _call(n, "alerts", f, "--send")
    alone_txt = [t for w, t in sent if w == "Alex"]
    assert alone_txt and "100 Example" in alone_txt[0] and "skipped" not in alone_txt[0].lower()
    assert not style.check(alone_txt[0]), style.check(alone_txt[0])
    d, n = _notify(); sent = []
    n.send = lambda r, t, really, card=None: sent.append((r["name"], t)) or True
    json.dump([stale, fresh], open(f"{d}/a.json", "w"))
    out = _call(n, "alerts", f"{d}/a.json", "--send")
    assert "skipped for age" in out and "t:2" in out and "1111" not in out
    texts = [t for w, t in sent if w == "Alex"]
    assert texts == alone_txt                                          # the timely text is unchanged
    assert all("Old Pier" not in t for _, t in sent)
    assert json.load(open(f"{d}/outbox.json"))["queue"] == []
    again = len(sent)
    _call(n, "alerts", f"{d}/a.json", "--send")                        # passing the same stale find again does not text it
    assert len(sent) == again + 2                                      # only the timely one, to both people, once more
    assert all("Old Pier" not in t for _, t in sent)
    # sleep hold and evening hold: past the window is dropped, a fresh one still goes out as itself
    d, n = _notify(); sent = []
    n.send = lambda r, t, really, card=None: sent.append(t) or True
    json.dump({"held": {"Alex": [stale, fresh], "Sarah": [stale, fresh]}, "queue": [], "last_sent": 0}, open(f"{d}/outbox.json", "w"))
    out = _call(n, "morning", "--send")
    assert "skipped for age" in out and sent and all("Old Pier" not in t and "100 Example" in t for t in sent)
    assert not style.check(sent[0]), style.check(sent[0])
    assert "Alex" not in (json.load(open(f"{d}/outbox.json")).get("held") or {})
    d, n = _notify(); sent = []
    n.send = lambda r, t, really, card=None: sent.append(t) or True
    json.dump({"evening": [stale], "queue": []}, open(f"{d}/outbox.json", "w"))
    out = _call(n, "evening", "--now", "--send")
    assert sent == [] and "skipped for age" in out
    assert json.load(open(f"{d}/outbox.json")).get("evening") == []

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} v1.2.21 health/stale tests passed")
