# Listing Scout — bot-only notes (template 1.1.0)
User-facing docs (SETUP.md, SETUP_SCRIPT.md, PHOTON_FAQ.md, COSTS.md) stay plain. Every command and technical detail lives here.
Never print phone numbers (last 4 only) or `PHOTON_API_KEY`. Nothing is texted without the owner's okay.

## Update / version
- `VERSION` holds the template version. To update: `git pull` in this folder (or download the new release archive), keeping `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/`, `out/`. Then run `python3 tests/test_style.py` and `./ensure_running.sh`.

## Requirements
Node 20+, `npm install` in this folder (spectrum-ts), Python 3 with pyyaml, bs4, Pillow (avatar only).
Env: `PHOTON_API_KEY` (Project secret, from the secure form). Project ID: `photon.project_id` in CRITERIA.yaml or `PHOTON_PROJECT_ID`.

## Setup step → command
3. `python3 notify.py check` (sends nothing; shows project, plan, reachability).
4. Household add: `NEW_USER_PHONE=… python3 notify.py add_user "Name" --confirm` (number only from env via secure form), then add `name / channel / phone_last4` to `recipients`. First recipient is the owner (or set `role: owner`).
5. `python3 make_contact.py Name` → `out/Listing-Scout-<Name>.vcf` (with `assets/avatar.png` house photo). Share in chat; the bot can't text before step 6.
7. `python3 scout.py --all --dry-run` → pick a real MATCH for the sample.
8. Install (after approval):
   ```
   cd <this folder> && python3 scout.py --seed && python3 notify.py seeded && ./ensure_running.sh
   python3 notify.py welcome "Owner" --card --send     # owner welcome = test (+ contact card)
   python3 notify.py snapshot --send                   # once: counts by tier + top 3 current matches
   ```
   `scout.py --seed` writes `out/sample.json` (all current MATCHes) for the snapshot. `--sample` refreshes it without seeding.
   `notify.py firstday --send` runs every loop: one-time note after 6 PM, skipped if the snapshot or any alert went out. State: `logs/lifecycle.json`.
Household welcome: `python3 notify.py welcome "Name" --send` (member wording). Never before they have texted the line.

## Running, restart, health
- No cron/systemd on the box. `ensure_running.sh` keeps exactly one `run_loop.sh` (flock + `logs/loop.pid`; adopts a stray loop instead of starting a second).
- Restart after a reboot: add this line to `~/.bashrc` on day one (use your real folder path):
  `[ -x <folder>/ensure_running.sh ] && ( <folder>/ensure_running.sh >/dev/null 2>&1 & )`
  It calls `ensure_running.sh` whenever any agent shell opens (only starts if `PHOTON_API_KEY` is in that shell). ⚠️ After a reboot, nothing restarts until some shell opens; the weekly health check is the backstop.
- Weekly health check (bot routine, every plan): `python3 health.py --restart`. Exit 0 = say nothing. Exit 1 = tell the owner in calm style, one next step.
- Stop: `kill $(cat logs/loop.pid)`. Status: `tail logs/loop.log`, `python3 health.py`.
- Pause: `paused: true` in CRITERIA.yaml (checks continue, nothing is sent).

