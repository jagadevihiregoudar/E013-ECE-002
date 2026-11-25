"""CSV loading with row-level validation.

Every loader returns (valid_items, errors).  An error is a tuple
(line_no, command, reason) where line_no is the physical line in the CSV
(header = line 1).  Bad rows are skipped; the rest of the file is still loaded.
"""
import csv

import config
from .models import Alarm, Engineer, Site
from .timeutil import parse_timestamp


def _read_rows(path, command, required_columns):
    """Return ([(line_no, row_dict)], errors) for a CSV file."""
    errors = []
    rows = []
    try:
        handle = open(path, newline="", encoding="utf-8-sig")
    except OSError as exc:
        return rows, [(0, command, f"cannot open file '{path}': {exc.strerror}")]
    with handle:
        reader = csv.reader(handle)
        header = None
        for raw in reader:
            if header is None:
                header = [col.strip() for col in raw]
                missing = [c for c in required_columns if c not in header]
                if missing:
                    return rows, [(reader.line_num, command,
                                   "missing column(s): " + ",".join(missing))]
                continue
            if not any(cell.strip() for cell in raw):
                continue  # blank line
            if len(raw) != len(header):
                errors.append((reader.line_num, command,
                               f"expected {len(header)} fields, got {len(raw)}"))
                continue
            rows.append((reader.line_num,
                         {h: v.strip() for h, v in zip(header, raw)}))
    return rows, errors


def load_sites(path):
    rows, errors = _read_rows(path, "LOAD_SITES",
                              ["site_id", "circle", "dependent_sites"])
    sites = {}
    for line_no, row in rows:
        if not row["site_id"] or not row["circle"]:
            errors.append((line_no, "LOAD_SITES", "empty site_id or circle"))
            continue
        if row["site_id"] in sites:
            errors.append((line_no, "LOAD_SITES",
                           f"duplicate site_id {row['site_id']}"))
            continue
        try:
            dependent = int(row["dependent_sites"])
            if dependent < 0:
                raise ValueError
        except ValueError:
            errors.append((line_no, "LOAD_SITES",
                           f"invalid dependent_sites '{row['dependent_sites']}'"))
            continue
        sites[row["site_id"]] = Site(row["site_id"], row["circle"], dependent)
    return sites, errors


def load_engineers(path):
    rows, errors = _read_rows(path, "LOAD_ENGINEERS",
                              ["engineer_id", "circle"])
    engineers = {}
    for line_no, row in rows:
        if not row["engineer_id"] or not row["circle"]:
            errors.append((line_no, "LOAD_ENGINEERS",
                           "empty engineer_id or circle"))
            continue
        if row["engineer_id"] in engineers:
            errors.append((line_no, "LOAD_ENGINEERS",
                           f"duplicate engineer_id {row['engineer_id']}"))
            continue
        engineers[row["engineer_id"]] = Engineer(row["engineer_id"],
                                                 row["circle"])
    return engineers, errors


def load_alarms(path, sites, known_alarm_ids=()):
    """Load alarms; reject unknown sites/types, bad timestamps and values."""
    required = ["alarm_id", "site_id", "timestamp", "alarm_type",
                "measured_value"]
    rows, errors = _read_rows(path, "LOAD_ALARMS", required)
    alarms = []
    seen = set(known_alarm_ids)
    for line_no, row in rows:
        alarm_id = row["alarm_id"]
        if not alarm_id:
            errors.append((line_no, "LOAD_ALARMS", "empty alarm_id"))
            continue
        if alarm_id in seen:
            errors.append((line_no, "LOAD_ALARMS",
                           f"duplicate alarm_id {alarm_id}"))
            continue
        if row["site_id"] not in sites:
            errors.append((line_no, "LOAD_ALARMS",
                           f"{alarm_id}: unknown site_id '{row['site_id']}'"))
            continue
        if row["alarm_type"] not in config.PRIORITY_RULES:
            errors.append((line_no, "LOAD_ALARMS",
                           f"{alarm_id}: unknown alarm_type "
                           f"'{row['alarm_type']}'"))
            continue
        try:
            timestamp = parse_timestamp(row["timestamp"])
        except ValueError as exc:
            errors.append((line_no, "LOAD_ALARMS", f"{alarm_id}: {exc}"))
            continue
        try:
            value = float(row["measured_value"])
        except ValueError:
            errors.append((line_no, "LOAD_ALARMS",
                           f"{alarm_id}: invalid measured_value "
                           f"'{row['measured_value']}'"))
            continue
        seen.add(alarm_id)
        alarms.append(Alarm(alarm_id, row["site_id"], timestamp,
                            row["alarm_type"], value))
    return alarms, errors
