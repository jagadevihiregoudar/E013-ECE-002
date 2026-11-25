"""Priority rules, hub uplift, ordering, duplicates and DG/MAINS linking."""
import unittest

from tests.helpers import EngineTestCase
from src.models import Site
from src import priority

HUB = Site("H", "KA-SOUTH", 3)
PLAIN = Site("P", "KA-SOUTH", 2)


class PriorityTests(unittest.TestCase):
    def test_rssi_boundaries(self):
        self.assertEqual(priority.base_priority("RSSI_LOW", -110.1), "P1")
        self.assertEqual(priority.base_priority("RSSI_LOW", -110.0), "P2")
        self.assertEqual(priority.base_priority("RSSI_LOW", -100.0), "P2")
        self.assertEqual(priority.base_priority("RSSI_LOW", -99.9), "P3")

    def test_vswr_boundary(self):
        self.assertEqual(priority.base_priority("VSWR_HIGH", 2.00), "P3")
        self.assertEqual(priority.base_priority("VSWR_HIGH", 2.01), "P1")

    def test_diesel_boundary(self):
        self.assertEqual(priority.base_priority("DIESEL_LOW", 9.9), "P1")
        self.assertEqual(priority.base_priority("DIESEL_LOW", 10.0), "P2")

    def test_mains_fail_alone_is_p2(self):
        self.assertEqual(priority.base_priority("MAINS_FAIL", 0), "P2")

    def test_hub_threshold_is_three_dependents(self):
        self.assertFalse(Site("S", "C", 2).is_hub)
        self.assertTrue(Site("S", "C", 3).is_hub)

    def test_hub_uplift_levels(self):
        self.assertEqual(priority.apply_hub_uplift("P3", HUB), "P2")
        self.assertEqual(priority.apply_hub_uplift("P2", HUB), "P1")
        self.assertEqual(priority.apply_hub_uplift("P1", HUB), "P1")  # no P0
        self.assertEqual(priority.apply_hub_uplift("P3", PLAIN), "P3")


class TicketCreationTests(EngineTestCase):
    def test_ids_follow_sorted_order_with_out_of_order_row(self):
        self.run_case([
            ("ALM-00001", "SITE-001", "2026-10-01 11:00:00", "RSSI_LOW", -105),
            ("ALM-00002", "SITE-003", "2026-10-01 10:00:00", "RSSI_LOW", -105),
        ])
        self.assertEqual(self.ticket("ALM-00002").ticket_id, "TKT-0001")
        self.assertEqual(self.ticket("ALM-00001").ticket_id, "TKT-0002")

    def test_same_timestamp_ties_broken_by_alarm_id(self):
        self.run_case([
            ("ALM-00005", "SITE-001", "2026-10-01 10:00:00", "RSSI_LOW", -105),
            ("ALM-00004", "SITE-003", "2026-10-01 10:00:00", "RSSI_LOW", -105),
        ])
        self.assertEqual(self.ticket("ALM-00004").ticket_id, "TKT-0001")

    def test_ticket_takes_circle_and_site_from_sites_file(self):
        self.run_case([("ALM-1", "SITE-003", "2026-10-01 10:00:00",
                        "RSSI_LOW", -105)])
        self.assertEqual(self.ticket("ALM-1").circle, "KA-NORTH")

    def test_hub_uplift_applied_to_new_ticket(self):
        self.run_case([
            ("ALM-1", "SITE-002", "2026-10-01 10:00:00", "TX_POWER_LOW", 36),
            ("ALM-2", "SITE-002", "2026-10-01 12:00:00", "RSSI_LOW", -105),
            ("ALM-3", "SITE-002", "2026-10-01 14:00:00", "RSSI_LOW", -115),
        ])
        self.assertEqual(self.ticket("ALM-1").priority, "P2")   # P3 -> P2
        self.assertEqual(self.ticket("ALM-2").priority, "P1")   # P2 -> P1
        self.assertEqual(self.ticket("ALM-3").priority, "P1")   # stays P1


