"""Ticket creation, duplicate handling and the ticket lifecycle.

Lifecycle:  OPEN --ASSIGN--> ASSIGNED --RESOLVE--> RESOLVED --REOPEN--> ASSIGNED
            RESOLVED --(24 h with no reopen, applied at REPORT)--> CLOSED
"""
from datetime import timedelta

import config
from . import priority as priority_rules
from .models import ASSIGNED, CLOSED, OPEN, RESOLVED, Ticket
from .timeutil import format_timestamp

EVENT_COLUMNS = ["ticket_id", "event", "timestamp", "alarm_id",
                 "engineer_id", "priority", "detail"]


class RejectedCommand(Exception):
    """A lifecycle command broke a rule; the message goes to errors.csv."""


class TicketStore:
    def __init__(self):
        self.tickets = {}              # ticket_id -> Ticket (creation order)
        self.by_opening_alarm = {}     # opening alarm id -> Ticket
        self.alarm_to_ticket = {}      # any alarm id -> ticket_id
        self.events = []               # rows for ticket_events.csv
        self._site_tickets = {}        # site_id -> [Ticket, ...]
        self._counter = 0

    # ------------------------------------------------------------- events
    def _log(self, ticket, event, timestamp, alarm_id, detail,
             engineer_id=None):
        self.events.append([
            ticket.ticket_id, event, format_timestamp(timestamp),
            alarm_id, engineer_id or config.NONE_TEXT, ticket.priority,
            detail])

    # ------------------------------------------------- alarm -> ticket
    def add_alarms(self, alarms, sites):
        """Sort alarms by (timestamp, alarm_id) and open/attach tickets."""
        for alarm in sorted(alarms, key=lambda a: (a.timestamp, a.alarm_id)):
            self._process_alarm(alarm, sites[alarm.site_id])

    def _process_alarm(self, alarm, site):
        if alarm.alarm_type == config.DG_ALARM_TYPE:
            mains_ticket = self._find_mains_ticket(alarm)
            if mains_ticket is not None:
                self._attach_dg(mains_ticket, alarm)
                return
        duplicate_of = self._find_duplicate_ticket(alarm)
        if duplicate_of is not None:
            self._attach(duplicate_of, alarm,
                         f"duplicate {alarm.alarm_type}")
            return
        self._open_ticket(alarm, site)

    def _minutes_since_open(self, ticket, alarm):
        return (alarm.timestamp - ticket.opened_at) / timedelta(minutes=1)

    def _find_duplicate_ticket(self, alarm):
        """Same type + same site, 0..15 min after the OPENING alarm."""
        for ticket in reversed(self._site_tickets.get(alarm.site_id, [])):
            if ticket.alarm_type != alarm.alarm_type:
                continue
            gap = self._minutes_since_open(ticket, alarm)
            if 0 <= gap <= config.DUPLICATE_WINDOW_MINUTES:
                return ticket
        return None

    def _find_mains_ticket(self, alarm):
        """Latest MAINS_FAIL ticket on the site opened 0..30 min before."""
        for ticket in reversed(self._site_tickets.get(alarm.site_id, [])):
            if ticket.alarm_type != config.MAINS_ALARM_TYPE:
                continue
            gap = self._minutes_since_open(ticket, alarm)
            if 0 <= gap <= config.DG_WINDOW_MINUTES:
                return ticket
        return None

    def _open_ticket(self, alarm, site):
        self._counter += 1
        ticket = Ticket(
            ticket_id=f"TKT-{self._counter:04d}",
            opening_alarm_id=alarm.alarm_id,
            site_id=site.site_id,
            circle=site.circle,
            alarm_type=alarm.alarm_type,
            priority=priority_rules.alarm_priority(alarm, site),
            opened_at=alarm.timestamp,
            last_event_at=alarm.timestamp)
        self.tickets[ticket.ticket_id] = ticket
        self.by_opening_alarm[alarm.alarm_id] = ticket
        self.alarm_to_ticket[alarm.alarm_id] = ticket.ticket_id
        self._site_tickets.setdefault(site.site_id, []).append(ticket)
        self._log(ticket, "OPEN", alarm.timestamp, alarm.alarm_id,
                  f"{alarm.alarm_type} on {site.site_id}")

    def _attach(self, ticket, alarm, detail):
        ticket.attached_alarm_ids.append(alarm.alarm_id)
        self.alarm_to_ticket[alarm.alarm_id] = ticket.ticket_id
        self._log(ticket, "ATTACH", alarm.timestamp, alarm.alarm_id, detail)

    def _attach_dg(self, ticket, alarm):
        """DG_NOT_STARTED after MAINS_FAIL: attach and force P1."""
        ticket.priority = config.DG_ATTACH_PRIORITY
        self._attach(ticket, alarm,
                     f"{config.DG_ALARM_TYPE} within "
                     f"{config.DG_WINDOW_MINUTES} min of "
                     f"{config.MAINS_ALARM_TYPE}; priority set to "
                     f"{config.DG_ATTACH_PRIORITY}")

    # ---------------------------------------------------------- lifecycle
    def get_ticket(self, opening_alarm_id):
        """Find a ticket by the alarm id that opened it."""
        ticket = self.by_opening_alarm.get(opening_alarm_id)
        if ticket is not None:
            return ticket
        if opening_alarm_id in self.alarm_to_ticket:
            raise RejectedCommand(
                f"alarm {opening_alarm_id} is attached to "
                f"{self.alarm_to_ticket[opening_alarm_id]}, "
                "not an opening alarm")
        raise RejectedCommand(f"unknown alarm id {opening_alarm_id}")

    def _check_order(self, ticket, timestamp):
        if config.ENFORCE_TIME_ORDER and timestamp < ticket.last_event_at:
            raise RejectedCommand(
                f"timestamp {format_timestamp(timestamp)} is earlier than the "
                f"ticket's last event {format_timestamp(ticket.last_event_at)}")

    def _require_state(self, ticket, command, expected):
        if ticket.status != expected:
            raise RejectedCommand(
                f"invalid transition: {command} needs {expected} but "
                f"{ticket.ticket_id} is {ticket.status}")

    def assign(self, opening_alarm_id, engineer_id, timestamp):
        ticket = self.get_ticket(opening_alarm_id)
        self._require_state(ticket, "ASSIGN", OPEN)
        self._check_order(ticket, timestamp)
        ticket.status = ASSIGNED
        ticket.engineer_id = engineer_id
        ticket.assigned_at = timestamp          # first assignment time
        ticket.last_event_at = timestamp
        self._log(ticket, "ASSIGN", timestamp, ticket.opening_alarm_id,
                  f"assigned to {engineer_id}", engineer_id)

    def resolve(self, opening_alarm_id, timestamp):
        ticket = self.get_ticket(opening_alarm_id)
        self._require_state(ticket, "RESOLVE", ASSIGNED)
        self._check_order(ticket, timestamp)
        ticket.status = RESOLVED
        ticket.resolved_at = timestamp
        ticket.last_event_at = timestamp
        self._log(ticket, "RESOLVE", timestamp, ticket.opening_alarm_id,
                  "resolved")

    def reopen(self, opening_alarm_id, timestamp):
        ticket = self.get_ticket(opening_alarm_id)
        if ticket.status == CLOSED:
            raise RejectedCommand(f"ticket {ticket.ticket_id} already CLOSED")
        self._require_state(ticket, "REOPEN", RESOLVED)
        self._check_order(ticket, timestamp)
        window = timedelta(hours=config.REOPEN_WINDOW_HOURS)
        if timestamp - ticket.resolved_at > window:
            raise RejectedCommand(
                f"ticket {ticket.ticket_id} already CLOSED "
                f"(reopen later than {config.REOPEN_WINDOW_HOURS} h after "
                "RESOLVE)")
        ticket.status = ASSIGNED
        ticket.resolved_at = None   # opened_at is kept: SLA clock continues
        ticket.last_event_at = timestamp
        self._log(ticket, "REOPEN", timestamp, ticket.opening_alarm_id,
                  f"reopened within {config.REOPEN_WINDOW_HOURS} h of RESOLVE")

    def auto_close_resolved(self):
        """REPORT step: every RESOLVED ticket (no reopen) becomes CLOSED."""
        for ticket in self.tickets.values():
            if ticket.status != RESOLVED:
                continue
            ticket.closed_at = ticket.resolved_at + timedelta(
                hours=config.AUTO_CLOSE_HOURS)
            ticket.status = CLOSED
            self._log(ticket, "CLOSE", ticket.closed_at,
                      ticket.opening_alarm_id,
                      f"auto-closed {config.AUTO_CLOSE_HOURS} h after RESOLVE")
