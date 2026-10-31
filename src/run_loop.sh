#!/usr/bin/env bash
# Zero-AI scheduler for Listing Scout (no cron/systemd on this box, so a simple loop under nohup).
# Interval: CRITERIA.yaml loop_minutes (default 5). It is read each pass, so a change applies after the current wait.
# Needs PHOTON_API_KEY in the environment of the shell that starts it (never written to disk here).
# Start it with ./src/ensure_running.sh (keeps exactly one copy), not directly.
cd "$(dirname "$0")"; S=""; if [ "$(basename "$PWD")" = src ]; then cd ..; S="src/"; fi   # works from src/ (repo) or a flat install
ENVF="${SCOUT_ENV:-$HOME/.config/listing-scout/env}"; [ -f "$ENVF" ] && { set -a; . "$ENVF"; set +a; }   # key survives restarts (chmod 600, never printed)
while true; do
  mode=$(python3 -c "import yaml;print(yaml.safe_load(open('CRITERIA.yaml')).get('plan_mode','standard'))")
  N=$(python3 -c "import yaml;print(max(1, int(yaml.safe_load(open('CRITERIA.yaml')).get('loop_minutes') or 5)))" 2>/dev/null || echo 5)
  ts=$(date '+%F %T %Z'); t0=$(date +%s)
  ./${S}ensure_running.sh >/dev/null 2>&1 || true   # keeps the reply listener up (one copy); flags a missing key
  if [ -f out/search_ended.json ]; then echo "$ts search wrapped up (out/search_ended.json); loop stopping" >> logs/loop.log; exit 0; fi   # We found it
  python3 ${S}fetch_inbox.py >> logs/notify.log 2>&1   # pull Zillow/Redfin/HotPads alert emails into ./inbox (needs AGENTMAIL_API_KEY)
  if python3 ${S}scout.py --json --matches-only > out/alerts.json 2>> logs/scout.err; then
    python3 ${S}notify.py alerts out/alerts.json --send >> logs/notify.log 2>&1
    python3 ${S}notify.py firstday --send >> logs/notify.log 2>&1   # one-time, capped; skipped if the snapshot went out
    python3 ${S}notify.py nudge --send >> logs/notify.log 2>&1      # one-time owner nudge if a member hasn't replied OK in ~24h
    python3 ${S}notify.py outage --send >> logs/notify.log 2>&1     # a source down > 1 day: owner told once
    python3 ${S}notify.py emailwatch --send >> logs/notify.log 2>&1 # owner only: unreadable alert email, email sync stalled past the plan interval + 3h, a site quiet 48h
    python3 ${S}notify.py morning --send >> logs/notify.log 2>&1    # Sleep mode: held finds at wake time; the one-time offer after a late alert
    python3 ${S}notify.py gone --send >> logs/notify.log 2>&1       # Still available?: liked places gone ~24h ("no longer listed")
    python3 ${S}notify.py offmarket --send >> logs/notify.log 2>&1  # buy: shortlisted home went pending/sold -> only its shortlisters hear
    python3 ${S}notify.py evening --send >> logs/notify.log 2>&1    # Daily cap (off by default): held finds as one text after 6 PM
    python3 ${S}notify.py pulse --send >> logs/notify.log 2>&1      # Quiet-week pulse: one note with a real count after 7 silent days
    python3 ${S}notify.py firstweek --send >> logs/notify.log 2>&1  # once, day 4+: "Anything bugging you so far?" (into Make it better, gated)
    python3 ${S}notify.py hygiene --send >> logs/notify.log 2>&1    # Criteria hygiene: weekly near-miss / volume check-in (confirm-first; quiet on day one)
    nohup python3 ${S}gonecheck.py --apply --daily >> logs/gonecheck.out 2>&1 9>&- &   # Still listed? once a day, polite, in the background; never texts
    PYTHONPATH=${S:-.} python3 -c "import features; features.prune_logs()" 2>> logs/scout.err   # logs kept 30 days
    echo "$ts ok mode=$mode $(python3 -c "import json;print(len(json.load(open('out/alerts.json'))))") alerts took=$(( $(date +%s)-t0 ))s" >> logs/loop.log
  else
    echo "$ts scout failed (see logs/scout.err)" >> logs/loop.log
  fi
  el=$(( $(date +%s)-t0 )); w=$(( N*60-el )); [ $w -lt 30 ] && w=30
  sleep $w   # fixed cadence: a slow pass shortens the wait, so checks stay ~every N minutes
done
