# Listing Scout: for your bot

The owner reads `FOR_YOU.md` only. Everything technical lives here and in the files below. Never ask the owner to edit files, run commands or read these docs.

What it does: alerts for new places that fit, decide together, and **Apply for me** (v1.2.0): a member texts "apply", the bot fills the listing's own apply page from the profile and vault, stops at review, and submits or pays only after that member's yes for that listing. It never emails, calls or messages landlords. Details: "Apply for me" below and `docs/routines/apply-watch.md`.

## Get the code

Clone the repo into the working folder, or download the release archive and unpack it:

```bash
git clone https://github.com/Errnsterr/listing-scout
cd listing-scout
```

Release archive: https://github.com/Errnsterr/listing-scout/archive/refs/tags/v1.2.7.tar.gz

Then copy `CRITERIA.example.yaml` to `CRITERIA.yaml`. Install dependencies: Node 20 or newer, `npm install`, and Python 3 with pyyaml, bs4 and Pillow (`python3 -m pip install pyyaml beautifulsoup4 Pillow`). Commands are in this file, under "Commands and technical detail".

To update an existing install, `git pull` (or download the new release archive) and keep `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/` and `out/`.

| Need | Read |
|---|---|
| The setup and care playbook (getting started: rent or buy, 4 questions, current matches, texts and listing-site alerts, finer details, chat-only reminders; rules, ongoing care, "end my search") | `docs/skill/SKILL.md` |
| Full setup reference, including the setup conversation script | `docs/SETUP.md` |
| Running, restart, health, email pull, loop commands | This file, "Commands and technical detail" |
| Photon sign-up, secret, Users, first text, errors | `docs/PHOTON_FAQ.md` |
| Plans, AI usage, routine schedules | `docs/COSTS.md` |
| Search settings (incl. `timezone`, `plan_mode`, `loop_minutes`, `bundle_cooldown_min`, `inbox_pull`, `shadow`) | `CRITERIA.example.yaml` |
| What's stored, and the disclaimer | `docs/PRIVACY.md`, `docs/DISCLAIMER.md` |
| What ships | "What ships" below |

Key internals:

