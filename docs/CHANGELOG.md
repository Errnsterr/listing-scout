# Listing Scout: changelog

All notable changes to the Listing Scout template. The current version is in `VERSION`.

## v1.2.10 (October 27, 2026): fewer silent misses, a record of every text

- Held buildings text once. A building card with a stated "from" price at or under your cap and a bed range that reaches your minimum is sent as its own "New place that fits" text ("From $X/mo", the stated bed range), instead of waiting on the held list. Cards with no price stay held. Never one already texted or marked gone by the still-listed check. `held_release_per_pass: N` (optional) spreads a backlog over several passes; `release_held: false` turns it off.
- A daily market snapshot can be a source. Rows saved as JSON in `inbox/market/*.json` (`site, address, zip, price, beds, baths, age_shown, url`) are checked against everything tracked and texted (same id, same link, same street address and unit, same building by name or street) and only a place never seen before alerts. A snapshot never changes a saved price and never causes a price-drop text. Add `{name: Market snapshot, type: market, dir: inbox/market}` to `sources`.
- Every text is logged in `out/text_log.jsonl`: time, who (first name only), listing ids, addresses and the exact text.
- Redfin unit ranges ("$3,130-$3,295/mo") keep the lowest unit as the price, so they match and sort, and the text still shows the stated range. Saved ids don't change.
- A building's own name ("Halcyon House", "... Apartment Homes") is no longer read as the property type or layout. A long building name on the "Another unit at" line wraps at a word break.

## v1.2.9 (October 27, 2026): places from emails can go away

- Once a day the scout checks each place from an alert email (one plain visit per place, spaced out) and marks it gone only on a clear sign: the page is missing (404/410), it sends you to a search or off-market page, or the page itself says it's off market, no longer available or rented. A blocked page, a captcha or no answer counts as unknown and is never marked gone, and the check never tries to get around a block.
- Gone places come off the shortlist (kept in `out/shortlist_gone.json` with their notes) and the reply-by-number lists. Every change is logged in `logs/gonecheck.log`. Nothing is texted about it.
- The scripts run the same from `src/` or from a flat installed copy.

## v1.2.8 (October 27, 2026): buying details you can trust

- Lot size shows only when it's the home's own lot. Redfin lists a condo or HOA community's whole lot (for example "10.42 acre lot" on a condo), so a unit, a condo or townhome, or an HOA home on half an acre or more shows no lot. A lot is read only where the email calls it one.
- HOA written as "$635 HOA" (Redfin) is now read. HOA shows only when the listing states it.
- The home type (condo, townhome, house) shows only when the listing states it. It's never taken from the address ("APT C2") or an open-house icon.
- A search with no price limit works again ("Any price"; no range words).
- Buy alerts use the rental alert's exact shape, with the range line from the buy budget when one is set (see docs/RENT_VS_BUY.md).
- Redfin links come from the address line's own link, so they resolve to the home's page. HOA, open house, lot and year built combine across Zillow, Redfin and Realtor.com copies of the same home.
- A ZIP like "02627" on a Costa Mesa listing is read as 92627, only when 92627 is a search ZIP and the city or link agrees.
- The health check knows the shadow-only proof loop.

## v1.2.7 (October 27, 2026): the right link, one text per place

- Fixed a mix-up in Zillow emails: a place without its own Zillow ID could borrow the next place's ID and link. Each place now uses only its own lines. The place that was mixed up stays recorded correctly, and the next place is no longer dropped.
- Rentals are instant: several fits from one email now go out as separate texts, each with its price range words, pets and source. No more "Three new places today".
- New line "Another unit at <Building>" when a place is in a building you were already sent.
- Missing ZIPs are filled from a saved place at the same address or building; places still missing one are logged.
- New `notify.py correct` sends one short "Fix for ..." text with the right link when a wrong link went out.
- A held building listing never holds back a specific unit with its own price and beds (documented).

## v1.2.6 (October 27, 2026): one home, one text across sites

