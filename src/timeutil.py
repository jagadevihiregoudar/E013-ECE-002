"""Timestamp helpers.  All timestamps are 'YYYY-MM-DD HH:MM:SS' (IST, no zone)."""
from datetime import datetime

TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_timestamp(text):
    """Parse a timestamp strictly; raise ValueError if the format is wrong."""
    text = (text or "").strip()
    if len(text) != 19:  # blocks sloppy forms such as 2026-1-1 1:1:1
        raise ValueError(f"invalid timestamp '{text}'")
    try:
        return datetime.strptime(text, TS_FORMAT)
    except ValueError:
        raise ValueError(f"invalid timestamp '{text}'") from None


def format_timestamp(value, none_text="NONE"):
    """Format a datetime for output; None becomes the NONE marker."""
    return none_text if value is None else value.strftime(TS_FORMAT)
