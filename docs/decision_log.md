# Decision log

| # | Decision | Why |
|---|---|---|
| D1 | All rule values in `config.py`, read at call time | Missing brief values can be filled in without touching logic; tests can patch them |
| D2 | Unknown values are `None` = "check skipped", not guessed | Brief said never invent rules; warnings printed by main.py |
| D3 | Only the standard library, `unittest` | Nothing to install; simple to explain |
| D4 | `Ticket` keeps `opened_at` forever; reopen only clears `resolved_at` | README: reopen keeps original OPEN time |
| D5 | Auto-close happens at REPORT, REOPEN checks the 24 h window itself | README: REOPEN after 24 h must be rejected even though CLOSE is applied at REPORT |
| D6 | Hub decided by `dependent_sites >= 3`, not the `is_hub` column | README states this rule; avoids inconsistent data |
| D7 | Duplicate window measured from the OPENING alarm | README wording |
| D8 | DG with several MAINS_FAIL tickets in window → latest one | Not specified; most recent outage is the natural link |
| D9 | Lifecycle timestamps may not go backwards (config flag) | Prevents negative durations; sample data has no such lines |
| D10 | Engineer circle not enforced (config flag) | Not in README; sample has no mismatch |
| D11 | Errors from one CSV sorted by line number | Predictable errors.csv |
| D12 | Events logged in processing order: alarm events in time order, then commands | README: "processing order" |