## Email alerts
- `fetch_inbox.py` runs at the top of every `run_loop.sh` cycle: with `AGENTMAIL_API_KEY` in the env it pulls new listing-site emails (zillow, redfin, hotpads, trulia, rent.com, apartments.com, realtor.com, zumper) from `alert_inbox` into `inbox/` (.html/.txt), reading every page (not just the newest 50). Ids: `out/fetched_ids.txt`, one per line (the same file the routine uses). Welcome/verify/code subjects are skipped only when the body shows no listing; every skip goes to `logs/email_skips.log`; it writes `out/routine_heartbeat.txt` each run. Without the key it prints "skipped" and the inbox-reader routine does the same job on the plan's schedule (Lean twice a day, Standard every 2 h, Hands-on hourly; COSTS.md).
- `scout.py` parser reads listing cards (price, beds, baths, address) from Zillow, Redfin and HotPads alert bodies, including tracked click links (click.mail.zillow.com, redmail*.redfin.com, HotPads /pad). IDs: Zillow zpid or Redfin home id when in the email, else normalized address + unit (same home on two sites = one text). A "was $X" in the email counts as a price drop. Missing fields stay "not listed yet". Tested on SYNTHETIC tracked-link fixtures in `tests/fixtures/email_tracked/` (`tests/test_email.py`); ⚠️ check the first real email of each site by hand and save a redacted copy as a fixture.
- Watch (owner only, `notify.py emailwatch`, every loop): an inbox email that parses to 0 homes (file kept in `inbox/` for review), `out/routine_heartbeat.txt` older than the plan's routine interval + 3 h (`features.email_stale_limit`: Lean 15 h, Standard 5 h, Hands-on 4 h; `inbox_pull: api` 3 h), or a site that has sent alerts going quiet for 48 h. Each told once. State: `logs/email_watch.json`.
- Delay, email landing → text: with `inbox_pull: api`, ≤ one loop (15 min Lean, 5 Standard/Hands-on); with the routine, up to the routine interval (≈12 h Lean, 2 h Standard, 1 h Hands-on) + one loop → the first new find goes out right away (≈ 25 min worst case). Finds that follow within `bundle_cooldown_min` (60) of the last text are bundled: ≈ 85 min worst case. Quiet hours / Sleep mode hold until morning; a daily cap (off by default) holds extras for the evening. Sends are tracked per person; a failed send is retried next pass for that person only.

## Reply listener (case B, co-deciders)
- `replies: true` in CRITERIA.yaml → `ensure_running.sh` starts `node listen.mjs` (one copy, `logs/listen.pid`). No AI: `replies.py` attaches natural replies to the latest listing (or a named street), marks the shortlist by keyword, and relays the words verbatim. "shortlist", "help", "pause", "resume", "OK" always work.
- It uses spectrum-ts `app.messages` (a long-lived stream; no public URL or webhook needed). There's no message history through Spectrum: texts sent while the listener is down are not replayed. ✅ Connects on Photon Free (2026-10-26). ⚠️ Receiving real inbound texts not yet tested; test with `node listen.mjs --observe` while the owner texts the line.
- Simulate without Photon: `python3 replies.py --as "Name" --text "Love the yard!"`.
- State: `out/last_numbered.json` (the places in the latest text, in order; replies attach to these), `out/shortlist.json`, `out/members.json` (joined, paused, stopped, left, sleep, sleep_offered, late_at, pending).
- Confirm-first questions are stored as `pending` on the person who must answer (`remove`, `purge`, `sleep`, `change`, `wrapup`, `wrapup_data`). A yes runs it (`do_pending` in replies.py); a no says "Okay, nothing changed." (Sleep mode: silent); anything else lets the question lapse.
- Tapbacks ("Liked …", "Loved …") are parsed by `reaction_of()` and relayed as a short note ("Sarah ❤️ Maple St"), never as typed words.

## Light filters + criteria hygiene
- `scout.is_match()`: area + beds_min + match.baths_min + match.price_max (unknowns kept) + pets not explicitly disallowed (`exclude_no_pets`). `match.garage_min` / `match.layout_any` make those hard filters again; `match.nice_to_have` lists details shown in every alert.
- `scout.py` writes `out/pool.json` (in-area listings with `misses`) each live run. `features.tradeoff()`, `near_misses()`, `suggest_change()`, `tighten_change()`, `hygiene_due()`; texts in `style.must_or_nice_q / tradeoff_text / near_miss_ask / loosen_ask / tighten_ask`.
- `notify.py hygiene --send` runs each loop: weekly at most, nothing on day one, owner only; stores the proposal as a `change` pending (Fine-tune), so only a clear yes writes CRITERIA (backup first). `checkins: false` = off.
- Channels: per-person line check (iMessage vs SMS/RCS); non-iMessage gets plain text via `notify.for_channel()`; unknown falls back to iMessage.

