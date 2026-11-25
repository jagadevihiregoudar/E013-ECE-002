# Business-rule register

The original brief with BR-01…BR-07 was not available. Rules below are taken
from the sample-data README (IDs `R1…`). When you have the brief, add the
matching BR-ID in the last column.

Status: **I** = implemented and tested, **P** = implemented with placeholder
(value missing), **Q** = open question / assumption.

| ID | Rule | Where in code | Status | BR-ID |
|---|---|---|---|---|
| R1 | Sort alarms by (timestamp, alarm_id) | `tickets.add_alarms` | I | |
| R2 | Ticket ids TKT-0001… in order of opening alarm | `tickets._open_ticket` | I | |
| R3 | Duplicate = same type + same site, 0–15 min inclusive after the OPENING alarm | `tickets._find_duplicate_ticket` | I | |
| R4 | DG_NOT_STARTED 0–30 min inclusive after MAINS_FAIL on same site attaches, ticket becomes P1 | `tickets._find_mains_ticket/_attach_dg` | I | |
| R5 | RSSI < -110 P1; -110…-100 inclusive P2 | `config.PRIORITY_RULES`, `priority.py` | I | |
| R6 | VSWR 2.00 is P3 (not above 2.0) | same | I (band above 2.0 = P) | |
| R7 | DIESEL_LOW < 10 is P1, 10.0 is P2 | same | I (upper P2 limit = P) | |
| R8 | MAINS_FAIL alone = P2 | same | I | |
| R9 | Hub = dependent_sites >= 3; uplift P3→P2, P2→P1, P1 stays P1 | `priority.apply_hub_uplift` | I | |
| R10 | Lifecycle OPEN→ASSIGNED→RESOLVED; invalid transition → errors.csv | `tickets.assign/resolve` | I | |
| R11 | REOPEN within 24 h of RESOLVE → ASSIGNED; later → error (CLOSED); opened_at kept | `tickets.reopen` | I | |
| R12 | REPORT auto-closes RESOLVED tickets (resolved_at + 24 h) | `tickets.auto_close_resolved` | I (Q: reference time) | |
| R13 | Unknown alarm id → error, nothing changes | `tickets.get_ticket` | I | |
| R14 | hours_late = FULL hours beyond resolution SLA; on-time at deadline | `sla.evaluate` | I | |
| R15 | P1 penalty Rs 500 per full hour; cap Rs 10,000 per ticket | `config`, `sla.py` | I | |
| R16 | P2 resolution SLA 24 h; P1 = 6 h (derived from ALM-00673 example) | `config` | I (P1 derived) | |
| R17 | Monthly per-circle report | `reports.py` | I (Q: month rule) | |
| R18 | Output formats, NONE for missing timestamps, true/false booleans | `writers.py` | I | |
| R19 | Comments/blank lines ignored; invalid lines logged, run continues | `commands.py` | I | |

## What to fill in from the brief (all in `config.py`)
| Missing value | Config name | Today's behaviour |
|---|---|---|
| Response SLA minutes P1/P2/P3 | `RESPONSE_SLA_MINUTES` | `None` → never breached |
| Resolution SLA P3 (confirm P1 = 6) | `RESOLUTION_SLA_HOURS` | P3 `None` → never breached |
| Penalty rate P2, P3 | `PENALTY_RATE_PER_HOUR` | `None` → Rs 0 |
| TX_POWER_LOW thresholds | `PRIORITY_RULES["TX_POWER_LOW"]` | empty → default P3 |
| VSWR bands above 2.0 | `PRIORITY_RULES["VSWR_HIGH"]` | one rule: > 2.0 → P2 |
| DIESEL_LOW P2/P3 cut-off | `PRIORITY_RULES["DIESEL_LOW"]` | ≥ 10 → P2 |
| Lone DG_NOT_STARTED priority | `PRIORITY_RULES["DG_NOT_STARTED"]` | empty → default P3 |
| Priority above -100 RSSI | `DEFAULT_PRIORITY` | P3 |
| Money format (10000 vs 10000.00) | `PENALTY_DECIMALS` | 2 decimals |

Example — to add a response SLA of 30/60/120 minutes:
`RESPONSE_SLA_MINUTES = {"P1": 30, "P2": 60, "P3": 120}`. No code change needed.
If the brief needs a *different kind* of rule (e.g. response-breach penalty),
change `sla.evaluate` (SLA/penalty) or `reports.build_monthly_report` (report).

## Open questions / assumptions (answer from the brief)
1. Month of a ticket in the report: **opened_at** assumed.
2. Auto-close at REPORT: **all** RESOLVED tickets are closed (closed_at = resolved_at + 24 h), whatever the report month.
3. Unassigned / unresolved tickets: **not** breached, hours_late 0.
4. Response SLA clock: opened_at → **first** ASSIGN; breach if strictly greater. Resolution breach likewise strictly greater.
5. A late-by-less-than-1-hour ticket is a breach with hours_late 0 and penalty 0.
6. `attached_alarm_count` = attached alarms **excluding** the opening alarm.
7. After REOPEN, `resolved_at` becomes NONE until the next RESOLVE.
8. REOPEN at exactly 24 h is allowed (inclusive).
9. A lone DG_NOT_STARTED, and DG with two MAINS_FAIL tickets in window (latest chosen).
10. Event `detail` wording and engineer_id on non-ASSIGN events (NONE) are our own.
11. errors.csv `command` column holds the raw command line (for CSV rows: `LOAD_ALARMS` etc., line_no = CSV line).
12. Engineer must be in the site's circle: **not** enforced (sample has no mismatch).
13. Timestamps going backwards for a ticket are rejected (`ENFORCE_TIME_ORDER`).
14. Sample data contains two unlisted rejected lines (commands.txt 1718 second ASSIGN, 1735 RESOLVE before REOPEN) — consistent with the README transition table and with "20 h after resolve" for ALM-00903.
