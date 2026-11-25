# Five-minute demo script

**0:00–0:30 Intro.** Project, team, what the engine does: alarms in, tickets and SLA reports out.

**0:30–1:15 Inputs.** Show sites.csv, engineers.csv, alarms.csv and commands.txt (command format `NAME|arg|arg`).

**1:15–2:00 Run.** `python main.py sample_data --output output`. Point at the WARNING lines: these are the values the brief must supply; they live in config.py.

**2:00–3:00 Outputs.** Open tickets.csv (statuses, NONE values, hours_late, penalty), ticket_events.csv (OPEN/ATTACH/ASSIGN/RESOLVE/REOPEN/CLOSE), sla_report.csv (one row per circle), errors.csv (line 1058 reopen after close, 1434 resolve before assign, 1576 unknown alarm).

**3:00–4:00 Edge cases.** DG exactly 30 min (ALM-00196/197 → P1); duplicate at 15:00:01 (ALM-00339/340 → new ticket); penalty cap (ALM-00673 → 10000); exact-deadline resolve (ALM-00430 → no penalty).

**4:00–4:40 Tests.** `python -m unittest discover -s tests -t . -v` → 89 tests OK.

**4:40–5:00 Wrap-up.** Config-driven rules, remaining work: confirm unknown values against the brief.
