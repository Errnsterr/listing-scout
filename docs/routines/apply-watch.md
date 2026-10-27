# Listing Scout: apply requests routine

Create at go-live, only after the owner says okay. Schedule: every 5 minutes. Working folder: the Listing Scout repo root.

## Routine prompt (paste as is)

```prompt
You are running the "Listing Scout: apply requests" routine.

1. In the Listing Scout folder, run: python3 src/apply.py pending --send
2. If it prints "none", stop. Say nothing to anyone.
3. Lines starting with EXPIRED are already handled: the member got one short text. Do nothing more for them.
4. Act only on requests with status "new". Requests marked "waiting" or "in_progress" are already with someone: don't message again, just wait for their answer.
   For each "new" request id:
   a. Run: python3 src/apply.py plan <id>   (this marks it "waiting")
   b. If it prints "stop_and_ask_owner": message the member who asked in the Grok Bot app (and the owner too, if that member isn't the owner) with the place and each reason, in plain calm words. Do not open the apply link. If they say go ahead anyway, run: python3 src/apply.py mark <id> in_progress, tell them what they'll need to give you (as in 4c), and continue with step 5. If they say no, run: python3 src/apply.py mark <id> declined.
   c. If it prints "ready_to_fill": read out/apply_plans/<id>.json and message the member who asked, in the Grok Bot app:
      - the place, the price and the apply link's site;
      - what you will fill from their profile and vault (field names only, never values);
      - what they will need to give you: SSN and date of birth (private form, used once), photo ID or pay stub uploads, any ID selfie check, credit-check consent, their signature, and phone codes;
      - the fee, or "not listed yet";
      - then ask: "Want me to start this application?"
      On a clear yes, run: python3 src/apply.py mark <id> in_progress. On a no, run: python3 src/apply.py mark <id> declined.
5. Only for an "in_progress" request (a clear yes from that member for that one listing), follow "Apply for me" in FOR_YOUR_BOT.md: fill the listing's own apply page, stop at the review page, show what was filled (SSN masked) and the fee, and submit or pay only after a second explicit yes for that application. When done, run: python3 src/apply.py mark <id> handled. If they stop partway, run: python3 src/apply.py mark <id> declined.
6. Never submit or pay without that per-listing yes. Never email, call or message a landlord or agent. Never use one member's info for another. Never save or repeat an SSN, date of birth, license number, bank number or document. Never text anyone except what apply.py sends itself.
7. Requests still "new" or "waiting" after 24 hours expire on their own (apply.py texts that member once). "in_progress" requests never expire.
```
