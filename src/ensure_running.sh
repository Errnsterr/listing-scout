#!/usr/bin/env bash
# Keeps exactly ONE Listing Scout loop running. Safe to call any time (from ~/.bashrc, the health check, or by hand).
# Secrets: sources ${SCOUT_ENV:-~/.config/listing-scout/env} (chmod 600; never printed, never in this folder) so a restart keeps the key.
# Starts nothing if PHOTON_API_KEY is still missing; flags it for the owner (out/health_flags.json) instead. (paused: true still runs the checks; notify.py just skips sending.)
cd "$(dirname "$0")" || exit 0; S=""; if [ "$(basename "$PWD")" = src ]; then cd .. || exit 0; S="src/"; fi   # src/ (repo) or flat install
exec 9>logs/.ensure.lock; flock -n 9 || exit 0
ENVF="${SCOUT_ENV:-$HOME/.config/listing-scout/env}"
if [ -f "$ENVF" ]; then
  [ "$(stat -c %a "$ENVF")" = "600" ] || chmod 600 "$ENVF"
  set -a; . "$ENVF"; set +a
fi
flag() { python3 - "$1" "$2" <<'PY'
import json, os, sys, time
f = "out/health_flags.json"; os.makedirs("out", exist_ok=True)
d = json.load(open(f)) if os.path.exists(f) else {}
k, on = sys.argv[1], sys.argv[2] == "on"
if on: d.setdefault(k, {"since": time.strftime("%F %T %Z")})
else: d.pop(k, None)
json.dump(d, open(f, "w"), indent=1)
PY
}
python3 ${S}selfheal.py >/dev/null 2>&1 || true   # v1.2.11: npm ci / restore missing files from backups (logs/heal.log); hourly + daily backups; may block sends
[ -f out/search_ended.json ] && exit 0   # We found it: the search is wrapped up; start nothing
start_loop() {
  pid=$(cat logs/loop.pid 2>/dev/null)
  if [ -n "$pid" ] && grep -q run_loop.sh /proc/"$pid"/cmdline 2>/dev/null; then return; fi
  for p in $(pgrep -f "bash ./${S}run_loop.sh"); do echo "$(date '+%F %T %Z') found stray loop, adopting pid $p" >> logs/loop.log; echo "$p" > logs/loop.pid; return; done
  nohup ./${S}run_loop.sh >/dev/null 2>&1 9>&- &
  echo $! > logs/loop.pid
  echo "$(date '+%F %T %Z') loop (re)started, pid $!" >> logs/loop.log
}
if [ -z "$PHOTON_API_KEY" ]; then
  flag photon_key_missing on
  pgrep -f "bash ./${S}run_loop.sh" >/dev/null || echo "$(date '+%F %T %Z') loop down; not restarted (no PHOTON_API_KEY in $ENVF or this shell)" >> logs/loop.log
  exit 0
fi
flag photon_key_missing off
start_loop

# Reply listener (only when CRITERIA.yaml has replies: true). Exactly one copy, same rules.
if python3 -c "import yaml,sys;sys.exit(0 if yaml.safe_load(open('CRITERIA.yaml')).get('replies') else 1)"; then
  lp=$(cat logs/listen.pid 2>/dev/null)
  if ! { [ -n "$lp" ] && grep -q listen.mjs /proc/"$lp"/cmdline 2>/dev/null; }; then
    [ -n "$lp" ] && { flag listener_restarted on; [ -f out/outage_pending.json ] || python3 -c "import json,time;json.dump({'source':'Reply listener','since':time.strftime('%a %-I:%M %p')},open('out/outage_pending.json','w'))"; }   # was running before: owner told once
    nohup node ${S}listen.mjs >> logs/listen.log 2>&1 9>&- &
    echo $! > logs/listen.pid; echo "$(date '+%F %T %Z') reply listener (re)started, pid $!" >> logs/loop.log
  fi
fi
# --- v1.2.15 instant email listener (paste at the END of ensure_running.sh). DISABLED unless CRITERIA.yaml has mail_listener: true.
# Exactly one copy (logs/mail_listener.pid), same rules as the reply listener. Needs AGENTMAIL_API_KEY in $ENVF; never sends texts.
if python3 -c "import yaml,sys;sys.exit(0 if yaml.safe_load(open('CRITERIA.yaml')).get('mail_listener') else 1)" && [ -n "$AGENTMAIL_API_KEY" ]; then
  mp=$(cat logs/mail_listener.pid 2>/dev/null)
  if ! { [ -n "$mp" ] && grep -q mail_listener.py /proc/"$mp"/cmdline 2>/dev/null; }; then
    nohup python3 ${S}mail_listener.py >> logs/mail_listener.out 2>&1 9>&- &
    echo $! > logs/mail_listener.pid; echo "$(date '+%F %T %Z') mail listener (re)started, pid $!" >> logs/loop.log
  fi
fi
