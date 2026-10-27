# What Listing Scout costs, in plain words

## The short version
- **Checking listings uses no AI.** A small script on the bot's computer does it, with no AI involved.
- **Texts go through Photon.** See photon.codes/pricing for current plans and limits.
- **AI is used only when you talk to the bot**: setup, adding a person, changing your search, and (on Hands-on) per-listing notes, which are experimental. That uses your Grok Bot usage.

## What costs money
| Item | Cost | Source |
|---|---|---|
| Photon texting | Depends on your plan | photon.codes/pricing |
| Grok Bot AI | Depends on use (see below) | Your **Usage** settings show your actual spend |

## When AI is used (and when it isn't)
**No AI:**
- Checking property-manager pages every few minutes.
- Filtering by your criteria, removing duplicates, and spotting price drops and relists.
- Formatting and sending the alert texts.
- Saving what's been seen.

**Uses AI (counts toward your Grok Bot usage):**
- Setup conversations, and adding a household member.
- Changing your search ("add Huntington Beach", "raise the budget").
- Any question you ask the bot.
- **Reading listing-site alert emails** (Zillow, Redfin, HotPads), when `inbox_pull: routine`. Alert speed is how often the inbox is read. Each routine run is a short bot visit. Your plan sets how often (below); a faster routine, like every 10 minutes, means quicker alerts and more usage. With `inbox_pull: api` (an AgentMail key), the script pulls them with no AI.
- The **weekly health check** (every plan; a short bot visit that only messages you if something is wrong) and **per-match notes** (Hands-on, experimental).

We don't list token counts or dollar amounts for AI, because they vary with what you ask. Check **Settings → Usage** in Grok Bot to see what you've actually used.

## Pick a plan mode (`plan_mode` in CRITERIA.yaml)
| Mode | Listing checks | Alerts | Email alerts (Zillow, etc.) | AI use |
|---|---|---|---|---|
| **Lean** (default) | Every 15 min (script) | Instant | Routine reads the inbox 2× a day | Lowest: inbox reads plus when you ask |
| **Standard** | Every 5 min (script) | Instant | Routine reads the inbox every 2 hours | Low: more inbox reads |
| **Hands-on** | Every 5 min (script) | Instant, plus a short AI note per match (experimental) | Routine reads the inbox every hour | Highest: AI looks at every match |
All modes text you the same way; quiet days mean no texts. With `inbox_pull: api` the email column doesn't apply: emails are pulled every listing check, with no AI. You can also speed up the routine (e.g. every 10 minutes); it costs more usage. The "email sync stalled" note waits for your plan's interval plus 3 hours, so a normal Lean gap never triggers it.
**Email-alert timing:** on Lean, a Zillow/Redfin/HotPads listing can reach you up to ~12 hours after its email arrives. Property-manager listings are checked every 15 minutes on Lean, or every 5 on Standard and Hands-on. You can switch anytime by saying "switch to lean".

## How it runs
A small script on the bot's computer does the checking. It restarts itself after a computer restart, and a weekly health check confirms it's running. Technical details are in `FOR_YOUR_BOT.md`.

## Extra features and cost
Sleep mode, Still available?, One home one text, Fine-tune the search, We found it and the data clean-up all run in the same no-AI script, so they add no AI use. Texts they send count like every other text on your Photon plan. The only AI step is closing the Zillow/Redfin/HotPads saved searches at the finish line, done once by the bot in its browser.
