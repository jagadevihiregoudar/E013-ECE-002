# Viva preparation

1. **What does the program do?** Reads commands.txt, builds tickets from alarms, applies lifecycle commands, computes SLA/penalty, writes 4 CSVs.
2. **Why `config.py`?** All business numbers in one place; engine code has no magic numbers; missing values can be filled without code changes.
3. **How are tickets numbered?** Alarms sorted by (timestamp, alarm_id); each opening alarm gets the next TKT-nnnn (`TicketStore._open_ticket`).
4. **How is a duplicate detected?** Same site and type, 0–15 min (inclusive) after the ticket's opening alarm (`_find_duplicate_ticket`). 15 min 1 s → new ticket.
5. **How does DG_NOT_STARTED work?** If a MAINS_FAIL ticket on the same site is 0–30 min old, it attaches and the ticket becomes P1 (`_attach_dg`).
6. **Hub uplift?** `priority.apply_hub_uplift`: P3→P2, P2→P1, P1 stays P1; hub = dependent_sites ≥ 3.
7. **Lifecycle?** OPEN→ASSIGNED→RESOLVED→(REOPEN→ASSIGNED | CLOSED). Other transitions raise `RejectedCommand` and go to errors.csv.
8. **Why can REOPEN be rejected before REPORT closes the ticket?** The window check (`resolved_at + 24 h`) is done in `reopen` itself.
9. **How is hours_late computed?** `int((resolved_at − deadline) // 1 hour)`; deadline = opened_at + SLA; exactly on the deadline = on time.
10. **Penalty?** `min(hours_late × rate, cap)`; P1 500/h, cap 10,000.
11. **After a reopen, which time is used for SLA?** The original opened_at.
12. **What happens on a bad line?** `commands._execute` raises `RejectedCommand`; `run_lines` logs it and continues.
13. **What is still unknown?** Response SLA, P3 SLA, P2/P3 penalty, some thresholds — see `docs/business_rules.md`.
14. **How would you add a new priority threshold?** Add a tuple to `PRIORITY_RULES[type]`.
15. **How did you test?** unittest, helper builds tiny datasets, plus README scenarios on the real data.
