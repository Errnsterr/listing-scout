#!/usr/bin/env python3
"""Self-heal + automatic backups for Listing Scout (no AI; never sends a text; never prints secrets or numbers).
  python3 src/selfheal.py                 # heal this install if needed, then back up if one is due
  python3 src/selfheal.py --backup-now    # force a backup now
  python3 src/selfheal.py --status        # one JSON line: last backup + last heal (health.py uses this)
Called every loop pass by ensure_running.sh and by health.py --restart. Extra installs (e.g. a shadow
proof copy) and an off-box mirror folder come from selfheal.local.json in the install root (not in the repo):
  {"also": ["/path/to/other-install"], "mirror": "/persistent/folder"}
Backups: <install>/backups/auto/{hourly,daily}/*.tgz (chmod 600; 48 hourly, 14 daily). The mirror copy is
encrypted (openssl AES-256, key ~/.config/listing-scout/backup.key, chmod 600), so no phone number sits there in plain text.
Heal: node_modules/spectrum-ts missing -> npm ci. A missing out/ file, state.json or CRITERIA.yaml -> restored
from the newest backup that has a valid copy, only where the file is missing (nothing present is ever overwritten).
Safety: if state.json or out/texted.json is missing and no backup can supply it, sends are blocked
(out/search_ended.json, reason selfheal_block) and health says so. After restoring either one, a no-send dry run
(scout.py --dry-run in a temp copy) must show nothing already texted would go out again, or sends are blocked.
Every heal is logged to logs/heal.log."""
import os, sys, json, time, glob, shutil, tarfile, tempfile, subprocess, fcntl, io, hashlib

KEEP = {"hourly": 48, "daily": 14}
SKIP_RESTORE = {"alerts.json"}            # rebuilt every pass; a stale copy is never restored
CRITICAL = ["state.json", "out/texted.json"]
SENTINEL = ".selfheal_sentinel"   # in out/: if it vanished, out/ was wiped from outside
KEYF = os.path.expanduser(os.environ.get("SCOUT_BACKUP_KEY", "~/.config/listing-scout/backup.key"))
_SRC = os.path.dirname(os.path.abspath(__file__))
HOME_INSTALL = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC


def now(): return time.strftime("%F %T %Z")
def stamp(): return time.strftime("%Y%m%d-%H%M%S")


def log(d, msg):
    os.makedirs(os.path.join(d, "logs"), exist_ok=True)
    with open(os.path.join(d, "logs", "heal.log"), "a") as f: f.write(f"{now()} {msg}\n")


def local_cfg(d):
    p = os.path.join(d, "selfheal.local.json")
    try: return json.load(open(p))
    except Exception: return {}


def shadow(d): return os.path.exists(os.path.join(d, "SHADOW_ONLY"))


def valid(name, data):
    if name.endswith(".json"):
        try: json.loads(data.decode() or "null"); return True
        except Exception: return False
    return True


# ---------- backups ----------
def snapshot_files(d):
    fs = []
    for f in ("state.json", "CRITERIA.yaml"):
        if os.path.isfile(os.path.join(d, f)): fs.append(f)
    for root, _, names in os.walk(os.path.join(d, "out")):
        for n in names:
            if n == SENTINEL: continue
            fs.append(os.path.relpath(os.path.join(root, n), d))
    return sorted(fs)


def digest(d, fs):
    h = hashlib.sha256()
    h.update(str(os.path.exists(os.path.join(d, "out", "search_ended.json"))).encode())   # a block set or lifted refreshes the backup
    for f in ("state.json", "out/texted.json", "out/text_log.jsonl", "out/members.json"):
        p = os.path.join(d, f)
        if os.path.exists(p): h.update(f.encode()); h.update(open(p, "rb").read())
    return h.hexdigest()[:16]


def mirror_dir(d, mirror):
    tag = os.path.basename(os.path.abspath(d)).replace("/", "_")
    return os.path.join(mirror, "listing-scout-backups", tag)


def ensure_key():
    if not os.path.exists(KEYF):
        os.makedirs(os.path.dirname(KEYF), exist_ok=True)
        fd = os.open(KEYF, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, os.urandom(32).hex().encode()); os.close(fd)
    return KEYF


def enc(src, dst):
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-in", src, "-out", dst, "-pass", f"file:{ensure_key()}"],
                   check=True, capture_output=True)


def dec(src, dst):
    subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", src, "-out", dst, "-pass", f"file:{KEYF}"],
                   check=True, capture_output=True)


def rotate(folder, keep):
    xs = sorted(glob.glob(os.path.join(folder, "*.tgz*")))
    for x in xs[:-keep] if len(xs) > keep else []:
        try: os.remove(x)
        except OSError: pass


