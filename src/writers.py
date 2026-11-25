"""Write the four required CSV output files."""
import csv
import os

import config
from . import sla
from .reports import REPORT_COLUMNS, format_money
from .tickets import EVENT_COLUMNS
from .timeutil import format_timestamp

TICKET_COLUMNS = ["ticket_id", "opening_alarm_id", "site_id", "circle",
                  "alarm_type", "priority", "opened_at", "assigned_at",
                  "resolved_at", "closed_at", "final_status",
                  "attached_alarm_count", "response_breached",
                  "resolution_breached", "hours_late", "penalty_rs"]
ERROR_COLUMNS = ["line_no", "command", "reason"]


def _bool(value):
    return "true" if value else "false"


def _write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def ticket_row(ticket):
    result = sla.evaluate(ticket)
    none = config.NONE_TEXT
    return [ticket.ticket_id, ticket.opening_alarm_id, ticket.site_id,
            ticket.circle, ticket.alarm_type, ticket.priority,
            format_timestamp(ticket.opened_at, none),
            format_timestamp(ticket.assigned_at, none),
            format_timestamp(ticket.resolved_at, none),
            format_timestamp(ticket.closed_at, none),
            ticket.status, len(ticket.attached_alarm_ids),
            _bool(result.response_breached),
            _bool(result.resolution_breached),
            result.hours_late, format_money(result.penalty_rs)]


def write_all(output_dir, store, report_rows, errors):
    os.makedirs(output_dir, exist_ok=True)
    _write(os.path.join(output_dir, "ticket_events.csv"),
           EVENT_COLUMNS, store.events)
    _write(os.path.join(output_dir, "tickets.csv"), TICKET_COLUMNS,
           [ticket_row(t) for t in store.tickets.values()])
    _write(os.path.join(output_dir, "sla_report.csv"),
           REPORT_COLUMNS, report_rows)
    _write(os.path.join(output_dir, "errors.csv"), ERROR_COLUMNS, errors)