- The same home listed on two sites with slightly different addresses is now treated as one home. For example, "125 Baker St" on Redfin and "125 E Baker St" on HotPads.
- Matching ignores "East"/"E", "Street"/"St", "Unit"/"#"/"Apt", punctuation and spacing. "218.5" and "218 1/2" are the same number.
- It never joins different house numbers, different units, a different ZIP, or "N" and "S" on the same street. Two separate listings from one manager also stay separate.
- Long alert emails were being cut off by the mail reader at 4,000 characters, so later places in a Redfin email were lost. Your bot now reads each email in full (up to 50,000 characters). The scout also warns when an email looks cut off: it ends early, or a price in its subject line isn't among the places it read.
- When a site lists the street but hides the house number, the text shows the street, for example "Royan Ln (no number listed)", instead of "Address not shown".
- The health check can run every 10 minutes and stays quiet when all is well. It speaks up if texts have been failing for 30 minutes or an email looks cut off.
- The example settings file no longer has an unused headline setting with emoji in it.
- The text format is the same.

## v1.2.5 (October 27, 2026): no place left out for missing details

- A place is skipped only when something it states clearly misses your search. If rent, beds, baths or pets is missing, the place is still texted, with that detail shown as "not listed yet".
- Buildings with several units fit if any unit could. A HotPads card that says "1 to 3 beds" was read as "1 bed" and skipped; it now shows "1-3 bed" and fits a 2-bed search.
- Prices written "from $2,295" or "$2,295+" show as "From $2,295/mo". They fit when that lowest price is within your budget. The "In your target range" line is left out for them, since other units may cost more.
- Your bot can hold places for you to look at first. A held place is never texted by itself.
- The text format is the same.

## v1.2.4 (October 27, 2026): real links and street addresses

- Redfin places from alert emails now come with their listing link. Redfin emails only have tracked links, so these places used to go out with no link. Your bot now follows the tracked link once and texts only the plain listing page it leads to. Zillow emails with tracked links get the same fix.
- If a tracked link doesn't lead to a listing page, the place goes out with no link, as before. Tracked links are never texted or saved.
- When an email names only a building or community (for example "Example Villas"), the text shows the street address from the listing page instead, with the unit. The building name shows only when no street can be found. Nothing is guessed.
- Street numbers like "417 1/2" and "301-307" are read whole. A number inside a building name, like "Eight 80", is no longer read as a street number.
- The text format is the same. The street sits on its own line, right above its link.
- There is no v1.2.3 release.

## v1.2.2 (October 26, 2026): faster checks

- The script checks listings every 5 minutes on every plan. Set `loop_minutes` in `CRITERIA.yaml` to change it. Plans still decide how often alert emails are read.
- Every match is texted on the check that finds it. There's no hour-long wait after a text anymore (`bundle_cooldown_min: 0`). Several matches found on one check still go as one numbered text.
- Docs, examples and the health check match the new timing.

## v1.2.1 (October 26, 2026): price fix

- HotPads prices written like "$30K/mo", "from $1.8K", "$36.6K" or "$2.12K" are read as the full amount ($30,000, $1,800 and so on). Before, those emails read as no homes and the owner got a "couldn't read homes" note.
- "Email sync stalled" waits for your inbox routine's own interval plus 3 hours when `inbox_routine_minutes` is set in `CRITERIA.yaml`.

## v1.2.0 (October 26, 2026): Apply for me