def backup(d, force=False):
    """Hourly snapshot (or sooner when the texted record / state changed since the last one), plus one per day."""
    base = os.path.join(d, "backups", "auto"); meta_p = os.path.join(base, "last.json")
    meta = {}
    try: meta = json.load(open(meta_p))
    except Exception: pass
    fs = snapshot_files(d)
    if not fs: return None
    dg = digest(d, fs); t = time.time()
    hourly_due = force or t - meta.get("hourly_ts", 0) >= 3600 or (dg != meta.get("digest") and t - meta.get("hourly_ts", 0) >= 60)
    daily_due = force or time.strftime("%F") != meta.get("daily_day")
    if not (hourly_due or daily_due): return None
    os.makedirs(os.path.join(base, "hourly"), exist_ok=True); os.makedirs(os.path.join(base, "daily"), exist_ok=True)
    os.chmod(base, 0o700)
    name = f"{stamp()}.tgz"
    while any(os.path.exists(os.path.join(base, k, name)) for k in ("hourly", "daily")): time.sleep(1); name = f"{stamp()}.tgz"
    tmp = os.path.join(base, "." + name)
    old = os.umask(0o077)
    try:
        with tarfile.open(tmp, "w:gz") as tf:
            for f in fs:
                try: tf.add(os.path.join(d, f), arcname=f)
                except (FileNotFoundError, OSError): pass
            man = json.dumps({"ts": now(), "files": fs, "digest": dg}).encode()
            ti = tarfile.TarInfo("MANIFEST.json"); ti.size = len(man); ti.mtime = int(t); tf.addfile(ti, io.BytesIO(man))
    finally: os.umask(old)
    kinds = (["hourly"] if hourly_due else []) + (["daily"] if daily_due else [])
    for k in kinds:
        shutil.copy2(tmp, os.path.join(base, k, name)); os.chmod(os.path.join(base, k, name), 0o600); rotate(os.path.join(base, k), KEEP[k])
    mirror = local_cfg(HOME_INSTALL).get("mirror") or local_cfg(d).get("mirror")
    mirrored = False
    if mirror and os.path.isdir(mirror) and os.access(mirror, os.W_OK):
        try:
            for k in kinds:
                md = os.path.join(mirror_dir(d, mirror), k); os.makedirs(md, exist_ok=True)
                enc(tmp, os.path.join(md, name + ".enc")); rotate(md, KEEP[k])
            json.dump({"ever": sorted(set(meta.get("ever", [])) | set(fs))}, open(os.path.join(mirror_dir(d, mirror), "expected.json"), "w"))   # file names only
            mirrored = True
        except Exception as e: log(d, f"backup mirror copy failed: {type(e).__name__}")
    os.remove(tmp)
    if hourly_due: meta["hourly_ts"] = t
    if daily_due: meta["daily_day"] = time.strftime("%F")
    meta.update({"digest": dg, "last": now(), "last_ts": t, "files": len(fs), "mirrored": mirrored,
                 "ever": sorted(set(meta.get("ever", [])) | set(fs))})   # every file a backup has ever held: "expected" files
    json.dump(meta, open(meta_p, "w"), indent=1)
    return name


def candidates(d):
    """Backup archives, newest first: local hourly/daily, then the encrypted mirror."""
    base = os.path.join(d, "backups", "auto"); xs = []
    for k in ("hourly", "daily"): xs += glob.glob(os.path.join(base, k, "*.tgz"))
    mirror = local_cfg(HOME_INSTALL).get("mirror") or local_cfg(d).get("mirror")
    if mirror and os.path.exists(KEYF):
        for k in ("hourly", "daily"): xs += glob.glob(os.path.join(mirror_dir(d, mirror), k, "*.tgz.enc"))
    return sorted(set(xs), key=lambda p: (os.path.basename(p).replace(".enc", ""), not p.endswith(".enc")), reverse=True)   # newest first; local before mirror


def open_archive(p, tmpd):
    if p.endswith(".enc"):
        out = os.path.join(tmpd, os.path.basename(p)[:-4]); dec(p, out); p = out
    return tarfile.open(p, "r:gz")


# ---------- heal ----------
def expected(d):
    meta = {}
    try: meta = json.load(open(os.path.join(d, "backups", "auto", "last.json")))
    except Exception: pass
    ex = set(meta.get("ever", []))
    mirror = local_cfg(HOME_INSTALL).get("mirror") or local_cfg(d).get("mirror")
    if mirror:   # the local backups folder may be gone too: the mirror keeps the list of expected file names
        try: ex |= set(json.load(open(os.path.join(mirror_dir(d, mirror), "expected.json"))).get("ever", []))
        except Exception: pass
    sends = os.path.join(d, "logs", "sends.jsonl")
    if os.path.exists(sends) and any('"ok": true' in l and '"dry_run": false' in l for l in open(sends)): ex.add("out/texted.json")
    ll = os.path.join(d, "logs", "loop.log")
    if os.path.exists(ll) and any(" ok " in l for l in open(ll)): ex.add("state.json")
    return ex


