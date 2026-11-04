# Changelog

## v1.2.20 (2026-11-04)
- Fix: every pass crashed from midnight Nov 4 with `ValueError` in `fuzzy_dup`. state.json still held 28 records from v1.1.x (Oct 26–27) whose `addr` was the old space-joined form ('2 sample'), not the `num|name|unit` key. They sat unused until a new listing in the same ZIP at a close price reached the split.
- Root fix: `normalize_state_addrs()` runs when state loads and moves any non-3-part `addr` to `legacy_addr` (idempotent). `addr_key()` is still the only writer of `addr` and always returns 3 parts.
- Hardening: `fuzzy_dup` and `build_zipidx` read addresses through `_addr3()` and skip malformed records, so one bad record can't stall the loop again.
- Not changed: who gets texted, text wording, search criteria, the stale rule.
- Tests: `tests/test_v1220_legacy_addr.py`.

## v1.2.19 (2026-10-31)
- Free, no-AI catch-up every loop pass: with `inbox_pull: routine`, `fetch_inbox.py` now lists unseen messages in the listener's AgentMail inbox (default ern@agentmail.to) using the listener's own seen check (`out/fetched_ids.txt`, bare ids) and routing. Rental alerts from Zillow, Redfin and HotPads go to `inbox/<site>-am-<id>.txt`. It never reads the routine's `alert_inbox`.
- Hard limits and fail-safe: stops between messages after 50 s, a 60 s alarm, and the loop's 120 s `timeout`. Any error is logged and the pass continues. A clean catch-up writes the sync heartbeat.
- For-sale mail (a 'Buy Test' search, for-sale wording, or Realtor.com/move.com) is skipped as "buy test ended" and marked seen in both the listener and the catch-up. It is no longer saved to a buy-test folder.
- Every skip goes to `logs/email_skips.log`; routed lines are tagged `[listener]` or `[pass catch-up]`.
- Tests: `tests/test_v1219_pass_catchup.py`; updated `test_mail_listener.py` and `test_fetch_gate.py`.
