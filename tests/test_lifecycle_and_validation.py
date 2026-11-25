"""Lifecycle transitions, auto-close and command validation."""
import unittest
from unittest import mock

import config
from tests.helpers import EngineTestCase

ONE = [("ALM-1", "SITE-001", "2026-10-01 10:00:00", "RSSI_LOW", -105)]
ASSIGN = "ASSIGN|ALM-1|ENG-01|2026-10-01 11:00:00"
RESOLVE = "RESOLVE|ALM-1|2026-10-01 20:00:00"


class LifecycleTests(EngineTestCase):
    def test_assign_then_resolve(self):
        self.run_case(ONE, [ASSIGN, RESOLVE])
        ticket = self.ticket("ALM-1")
        self.assertEqual(ticket.status, "RESOLVED")
        self.assertEqual(ticket.engineer_id, "ENG-01")
        self.assertEqual(self.processor.errors, [])

    def test_resolve_before_assign_rejected(self):
        self.run_case(ONE, [RESOLVE, ASSIGN, RESOLVE])
        self.assertEqual(len(self.processor.errors), 1)
        self.assertEqual(self.processor.errors[0][0], 4)   # physical line
        self.assertEqual(self.ticket("ALM-1").status, "RESOLVED")

    def test_second_assign_rejected(self):
        self.run_case(ONE, [ASSIGN, "ASSIGN|ALM-1|ENG-01|2026-10-01 12:00:00"])
        self.assertEqual(len(self.processor.errors), 1)
        self.assertEqual(self.ticket("ALM-1").assigned_at.hour, 11)

    def test_reopen_exactly_24h_after_resolve_allowed(self):
        self.run_case(ONE, [ASSIGN, RESOLVE,
                            "REOPEN|ALM-1|2026-10-02 20:00:00"])
        self.assertEqual(self.ticket("ALM-1").status, "ASSIGNED")
        self.assertEqual(self.processor.errors, [])

    def test_reopen_after_24h_rejected(self):
        self.run_case(ONE, [ASSIGN, RESOLVE,
                            "REOPEN|ALM-1|2026-10-02 20:00:01"])
        self.assertEqual(self.ticket("ALM-1").status, "RESOLVED")
        self.assertIn("CLOSED", self.error_reasons()[0])

    def test_reopen_on_open_or_assigned_ticket_rejected(self):
        self.run_case(ONE, ["REOPEN|ALM-1|2026-10-01 10:30:00", ASSIGN,
                            "REOPEN|ALM-1|2026-10-01 11:30:00"])
        self.assertEqual(len(self.processor.errors), 2)

    def test_reopen_keeps_original_open_time_and_clears_resolved_at(self):
        self.run_case(ONE, [ASSIGN, RESOLVE,
                            "REOPEN|ALM-1|2026-10-02 06:00:00"])
        ticket = self.ticket("ALM-1")
        self.assertEqual(str(ticket.opened_at), "2026-10-01 10:00:00")
        self.assertIsNone(ticket.resolved_at)

    def test_resolve_again_after_reopen(self):
        self.run_case(ONE, [ASSIGN, RESOLVE,
                            "REOPEN|ALM-1|2026-10-02 06:00:00",
                            "RESOLVE|ALM-1|2026-10-02 09:00:00"])
        self.assertEqual(str(self.ticket("ALM-1").resolved_at),
                         "2026-10-02 09:00:00")

    def test_report_auto_closes_resolved_ticket(self):
        self.run_case(ONE, [ASSIGN, RESOLVE, "REPORT|2026-10"])
        ticket = self.ticket("ALM-1")
        self.assertEqual(ticket.status, "CLOSED")
        self.assertEqual(str(ticket.closed_at), "2026-10-02 20:00:00")
        self.assertEqual(self.processor.store.events[-1][1], "CLOSE")

    def test_report_does_not_close_unresolved_tickets(self):
        self.run_case(ONE, [ASSIGN, "REPORT|2026-10"])
        self.assertEqual(self.ticket("ALM-1").status, "ASSIGNED")

    def test_reopen_after_report_rejected_as_closed(self):
        self.run_case(ONE, [ASSIGN, RESOLVE, "REPORT|2026-10",
                            "REOPEN|ALM-1|2026-10-01 21:00:00"])
        self.assertIn("already CLOSED", self.error_reasons()[0])

    def test_backwards_timestamp_rejected(self):
        self.run_case(ONE, ["ASSIGN|ALM-1|ENG-01|2026-10-01 09:00:00"])
        self.assertEqual(len(self.processor.errors), 1)
        self.assertEqual(self.ticket("ALM-1").status, "OPEN")

    def test_time_order_check_can_be_disabled(self):
        with mock.patch.object(config, "ENFORCE_TIME_ORDER", False):
            self.run_case(ONE, ["ASSIGN|ALM-1|ENG-01|2026-10-01 09:00:00"])
        self.assertEqual(self.ticket("ALM-1").status, "ASSIGNED")


