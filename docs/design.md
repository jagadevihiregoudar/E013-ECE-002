# Design document — E013-ECE-002

## 1. Purpose
Batch engine: alarms + commands in, four CSVs out. No GUI, no database.

## 2. Architecture
`main.py` → `CommandProcessor` (reads commands.txt line by line) → loaders /
`TicketStore` / `reports` → `writers`. All thresholds sit in `config.py`.

```
commands.txt ─► commands.py ─► loader.py (sites, engineers, alarms)
                    │            └─► tickets.py (open/attach, lifecycle) ◄─ priority.py
                    │                                  └─► sla.py ─► reports.py
                    └─► errors list               writers.py ─► 4 CSV files
```

## 3. Entities
Site(site_id, circle, dependent_sites → is_hub), Engineer(engineer_id, circle),
Alarm(id, site, timestamp, type, value), Ticket(id, opening alarm, site,
circle, type, priority, opened/assigned/resolved/closed times, status,
attached alarms, engineer).

## 4. Ticket lifecycle
```
OPEN --ASSIGN--> ASSIGNED --RESOLVE--> RESOLVED --REOPEN (<=24h)--> ASSIGNED
                                          └--REPORT (auto-close, +24h)--> CLOSED
```
Everything else is rejected into errors.csv.

## 5. Alarm processing (LOAD_ALARMS)
1. Validate rows (site exists, type known, timestamp, number, unique id).
2. Sort by (timestamp, alarm_id).
3. For each alarm: DG_NOT_STARTED → try attach to a MAINS_FAIL ticket on the
   same site 0–30 min old (ticket → P1); else try duplicate (same site+type,
   0–15 min after the ticket's opening alarm); else open a new ticket with
   priority = base rule, then hub uplift.

## 6. SLA
Resolution deadline = opened_at + SLA hours (original open time, even after
reopen). Breach only if strictly later. hours_late = full hours late. Penalty
= min(hours_late × rate, cap).

## 7. Error handling
Each bad line/row becomes `(line_no, command, reason)`; processing continues.
Unexpected exceptions on one line are also caught and logged.

## 8. Testing strategy
`unittest`; one test per rule and boundary, helper that builds a tiny data
set in a temp folder, plus an end-to-end test of every README scenario.
