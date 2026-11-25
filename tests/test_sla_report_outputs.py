"""SLA, penalty, monthly report, loader validation and CSV output format."""
import unittest
from unittest import mock

import config
from tests.helpers import EngineTestCase, alarm_csv
from src import sla

SLA_VALUES = dict(
    RESPONSE_SLA_MINUTES={"P1": 30, "P2": 60, "P3": 120},
    RESOLUTION_SLA_HOURS={"P1": 6, "P2": 24, "P3": 72},
    PENALTY_RATE_PER_HOUR={"P1": 500, "P2": 200, "P3": 100},
)
P1_ALARM = [("ALM-1", "SITE-001", "2026-10-01 10:00:00", "RSSI_LOW", -115)]
P2_ALARM = [("ALM-1", "SITE-001", "2026-10-01 10:00:00", "MAINS_FAIL", 0)]


def patched(**overrides):
    values = dict(SLA_VALUES)
    values.update(overrides)
    return mock.patch.multiple(config, **values)


class SlaTests(EngineTestCase):
    def _result(self, alarms, resolve_ts, assign_ts="2026-10-01 10:10:00"):
        self.run_case(alarms, [f"ASSIGN|ALM-1|ENG-01|{assign_ts}",
                               f"RESOLVE|ALM-1|{resolve_ts}"])
        return sla.evaluate(self.ticket("ALM-1"))

    def test_resolved_exactly_at_deadline_no_penalty(self):
        with patched():
            result = self._result(P2_ALARM, "2026-10-02 10:00:00")
        self.assertEqual((result.resolution_breached, result.penalty_rs),
                         (False, 0))

    def test_one_second_late_is_breach_but_zero_full_hours(self):
        with patched():
            result = self._result(P2_ALARM, "2026-10-02 10:00:01")
        self.assertTrue(result.resolution_breached)
        self.assertEqual((result.hours_late, result.penalty_rs), (0, 0))

    def test_hours_late_counts_full_hours_only(self):
        with patched():
            result = self._result(P2_ALARM, "2026-10-02 12:59:59")
        self.assertEqual(result.hours_late, 2)
        self.assertEqual(result.penalty_rs, 400)

    def test_p1_penalty_cap(self):
        # P1 SLA 6 h; resolved after 30 h -> 24 h late -> 12000 -> cap 10000
        with patched():
            result = self._result(P1_ALARM, "2026-10-02 16:00:00")
        self.assertEqual((result.hours_late, result.penalty_rs), (24, 10000))

    def test_p1_penalty_below_cap(self):
        with patched():
            result = self._result(P1_ALARM, "2026-10-01 20:00:00")  # 4 h late
        self.assertEqual(result.penalty_rs, 2000)

    def test_resolution_measured_from_original_open_after_reopen(self):
        with patched():
            self.run_case(P2_ALARM, [
                "ASSIGN|ALM-1|ENG-01|2026-10-01 10:30:00",
                "RESOLVE|ALM-1|2026-10-01 20:00:00",
                "REOPEN|ALM-1|2026-10-02 06:00:00",
                "RESOLVE|ALM-1|2026-10-02 13:00:00"])   # 27 h after open
            result = sla.evaluate(self.ticket("ALM-1"))
        self.assertEqual(result.hours_late, 3)

    def test_response_breach_is_strictly_greater(self):
        with patched():
            on_time = self._result(P1_ALARM, "2026-10-01 11:00:00",
                                   assign_ts="2026-10-01 10:30:00")
            late = self._result(P1_ALARM, "2026-10-01 11:00:00",
                                assign_ts="2026-10-01 10:30:01")
        self.assertFalse(on_time.response_breached)
        self.assertTrue(late.response_breached)

    def test_unassigned_or_unresolved_ticket_not_breached(self):
        with patched():
            self.run_case(P1_ALARM, [])
            result = sla.evaluate(self.ticket("ALM-1"))
        self.assertEqual(tuple(result), (False, False, 0, 0))

    def test_default_config_applies_p2_sla_and_penalty(self):
        result = self._result(P2_ALARM, "2026-10-05 10:00:00")
        self.assertFalse(result.response_breached)
        self.assertTrue(result.resolution_breached)
        self.assertEqual(result.penalty_rs, 10000)

    def test_p2_penalty_rate_when_configured(self):
        with patched():
            result = self._result(P2_ALARM, "2026-10-02 14:00:00")
        self.assertEqual(result.penalty_rs, 800)


