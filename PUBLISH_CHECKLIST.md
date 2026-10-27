# Before you publish Listing Scout

- [ ] **Disclaimer:** `DISCLAIMER.md` is included and linked in SETUP. Optional one-line disclaimer in the welcome text (see options below).
- [ ] **Consent:** people text the bot first (opt-in). STOP works instantly with no reply. No cold texting: invites are forwarded by someone they know.
- [ ] **Site terms, per source:**
  - Zillow, Redfin, HotPads: saved-search email alerts to the bot's inbox only; no scraping of their pages.
  - Property-manager pages (AppFolio, TenantTurner): public listing pages, checked gently (one request per source per cycle).
  - Craigslist, Realtor.com, Zumper, Rent.com: email alerts only.
  - Facebook Marketplace and groups: by hand only; the bot never logs in.
  - Each template owner re-checks the terms of the sites they turn on.
- [ ] **Fair housing:** filters cover home features only. No filters or wording about who lives there. Review any new filter before adding it.
- [ ] **Cost:** Photon's public pricing (photon.codes/pricing, checked Oct 26, 2026): Free $0 (up to 10 users, RCS/SMS fallback included), Pro $25/mo (up to 100 users), Business $250/line/mo, Enterprise custom. Prices change; link to Photon's pricing page rather than copying numbers. Grok Bot AI use varies (see COSTS.md).
- [ ] **Privacy:** `PRIVACY.md` included. No hosted pages. Numbers masked in logs. Secrets only via env or vault.
- [ ] **Misuse safeguards:** confirm-first for every change; STOP first; delete-all needs a word yes; no landlord contact, tours or applications; scam flags on; never invents data; up to 10 people on Photon Free.
- [ ] **Support and updates:** say how people report issues ("Make it better", owner-reviewed, nothing auto-queued), where updates come from (VERSION, BOT_NOTES "Update / version"), and how fast you respond.
- [ ] **License:** suggest **MIT** for the code (simple, permissive). Note: MIT covers the code only. Listing data, site content and Photon's service have their own terms, and the disclaimer still applies.
- [ ] **Clean install:** no personal names, numbers or emails in template files; `feedback_email` blank; no `__pycache__`; tests and render_all pass.
- [ ] **Legal review:** if publishing commercially, have a lawyer review DISCLAIMER.md and PRIVACY.md.

## Welcome lines (installed)
- ✅ "Always see a place first." is in every welcome; member welcomes add "Text STOP anytime to stop."

## Publish decisions (made Oct 26, 2026)
- [x] Support: best effort, no guarantees. "Make it better" feedback reaches the builder only after a clear yes; nothing is built automatically.
- [x] 18+: stated in README and DISCLAIMER (docs only; the welcome text is already at its length limit).
- [x] US only: stated in README, DISCLAIMER, SETUP and the profile description.
- [x] Updates: CHANGELOG.md next to VERSION, linked from README.
- [x] One skill ships: `listing-scout` (skill/SKILL.md).
- [x] Buying released in v1.1.0 as **experimental** (Oct 26, 2026), by the owner's choice, before the 3-day shadow proof finished. Buy welcomes include "Not an agent or advice."

## Other welcome lines considered (30 characters or fewer)
- "I'm a helper, not an agent." (27)
- "Always see a place first." (25)
- "Listings can change fast." (25)
- "Check details before paying." (28)
