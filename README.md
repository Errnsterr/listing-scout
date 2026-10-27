# Listing Scout

Calm rental alerts by text, for you and anyone deciding with you. Home buying is experimental.

Built by [@errnsterr](https://x.com/errnsterr).

Listing Scout watches listings in your areas and texts you when a new place fits your beds, baths, budget and pets. Missing details show as "not listed yet". It never makes them up.

When a place looks right, text "apply" and your bot fills in that listing's own application. Nothing goes out without your yes.

## Get the code

Your bot gets this repo with:

```bash
git clone https://github.com/Errnsterr/listing-scout
cd listing-scout
```

Or download the v1.2.0 release archive and unpack it: https://github.com/Errnsterr/listing-scout/archive/refs/tags/v1.2.0.tar.gz

Then install dependencies (Node 20 or newer, and Python 3) and start a search file:

```bash
python3 -m pip install pyyaml beautifulsoup4 Pillow
npm install
cp CRITERIA.example.yaml CRITERIA.yaml
```

`CRITERIA.yaml` stays on your computer. It is listed in `.gitignore`.

## What it does

- Checks property-manager pages every 5–15 minutes, depending on your plan.
- Reads Zillow, Redfin and HotPads alert emails on the schedule you pick (see [docs/COSTS.md](docs/COSTS.md)).
- Sends one short text per new place, price drop or relist. Quiet days mean nothing fit.
- **Decide together:** invite a partner, roommate, family, friend or coworker. Each joins by texting from their own phone. Everyone gets each place, sees each other's thoughts and shares a shortlist.
- **Apply for me:** text "apply" (or "apply 2"). Your bot fills in the listing's own apply page from your profile and vault, then stops and shows you what it filled and the fee. It submits and pays only after your yes for that listing.

  You give your SSN and date of birth each time, attach ID or pay stubs, and sign. See [FOR_YOU.md](FOR_YOU.md).

- Text "what can you do" anytime for the list. Text STOP to stop, "leave" to leave, or "no check-ins" to skip the occasional check-in texts.

## What it never does

- Email, call or message landlords, agents or sellers, book tours or make offers.
- Apply without your yes for that listing, or anywhere but the listing's own apply page.
- Save your SSN, date of birth, license number, bank numbers or documents.
- Text anyone without your okay, or change your search without asking first.
- Give legal, financial or real estate advice. See it before paying anything.

## Limits, up front

- **US only.** Rentals by default, and buying (**experimental**, new in v1.1.0). Apply for me is for rentals.
- For adults 18 and over.
- Texts go through Photon. Check its plans and limits at photon.codes/pricing.
- Setup takes about an hour with your bot's help. You see your first matches in chat, scam-checked and in alert format, in about 10 minutes; the first texted alert can take up to a day. Your phone and laptop can be off; the scout runs on your bot's own computer.
- Two features are best-effort: "Posted about N min ago" (only when a site gives a time) and Hands-on per-match notes.

## What we learned building this

- **Prove each site separately.** Zillow, Redfin and HotPads all format alert emails differently. A site counts as working only after one of its real alert emails parses (see `out/sources_proven.json`).
- **Never use tracked links.** Links inside alert emails carry your account's sign-in tokens. Alerts use the plain listing link instead (for example `zillow.com/homedetails/<id>_zpid/`).
- **The watchdog waits for your plan's schedule.** Routines drift and sites go quiet. A short alarm warned people about nothing, so it waits for the plan's inbox-reading interval plus 3 hours before saying anything, and then says it calmly.
- **Test new things with sending off.** New sources and buying (experimental) start in shadow mode (`shadow: true`). Would-be texts go to `out/shadow_texts.jsonl` until real emails parse cleanly.
- **Duplicates across sites happen.** In testing, the same house came from Zillow, Redfin and HotPads. The scout matches them by address, so each home shows up once.
- **Apply and agent links are rare.** Real alert emails almost never include them, so that line shows only when a site sends one. Nothing is made up.
- **Keep site filters loose.** A pet filter and Redfin's "deals" option quietly hid places that fit. Set sites to rent plus area, and let the scout filter.

## Run the tests

From the repo folder, run each test file with Python 3:

```
for f in tests/test_*.py; do python3 "$f" || break; done
```

Each file prints `ok` per test and stops on the first failure. No network or texts are used.

## Start here

1. [FOR_YOU.md](FOR_YOU.md): one page, only the steps you do yourself.
2. [FOR_YOUR_BOT.md](FOR_YOUR_BOT.md): the internals, commands, and file list, for your bot.
3. [docs/SETUP.md](docs/SETUP.md): the full setup reference, including the setup conversation script.
4. [docs/COSTS.md](docs/COSTS.md): what uses AI, and where to check Photon pricing.
5. [docs/PRIVACY.md](docs/PRIVACY.md): what's stored, and how to delete it.
6. [docs/DISCLAIMER.md](docs/DISCLAIMER.md): please read.
7. [docs/SAMPLE_MESSAGE.txt](docs/SAMPLE_MESSAGE.txt): every text, as it looks on a phone.
8. [docs/CHANGELOG.md](docs/CHANGELOG.md): what's new.

## Support and updates

- **Support is best effort, with no guarantees.** Text a bug or idea to your bot ("bug, the link didn't open"). After you say yes, it goes to the template's builder for review. Nothing is changed or built automatically.
- **Updates:** see [docs/CHANGELOG.md](docs/CHANGELOG.md). The current version is in `VERSION`. To update a running install, `git pull` (or download the new release archive) and keep `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/` and `out/`.

## License

MIT. Copyright errnsterr. See [LICENSE](LICENSE).

Provided as is, with no warranty. Use at your own risk. Not a real estate broker, agent, or legal or financial adviser.

Not affiliated with or endorsed by any listing site, portal or Photon. For adults 18+ in the US. See [docs/DISCLAIMER.md](docs/DISCLAIMER.md).