class ReportTests(EngineTestCase):
    ALARMS = [
        ("ALM-1", "SITE-001", "2026-10-01 10:00:00", "RSSI_LOW", -115),
        ("ALM-2", "SITE-003", "2026-10-02 10:00:00", "MAINS_FAIL", 0),
        ("ALM-3", "SITE-003", "2026-10-03 10:00:00", "RSSI_LOW", -95),
        ("ALM-4", "SITE-001", "2026-11-01 10:00:00", "RSSI_LOW", -115),
    ]

    def test_counts_per_circle_and_month(self):
        with patched():
            self.run_case(self.ALARMS, [
                "ASSIGN|ALM-1|ENG-01|2026-10-01 10:10:00",
                "RESOLVE|ALM-1|2026-10-01 20:00:00",   # 4 h late -> 2000
                "REPORT|2026-10"])
        rows = {row[1]: row for row in self.processor.report_rows}
        self.assertEqual(rows["KA-SOUTH"],
                         ["2026-10", "KA-SOUTH", 1, 0, 0, 0, 1, "2000.00"])
        self.assertEqual(rows["KA-NORTH"],
                         ["2026-10", "KA-NORTH", 0, 1, 1, 0, 0, "0.00"])

    def test_circle_without_tickets_still_gets_a_row(self):
        self.run_case(self.ALARMS[:1], ["REPORT|2026-12"])
        self.assertEqual(len(self.processor.report_rows), 2)
        self.assertTrue(all(r[2:7] == [0, 0, 0, 0, 0]
                            for r in self.processor.report_rows))

    def test_rows_sorted_by_circle(self):
        self.run_case(self.ALARMS, ["REPORT|2026-10"])
        self.assertEqual([r[1] for r in self.processor.report_rows],
                         ["KA-NORTH", "KA-SOUTH"])


class LoaderValidationTests(EngineTestCase):
    def test_bad_alarm_rows_rejected_with_csv_line_numbers(self):
        text = (alarm_csv([("ALM-1", "SITE-001", "2026-10-01 10:00:00",
                            "RSSI_LOW", -105)])
                + "ALM-2,SITE-999,2026-10-01 10:00:00,RSSI_LOW,-105,dBm\n"
                + "ALM-3,SITE-001,not-a-time,RSSI_LOW,-105,dBm\n"
                + "ALM-4,SITE-001,2026-10-01 10:00:00,RSSI_LOW,abc,dBm\n"
                + "ALM-5,SITE-001,2026-10-01 10:00:00,WEIRD,1,dBm\n"
                + "ALM-1,SITE-001,2026-10-01 10:00:00,RSSI_LOW,-105,dBm\n"
                + "ALM-7,SITE-001\n")
        self.run_case([], alarms_text=text)
        self.assertEqual([e[0] for e in self.processor.errors],
                         [3, 4, 5, 6, 7, 8])
        self.assertEqual(len(self.processor.store.tickets), 1)

    def test_missing_file_logged_and_run_continues(self):
        self.run_case([], ["LOAD_ALARMS|nope.csv", "BAD|x"])
        self.assertEqual(len(self.processor.errors), 2)

    def test_missing_header_column_rejected(self):
        self.run_case([], alarms_text="alarm_id,site_id\nALM-1,SITE-001\n")
        self.assertIn("missing column", self.error_reasons()[0])

    def test_empty_alarm_file_is_not_a_crash(self):
        self.run_case([], alarms_text="")
        self.assertEqual(len(self.processor.store.tickets), 0)

    def test_bad_site_and_engineer_rows(self):
        sites = ("site_id,site_name,circle,city,is_hub,dependent_sites\n"
                 "SITE-001,A,KA-SOUTH,X,false,x\n"
                 "SITE-002,A,KA-SOUTH,X,false,1\n"
                 "SITE-002,A,KA-SOUTH,X,false,1\n")
        engineers = ("engineer_id,engineer_name,circle,mobile\n"
                     "ENG-01,A,KA-SOUTH,1\nENG-01,A,KA-SOUTH,1\n")
        self.run_case([], sites=sites, engineers=engineers)
        self.assertEqual(len(self.processor.errors), 3)
        self.assertEqual(list(self.processor.sites), ["SITE-002"])

    def test_second_load_alarms_rejects_already_known_ids(self):
        self.run_case(P1_ALARM, ["LOAD_ALARMS|alarms.csv"])
        self.assertEqual(len(self.processor.store.tickets), 1)
        self.assertIn("duplicate alarm_id", self.error_reasons()[0])