- `mode: lease` is the default. `mode: buy` is **experimental**: start in `shadow: true` for a day, and say "Buying is still new." / "Tell me if anything looks off." See skill "Buy mode".
- `timezone` (default the owner's known zone, else America/Los_Angeles) drives quiet hours, Sleep mode, the 6 PM roundup and the day-4 check-in (`features.local_hour`).
- The "email sync stalled" note waits for the plan's routine interval + 3 h (`features.email_stale_limit`).
- "end my search": word-yes confirm, goodbye to all, `out/search_ended.json` stops the loop and listener; on `PAUSE_ROUTINES`, pause your own routines; then offer deletion, closing site searches, and the Photon Users reminder.
- Every text goes through `src/style.py`; never write a text by hand.
- Tests: `python3 -B tests/test_*.py`, `python3 tests/render_all.py` (both modes). Shadow mode: `shadow: true` logs to `out/shadow_texts.jsonl` and sends nothing.


**v1.2.7 behavior (alerts):**
- Rentals are instant: each fitting place is its own single alert (range words, pets, "Via ___"), even when several come in one email. A failed send is retried for that place and person only.
- Card IDs and links in text-only alert emails come from that card's own lines; the next card's photo link is never borrowed (`scout._parse_text_cards`).
- Held buildings (`held_review`, e.g. a "From $X, 0-3 bed" building listing) stay held, but they never block a specific unit with its own price and beds. That unit is a separate listing and alerts normally.
- "Another unit at <Building>": a new place in a building texted before (same street number and street, or same building name or Zillow/Redfin building slug) gets this line. Sent places are saved in `out/texted.json`; state records keep `bldg` and `bkeys`, even Redfin records with no street.
- ZIP backfill: a missing ZIP comes from a saved record at the same street address or building (one ZIP only, never guessed). Places still without one are logged once in `logs/zip_missing.log` and matched by city as before.
- Wrong link sent: `python3 src/notify.py correct ID --send` texts everyone "Fix for <street>" with the saved right link, once per place (`out/corrections.json`). Fix the saved link in `out/last_numbered.json` first.

## What ships

Generic only. Skill name: `listing-scout`. `drafts/`, `__pycache__/` and `*.pyc` are internal and do not ship (see `.gitignore` / `.exportignore`). No owner criteria, Project ID, phone numbers, listing history, logs, contact cards or secrets.

| File | What it is |
|---|---|
| `docs/skill/SKILL.md` | The setup and care skill the installing bot follows (getting started flow; case A: texting setup, 8 steps; case B: sharing a search) |
| `CRITERIA.example.yaml` | Blank criteria to copy to `CRITERIA.yaml` |
| `docs/SETUP.md` | Owner-facing guide (email alerts, steps, household, text style) plus the setup conversation script. `docs/skill/SKILL.md` is the source of truth for the flow |
| `docs/PHOTON_FAQ.md` | Photon questions, with "for the bot" notes |
| `docs/COSTS.md` | Plain-words costs and plan modes |
| `FOR_YOUR_BOT.md` | This file: the bot's map, every command, and what ships |
| `README.md` | Start here: what it is, limits, links |
| `docs/SAMPLE_MESSAGE.txt` | Every text, rentals and buying (experimental), rendered for a made-up Los Angeles household |
| `docs/CHANGELOG.md` | What changed in each version |
| `FOR_YOU.md` | One-page human steps (plain language) |
| `VERSION` | 1.2.7. Update = `git pull` or download the new release archive, and keep `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/`, `out/` |
| `LICENSE` | MIT. Copyright errnsterr |
| `src/style.py` | The one text formatter and style check |
| `src/scout.py` | Checks property-manager pages and alert emails, matches, dedupes, renders alerts and the snapshot |
| `src/notify.py` | Sends through Photon (check, welcome, snapshot, alerts, first-day note, add_user, morning, gone) |
| `docs/DISCLAIMER.md`, `docs/PRIVACY.md` | Disclaimer (not an agent or legal advice; verify in person; opt-in texting; fair housing), and what's stored and how to delete it |
| `src/fetch_inbox.py` | (inbox_pull: api) Pulls Zillow/Redfin/HotPads alert emails from the AgentMail alerts inbox into `inbox/` each loop cycle (needs `AGENTMAIL_API_KEY`; dedupes; skips verify/welcome/code emails; sends nothing) |
| `src/features.py` | Extra features with no sending: Fine-tune the search (parse + safe CRITERIA write), Your data stays put (purge, 30-day logs), Sleep mode hours, Still available?, Make it better (is_feedback, feedback_payload, record_feedback, feedback_items; pending_review gate), Criteria hygiene (tradeoff, near_misses, suggest_change, tighten_change, hygiene_due) |
| `src/photon_send.mjs` | Photon delivery (spectrum-ts), text plus optional contact card |
| `src/listen.mjs`, `src/replies.py` | Reply listener and co-decider replies (relay, shortlist, mutual yes, pause, Take a break, Sleep mode, Fine-tune, We found it, data requests) |
| `src/review_feedback.py` | Make it better review: lists pending_review feedback; `--approve`/`--decline` only mark items; `--fixed` prints a draft "You asked, it's fixed" text (never sent). Nothing is auto-queued or built. |
| `src/make_contact.py`, `src/assets/avatar.png` | Contact card with a house photo |
| `src/make_invite.py` | Household invite kit: intro text + plain, link-free invite the owner forwards (internal `sms:` fallback, never texted) |
| `src/run_loop.sh`, `src/ensure_running.sh`, `src/health.py` | Watcher loop (exactly one), restart, weekly health check |
| `package.json`, `package-lock.json` | Run `npm install` (Node 20+) to get spectrum-ts |
| `tests/test_style.py`, `tests/test_edges.py`, `tests/test_features.py`, `tests/test_email.py` | Style, edge-case, 1.1.0 feature and email-flow tests: `python3 tests/test_style.py`, `python3 tests/test_edges.py`, `python3 tests/test_features.py`, `python3 tests/test_email.py` (made-up fixtures, no network, nothing sent) |
| `src/apply.py`, `tests/test_apply.py`, `docs/routines/apply-watch.md` | Apply for me: gate (scam, fair housing, host match, freshness) and the hand-off plan; no SPI ever stored |
| `tests/test_actions.py`, `tests/fixtures/email_actions/` | Apply/agent link parsing, cleaning, rendering, and the never-follows check (synthetic fixtures) |
| `tests/render_all.py` | Renders every text into a temp folder (sends nothing; buy mode (experimental) renders with `RENDER_CRITERIA=tests/fixtures/CRITERIA.buy.test.yaml`). Copy the output to `docs/SAMPLE_MESSAGE.txt` by hand |
| `tests/render_journey.py` | Owner vs member journey, beat by beat → `out/journey-compare.md` |
| `tests/fixtures/` | `CRITERIA.test.yaml`, `sample_alerts.test.json`, `email/zillow_alert.eml`, `email_tracked/` (Zillow, Redfin, HotPads tracked-link alerts + a no-listing email; all made-up) |
| `inbox/`, `out/`, `logs/` | Working folders. `inbox/.keep` is in git so the inbox directory exists; the loop creates `out/` and `logs/` |

Not shipped (owner-only): `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/*`, `out/*` (cards, alerts, shortlist), `node_modules/`, live sample alerts.

---

## Commands and technical detail (template 1.2.7)

User-facing docs (`docs/SETUP.md`, `docs/PHOTON_FAQ.md`, `docs/COSTS.md`) stay plain. Every command and technical detail lives here.

Never print phone numbers (last 4 only) or `PHOTON_API_KEY`. Nothing is texted without the owner's okay.

### Update / version

- `VERSION` holds the template version. To update: `git pull` in this folder (or download the new release archive), keeping `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/`, `out/`. Then run `python3 tests/test_style.py` and `./src/ensure_running.sh`.

### Requirements

Node 20+, `npm install` in this folder (spectrum-ts), Python 3 with pyyaml, bs4, Pillow (avatar only).

Env: `PHOTON_API_KEY` (Project secret, from the secure form). Project ID: `photon.project_id` in CRITERIA.yaml or `PHOTON_PROJECT_ID`.

### Setup step → command

3. `python3 src/notify.py check` (sends nothing; shows project, plan, reachability).
4. Household add: `NEW_USER_PHONE=… python3 src/notify.py add_user "Name" --confirm` (number only from env via secure form), then add `name / channel / phone_last4` to `recipients`. First recipient is the owner (or set `role: owner`).
5. `python3 src/make_contact.py Name` → `out/Listing-Scout-<Name>.vcf` (with `src/assets/avatar.png` house photo). Share in chat; the bot can't text before step 6.
7. `python3 src/scout.py --all --dry-run` → pick a real MATCH for the sample.
8. Install (after approval):

   ```bash
   cd <this folder> && python3 src/scout.py --seed && python3 src/notify.py seeded && ./src/ensure_running.sh
   python3 src/notify.py welcome "Owner" --card --send     # owner welcome = test (+ contact card)
   python3 src/notify.py snapshot --send                   # once: counts by tier + every current match
   ```

`src/scout.py --seed` writes `out/sample.json` (all current MATCHes) for the snapshot. `--sample` refreshes it without seeding.

`src/notify.py firstday --send` runs every loop: one-time note after 6 PM, skipped if the snapshot or any alert went out. State: `logs/lifecycle.json`.

Household welcome: `python3 src/notify.py welcome "Name" --send` (member wording). Never before they have texted the line.

### Running, restart, health

- No cron/systemd on the box. `src/ensure_running.sh` keeps exactly one `src/run_loop.sh` (flock + `logs/loop.pid`; adopts a stray loop instead of starting a second).
- Restart after a reboot: add this line to `~/.bashrc` on day one (use your real folder path): `[ -x <folder>/src/ensure_running.sh ] && ( <folder>/src/ensure_running.sh >/dev/null 2>&1 & )` It calls `src/ensure_running.sh` whenever any agent shell opens (only starts if `PHOTON_API_KEY` is in that shell). Unverified: After a reboot, nothing restarts until some shell opens; the weekly health check is the backstop.
- Weekly health check (bot routine, every plan): `python3 src/health.py --restart`. Exit 0 = say nothing. Exit 1 = tell the owner in calm style, one next step. `--quiet` prints nothing on exit 0, so `python3 src/health.py --restart --quiet` can run every 10 minutes. It also flags texts failing for 30+ minutes (`send_failing` in `out/health_flags.json`, from `logs/sends.jsonl`) and alert emails that may be cut off (`out/email_cutoff.json`).
- Stop: `kill $(cat logs/loop.pid)`. Status: `tail logs/loop.log`, `python3 src/health.py`.
- Pause: `paused: true` in CRITERIA.yaml (checks continue, nothing is sent).

### Email alerts

- `src/fetch_inbox.py` runs at the top of every `src/run_loop.sh` cycle: with `AGENTMAIL_API_KEY` in the env it pulls new listing-site emails (zillow, redfin, hotpads, trulia, rent.com, apartments.com, realtor.com, zumper) from `alert_inbox` into `inbox/` (.html/.txt), reading every page (not just the newest 50). Ids: `out/fetched_ids.txt`, one per line (the same file the routine uses). Welcome/verify/code subjects are skipped only when the body shows no listing; every skip goes to `logs/email_skips.log`; it writes `out/routine_heartbeat.txt` each run.

  Without the key it prints "skipped" and the inbox-reader routine does the same job on the plan's schedule (Lean twice a day, Standard every 2 h, Hands-on hourly; docs/COSTS.md).

- `src/scout.py` parser reads listing cards (price, beds, baths, address) from Zillow, Redfin and HotPads alert bodies, including tracked click links (click.mail.zillow.com, redmail*.redfin.com, HotPads /pad). An opaque Redfin/Zillow tracker is resolved once by following its redirects (`resolve_tracker`: HEAD, then GET; 6 s timeout; no cookies). Only a www.redfin.com `/home/` or `/apartment/` page or a www.zillow.com `homedetails` page is kept, with no query string. Results are cached in `out/link_cache.json` under a hash (a miss is retried after 6 h), and the tracker itself is never stored or texted. A building-name address takes its street (and unit) from that clean URL's slug (`slug_street`). Street numbers like `417 1/2` and `301-307` are read whole, and a number inside a name ("Eight 80 Newport Beach") is never taken as a street number. IDs: Zillow zpid or Redfin home id when in the email, else normalized address + unit (same home on two sites = one text). A "was $X" in the email counts as a price drop.

  Missing fields stay "not listed yet". Tested on SYNTHETIC tracked-link fixtures in `tests/fixtures/email_tracked/` (`tests/test_email.py`); Unverified: check the first real email of each site by hand and save a redacted copy as a fixture.

- Watch (owner only, `src/notify.py emailwatch`, every loop): an inbox email that parses to 0 homes (file kept in `inbox/` for review), `out/routine_heartbeat.txt` older than the plan's routine interval + 3 h (`features.email_stale_limit`: Lean 15 h, Standard 5 h, Hands-on 4 h; `inbox_pull: api` 3 h), or a site that has sent alerts going quiet for 48 h. Each told once. State: `logs/email_watch.json`.
- Delay, email landing → text: with `inbox_pull: api`, ≤ one loop (`loop_minutes`, default 5); with the routine, up to the routine interval (≈12 h Lean, 2 h Standard, 1 h Hands-on) + one loop → every new find is texted on the pass that finds it (`bundle_cooldown_min: 0`, the default; several on one pass go as one numbered text). Set `bundle_cooldown_min: N` to hold later finds for N minutes after a text and send them together. Quiet hours / Sleep mode hold until morning; a daily cap (off by default) holds extras for the evening.

  Sends are tracked per person; a failed send is retried next pass for that person only.

### Reply listener (case B, co-deciders)

- `replies: true` in CRITERIA.yaml → `src/ensure_running.sh` starts `node src/listen.mjs` (one copy, `logs/listen.pid`). No AI: `src/replies.py` attaches natural replies to the latest listing (or a named street), marks the shortlist by keyword, and relays the words verbatim. "shortlist", "help", "pause", "resume", "OK" always work.
- It uses spectrum-ts `app.messages` (a long-lived stream; no public URL or webhook needed). There's no message history through Spectrum: texts sent while the listener is down are not replayed. (confirmed) Connects on Photon Free (2026-10-26).

  Unverified: Receiving real inbound texts not yet tested; test with `node src/listen.mjs --observe` while the owner texts the line.

- Simulate without Photon: `python3 src/replies.py --as "Name" --text "Love the yard!"`.
- State: `out/last_numbered.json` (the places in the latest text, in order; replies attach to these), `out/shortlist.json`, `out/members.json` (joined, paused, stopped, left, sleep, sleep_offered, late_at, pending).
- Confirm-first questions are stored as `pending` on the person who must answer (`remove`, `purge`, `sleep`, `change`, `wrapup`, `wrapup_data`). A yes runs it (`do_pending` in src/replies.py); a no says "Okay, nothing changed." (Sleep mode: silent); anything else lets the question lapse.
- Tapbacks ("Liked …", "Loved …") are parsed by `reaction_of()` and relayed as a short note ("Sarah loved Maple St"), never as typed words.

### Light filters + criteria hygiene

- `scout.is_match()`: area + beds_min + match.baths_min + match.price_max (unknowns kept) + pets not explicitly disallowed (`exclude_no_pets`). Beds pass if the top of any stated range (`beds_range`, HotPads `beds_max`) reaches beds_min. A HotPads "from $X" / "$X+" card sets `price_from` (rendered "From $X/mo", no tier line) and passes when $X is within price_max. A state record with `held_review: true` is never alerted (owner decides). `match.garage_min` / `match.layout_any` make those hard filters again; `match.nice_to_have` lists details shown in every alert.
- `src/scout.py` writes `out/pool.json` (in-area listings with `misses`) each live run. `features.tradeoff()`, `near_misses()`, `suggest_change()`, `tighten_change()`, `hygiene_due()`; texts in `style.must_or_nice_q / tradeoff_text / near_miss_ask / loosen_ask / tighten_ask`.
- `src/notify.py hygiene --send` runs each loop: weekly at most, nothing on day one, owner only; stores the proposal as a `change` pending (Fine-tune), so only a clear yes writes CRITERIA (backup first). `checkins: false` = off.
- Channels: per-person line check (iMessage vs SMS/RCS); non-iMessage gets plain text via `notify.for_channel()`; unknown falls back to iMessage.

### Restarts, secrets, health flags

- Secrets file: `~/.config/listing-scout/env` (override with `SCOUT_ENV`), chmod 600, outside the install, never printed. `src/ensure_running.sh` and `src/run_loop.sh` source it; `src/run_loop.sh` calls `src/ensure_running.sh` each cycle so the reply listener stays up.
- `out/health_flags.json`: `photon_key_missing`, `listener_restarted` (owner told once via `src/notify.py outage` → "Replies paused for a moment."), `email_pull_missing` (fetch_inbox, once). `out/email_proven.json` appears when the first real alert email is parsed; until then `src/health.py` says "email path unproven".
- `inbox_pull: routine | api` in CRITERIA: routine = the inbox-reader routine copies alert emails on the plan's schedule; api = `AGENTMAIL_API_KEY`. The routine must read each email with `body_max_chars: 50000` (the default 4,000 cuts long Redfin emails). `src/scout.py` logs any email whose body ends "[body truncated" or whose subject-line price matches no parsed place to `logs/email_cutoff.log` and `out/email_cutoff.json`; re-read those in full.
- HotPads cards with a street but no house number keep it as `street_only`; texts show "Royan Ln (no number listed)" (roundups put "(no number listed)" on its own line when the entry would pass 30 characters).
- `timezone` in CRITERIA (default America/Los_Angeles): quiet hours, Sleep mode, the 6 PM roundup and the day-4 check-in use `features.local_hour(C)`, never the box clock.
- "end my search": see skill "Ongoing care". `out/search_ended.json` has `pause_routines: true`; pause your routines when you see `PAUSE_ROUTINES`.
- New loop commands: `src/notify.py evening` (daily cap bundle after 6 PM; `daily_cap: 0` = off), `src/notify.py pulse` (quiet-week pulse, real count from the last check), `src/notify.py firstweek` (once, day 4+, pending `feedback_open` → Make it better, gated).
- Alerts: `scout.via_line()` ("Via Redfin"; `show_source`), `scout.posted_line()` (only with a real `posted_ts` from a parser; none of today's parsers provide one yet).

### Texting

- `node src/photon_send.mjs send +1… file.txt --send [--card file.vcf]`. The card uses spectrum-ts `contact(vcfString)` (vCard as a file attachment). "Sent" = accepted by Photon, not delivered.
- "Target not allowed for this project" = that person hasn't texted the line yet.
- SMS fallback and Android: unverified.

### Text style (src/style.py)

- All text goes through `style.text()`; `src/notify.py` refuses anything failing `style.check()`. Run `python3 tests/test_style.py` (no pytest needed) after any wording change.
- Colon rule: nothing after a colon on the same line, except fact labels (Pets:, Garage:, Rent:, Address:, Link:). Write headers as plain sentences ("This is a sample, not a new listing."), or end the line at the colon.
- Max 30 characters per line (`style.MAX`); rewrite shorter, never wrap. URLs, a street address directly above its link, and quoted member words are exempt.

### Extra features (commands)

- **Take a break:** STOP keywords in src/replies.py (instant, silent). Owner "remove {first}" → `pending: remove` → on yes `features.purge_member()`.
- **Sleep mode:** `members.json` `sleep: true`. `src/notify.py alerts` holds that person's finds during `quiet_hours` (default 22→7) in `outbox.json` `held`; `src/notify.py morning --send` (run by the loop every pass) sends them as one bundle after wake time and, once, offers Sleep mode to anyone who got an alert during quiet hours (`late_at`).
- **Still available?:** `src/scout.py` sets `gone_since`; `src/notify.py gone --send` (loop) texts owner + co-deciders once (`gone_told`) for shortlisted places gone ≥24h (`features.gone_liked`). Wording: "It's no longer listed." `style.check()` rejects "rented".
- **One home, one text:** `scout.cross_source()` runs before a new id alerts: same normalized address (`addr_key`: house number + street name without directional or suffix + unit; `same_place()` also needs the ZIP to agree, or the city when a ZIP is missing, and conflicting directionals never match; two ids from one manager feed never merge; listing ids still use `addr_id_key`, unchanged) still listed → attach silently (`dup_of`, `also_ids`), or a price-drop alert if lower. No address → alerts as new.
- **Fine-tune the search:** `features.parse_change()` (zip add/remove, target/stretch, beds_min; unclear → ask). On the owner's yes: `features.apply_change()` backs up to `out/CRITERIA.backup-*.yaml`, edits the line in place (comments kept), then `src/scout.py --seed` runs quietly.
- **We found it:** owner yes → `wrapped_up` to all, `out/search_ended.json` (src/run_loop.sh exits, src/ensure_running.sh starts nothing, src/notify.py sends nothing) → `wrapup_data` question. Yes → `features.purge_all(everything=True)` and prints `CLOSE_SAVED_SEARCHES` (the bot closes the Zillow/Redfin/HotPads saved searches by hand). Either answer prints `LISTENER_STOP`, and src/listen.mjs exits.

  To restart a search, delete `out/search_ended.json`.

- **Your data stays put:** `features.purge_all()` on "delete everything" (owner, confirm-first). `features.prune_logs()` (loop, every pass) deletes files in `logs/` older than 30 days (never `.pid`, `.lock` or `lifecycle.json`).
- Tests: `python3 tests/test_features.py`.

### Apply for me (v1.2.0)

- **Profile (once per person):** ask the non-sensitive fields in `apply.PROFILE_FIELDS` in chat, then `apply.save_profile(name, fields)` → `~/.config/listing-scout/apply_profile.json` (chmod 600; anything outside the list, or SSN-shaped, is dropped/refused). Never print it in full, never text it. Check with `python3 src/apply.py profile --check NAME` (field names only).
- **Never stored anywhere:** SSN, date of birth, driver's license number, bank numbers, ID or pay stub files. Ask for SSN/DOB with a use-once Secure Form per application; ID/pay stubs as a chat attachment; fill with browser secure-fill.
- **Trigger:** `src/replies.py` matches "apply", "apply 2", "apply for it", "apply #1" (owner/co-decider only). No profile → `style.apply_need_profile()`. Unclear place → `style.apply_no_place()`.

  Otherwise it appends to `out/apply_requests.json`, prints `APPLY_REQUEST {id, member, where}` and texts `style.apply_ack()`. Only that member's profile is used; nobody else is texted.

- **Gate + plan:** `python3 src/apply.py plan <id>` → `out/apply_plans/<id>.json`. `stop_and_ask_owner` if: scam flags or scam-list wording, payment up front / wire / gift card, `NO_RELAY` fair-housing wording, no apply link, non-https, apply host ≠ listing domain (known platforms in `apply.PLATFORMS` allowed), or alert older than 72 h. Then stop and ask in chat; never fill.
- **Execute (bot, in its browser):** open only `apply_url`; fill from profile + vault (`from_profile`, `from_vault`); owner handles `owner_provides` (SSN, DOB, ID/pay stub uploads, ID selfie, credit consent, e-signature, phone codes, captchas). Stop at review, show the member what was filled (mask SSN) and the fee. Submit / pay with a vault card only after an explicit yes for that application.

  Never email, call or message landlords or agents. Never auto-submit.

- **Wake-up routine:** "Listing Scout: apply requests", every 5 minutes, prompt in `docs/routines/apply-watch.md`. Create it at go-live with the owner's okay. It runs `python3 src/apply.py pending --send` (prints `none` when idle: stay silent), then `apply.py plan <id>` for each new request, messages the member in the Grok Bot app, Statuses: `new` → `waiting` (set by `plan`) → `in_progress` (`mark` on the member's yes) → `handled` / `declined`.

  The routine acts only on `new`. `new`/`waiting` requests older than 24 h expire (never `in_progress`) on the next run; only that member gets `style.apply_expired()`.