class DuplicateTests(EngineTestCase):
    def _two(self, second_ts, second_type="RSSI_LOW", second_site="SITE-001"):
        self.run_case([
            ("ALM-1", "SITE-001", "2026-10-01 15:00:00", "RSSI_LOW", -105),
            ("ALM-2", second_site, second_ts, second_type, -105),
        ])

    def test_same_time_is_duplicate(self):
        self._two("2026-10-01 15:00:00")
        self.assertEqual(len(self.processor.store.tickets), 1)

    def test_exactly_15_minutes_is_duplicate(self):
        self._two("2026-10-01 15:15:00")
        self.assertEqual(self.ticket("ALM-1").attached_alarm_ids, ["ALM-2"])

    def test_15_minutes_1_second_opens_new_ticket(self):
        self._two("2026-10-01 15:15:01")
        self.assertEqual(len(self.processor.store.tickets), 2)

    def test_other_site_or_type_is_not_duplicate(self):
        self._two("2026-10-01 15:05:00", second_site="SITE-003")
        self.assertEqual(len(self.processor.store.tickets), 2)
        self._two("2026-10-01 15:05:00", second_type="VSWR_HIGH")
        self.assertEqual(len(self.processor.store.tickets), 2)

    def test_window_is_measured_from_opening_alarm_not_last_attached(self):
        self.run_case([
            ("ALM-1", "SITE-001", "2026-10-01 15:00:00", "RSSI_LOW", -105),
            ("ALM-2", "SITE-001", "2026-10-01 15:10:00", "RSSI_LOW", -105),
            ("ALM-3", "SITE-001", "2026-10-01 15:20:00", "RSSI_LOW", -105),
        ])
        self.assertEqual(len(self.processor.store.tickets), 2)
        self.assertEqual(self.ticket("ALM-1").attached_alarm_ids, ["ALM-2"])

    def test_attach_event_logged_after_open(self):
        self._two("2026-10-01 15:10:00")
        events = [row[1] for row in self.processor.store.events]
        self.assertEqual(events, ["OPEN", "ATTACH"])


class DgMainsTests(EngineTestCase):
    def _pair(self, dg_ts, site="SITE-001", dg_site=None):
        self.run_case([
            ("ALM-1", site, "2026-10-01 02:10:00", "MAINS_FAIL", 0),
            ("ALM-2", dg_site or site, dg_ts, "DG_NOT_STARTED", 0),
        ])

    def test_dg_exactly_30_minutes_attaches_and_makes_p1(self):
        self._pair("2026-10-01 02:40:00")
        ticket = self.ticket("ALM-1")
        self.assertEqual(ticket.priority, "P1")
        self.assertEqual(ticket.attached_alarm_ids, ["ALM-2"])

    def test_dg_30_minutes_1_second_is_separate_ticket(self):
        self._pair("2026-10-01 02:40:01")
        self.assertEqual(len(self.processor.store.tickets), 2)
        self.assertEqual(self.ticket("ALM-1").priority, "P2")

    def test_dg_on_other_site_is_separate(self):
        self._pair("2026-10-01 02:20:00", dg_site="SITE-003")
        self.assertEqual(len(self.processor.store.tickets), 2)

    def test_dg_before_mains_does_not_attach(self):
        self.run_case([
            ("ALM-1", "SITE-001", "2026-10-01 02:10:00", "DG_NOT_STARTED", 0),
            ("ALM-2", "SITE-001", "2026-10-01 02:20:00", "MAINS_FAIL", 0),
        ])
        self.assertEqual(len(self.processor.store.tickets), 2)

    def test_dg_on_hub_stays_p1(self):
        self._pair("2026-10-01 02:20:00", site="SITE-002")
        self.assertEqual(self.ticket("ALM-1").priority, "P1")

    def test_attach_event_carries_new_priority(self):
        self._pair("2026-10-01 02:20:00")
        attach = self.processor.store.events[1]
        self.assertEqual((attach[1], attach[5]), ("ATTACH", "P1"))

    def test_second_mains_fail_inside_15_min_is_duplicate(self):
        self.run_case([
            ("ALM-1", "SITE-001", "2026-10-01 02:00:00", "MAINS_FAIL", 0),
            ("ALM-2", "SITE-001", "2026-10-01 02:10:00", "MAINS_FAIL", 0),
        ])
        self.assertEqual(len(self.processor.store.tickets), 1)


if __name__ == "__main__":
    unittest.main()
