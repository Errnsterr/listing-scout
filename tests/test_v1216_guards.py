"""v1.2.16: timeout backoff, bare ids, loop guard, listener catch-up/poll. No network, no sends."""
import os, sys, json, time, tempfile, importlib, subprocess, asyncio
HERE = os.path.dirname(os.path.abspath(__file__)); TOP = os.path.dirname(HERE)
SRC = os.path.join(TOP, "src") if os.path.exists(os.path.join(TOP, "src", "scout.py")) else TOP; sys.path.insert(0, SRC)

def test_backoff_sequence_and_pause():
    import scout
    h, now = {}, 1_000_000.0
    seq = [scout.backoff_after_timeout(h, now)["skip_left"] for _ in range(6)]
    assert seq == [2, 4, 8, 16, 24, 24], seq
    assert not h.get("paused")
    scout.backoff_after_timeout(h, now + 3 * 86400 - 60); assert not h.get("paused")
    scout.backoff_after_timeout(h, now + 3 * 86400 + 60); assert h["paused"] is True

def test_ids_normalized():
    import fetched_ids as F
    for raw in ["<a.b@c>", "am:<a.b@c>", "am:a.b@c", " a.b@c \n", "a.b@c"]: assert F.norm(raw) == "a.b@c", raw
    import mail_listener as L
    assert L.norm_id("am:<x@y>") == L.norm_id("<x@y>") == "x@y"

def test_ids_cli_seen_add(tmp_path=None):
    tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(tmp, "out"))
    src = open(os.path.join(SRC, "fetched_ids.py")).read(); open(os.path.join(tmp, "fetched_ids.py"), "w").write(src)
    open(os.path.join(tmp, "out", "fetched_ids.txt"), "w").write("<old@id>\nam:<older@id>\n")
    r = lambda *a: subprocess.run([sys.executable, os.path.join(tmp, "fetched_ids.py"), *a]).returncode
    assert r("seen", "old@id") == 0 and r("seen", "am:older@id") == 0 and r("seen", "<older@id>") == 0
    assert r("seen", "<new@id>") == 1
    r("add", "<new@id>"); r("add", "am:new@id")
    lines = open(os.path.join(tmp, "out", "fetched_ids.txt")).read().splitlines()
    assert lines[-1] == "new@id" and lines.count("new@id") == 1

def test_loop_guard_decide():
    import loop_watchdog as W
    now = 10_000.0
    assert W.decide(now, now - 4 * 60, 7) == "ok"                                   # sleeping, fresh line
    assert W.decide(now, now - 8 * 60, 7) == "restart"                              # nothing logged 8 min
    assert W.decide(now, now - 10 * 60, 7, start_mtime=now - 6 * 60) == "ok"        # slow pass, 6 min in
    assert W.decide(now, now - 12 * 60, 7, start_mtime=now - 8 * 60) == "restart"   # pass stuck 8 min
    assert W.decide(now, now - 12 * 60, 7, sending=True, start_mtime=now - 8 * 60) == "wait_send"
    assert W.decide(now, now - 60, 7, loop_alive=False) == "restart"
    assert W.decide(now, now - 3 * 60, 7, start_mtime=now - 9 * 60) == "ok"         # mark older than line: pass done

def test_listener_catchup_every_connect_and_poll():
    tmp = tempfile.mkdtemp(); os.environ.update(LS_ROOT=tmp, AGENTMAIL_API_KEY="test-key-not-real")
    import mail_listener as L; importlib.reload(L)
    calls = []
    L.catch_up = lambda key, quiet=False: calls.append(quiet) or 0
    src = open(L.__file__).read()
    assert "await asyncio.to_thread(catch_up, key)" in src.split("async def run_forever")[1]   # on every (re)connect
    async def go():
        t = asyncio.create_task(L.side_jobs("k", every=0.01, poll_every=0)); await asyncio.sleep(0.2); t.cancel()
    import subprocess as sp; real = sp.run; sp.run = lambda *a, **k: None
    try: asyncio.run(go())
    finally: sp.run = real
    assert calls and all(calls), calls   # quiet periodic polls happened

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
