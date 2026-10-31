"""v1.2.19: per-pass catch-up in fetch_inbox.py + listener skips for-sale mail. No network, temp folders only."""
import os, sys, io, json, time, importlib, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import test_mail_listener as T

def test_for_sale_wording_skipped():
    L, root, buy = T.fresh()
    for frm, subj, body in [("Zillow <instant-updates@mail.zillow.com>", "3 homes for sale in 92627", "$1,250,000 https://zillow.com/homedetails/x"),
                            ("Redfin <listings@redfin.com>", "New in Newport", "Buy Test - 92663 $3,200,000 https://redfin.com/CA/x/home/1"),
                            ("move.com <a@move.com>", "New listing", "$900,000 realtor.com/realestateandhomes-detail/x")]:
        assert L.route(frm, subj, body)[0] is None and L.route(frm, subj, body)[1].startswith("buy test ended")
    assert L.route("Zillow <instant-updates@mail.zillow.com>", "New Rental Match", "$3,580/mo https://zillow.com/homedetails/x") == ("rental", "zillow")

def test_pass_catchup_saves_once_and_marks_seen():
    L, root, buy = T.fresh()
    sys.path.insert(0, T.SRC); cwd = os.getcwd()
    try:
        F = importlib.import_module("fetch_inbox"); os.chdir(root)
        sys.modules["mail_listener"] = L
        with contextlib.redirect_stdout(io.StringIO()) as o: F.catch_up_pass()
        assert "3 new" in o.getvalue() and F.CATCHUP_OK
        assert sorted(T.files(root)) == sorted(f for f in T.files(root) if "-am-" in f) and len(T.files(root)) == 3 and T.files(buy) == []
        with contextlib.redirect_stdout(io.StringIO()) as o: F.catch_up_pass()
        assert "0 new" in o.getvalue()
        log = open(os.path.join(root, "logs", "email_skips.log")).read()
        assert "[pass catch-up]" in log and log.count("buy test ended") == 3
    finally: os.chdir(cwd)

def test_pass_catchup_fail_safe_and_deadline():
    L, root, buy = T.fresh(); sys.path.insert(0, T.SRC)
    F = importlib.import_module("fetch_inbox"); sys.modules["mail_listener"] = L
    def boom(*a, **k): raise TimeoutError("slow")
    L.get = boom; F.CATCHUP_OK = False
    with contextlib.redirect_stdout(io.StringIO()) as o: assert F.catch_up_pass() == 0
    assert "error TimeoutError" in o.getvalue() and not F.CATCHUP_OK
    L2, root2, _ = T.fresh()
    assert L2.catch_up("k", quiet=True, deadline=time.monotonic() - 1) == 0 and T.files(root2) == []

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
