
"""End-to-end check of the scenarios planted in the sample-data README."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

import config
import main
from src import sla
from tests.helpers import ROOT

SAMPLE = os.path.join(ROOT, "sample_data")


@unittest.skipUnless(os.path.exists(os.path.join(SAMPLE, "commands.txt")),
                     "sample_data folder not present")
class SampleDataScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = tempfile.mkdtemp()
        cls.processor = main.run(SAMPLE, output_dir=cls.out)
        cls.store = cls.processor.store

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.out, True)

    def t(self, alarm_id):
        return self.store.by_opening_alarm[alarm_id]

    def test_row_counts(self):
        self.assertEqual(
            len(self.store.by_opening_alarm)
            + sum(len(t.attached_alarm_ids)
                  for t in self.store.tickets.values()),
            1202
        )

    def test_dg_exactly_30_minutes_makes_p1(self):
        ticket = self.t("ALM-00196")
        self.assertEqual(ticket.priority, "P1")
        self.assertIn("ALM-00197", ticket.attached_alarm_ids)

    def test_hub_uplift_scenarios(self):
        self.assertEqual(self.t("ALM-00253").priority, "P1")
        self.assertEqual(self.t("ALM-00255").priority, "P2")
        self.assertEqual(self.t("ALM-00257").priority, "P1")

    def test_duplicate_15_min_1_second_opens_new_ticket(self):
        self.assertIn("ALM-00340", self.store.by_opening_alarm)
        self.assertIn("ALM-00339", self.store.by_opening_alarm)

    def test_true_duplicate_is_attached(self):
        self.assertIn(
            "ALM-00349",
            self.t("ALM-00348").attached_alarm_ids
        )

    def test_resolved_exactly_at_deadline_has_no_penalty(self):
        ticket = self.t("ALM-00430")
        self.assertEqual(ticket.priority, "P2")
        result = sla.evaluate(ticket)
        self.assertEqual(
            (result.resolution_breached, result.penalty_rs),
            (False, 0)
        )

    def test_reopen_after_close_rejected_at_line_1058(self):
        self.assertIn(1058, [e[0] for e in self.processor.errors])
        self.assertEqual(self.t("ALM-00508").status, "CLOSED")

    def test_penalty_cap(self):
        result = sla.evaluate(self.t("ALM-00673"))
        self.assertEqual((result.hours_late, result.penalty_rs), (24, 10000))

    def test_resolve_before_assign_rejected_then_valid(self):
        self.assertIn(1434, [e[0] for e in self.processor.errors])
        ticket = self.t("ALM-00762")
        self.assertEqual(ticket.status, "CLOSED")
        self.assertEqual(
            str(ticket.resolved_at),
            "2026-10-20 19:00:00"
        )

    def test_unknown_alarm_id_rejected_at_line_1576(self):
        self.assertIn(1576, [e[0] for e in self.processor.errors])

    def test_boundary_values(self):
        self.assertEqual(self.t("ALM-00599").priority, "P2")
        self.assertEqual(self.t("ALM-00601").priority, "P2")
        self.assertEqual(self.t("ALM-00604").priority, "P3")
        self.assertEqual(self.t("ALM-00605").priority, "P2")

    def test_out_of_order_row_sorted(self):
        ids = [t.opening_alarm_id for t in self.store.tickets.values()]
        self.assertLess(
            ids.index("ALM-00402"),
            ids.index("ALM-00401") + 3
        )
        times = [t.opened_at for t in self.store.tickets.values()]
        self.assertEqual(times, sorted(times))

    def test_reopen_within_24h_keeps_open_time(self):
        ticket = self.t("ALM-00903")
        self.assertEqual(
            str(ticket.resolved_at),
            "2026-10-25 06:44:00"
        )
        self.assertEqual(
            str(ticket.opened_at),
            "2026-10-24 00:03:00"
        )
        events = [
            e[1] for e in self.store.events
            if e[0] == ticket.ticket_id
        ]
        self.assertIn("REOPEN", events)

    def test_every_rejection_is_explained_and_expected(self):
        # 3 planted rejections + 2 unlisted duplicate lifecycle lines.
        self.assertEqual(
            sorted(e[0] for e in self.processor.errors),
            [1058, 1434, 1576, 1718, 1735]
        )

    def test_configured_response_sla_counts_breaches(self):
        self.assertTrue(
            all(r[5] > 0 for r in self.processor.report_rows)
        )

    def test_report_has_one_row_per_circle(self):
        self.assertEqual(
            [r[:2] for r in self.processor.report_rows],
            [["2026-10", "KA-NORTH"], ["2026-10", "KA-SOUTH"]]
        )

    def test_input_files_untouched_and_outputs_written(self):
        for name in (
            "ticket_events.csv",
            "tickets.csv",
            "sla_report.csv",
            "errors.csv"
        ):
            self.assertTrue(os.path.exists(os.path.join(self.out, name)))

    def test_sample_run_is_deterministic(self):
        second = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, second, True)
        main.run(SAMPLE, output_dir=second)

        for name in ("tickets.csv", "ticket_events.csv", "sla_report.csv"):
            with open(os.path.join(self.out, name)) as a, \
                    open(os.path.join(second, name)) as b:
                self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()