def heal_node(d):
    if not os.path.exists(os.path.join(d, "package-lock.json")): return None
    if os.path.isdir(os.path.join(d, "node_modules", "spectrum-ts")): return None
    p = subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=d, capture_output=True, text=True, timeout=600)
    ok = p.returncode == 0 and os.path.isdir(os.path.join(d, "node_modules", "spectrum-ts"))
    log(d, f"HEAL node_modules/spectrum-ts missing -> npm ci {'ok' if ok else 'FAILED (rc %d)' % p.returncode}")
    return ok


def block(d, why):
    p = os.path.join(d, "out", "search_ended.json"); os.makedirs(os.path.dirname(p), exist_ok=True)
    cur = {}
    try: cur = json.load(open(p)) if os.path.exists(p) else {}
    except Exception: pass
    if not isinstance(cur, dict): cur = {}
    if os.path.exists(p) and cur.get("reason") != "selfheal_block":   # already blocked/ended: keep it, add why
        cur["selfheal_block"] = why
    else:
        cur = {"reason": "selfheal_block", "why": why, "since": now(),
               "clear": "fix the cause, then delete this file and run ensure_running.sh"}
    json.dump(cur, open(p, "w"), indent=1)
    log(d, f"BLOCK sends blocked: {why}")


def ids_texted(d):
    ids, addrs = set(), set()
    try:
        for x in json.load(open(os.path.join(d, "out", "texted.json"))):
            ids.add(x.get("id"))
    except Exception: pass
    tl = os.path.join(d, "out", "text_log.jsonl")
    if os.path.exists(tl):
        for l in open(tl):
            try: x = json.loads(l); ids |= set(x.get("ids") or []); addrs |= {a.lower() for a in x.get("addresses") or []}
            except Exception: pass
    ids.discard(None); return ids, addrs


def dry_run_check(d):
    """No-send check in a temp copy: what would the next pass text? Returns (ok, n, repeats)."""
    tmp = tempfile.mkdtemp(prefix="scout-healcheck-")
    try:
        for f in os.listdir(d):
            if f in ("node_modules", "backups", "logs"): continue
            s = os.path.join(d, f)
            if os.path.islink(s): os.symlink(os.readlink(s), os.path.join(tmp, f))
            elif os.path.isdir(s): shutil.copytree(s, os.path.join(tmp, f), symlinks=True)
            else: shutil.copy2(s, os.path.join(tmp, f))
        os.makedirs(os.path.join(tmp, "logs"), exist_ok=True)
        try: os.remove(os.path.join(tmp, "out", "search_ended.json"))
        except OSError: pass
        env = {k: v for k, v in os.environ.items() if not k.startswith(("PHOTON_", "AGENTMAIL_"))}
        sc = "src/scout.py" if os.path.exists(os.path.join(tmp, "src", "scout.py")) and not os.path.islink(os.path.join(tmp, "src")) else "scout.py"
        p = subprocess.run(["python3", sc, "--json", "--matches-only", "--dry-run"], cwd=tmp, env=env,
                           capture_output=True, text=True, timeout=600)
        if p.returncode != 0: return False, -1, ["scout dry run failed"]
        alerts = json.loads(p.stdout or "[]")
        ids, addrs = ids_texted(d)
        L = [a.get("l") if isinstance(a.get("l"), dict) else a for a in alerts]   # alerts nest the listing under "l"
        rep = [x.get("address") or x.get("id") for x in L
               if x.get("id") in ids or (x.get("address") or "").lower() in addrs]
        return (not rep and len(alerts) <= 10), len(alerts), rep
    finally: shutil.rmtree(tmp, ignore_errors=True)


