# Test documentation

Run: `python -m unittest discover -s tests -t . -v`

| File | Covers |
|---|---|
| test_priority_and_tickets.py | RSSI/VSWR/DIESEL boundaries, hub uplift, ticket numbering, tie-break, out-of-order rows, duplicate window (0, 15:00, 15:01), DG window (30:00, 30:01), different site/type, window from opener |
| test_lifecycle_and_validation.py | assign/resolve/reopen, 24 h boundary, auto-close, invalid transitions, unknown alarm/engineer, bad timestamp, unknown command, argument count, report month, comment lines, run continues after error |
| test_sla_report_outputs.py | deadline boundary, full hours, cap, reopen SLA clock, strict response breach, unconfigured SLA, monthly report per circle, loader validation (bad rows, missing file/columns, empty file), exact CSV headers, NONE, true/false |
| test_sample_data.py | every planted README scenario on the real sample data, error lines, determinism |

Not covered: hidden data can't be tested; hand-checked expected outputs for
the sample don't exist (README says none are provided).
