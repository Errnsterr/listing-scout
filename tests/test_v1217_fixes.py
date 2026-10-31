"""v1.2.17: listener misses after a box pause, hard request/pass limits, Redfin ranges. No network, no sends."""
import os, sys, time, tempfile, importlib, asyncio, threading, http.server, socket
HERE = os.path.dirname(os.path.abspath(__file__)); TOP = os.path.dirname(HERE)
SRC = os.path.join(TOP, "src") if os.path.exists(os.path.join(TOP, "src", "scout.py")) else TOP; sys.path.insert(0, SRC)

def _listener():
    tmp = tempfile.mkdtemp(); os.environ.update(LS_ROOT=tmp, AGENTMAIL_API_KEY="test-key-not-real")
    import mail_listener as L; importlib.reload(L); return L

def test_resume_detect():
    L = _listener()
    assert L.resumed(0, 0, 600, 5)          # 10 min of wall time, 5 s of run time: the box was paused
    assert not L.resumed(0, 0, 60, 59.5)

def test_miss_reproduced_pause_then_mail():
    """The 8:19 / 9:21 misses: mail lands while the box is paused; the socket is dead but looks 'connected'.
    On wake the listener must poll at once (not after a 3-min timer behind the watchdog) and drop the socket."""
    L = _listener(); polls, closed = [], []
    L.catch_up = lambda key, quiet=False: polls.append(time.monotonic()) or 1
    async def no_wd(every=60): await asyncio.sleep(3600)
    L.watchdog_job = no_wd
    class WS:
        async def close(self): closed.append(1)
    real = time.time; jump = {"s": 0.0}; L.time.time = lambda: real() + jump["s"]
    async def go():
        t = asyncio.create_task(L.side_jobs("k", poll_every=3600, tick=0.01, ws_holder={"ws": WS()}))
        await asyncio.sleep(0.05); assert not polls
        jump["s"] = 900.0                     # wake: wall clock leaps 15 min
        await asyncio.sleep(0.05); t.cancel()
    try: asyncio.run(go())
    finally: L.time.time = real
    assert polls and closed, (polls, closed)
    assert os.path.exists(os.path.join(os.environ["LS_ROOT"], "out", "resumed_at"))

def test_poll_every_minute_default():
    import inspect; L = _listener()
    assert inspect.signature(L.side_jobs).parameters["poll_every"].default == 60

def test_watchdog_pause_grace():
    import loop_watchdog as W; now = 10_000.0
    assert W.decide(now, now - 20 * 60, 7, start_mtime=now - 15 * 60) == "restart"
    assert W.decide(now, now - 20 * 60, 7, start_mtime=now - 15 * 60, resumed_at=now - 60) == "ok"
    assert W.decide(now, now - 20 * 60, 7, start_mtime=now - 15 * 60, resumed_at=now - 8 * 60) == "restart"

def test_get_total_deadline():
    """A page that drips one byte at a time must fail fast as a timeout (feeds the normal backoff)."""
    import scout
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.send_header("Content-Length", "100000"); self.end_headers()
            try:
                for _ in range(100000): self.wfile.write(b"x"); self.wfile.flush(); time.sleep(0.05)
            except Exception: pass
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    t0 = time.monotonic()
    try: scout.get(f"http://127.0.0.1:{srv.server_port}/", total=1.5); assert False, "no timeout"
    except TimeoutError as e: assert "timed out" in str(e).lower()
    finally: srv.shutdown()
    assert time.monotonic() - t0 < 6

def test_loop_has_hard_caps():
    s = open(os.path.join(SRC, "run_loop.sh")).read()
    assert "timeout -k 10 ${SCOUT_PASS_LIMIT:-300} python3 ${S}scout.py" in s and "timeout -k 10 120 python3 ${S}fetch_inbox.py" in s

B = """Subject: New rentals in Town at $2,469-$3,125/mo, Town at $2,609-$3,480/mo
1. NEW: 1 Sample Park, Town, CA 90001
- Price: $2,469-$3,125/mo
- Details: 0-1 Beds, 1 Bath, 513-745 Sq. Ft.
- Additional Details: https://www.redfin.com/CA/Town/1-Sample-Park-90001/home/1?utm=x
1. NEW: 300 Demo Dr E, Town, CA 90001
- Price: $2,609-$3,480/mo
- Details: 1-2 Beds, 1-2 Baths, 600-1,120 Sq. Ft.
- Additional Details: https://www.redfin.com/CA/Town/300-Demo-Dr-E-90001/home/2?utm=x
* Nearby similar homes *
"""
def test_redfin_ranges_and_cutoff():
    import scout
    L = scout._parse_redfin_list_text(B, "t"); a, b = L
    assert a["price"] == 2469 and a["price_to"] == 3125 and a["price_range"] == [2469, 3125] and a["price_from"]
    assert a["beds_range"] == [0, 1] and a["beds_max"] == 1
    assert b["beds_range"] == [1, 2] and b["price_range"] == [2609, 3480]
    f = os.path.join(tempfile.mkdtemp(), "redfin-x.txt"); open(f, "w").write(B)
    assert scout.email_cutoff(f, L) is None   # the high end of the subject range is now understood

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
