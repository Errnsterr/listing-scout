# Listing Scout template 1.1.0: what ships
Generic only. Skill name: `listing-scout`. `drafts/`, `__pycache__/` and `*.pyc` are internal and do not ship (see `.gitignore` / `.exportignore`). No owner criteria, Project ID, phone numbers, listing history, logs, contact cards or secrets.

| File | What it is |
|---|---|
| `skill/SKILL.md` | The setup and care skill the installing bot follows (case A: own search, 8 steps; case B: sharing a search) |
| `CRITERIA.example.yaml` | Blank criteria to copy to `CRITERIA.yaml` |
| `SETUP.md` | Owner-facing guide (email alerts, steps, household, text style) |
| `SETUP_SCRIPT.md` | Longer bot wording notes (SKILL.md is the source of truth) |
| `PHOTON_FAQ.md` | Photon questions, with "for the bot" notes |
| `COSTS.md` | Plain-words costs and plan modes |
| `BOT_NOTES.md` | Every command and technical detail (bot only) |
| `README.md` | Start here: what it is, limits, links |
| `SAMPLE_MESSAGE.txt` | Every text, rentals and buying (experimental), rendered for a made-up Los Angeles household |
| `CHANGELOG.md` | What changed in each version |
| `FOR_YOU.md`, `FOR_YOUR_BOT.md` | One-page human steps (plain language); the bot's map of the internals |
| `VERSION` | 1.1.0. Update = `git pull` or download the new release archive, and keep `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/`, `out/` |
| `LICENSE` | MIT. Copyright errnsterr |
| `style.py` | The one text formatter and style check |
| `scout.py` | Checks property-manager pages and alert emails, matches, dedupes, renders alerts and the snapshot |
| `notify.py` | Sends through Photon (check, welcome, snapshot, alerts, first-day note, add_user, morning, gone) |
| `DISCLAIMER.md`, `PRIVACY.md`, `PUBLISH_CHECKLIST.md` | Disclaimer (not an agent or legal advice; verify in person; opt-in texting; fair housing), what's stored and how to delete it, and the pre-publish checklist |
| `fetch_inbox.py` | (inbox_pull: api) Pulls Zillow/Redfin/HotPads alert emails from the AgentMail alerts inbox into `inbox/` each loop cycle (needs `AGENTMAIL_API_KEY`; dedupes; skips verify/welcome/code emails; sends nothing) |
| `features.py` | Extra features with no sending: Fine-tune the search (parse + safe CRITERIA write), Your data stays put (purge, 30-day logs), Sleep mode hours, Still available?, Make it better (is_feedback, feedback_payload, record_feedback, feedback_items; pending_review gate), Criteria hygiene (tradeoff, near_misses, suggest_change, tighten_change, hygiene_due) |
| `photon_send.mjs` | Photon delivery (spectrum-ts), text plus optional contact card |
| `listen.mjs`, `replies.py` | Reply listener and co-decider replies (relay, shortlist, mutual yes, pause, Take a break, Sleep mode, Fine-tune, We found it, data requests) |
| `review_feedback.py` | Make it better review: lists pending_review feedback; `--approve`/`--decline` only mark items; `--fixed` prints a draft "You asked, it's fixed" text (never sent). Nothing is auto-queued or built. |
| `make_contact.py`, `assets/avatar.png` | Contact card with a house photo |
| `make_invite.py` | Household invite kit: intro text + plain, link-free invite the owner forwards (internal `sms:` fallback, never texted) |
| `run_loop.sh`, `ensure_running.sh`, `health.py` | Watcher loop (exactly one), restart, weekly health check |
| `package.json`, `package-lock.json` | Run `npm install` (Node 20+) to get spectrum-ts |
| `tests/test_style.py`, `tests/test_edges.py`, `tests/test_features.py`, `tests/test_email.py` | Style, edge-case, 1.1.0 feature and email-flow tests: `python3 tests/test_style.py`, `python3 tests/test_edges.py`, `python3 tests/test_features.py`, `python3 tests/test_email.py` (made-up fixtures, no network, nothing sent) |
| `tests/test_actions.py`, `tests/fixtures/email_actions/` | Apply/agent link parsing, cleaning, rendering, and the never-follows check (synthetic fixtures) |
| `tests/render_all.py` | Renders every text into a temp folder (sends nothing; buy mode (experimental) renders with `RENDER_CRITERIA=tests/fixtures/CRITERIA.buy.test.yaml`). Copy the output to `SAMPLE_MESSAGE.txt` by hand |
| `tests/render_journey.py` | Owner vs member journey, beat by beat → `out/journey-compare.md` |
| `tests/fixtures/` | `CRITERIA.test.yaml`, `sample_alerts.test.json`, `email/zillow_alert.eml`, `email_tracked/` (Zillow, Redfin, HotPads tracked-link alerts + a no-listing email; all made-up) |
| `inbox/`, `out/`, `logs/` | Empty working folders |

Not shipped (owner-only): `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/*`, `out/*` (cards, alerts, shortlist), `node_modules/`, live sample alerts.
