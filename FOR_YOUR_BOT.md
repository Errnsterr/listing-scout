# Listing Scout: for your bot

The owner reads `FOR_YOU.md` only. Everything technical lives here and in the files below. Never ask the owner to edit files, run commands or read these docs.

## Get the code
Clone the repo into the working folder, or download the release archive and unpack it:

```bash
git clone https://github.com/Errnsterr/listing-scout
cd listing-scout
```

Release archive: https://github.com/Errnsterr/listing-scout/archive/refs/tags/v1.1.0.tar.gz

Then copy `CRITERIA.example.yaml` to `CRITERIA.yaml`. Install dependencies: Node 20 or newer, `npm install`, and Python 3 with pyyaml, bs4 and Pillow (`python3 -m pip install pyyaml beautifulsoup4 Pillow`). Later commands are in `BOT_NOTES.md`. To update an existing install, `git pull` (or download the new release archive) and keep `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/` and `out/`.

| Need | Read |
|---|---|
| The setup and care playbook (8 steps, rules, ongoing care, "end my search") | `skill/SKILL.md` |
| Full setup reference: email alerts, sign-up fallback, shadow mode, edge cases | `SETUP.md` |
| Exact chat wording per step | `SETUP_SCRIPT.md` |
| Running, restart, health, email pull, loop commands | `BOT_NOTES.md` |
| Photon sign-up, secret, Users, first text, errors | `PHOTON_FAQ.md` |
| Plans, AI usage, routine schedules | `COSTS.md` |
| Search settings (incl. `timezone`, `plan_mode`, `inbox_pull`, `shadow`) | `CRITERIA.example.yaml` |
| What ships, what's kept | `MANIFEST.md`, `PRIVACY.md`, `DISCLAIMER.md` |

Key internals:
- `mode: lease` is the default. `mode: buy` is **experimental**: start in `shadow: true` for a day, and say "Buying is still new." / "Tell me if anything looks off." See skill "Buy mode".
- `timezone` (default the owner's known zone, else America/Los_Angeles) drives quiet hours, Sleep mode, the 6 PM roundup and the day-4 check-in (`features.local_hour`).
- The "email sync stalled" note waits for the plan's routine interval + 3 h (`features.email_stale_limit`).
- "end my search": word-yes confirm, goodbye to all, `out/search_ended.json` stops the loop and listener; on `PAUSE_ROUTINES`, pause your own routines; then offer deletion, closing site searches, and the Photon Users reminder.
- Every text goes through `style.py`; never write a text by hand.
- Tests: `python3 -B tests/test_*.py`, `tests/render_all.py` (both modes). Shadow mode: `shadow: true` logs to `out/shadow_texts.jsonl` and sends nothing.
