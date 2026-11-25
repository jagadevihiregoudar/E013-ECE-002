# ECE-002 – Cell-Tower Site Maintenance Ticketing and SLA Engine — Sample Data Pack
Prepared by 10 SECONDS for Team E013.

This pack is the input for a tower-operations ticketing engine. Alarms arrive in `alarms.csv`; your engine turns them into tickets (P1/P2/P3), attaches duplicates, and then applies the ASSIGN / RESOLVE / REOPEN events from `commands.txt`. Everything is for October 2026 and two circles.

Ticket ids: number tickets `TKT-0001`, `TKT-0002`, … in the order their opening alarm appears after sorting alarms by timestamp (ties by alarm_id). Lifecycle commands refer to a ticket by the alarm_id of the alarm that OPENED it. Pack conventions where the brief is silent: a duplicate is the same alarm_type on the same site arriving 0–15 min (inclusive) after the ticket's opening alarm; a DG_NOT_STARTED arriving 0–30 min (inclusive) after a MAINS_FAIL on the same site attaches to that ticket and makes it P1; the RSSI band -110 to -100 dBm is inclusive at both ends; dependent_sites ≥ 3 makes a hub.

## Files
| File | What it holds | Rows |
|---|---|---|
| sites.csv | Tower sites with circle and hub information | 25 |
| engineers.csv | Field engineers and their circle | 8 |
| alarms.csv | October 2026 alarm feed (RF, power, diesel) | 1202 |
| commands.txt | Load commands, then ticket lifecycle events in time order | 2323 |