def heal(d):
    d = os.path.abspath(d); sh = shadow(d); did = []
    try:
        r = heal_node(d)
        if r is not None: did.append("npm ci" + ("" if r else " (failed)"))
    except Exception as e: log(d, f"HEAL npm ci error: {type(e).__name__}"); did.append("npm ci (error)")
    ex = expected(d)
    # Restore out/ files only after a real loss (the sentinel this script keeps in out/ is gone, or texted/members are
    # gone): files the app deletes on purpose (a lifted send block, a cleared queue) must never come back by themselves.
    sentinel = os.path.join(d, "out", SENTINEL)
    lost = not os.path.exists(sentinel) and os.path.exists(os.path.join(d, "backups", "auto", "last.json")) \
        or any(f in ex and not os.path.exists(os.path.join(d, f)) for f in ("out/texted.json", "out/members.json"))
    if not lost: ex = {f for f in ex if not f.startswith("out/")}
    missing = sorted(f for f in ex if not os.path.exists(os.path.join(d, f)) and os.path.basename(f) not in SKIP_RESTORE)
    for f in ("state.json", "CRITERIA.yaml"):
        if not os.path.exists(os.path.join(d, f)) and f not in missing: missing.append(f)
    if not missing: return did
    restored = {}
    tmpd = tempfile.mkdtemp(prefix="scout-heal-")
    try:
        for arc in candidates(d):
            left = [f for f in missing if f not in restored]
            if not left: break
            try:
                with open_archive(arc, tmpd) as tf:
                    names = set(tf.getnames())
                    for f in left:
                        if f in names:
                            data = tf.extractfile(f).read()
                            if not valid(f, data): continue
                            dst = os.path.join(d, f)
                            if os.path.exists(dst): continue   # only where missing, never overwrite
                            os.makedirs(os.path.dirname(dst) or d, exist_ok=True)
                            with open(dst, "wb") as o: o.write(data)
                            restored[f] = os.path.basename(arc)
            except Exception as e: log(d, f"HEAL could not read backup {os.path.basename(arc)}: {type(e).__name__}")
    finally: shutil.rmtree(tmpd, ignore_errors=True)
    for f, a in sorted(restored.items()): log(d, f"HEAL restored {f} from {a}")
    if restored: did.append(f"restored {len(restored)} file(s)")
    gone = [f for f in missing if f not in restored]
    if gone: log(d, "HEAL not in any backup: " + ", ".join(gone))
    crit_gone = [f for f in CRITICAL if f in gone and (f in ex or f == "state.json")]
    if crit_gone and not sh:
        block(d, "missing with no backup: " + ", ".join(crit_gone) + " (risk of re-texting places)"); did.append("BLOCKED")
    elif crit_gone and sh:
        log(d, "shadow install: " + ", ".join(crit_gone) + " missing with no backup (never sends; nothing blocked)")
    elif any(f in restored for f in CRITICAL) and not sh:
        ok, n, rep = dry_run_check(d)
        log(d, f"CHECK no-send dry run after restore: {n} would-be alert(s), {len(rep)} repeat(s)")
        if not ok:
            block(d, f"after restore the next pass would send {n} alert(s), {len(rep)} already texted"); did.append("BLOCKED")
        else: did.append("dry run clean")
    return did


def status(d):
    meta = {}
    try: meta = json.load(open(os.path.join(d, "backups", "auto", "last.json")))
    except Exception: pass
    hl = os.path.join(d, "logs", "heal.log"); last_heal = None
    if os.path.exists(hl):
        ls = [l.strip() for l in open(hl) if " HEAL " in l or " BLOCK " in l]
        last_heal = ls[-1] if ls else None
    blocked = False
    try: b = json.load(open(os.path.join(d, "out", "search_ended.json"))); blocked = b.get("reason") == "selfheal_block" or "selfheal_block" in b
    except Exception: pass
    return {"install": d, "last_backup": meta.get("last"), "last_backup_ts": meta.get("last_ts"),
            "mirrored": meta.get("mirrored"), "last_heal": last_heal, "heal_blocked": blocked}


def mark(d):
    os.makedirs(os.path.join(d, "out"), exist_ok=True)
    open(os.path.join(d, "out", SENTINEL), "w").write("kept by selfheal.py; if this file disappears, out/ was wiped and gets restored from backups\n")


def run_one(d, force):
    d = os.path.abspath(d)
    if not os.path.isfile(os.path.join(d, "CRITERIA.yaml")) and not os.path.isdir(os.path.join(d, "backups", "auto")): return
    os.makedirs(os.path.join(d, "logs"), exist_ok=True)
    with open(os.path.join(d, "logs", ".selfheal.lock"), "w") as lk:
        try: fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError: return
        heal(d); mark(d)
        try:
            n = backup(d, force)
            if n and force: log(d, f"BACKUP {n} (forced)")
        except Exception as e: log(d, f"backup failed: {type(e).__name__}")


def installs():
    return [HOME_INSTALL] + [p for p in local_cfg(HOME_INSTALL).get("also", []) if os.path.isdir(p)]


if __name__ == "__main__":
    if "--status" in sys.argv:
        print(json.dumps([status(d) for d in installs()])); sys.exit(0)
    for d in installs(): run_one(d, "--backup-now" in sys.argv)