- HotPads text alerts are read correctly: each place gets its own link, two-line addresses are kept, "Call for price" and "$X+" prices are their own places, and a home listed on HotPads and Zillow or Redfin shows up once.
- Buying is experimental.
- Text "apply" (or "apply 2") on a place. Your bot opens that listing's own application, fills it from your application profile and vault, and stops for your yes before it submits or pays.
- You give your SSN and date of birth each time through a private form, attach ID or pay stubs, and do ID selfie checks, credit-check consent, signatures and phone codes. None of these are ever saved.
- A scam, fair-housing, link and freshness check runs first. If anything looks off, the bot stops and asks.
- Roundups show every place that fits, nothing left out, each as "N. address" / one facts line / its own link. Long ones go as "Part 1 of 2" texts; a place is never split and every number works for replies. The setup snapshot shows every current match the same way.
- One voice in every text: no emoji; "Sarah loved Maple St" on every phone; "Each home shows up once."; "See it before paying anything." on any scam signal; "A price came down" for rentals and buying; "N new places today" (buying: "N new homes today"); "Heads up on X:" openers; commands always "Text ___", with one command list in help, "what can you do" and the docs; "Text START" turns texts back on.
- Every price says "/mo" (rentals), in every roundup entry and alert. When a facts line would pass 30 characters, the area moves to its own line for every entry in that text.
- Single alerts show baths when known and "Baths: not listed yet" when not. Roundup entries add baths when known.
- Areas use your own spelling (for example "Vista del Sol"), never the site's.
- Redfin alerts: building names ("Example Villas, City, ST 90001") are read as the address, and price ranges ("$2,702-$3,953/mo", "1-2 beds") are shown as ranges, never as one made-up price.
- One wording each: "See it before paying anything." in both welcomes, "Text STOP anytime to stop." everywhere, and "Nothing goes out before a yes." in Apply for me texts.
- "Not listed yet" only for rent, beds, baths and pets. Garage, layout, move-in date and HOA show only when the listing states them; a missing address reads "Address not shown".
- Buying welcomes add "Buying is still new."
- The rule "never applies" is now "never applies without your yes for that listing; never contacts landlords".
- Requests move new → waiting → in_progress → handled or declined. New or waiting requests time out after 24 hours with one short text to that person. A new routine, "Listing Scout: apply requests" (every 5 minutes, `docs/routines/apply-watch.md`), is offered at go-live.
- The welcome text now says "Text apply on one you like." Help and "what can you do" say "Text apply to start one."
- Docs: Apply for me is in the README, FOR_YOU, privacy, disclaimer, costs and Photon FAQ pages. Fees are set by the landlord and are often not refundable.
- Consistency: setup time is "about an hour" everywhere, version 1.2.0 everywhere, and heading levels are fixed. Every text builder is checked by `tests/test_all_texts.py`. A paused-texts note now comes from `style.py`, and every send warns if a text fails the style check.
- Fix: AppFolio "Apply Now" links are now picked up, so Apply can start on AppFolio listings. Fees are read from each listing's own page, else "not listed yet".
- Fix: street names in texts drop a trailing unit tag ("Main Street - Unit C" shows as "Main").
- New first conversation: renting or buying, then 4 questions (where, beds and baths, comfortable and stretch budget, move date) with a fixed read-back. Every current match, shown exactly like a text, scam-checked, in about 10 minutes. Then texts and listing-site alerts, "texts anytime or hold late ones till morning" (Sleep mode still off by default), finer details one at a time, and chat-only reminders that stop after two skips.

  Setup is still about an hour.

- Welcomes: every person's welcome now says "By staying in, you're 18+." before the STOP line. Opt-in stays text-first. To fit, the member welcome drops "Spot a bug, just let me know." (the owner welcome keeps it).
- New: `src/apply.py`, `tests/test_apply.py`, `tests/test_all_texts.py`, `docs/routines/apply-watch.md`.

## v1.1.1 (October 26, 2026): File layout

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

### What it does

- Texts you new rentals that fit your list: beds, baths, budget and pets.
- Checks property-manager pages every 5–15 minutes, and reads Zillow, Redfin and HotPads alert emails on the schedule you pick.
- One calm text per new place, price drop or relist. Quiet days mean nothing fit.
- Decide together: invite a partner or roommate. You both get every place and share a shortlist.
- Missing details show as "not listed yet". Nothing is made up.

### Added today

- A README, this changelog, and clear notes on support (best effort), 18+, and US only.
- "What can you do" reply, and a "no check-ins" switch for the occasional check-in texts.
- Member welcomes now say "Text STOP anytime to stop." Help explains STOP and leave.
- The listing's own apply link, when an alert email includes one.
- Redfin alert emails sent as plain text are now read correctly.

### Fixed today

- Alerts never include tracked links (they carry account tokens). They use a plain public link, or no link.
- Calmer wording: a quiet site now reads "{Site} is quiet today." instead of "isn't loading".
- The privacy reply is honest: "Only Photon sees the texts."
- Setup time (about 45–60 minutes), costs and the email-check schedule now match everywhere.
- Unproven features are labeled best-effort ("Posted about N min ago", Hands-on notes).
- Sample addresses are obviously made up.

### Not in this release
