"""Shared helpers: build a tiny data set in a temp folder and run the engine."""
import csv
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import main  # noqa: E402

SITES = ("site_id,site_name,circle,city,is_hub,dependent_sites\n"
         "SITE-001,A,KA-SOUTH,X,false,0\n"
         "SITE-002,B,KA-SOUTH,X,true,3\n"
         "SITE-003,C,KA-NORTH,Y,false,1\n"
         "SITE-004,D,KA-NORTH,Y,false,2\n")
ENGINEERS = ("engineer_id,engineer_name,circle,mobile\n"
             "ENG-01,A,KA-SOUTH,7000000000\n"
             "ENG-02,B,KA-NORTH,7000000001\n")
ALARM_HEADER = "alarm_id,site_id,timestamp,alarm_type,measured_value,unit\n"
LOADS = ["LOAD_SITES|sites.csv", "LOAD_ENGINEERS|engineers.csv",
         "LOAD_ALARMS|alarms.csv"]


def alarm_csv(rows):
    """rows: iterable of (alarm_id, site, timestamp, type, value)."""
    return ALARM_HEADER + "".join(
        f"{a},{s},{t},{k},{v},-\n" for a, s, t, k, v in rows)


class EngineTestCase(unittest.TestCase):
    def run_case(self, alarms, commands=(), sites=SITES, engineers=ENGINEERS,
                 alarms_text=None, with_loads=True):
        """Run the engine; returns the CommandProcessor.  Outputs go to
        self.out_dir."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        self.out_dir = os.path.join(folder, "out")
        with open(os.path.join(folder, "sites.csv"), "w") as handle:
            handle.write(sites)
        with open(os.path.join(folder, "engineers.csv"), "w") as handle:
            handle.write(engineers)
        with open(os.path.join(folder, "alarms.csv"), "w") as handle:
            handle.write(alarms_text if alarms_text is not None
                         else alarm_csv(alarms))
        lines = (LOADS if with_loads else []) + list(commands)
        with open(os.path.join(folder, "commands.txt"), "w") as handle:
            handle.write("\n".join(lines) + "\n")
        self.processor = main.run(folder, output_dir=self.out_dir)
        return self.processor

    def ticket(self, opening_alarm_id):
        return self.processor.store.by_opening_alarm[opening_alarm_id]

    def read_csv(self, name):
        with open(os.path.join(self.out_dir, name), newline="") as handle:
            return list(csv.reader(handle))

    def error_reasons(self):
        return [reason for _, _, reason in self.processor.errors]
