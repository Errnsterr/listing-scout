# Changelog

All notable changes to the Listing Scout template. The current version is in `VERSION`.

## v1.1.1 (October 27, 2026): File layout

- Code is in `src/`. Longer docs are in `docs/`. `README.md`, `FOR_YOU.md`, and `FOR_YOUR_BOT.md` stay at the top.
- Commands and technical detail from `FOR_YOUR_BOT.md` are in `FOR_YOUR_BOT.md`. The setup conversation script from `docs/SETUP.md` is in `docs/SETUP.md`. The file list from `FOR_YOUR_BOT.md` is in `FOR_YOUR_BOT.md`.
- `PUBLISH_CHECKLIST.md` is removed.
- Run commands from the repo root, for example `python3 src/notify.py alerts out/alerts.json --send` and `./src/ensure_running.sh`.
- Rentals, buying (experimental), and the texts are unchanged.

## v1.1.0 (October 26, 2026): Buying (experimental)

- New, **experimental**: home-buying alerts (`mode: buy`) from Zillow, Redfin and Realtor.com for-sale emails. Rentals stay the default.
- New homes, price cuts and back on the market; pending or sold goes only to people who saved that home.
- Standouts right away, the rest in one evening roundup.
- The listing's own agent link, when the email has one.
- Welcome adds "Not an agent or advice." It never contacts agents or sellers, and gives no price, offer or mortgage advice.
- At setup the bot says "Buying is still new." / "Tell me if anything looks off." and starts in shadow mode for a day.
- Released before the full 3-day no-send proof; please report anything that looks off.
- Fixed: "Via" now names the site the link opens (a Redfin + Zillow duplicate no longer says "Via Redfin" with a Zillow link).
- US only and 18+ are unchanged.

## v1.0.1 update (October 26, 2026): end-to-end audit fixes

- New `timezone` setting (asked at setup step 1; default America/Los_Angeles). Quiet hours, Sleep mode, the 6 PM roundup and the day-4 check-in follow it, not the bot computer's clock.
- No false "email sync stalled" note on Lean: it now waits for the plan's inbox-reading interval plus 3 hours.
- New owner phrase "end my search": asks first (word yes), one goodbye to everyone, stops the scout and replies, the bot pauses its routines, then offers to delete data and close site searches, and reminds you about Photon's Users page.
- Photon step rewritten: real button names, 10–20 minutes, iPhone or Android, what to do if asked for payment or ID, and "stuck? tell me what you see".
- Before you start: your phone and laptop can be off; captcha heads-up; "If alerts stop, text Help or ask your bot."
- Site sign-up blocked? Make the account yourself and forward its alerts to the bot's inbox.
- New one-page FOR_YOU.md (your steps only) and FOR_YOUR_BOT.md (internals).
- Assistance-animal alert lines: "Assistance animals may be ok" / "Worth asking".
- Buying settings commented out in the example while buying is held. Version is 1.0.1 everywhere.

## v1.0.1 (October 26, 2026): pre-publish fixes

- Fixed: no alerts after an empty first run when several sources read the same inbox.
- Works in a freshly exported copy (makes `out/`, `logs/`, `inbox/` itself); placeholder sources are skipped, not fetched.
- Example search: one email source, price cap matches the stretch tier, one pet setting, 30-character lines.
- Owner welcome now says how to STOP. Headline: "New place that fits".
- Fair housing: asks about service or assistance animals (then never filters on pet rules); won't filter on or describe areas by safety, schools or who lives there; doesn't repeat "no Section 8" or "adults only" wording; neutral scam wording.
- Photon prices and people limits are no longer quoted; see photon.codes/pricing. Optional `photon.user_limit` check.
- Docs: "Before you start", a short glossary, renter shadow mode, setup time 60–90 minutes plus up to a day for the first alert.
- Credit: "Built by @errnsterr" in the README, the skill and the "what can you do" reply ([@errnsterr](https://x.com/errnsterr)).

## v1.0 (October 26, 2026): first public release

(Internal builds before this were numbered up to 1.4.0. Public numbering starts at 1.0.)

US rentals only. Buying is coming later.

**What it does**
- Texts you new rentals that fit your list: beds, baths, budget and pets.
- Checks property-manager pages every 5–15 minutes, and reads Zillow, Redfin and HotPads alert emails on the schedule you pick.
- One calm text per new place, price drop or relist. Quiet days mean nothing fit.
- Decide together: invite a partner or roommate. You both get every place and share a shortlist.
- Missing details show as "not listed yet". Nothing is made up.

**Added today**
- A README, this changelog, and clear notes on support (best effort), 18+, and US only.
- "What can you do" reply, and a "no check-ins" switch for the occasional check-in texts.
- Member welcomes now say "Text STOP anytime to stop." Help explains STOP and leave.
- The listing's own apply link, when an alert email includes one.
- Redfin alert emails sent as plain text are now read correctly.

**Fixed today**
- Alerts never include tracked links (they carry account tokens). They use a plain public link, or no link.
- Calmer wording: a quiet site now reads "{Site} is quiet today." instead of "isn't loading".
- The privacy reply is honest: "Only Photon sees the texts."
- Setup time (about 45–60 minutes), costs and the email-check schedule now match everywhere.
- Unproven features are labeled best-effort ("Posted about N min ago", Hands-on notes).
- Sample addresses are obviously made up.

**Not in this release**