## Restarts, secrets, health flags
- Secrets file: `~/.config/listing-scout/env` (override with `SCOUT_ENV`), chmod 600, outside the install, never printed. `ensure_running.sh` and `run_loop.sh` source it; `run_loop.sh` calls `ensure_running.sh` each cycle so the reply listener stays up.
- `out/health_flags.json`: `photon_key_missing`, `listener_restarted` (owner told once via `notify.py outage` → "Replies paused for a moment."), `email_pull_missing` (fetch_inbox, once). `out/email_proven.json` appears when the first real alert email is parsed; until then `health.py` says "email path unproven".
- `inbox_pull: routine | api` in CRITERIA: routine = the inbox-reader routine copies alert emails on the plan's schedule; api = `AGENTMAIL_API_KEY`.
- `timezone` in CRITERIA (default America/Los_Angeles): quiet hours, Sleep mode, the 6 PM roundup and the day-4 check-in use `features.local_hour(C)`, never the box clock.
- "end my search": see skill "Ongoing care". `out/search_ended.json` has `pause_routines: true`; pause your routines when you see `PAUSE_ROUTINES`.
- New loop commands: `notify.py evening` (daily cap bundle after 6 PM; `daily_cap: 0` = off), `notify.py pulse` (quiet-week pulse, real count from the last check), `notify.py firstweek` (once, day 4+, pending `feedback_open` → Make it better, gated).
- Alerts: `scout.via_line()` ("Via Redfin"; `show_source`), `scout.posted_line()` (only with a real `posted_ts` from a parser; none of today's parsers provide one yet).

## Texting
- `photon_send.mjs send +1… file.txt --send [--card file.vcf]`. The card uses spectrum-ts `contact(vcfString)` (vCard as a file attachment). "Sent" = accepted by Photon, not delivered.
- "Target not allowed for this project" = that person hasn't texted the line yet.
- SMS fallback and Android: ⚠️ untested.

## Text style (style.py)
- All text goes through `style.text()`; `notify.py` refuses anything failing `style.check()`. Run `python3 tests/test_style.py` (no pytest needed) after any wording change.
- Colon rule: nothing after a colon on the same line, except fact labels (Pets:, Garage:, Rent:, Address:, Link:). Write headers as plain sentences ("This is a sample, not a new listing."), or end the line at the colon.
- Max 30 characters per line (`style.MAX`); rewrite shorter, never wrap. URLs, a street address directly above its link, and quoted member words are exempt.

## Extra features (commands)
- **Take a break:** STOP keywords in replies.py (instant, silent). Owner "remove {first}" → `pending: remove` → on yes `features.purge_member()`.
- **Sleep mode:** `members.json` `sleep: true`. `notify.py alerts` holds that person's finds during `quiet_hours` (default 22→7) in `outbox.json` `held`; `notify.py morning --send` (run by the loop every pass) sends them as one bundle after wake time and, once, offers Sleep mode to anyone who got an alert during quiet hours (`late_at`).
- **Still available?:** `scout.py` sets `gone_since`; `notify.py gone --send` (loop) texts owner + co-deciders once (`gone_told`) for shortlisted places gone ≥24h (`features.gone_liked`). Wording: "It's no longer listed." `style.check()` rejects "rented".
- **One home, one text:** `scout.cross_source()` runs before a new id alerts: same normalized address (`addr_key`) still listed → attach silently (`dup_of`, `also_ids`), or a price-drop alert if lower. No address → alerts as new.
- **Fine-tune the search:** `features.parse_change()` (zip add/remove, target/stretch, beds_min; unclear → ask). On the owner's yes: `features.apply_change()` backs up to `out/CRITERIA.backup-*.yaml`, edits the line in place (comments kept), then `scout.py --seed` runs quietly.
- **We found it:** owner yes → `wrapped_up` to all, `out/search_ended.json` (run_loop.sh exits, ensure_running.sh starts nothing, notify.py sends nothing) → `wrapup_data` question. Yes → `features.purge_all(everything=True)` and prints `CLOSE_SAVED_SEARCHES` (the bot closes the Zillow/Redfin/HotPads saved searches by hand). Either answer prints `LISTENER_STOP`, and listen.mjs exits. To restart a search, delete `out/search_ended.json`.
- **Your data stays put:** `features.purge_all()` on "delete everything" (owner, confirm-first). `features.prune_logs()` (loop, every pass) deletes files in `logs/` older than 30 days (never `.pid`, `.lock` or `lifecycle.json`).
- Tests: `python3 tests/test_features.py`.