## Column reference
Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals (no commas, no symbol); percentages as plain numbers (12.5 = 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix.

### sites.csv
| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| site_id | string | SITE-nnn | SITE-001 … SITE-025 | Primary key |
| site_name | string | - | free text |  |
| circle | string | - | KA-SOUTH, KA-NORTH | Penalty report is per circle |
| city | string | - | Indian city |  |
| is_hub | boolean | true/false | true, false | true when dependent_sites ≥ 3 |
| dependent_sites | integer | count | 0–6 | Hub uplift applies when ≥ 3 |

### engineers.csv
| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| engineer_id | string | ENG-nn | ENG-01 … ENG-08 | Primary key |
| engineer_name | string | - |  |  |
| circle | string | - | KA-SOUTH, KA-NORTH |  |
| mobile | string | 10 digits | starts 6–9 | Not used by any rule |

### alarms.csv
| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| alarm_id | string | ALM-nnnnn | unique | Numbered in file order |
| site_id | string | SITE-nnn | must exist in sites.csv |  |
| timestamp | timestamp | YYYY-MM-DD HH:MM:SS | Oct 2026 | One row is deliberately out of order |
| alarm_type | string | - | RSSI_LOW, VSWR_HIGH, TX_POWER_LOW, MAINS_FAIL, DG_NOT_STARTED, DIESEL_LOW | RSSI_LOW/VSWR_HIGH/TX_POWER_LOW are RF alarms; the rest are power alarms |
| measured_value | decimal | see unit | RSSI dBm (negative), VSWR ratio, TX power dBm, DIESEL_LOW % of tank; 0 for MAINS_FAIL / DG_NOT_STARTED | Drives the P1/P2/P3 thresholds |
| unit | string | - | dBm, ratio, pct, - |  |

## Command file format
`commands.txt` holds one command per line as `COMMAND_NAME|arg1|arg2|...`. Commands must be processed in file order, top to bottom. Lines starting with `#` are comments and blank lines are ignored.

| Command | Arguments (in order) | Meaning |
|---|---|---|
| LOAD_SITES | file | Load sites.csv |
| LOAD_ENGINEERS | file | Load engineers.csv |
| LOAD_ALARMS | file | Load alarms.csv, sort by timestamp, create/attach tickets |
| ASSIGN | opening_alarm_id \| engineer_id \| timestamp | OPEN → ASSIGNED |
| RESOLVE | opening_alarm_id \| timestamp | ASSIGNED → RESOLVED |
| REOPEN | opening_alarm_id \| timestamp | RESOLVED → ASSIGNED if within 24 h of RESOLVE, else error (ticket already CLOSED) |
| REPORT | YYYY-MM | Apply auto-close (RESOLVED + 24 h with no reopen → CLOSED) and print the monthly report |

For engineer_id use ENG-nn exactly; for timestamps use the same format as alarms.csv. `hours_late` in tickets.csv is the number of FULL hours beyond the resolution SLA (0 when on time). Use `NONE` in any output timestamp column that has no value (for example closed_at on an open ticket).

## Planted scenarios
Line numbers count the header row as line 1, so the first data row of a CSV is line 2. For commands.txt the line number is the physical line in the file (comment lines included).

- **DG_NOT_STARTED arriving exactly 30 minutes after MAINS_FAIL** — alarms.csv line 197 (ALM-00196) MAINS_FAIL at 02:10:00 and alarms.csv line 198 (ALM-00197) DG_NOT_STARTED at 02:40:00 on SITE-005 — exactly 30 min, counts as within the window, ticket becomes P1.
- **Hub site P1 alarm (uplift must not create a P0)** — alarms.csv line 254 (ALM-00253) RSSI -115.0 dBm on hub SITE-021 (6 dependents): P1 before uplift, must stay P1. Also alarms.csv line 256 (ALM-00255) TX_POWER_LOW on hub SITE-003 (P3→P2) and alarms.csv line 258 (ALM-00257) RSSI -105.0 (P2→P1).
- **Duplicate alarm arriving 15 minutes and 1 second after the first** — alarms.csv line 340 (ALM-00339) VSWR 2.40 at 15:00:00 and alarms.csv line 341 (ALM-00340) VSWR 2.45 at 15:15:01 on SITE-010 — 15 min 1 s apart, so the second opens a NEW ticket. Compare the true duplicate alarms.csv line 349 (ALM-00348) / alarms.csv line 350 (ALM-00349) (DIESEL_LOW on SITE-011, 10 min apart, attached).
- **Ticket resolved exactly at the SLA deadline (no penalty)** — alarms.csv line 431 (ALM-00430) MAINS_FAIL alone on SITE-017 (P2, resolution SLA 24 h) opened 2026-10-12 09:30:00 and RESOLVE at commands.txt line 890 = 2026-10-13 09:30:00 exactly — no penalty.
- **Reopen event after the ticket is already CLOSED (rejected with an error line)** — alarms.csv line 509 (ALM-00508) SITE-019 resolved at commands.txt line 963; REOPEN at line 1058 comes 30 h later, after the 24 h auto-close, so it must be rejected with an error line.

Extra traps (realistic things your validation should catch):

- **Penalty cap** — alarms.csv line 674 (ALM-00673) RSSI -118.0 (P1) on SITE-023, resolved 30 h after open (commands.txt line 1354): 24 full hours late x Rs 500 = 12,000 → capped at Rs 10,000.
- **Invalid transition RESOLVE before ASSIGN** — commands.txt line 1434 resolves ALM-00762 while still OPEN → reject with error line; the ASSIGN at line 1439 and RESOLVE at line 1450 are then valid.
- **Unknown alarm id** — commands.txt line 1576 ASSIGN|ALM-99999 → error line, nothing changes.
- **Boundary values** — alarms.csv line 600 (ALM-00599) RSSI -110.0 (not below -110 → P2), alarms.csv line 602 (ALM-00601) RSSI -100.0 (P2, range is inclusive), alarms.csv line 605 (ALM-00604) VSWR 2.00 (not above 2.0 → P3), alarms.csv line 606 (ALM-00605) DIESEL_LOW 10.0 (not below 10 → P2).
- **Out-of-order alarm row** — alarms.csv line 403 carries an earlier timestamp than line 402; sort alarms by timestamp (then alarm_id) before processing.
- **Reopen within 24 h keeps the original OPEN time** — commands.txt line 1799 reopens ALM-00903 20 h after resolve → back to ASSIGNED; the second RESOLVE at line 1814 is measured from the original open time.

## What is NOT in this pack
Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-07). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation
Produce these files (CSV, header row, same conventions as above). Column order matters.

### ticket_events.csv
One row per lifecycle event in processing order (OPEN, ATTACH, ASSIGN, RESOLVE, REOPEN, CLOSE).

Columns in order: `ticket_id`, `event`, `timestamp`, `alarm_id`, `engineer_id`, `priority`, `detail`

### tickets.csv
One row per ticket after the REPORT command.

Columns in order: `ticket_id`, `opening_alarm_id`, `site_id`, `circle`, `alarm_type`, `priority`, `opened_at`, `assigned_at`, `resolved_at`, `closed_at`, `final_status`, `attached_alarm_count`, `response_breached`, `resolution_breached`, `hours_late`, `penalty_rs`

### sla_report.csv
One row per circle for the month.

Columns in order: `month`, `circle`, `p1_tickets`, `p2_tickets`, `p3_tickets`, `response_breaches`, `resolution_breaches`, `penalty_rs`

### errors.csv
Rejected commands and alarms.

Columns in order: `line_no`, `command`, `reason`
