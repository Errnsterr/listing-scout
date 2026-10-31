"""Fixture tests for mail_listener.py. No network, no sends; temp folders only."""
import os, sys, json, time, tempfile, importlib, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); TOP = os.path.dirname(HERE)
SRC = os.path.join(TOP, "src") if os.path.exists(os.path.join(TOP, "src", "mail_listener.py")) else TOP; sys.path.insert(0, SRC)
FX = json.load(open(os.path.join(HERE, "fixtures", "messages.json")))

def fresh(ts=None):
    tmp = tempfile.mkdtemp(); root, buy = os.path.join(tmp, "listing-scout"), os.path.join(tmp, "listing-scout-buytest")
    os.makedirs(root); os.makedirs(buy)
    os.environ.update(LS_ROOT=root, LS_BUYTEST=buy, AGENTMAIL_API_KEY="test-key-not-real")
    import mail_listener as L; importlib.reload(L)
    byid = {m["message_id"]: m for m in FX}
    L.get = lambda path, key, timeout=30: (byid[__import__("urllib.parse").parse.unquote(path.rsplit("/", 1)[1])]
                                           if "/messages/" in path else {"messages": [dict(m, timestamp=ts) for m in FX]})
    return L, root, buy

def files(d): return sorted(os.listdir(os.path.join(d, "inbox"))) if os.path.isdir(os.path.join(d, "inbox")) else []

def test_routing_and_files():
    L, root, buy = fresh()
    for m in FX:
        path = L.handle(dict(m), "k")
        exp = m["expect"]
        if exp in ("skip", "ignore"): assert path is None, m["message_id"]
        else:
            kind, site = exp.split(":")
            assert path and os.path.basename(path).startswith(site + "-"), (m["message_id"], path)
            assert path.startswith(buy if kind == "buy" else root + "/inbox"), (m["message_id"], path)
            body = open(path).read(); assert m["subject"] in body and m["text"] in body
    assert len(files(root)) == 3 and len(files(buy)) == 3, (files(root), files(buy))
    ids = open(os.path.join(root, "out", "fetched_ids.txt")).read().split()
    assert sorted(ids) == sorted(m["message_id"] for m in FX)
    log = open(os.path.join(root, "logs", "email_skips.log")).read()
    assert log.count("| routed |") == 6 and log.count("| skipped |") == 2 and "cloudflare" not in log.lower()
    assert "(Buy Test - 92660)" in log
    assert not os.path.exists(os.path.join(buy, "out")), "buy test never gets the id file"

def test_dedupe_and_shared_ids():
    L, root, buy = fresh()
    os.makedirs(os.path.join(root, "out")); open(os.path.join(root, "out", "fetched_ids.txt"), "w").write("4505683\n<r1@hotpads>\n")
    assert L.handle(dict(FX[0]), "k") is None   # already pulled by the routine
    p1 = L.handle(dict(FX[1]), "k"); assert p1
    assert L.handle(dict(FX[1]), "k") is None   # second event for same id
    assert L.catch_up("k") == 4                 # the rest; nothing twice
    assert L.catch_up("k") == 0
    ids = open(os.path.join(root, "out", "fetched_ids.txt")).read().split()
    assert len(ids) == len(set(ids)) and "4505683" in ids

def test_stale_catchup_skipped():
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=30)).isoformat()
    L, root, buy = fresh(ts=old)
    assert L.catch_up("k") == 0 and files(root) == [] and files(buy) == []
    assert "stale catch-up" in open(os.path.join(root, "logs", "email_skips.log")).read()

def test_no_partial_files_and_no_secret_in_output():
    L, root, buy = fresh(); L.catch_up("k")
    for d in (root, buy):
        assert not [f for f in files(d) if f.startswith(".")]
    for dp, _, fs in os.walk(os.path.dirname(root)):
        for f in fs: assert "test-key-not-real" not in open(os.path.join(dp, f), errors="ignore").read()

def test_no_send_code():
    src = open(os.path.join(SRC, "mail_listener.py")).read()
    for bad in ("photon", "spectrum", "notify", "smtplib", "/send", "POST"):
        assert bad not in src, bad

if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"): f(); n += 1; print("ok", k)
    print(f"{n} passed")
