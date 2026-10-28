"""Cut-off email warning, street-only HotPads places, and the every-10-minutes health check."""
import os, sys, json, tempfile, subprocess, shutil, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc, style, yaml
C = yaml.safe_load(open("CRITERIA.example.yaml")); sc.CFG.update(C)

def _f(text):
    f = tempfile.mktemp(suffix=".txt"); open(f, "w").write(text); return f

def test_cutoff_truncated_and_subject():
    assert sc.email_cutoff(_f("Subject: New rental at $3,000/mo\n$3,000/mo\n[body truncated; raise body_max_chars to read more]"), []) == "body cut off by the mail reader"
    f = _f("Subject: New rentals in Town at $3,150/mo, Town at $3,485/mo +1 more\nbody")
    assert "3,485" in sc.email_cutoff(f, [{"price": 3150}])
    assert sc.email_cutoff(f, [{"price": 3150}, {"price": 3485}]) is None
    g = _f("Subject: 1 Main St + more new rentals just dropped in 90001 (from $3.04K)\nbody")
    assert sc.email_cutoff(g, [{"price": 3045}]) is None                           # '$3.04K' rounds
    h = _f("Subject: New rental in Town at $3,130-$3,295/mo\nbody")
    assert sc.email_cutoff(h, [{"price": None, "price_range": [3130, 3295]}]) is None

def test_street_only_line():
    l = {"address": None, "street_only": "Example Ln", "city": "Town", "url": "https://hotpads.com/x/pad"}
    assert sc.street(l) == "Example Ln" and sc.street_line(l) == "Example Ln (no number listed)"
    g = sc.where_block(l); lines = list(g.lines if hasattr(g, "lines") else g)
    assert "Address not shown" not in str(lines) and "Example Ln (no number listed)" in str(lines)
    long = dict(l, street_only="Sampleton Ave", url=None)
    gl = str(list(sc.where_block(long).lines if hasattr(sc.where_block(long), "lines") else sc.where_block(long)))
    assert "Sampleton Ave" in gl and sc.NO_NUMBER in gl
    assert sc.street_line({"address": "12 Main St, Town, CA 90001", "street_only": "Main St"}) == "12 Main St"   # a real number wins

def test_hotpads_street_only_parse():
    body = "\n".join(["$4,247/mo", "", "1 bed", "", "31st St", "", "Town, CA 90001", "",
                      "(https://hotpads.com/town-ca-90001-x1/pad?nid=1)Contact (https://hotpads.com/x) View listing (https://hotpads.com/x)"])
    l = sc._parse_hotpads_text(body, "t.txt")[0]
    assert l["address"] is None and l["street_only"] == "31st St"
    b2 = body.replace("31st St", "Example Terrace Apartments")
    assert sc._parse_hotpads_text(b2, "t.txt")[0]["street_only"] is None          # a building name is not a street

def test_roundup_entry_fits():
    l = {"id": "a", "address": None, "street_only": "Sampleton Ave", "city": "Town", "price": 3000, "beds": 2, "url": "https://hotpads.com/x/pad", "zip": "90001", "flags": []}
    m = {"id": "b", "address": "1 Oak St, Town, CA 90001", "city": "Town", "price": 3100, "beds": 2, "url": "https://hotpads.com/y/pad", "zip": "90001", "flags": []}
    t = sc.render([{"l": l, "reason": "new", "was": None}, {"l": m, "reason": "new", "was": None}], C)
    assert not style.check(t), style.check(t)
    assert "Sampleton Ave" in t and sc.NO_NUMBER in t

def _health_box(sends, cut=None):
    d = tempfile.mkdtemp(); os.makedirs(f"{d}/logs"); os.makedirs(f"{d}/out"); os.makedirs(f"{d}/inbox")
    src = "src/health.py" if os.path.exists("src/health.py") else "health.py"
    shutil.copy(src, f"{d}/health.py"); y = yaml.safe_load(open("CRITERIA.example.yaml")); y["sources"] = []; y["replies"] = False
    yaml.safe_dump(y, open(f"{d}/CRITERIA.yaml", "w")); json.dump({"listings": {}}, open(f"{d}/state.json", "w"))
    open(f"{d}/logs/loop.log", "w").write(time.strftime("%F %T %Z") + " ok mode=lean 0 alerts\n")
    open(f"{d}/logs/sends.jsonl", "w").write("".join(json.dumps(x) + "\n" for x in sends))
    if cut: json.dump(cut, open(f"{d}/out/email_cutoff.json", "w"))
    return d

def _ts(mins_ago): return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(time.time() - mins_ago * 60))
def _run(d): return subprocess.run([sys.executable, "health.py"], cwd=d, capture_output=True, text=True).stdout

def test_health_send_failing_and_cutoff():
    d = _health_box([{"ts": _ts(45), "ok": False, "dry_run": False}, {"ts": _ts(10), "ok": False, "dry_run": False}])
    o = _run(d); assert "texts have failed for 45 min" in o, o
    assert "send_failing" in json.load(open(f"{d}/out/health_flags.json"))
    assert "texts have failed" not in _run(_health_box([{"ts": _ts(45), "ok": False, "dry_run": False}, {"ts": _ts(5), "ok": True, "dry_run": False}]))
    assert "texts have failed" not in _run(_health_box([{"ts": _ts(10), "ok": False, "dry_run": False}]))   # under 30 min: quiet retries
    assert "may be cut off" in _run(_health_box([], {"redfin-1.txt": {"reason": "body cut off by the mail reader", "since": "x"}}))

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} cutoff/street/health tests passed")