class ValidationTests(EngineTestCase):
    def test_unknown_alarm_id_rejected_and_nothing_changes(self):
        self.run_case(ONE, ["ASSIGN|ALM-99999|ENG-01|2026-10-01 11:00:00"])
        self.assertIn("unknown alarm id", self.error_reasons()[0])
        self.assertEqual(self.ticket("ALM-1").status, "OPEN")

    def test_unknown_engineer_rejected(self):
        self.run_case(ONE, ["ASSIGN|ALM-1|ENG-77|2026-10-01 11:00:00"])
        self.assertIn("unknown engineer", self.error_reasons()[0])

    def test_engineer_circle_check_when_enabled(self):
        with mock.patch.object(config, "ENFORCE_ENGINEER_CIRCLE", True):
            self.run_case(ONE, ["ASSIGN|ALM-1|ENG-02|2026-10-01 11:00:00"])
        self.assertEqual(len(self.processor.errors), 1)

    def test_engineer_circle_not_enforced_by_default(self):
        self.run_case(ONE, ["ASSIGN|ALM-1|ENG-02|2026-10-01 11:00:00"])
        self.assertEqual(self.processor.errors, [])

    def test_attached_alarm_id_is_not_an_opening_alarm(self):
        self.run_case([
            ("ALM-1", "SITE-001", "2026-10-01 10:00:00", "RSSI_LOW", -105),
            ("ALM-2", "SITE-001", "2026-10-01 10:05:00", "RSSI_LOW", -105)],
            ["ASSIGN|ALM-2|ENG-01|2026-10-01 11:00:00"])
        self.assertIn("not an opening alarm", self.error_reasons()[0])

    def test_invalid_timestamp_rejected(self):
        self.run_case(ONE, ["ASSIGN|ALM-1|ENG-01|2026-13-45 99:00:00",
                            "ASSIGN|ALM-1|ENG-01|2026-10-1 9:00:00"])
        self.assertEqual(len(self.processor.errors), 2)

    def test_unknown_command_and_wrong_argument_count(self):
        self.run_case(ONE, ["FLY|ALM-1", "ASSIGN|ALM-1|ENG-01", "RESOLVE"])
        self.assertEqual(len(self.processor.errors), 3)

    def test_invalid_report_month(self):
        self.run_case(ONE, ["REPORT|2026-13", "REPORT|Oct-2026"])
        self.assertEqual(len(self.processor.errors), 2)
        self.assertEqual(self.processor.report_rows, [])

    def test_comments_and_blank_lines_ignored_but_counted_in_line_no(self):
        self.run_case(ONE, ["# comment", "", "BAD|x"])
        self.assertEqual(self.processor.errors[0][0], 6)

    def test_run_continues_after_error(self):
        self.run_case(ONE, ["BAD|x", ASSIGN, RESOLVE])
        self.assertEqual(self.ticket("ALM-1").status, "RESOLVED")

    def test_alarms_before_sites_rejected(self):
        self.run_case(ONE, ["ASSIGN|ALM-1|ENG-01|2026-10-01 11:00:00"],
                      with_loads=False)
        self.assertEqual(len(self.processor.errors), 1)


if __name__ == "__main__":
    unittest.main()
