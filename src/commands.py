"""Command-file parser and dispatcher.

Each line is COMMAND|arg1|arg2|...  Lines starting with '#' and blank lines
are ignored.  A bad command is logged to errors.csv and processing continues.
"""
import os
import re

import config
from . import loader, reports
from .tickets import RejectedCommand, TicketStore
from .timeutil import parse_timestamp

# command name -> number of arguments
ARG_COUNTS = {"LOAD_SITES": 1, "LOAD_ENGINEERS": 1, "LOAD_ALARMS": 1,
              "ASSIGN": 3, "RESOLVE": 2, "REOPEN": 2, "REPORT": 1}
MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class CommandProcessor:
    def __init__(self, base_dir="."):
        self.base_dir = base_dir
        self.sites = {}
        self.engineers = {}
        self.store = TicketStore()
        self.errors = []          # (line_no, command, reason)
        self.report_rows = []
        self.messages = []        # text printed after each REPORT

    # ---------------------------------------------------------------- run
    def run_file(self, path):
        try:
            with open(path, encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except OSError as exc:
            self.errors.append((0, "COMMAND_FILE",
                                f"cannot open '{path}': {exc.strerror}"))
            return
        self.run_lines(lines)

    def run_lines(self, lines):
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text or text.startswith("#"):
                continue
            try:
                self._execute(line_no, text)
            except RejectedCommand as exc:
                self.errors.append((line_no, text, str(exc)))
            except Exception as exc:  # never let one line crash the run
                self.errors.append((line_no, text, f"internal error: {exc}"))

    # ----------------------------------------------------------- dispatch
    def _execute(self, line_no, text):
        parts = [part.strip() for part in text.split("|")]
        name, args = parts[0], parts[1:]
        if name not in ARG_COUNTS:
            raise RejectedCommand(f"unknown command '{name}'")
        if len(args) != ARG_COUNTS[name]:
            raise RejectedCommand(
                f"{name} expects {ARG_COUNTS[name]} argument(s), "
                f"got {len(args)}")
        getattr(self, "_do_" + name.lower())(*args)

    def _path(self, filename):
        if os.path.isabs(filename):
            return filename
        return os.path.join(self.base_dir, filename)

    def _merge_errors(self, load_errors):
        # errors from one CSV are reported in file-line order
        self.errors.extend(sorted(load_errors, key=lambda err: err[0]))

    def _do_load_sites(self, filename):
        sites, errors = loader.load_sites(self._path(filename))
        self.sites.update(sites)
        self._merge_errors(errors)

    def _do_load_engineers(self, filename):
        engineers, errors = loader.load_engineers(self._path(filename))
        self.engineers.update(engineers)
        self._merge_errors(errors)

    def _do_load_alarms(self, filename):
        if not self.sites:
            raise RejectedCommand("LOAD_ALARMS before sites were loaded")
        alarms, errors = loader.load_alarms(
            self._path(filename), self.sites, self.store.alarm_to_ticket)
        self._merge_errors(errors)
        self.store.add_alarms(alarms, self.sites)

    def _parse_ts(self, text):
        try:
            return parse_timestamp(text)
        except ValueError as exc:
            raise RejectedCommand(str(exc)) from None

    def _do_assign(self, alarm_id, engineer_id, timestamp):
        ticket = self.store.get_ticket(alarm_id)       # unknown id first
        engineer = self.engineers.get(engineer_id)
        if engineer is None:
            raise RejectedCommand(f"unknown engineer id {engineer_id}")
        if (config.ENFORCE_ENGINEER_CIRCLE
                and engineer.circle != ticket.circle):
            raise RejectedCommand(
                f"engineer {engineer_id} ({engineer.circle}) is not in "
                f"circle {ticket.circle}")
        self.store.assign(alarm_id, engineer_id, self._parse_ts(timestamp))

    def _do_resolve(self, alarm_id, timestamp):
        self.store.get_ticket(alarm_id)
        self.store.resolve(alarm_id, self._parse_ts(timestamp))

    def _do_reopen(self, alarm_id, timestamp):
        self.store.get_ticket(alarm_id)
        self.store.reopen(alarm_id, self._parse_ts(timestamp))

    def _do_report(self, month):
        if not MONTH_PATTERN.match(month):
            raise RejectedCommand(f"invalid month '{month}', expected YYYY-MM")
        self.store.auto_close_resolved()
        circles = {site.circle for site in self.sites.values()}
        circles |= {t.circle for t in self.store.tickets.values()}
        rows = reports.build_monthly_report(
            list(self.store.tickets.values()), month, circles)
        self.report_rows.extend(rows)
        self.messages.append(f"SLA report for {month}")
        self.messages.append(" | ".join(reports.REPORT_COLUMNS))
        self.messages.extend(" | ".join(str(c) for c in row) for row in rows)
