"""v1.2.11 self-heal + backups: restore only what is missing, never overwrite, block on re-text risk, encrypted mirror, rotation."""
import os, sys, json, glob, importlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, "src"))
import selfheal as sh


def mk(tmp, shadow=False, sent=True):
    d = str(tmp / "inst"); os.makedirs(d + "/out"); os.makedirs(d + "/logs")
    open(d + "/CRITERIA.yaml", "w").write("loop_minutes: 5\n")
    json.dump({"listings": {"a": {}}}, open(d + "/state.json", "w"))
    json.dump([{"id": "a"}], open(d + "/out/texted.json", "w"))
    json.dump({"m": 1}, open(d + "/out/members.json", "w"))
    if sent: open(d + "/logs/sends.jsonl", "w").write('{"ok": true, "dry_run": false}\n')
    if shadow: open(d + "/SHADOW_ONLY", "w").write("")
    return d


def setup(monkeypatch, tmp, d, mirror=None):
    monkeypatch.setattr(sh, "HOME_INSTALL", d); monkeypatch.setattr(sh, "KEYF", str(tmp / "k"))
    if mirror: json.dump({"mirror": mirror}, open(d + "/selfheal.local.json", "w"))
    monkeypatch.setattr(sh, "heal_node", lambda d: None)


def test_restore_only_missing_never_overwrite(tmp_path, monkeypatch):
    d = mk(tmp_path); setup(monkeypatch, tmp_path, d)
    assert sh.backup(d, force=True)
    json.dump({"m": 2}, open(d + "/out/members.json", "w"))          # present and newer: must stay
    os.remove(d + "/out/texted.json")
    monkeypatch.setattr(sh, "dry_run_check", lambda d: (True, 0, []))
    sh.heal(d)
    assert json.load(open(d + "/out/texted.json")) == [{"id": "a"}]
    assert json.load(open(d + "/out/members.json")) == {"m": 2}
    assert not os.path.exists(d + "/out/search_ended.json")
    assert "restored out/texted.json" in open(d + "/logs/heal.log").read()


def test_texted_gone_no_backup_blocks(tmp_path, monkeypatch):
    d = mk(tmp_path); setup(monkeypatch, tmp_path, d)
    os.remove(d + "/out/texted.json")
    sh.heal(d)
    b = json.load(open(d + "/out/search_ended.json"))
    assert b["reason"] == "selfheal_block" and "texted.json" in b["why"]
    assert sh.status(d)["heal_blocked"]


def test_repeat_after_restore_blocks(tmp_path, monkeypatch):
    d = mk(tmp_path); setup(monkeypatch, tmp_path, d); sh.backup(d, force=True)
    os.remove(d + "/state.json")
    monkeypatch.setattr(sh, "dry_run_check", lambda d: (False, 1, ["1 Main St"]))
    sh.heal(d)
    assert json.load(open(d + "/out/search_ended.json"))["reason"] == "selfheal_block"


def test_shadow_never_blocks(tmp_path, monkeypatch):
    d = mk(tmp_path, shadow=True); setup(monkeypatch, tmp_path, d)
    os.remove(d + "/out/texted.json"); sh.heal(d)
    assert not os.path.exists(d + "/out/search_ended.json")


def test_encrypted_mirror_restores(tmp_path, monkeypatch):
    m = str(tmp_path / "mirror"); os.makedirs(m)
    d = mk(tmp_path); setup(monkeypatch, tmp_path, d, mirror=m); sh.backup(d, force=True)
    enc = glob.glob(m + "/**/*.enc", recursive=True); assert enc
    assert b'"m"' not in open(enc[0], "rb").read()                    # nothing readable in the mirror
    import shutil; shutil.rmtree(d + "/backups"); os.remove(d + "/out/members.json")
    sh.heal(d)
    assert json.load(open(d + "/out/members.json")) == {"m": 1}


def test_rotation(tmp_path):
    f = tmp_path / "h"; f.mkdir()
    for i in range(60): (f / f"2026{i:04d}.tgz").write_text("x")
    sh.rotate(str(f), 48); assert len(list(f.iterdir())) == 48
    assert sorted(p.name for p in f.iterdir())[0] == "20260012.tgz"


def test_backup_not_due_twice(tmp_path, monkeypatch):
    d = mk(tmp_path); setup(monkeypatch, tmp_path, d)
    assert sh.backup(d) and sh.backup(d) is None


def test_deliberate_delete_not_restored(tmp_path, monkeypatch):
    d = mk(tmp_path); setup(monkeypatch, tmp_path, d)
    json.dump({"reason": "owner"}, open(d + "/out/search_ended.json", "w")); open(d + "/out/pending_review.json", "w").write("{}")
    sh.backup(d, force=True); sh.mark(d)
    os.remove(d + "/out/search_ended.json"); os.remove(d + "/out/pending_review.json")   # lifted on purpose
    sh.heal(d)
    assert not os.path.exists(d + "/out/search_ended.json") and not os.path.exists(d + "/out/pending_review.json")
    import shutil; shutil.rmtree(d + "/out")                                        # now a real wipe
    monkeypatch.setattr(sh, "dry_run_check", lambda d: (True, 0, []))
    sh.heal(d)
    assert os.path.exists(d + "/out/texted.json") and os.path.exists(d + "/out/search_ended.json")


def test_purge_removes_backups(tmp_path, monkeypatch):
    d = mk(tmp_path); setup(monkeypatch, tmp_path, d); sh.backup(d, force=True)
    json.dump({"Ern": {"joined": True}}, open(d + "/out/members.json", "w"))
    import features
    monkeypatch.setattr(features, "HERE", d); monkeypatch.setattr(features, "OUT", d + "/out")
    features.purge_all()
    assert not os.path.exists(d + "/backups/auto")


def test_block_keeps_existing_end_and_flags(tmp_path, monkeypatch):
    d = mk(tmp_path); setup(monkeypatch, tmp_path, d)
    json.dump({"reason": "owner"}, open(d + "/out/search_ended.json", "w")); os.remove(d + "/out/texted.json")
    sh.heal(d)
    b = json.load(open(d + "/out/search_ended.json"))
    assert b["reason"] == "owner" and "texted.json" in b["selfheal_block"] and sh.status(d)["heal_blocked"]


if __name__ == "__main__":   # no pytest needed: tiny tmp_path / monkeypatch stand-ins
    import tempfile, pathlib, inspect

    class MP:
        def __init__(self): self.undo = []
        def setattr(self, o, k, v): self.undo.append((o, k, getattr(o, k))); setattr(o, k, v)
        def close(self):
            for o, k, v in reversed(self.undo): setattr(o, k, v)
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            mp = MP(); t = pathlib.Path(tempfile.mkdtemp())
            args = {"tmp_path": t, "monkeypatch": mp}
            try: f(*[args[p] for p in inspect.signature(f).parameters])
            finally: mp.close()
            n += 1
    print(f"ok {n} tests")