class OutputFormatTests(EngineTestCase):
    def setUp(self):
        self.run_case(
            [("ALM-1", "SITE-001", "2026-10-01 10:00:00", "RSSI_LOW", -115),
             ("ALM-2", "SITE-001", "2026-10-01 10:05:00", "RSSI_LOW", -115),
             ("ALM-3", "SITE-003", "2026-10-01 10:00:00", "MAINS_FAIL", 0)],
            ["ASSIGN|ALM-1|ENG-01|2026-10-01 11:00:00",
             "RESOLVE|ALM-1|2026-10-01 20:00:00", "BAD|line", "REPORT|2026-10"])

    def test_headers_exact(self):
        self.assertEqual(self.read_csv("ticket_events.csv")[0], [
            "ticket_id", "event", "timestamp", "alarm_id", "engineer_id",
            "priority", "detail"])
        self.assertEqual(self.read_csv("tickets.csv")[0], [
            "ticket_id", "opening_alarm_id", "site_id", "circle",
            "alarm_type", "priority", "opened_at", "assigned_at",
            "resolved_at", "closed_at", "final_status",
            "attached_alarm_count", "response_breached",
            "resolution_breached", "hours_late", "penalty_rs"])
        self.assertEqual(self.read_csv("sla_report.csv")[0], [
            "month", "circle", "p1_tickets", "p2_tickets", "p3_tickets",
            "response_breaches", "resolution_breaches", "penalty_rs"])
        self.assertEqual(self.read_csv("errors.csv")[0],
                         ["line_no", "command", "reason"])

    def test_ticket_rows_use_none_and_lowercase_booleans(self):
        rows = {r[0]: r for r in self.read_csv("tickets.csv")[1:]}
        closed, untouched = rows["TKT-0001"], rows["TKT-0002"]
        self.assertEqual(closed[10], "CLOSED")
        self.assertEqual(closed[9], "2026-10-02 20:00:00")
        self.assertEqual(closed[11], "1")                  # one attached
        self.assertIn(closed[12], ("true", "false"))
        self.assertEqual(untouched[7:10], ["NONE", "NONE", "NONE"])
        self.assertEqual(untouched[10], "OPEN")

    def test_event_rows(self):
        events = self.read_csv("ticket_events.csv")[1:]
        self.assertEqual([e[1] for e in events],
                         ["OPEN", "OPEN", "ATTACH", "ASSIGN", "RESOLVE",
                          "CLOSE"])   # alarms are processed in time order
        self.assertEqual(events[0][4], "NONE")           # engineer_id
        self.assertEqual(events[3][4], "ENG-01")

    def test_one_error_row(self):
        self.assertEqual(len(self.read_csv("errors.csv")), 2)

    def test_one_ticket_row_per_ticket(self):
        self.assertEqual(len(self.read_csv("tickets.csv")), 3)  # header + 2


if __name__ == "__main__":
    unittest.main()
