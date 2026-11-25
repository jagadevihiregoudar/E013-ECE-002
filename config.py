
"""Business-rule configuration for E013-ECE-002.

Values are taken from the original 10 SECONDS assignment brief.
"""

PRIORITIES = ("P1", "P2", "P3")

# Unspecified alarm types default to P3.
DEFAULT_PRIORITY = "P3"

# Priority rules: first matching rule wins.
PRIORITY_RULES = {
    # RSSI below -110 = P1; -110 through -100 = P2; otherwise P3.
    "RSSI_LOW": [
        ("lt", -110.0, "P1"),
        ("le", -100.0, "P2"),
    ],

    # VSWR above 2.0 = P1.
    "VSWR_HIGH": [
        ("gt", 2.0, "P1"),
    ],

    # No separate TX_POWER_LOW threshold in the brief.
    "TX_POWER_LOW": [
        ("always", None, "P3"),
    ],

    # Diesel below 10% = P1; 10% to below 20% = P2.
    "DIESEL_LOW": [
        ("lt", 10.0, "P1"),
        ("lt", 20.0, "P2"),
    ],

    # MAINS_FAIL alone = P2.
    "MAINS_FAIL": [
        ("always", None, "P2"),
    ],

    # Standalone DG_NOT_STARTED is unspecified; default P3 applies.
    "DG_NOT_STARTED": [],
}

# Hub uplift: 3 or more dependent sites.
HUB_MIN_DEPENDENT_SITES = 3
HUB_UPLIFT = {
    "P3": "P2",
    "P2": "P1",
    "P1": "P1",
}

# Duplicate detection.
DUPLICATE_WINDOW_MINUTES = 15

# DG_NOT_STARTED within 30 minutes of MAINS_FAIL, inclusive.
DG_WINDOW_MINUTES = 30
DG_ALARM_TYPE = "DG_NOT_STARTED"
MAINS_ALARM_TYPE = "MAINS_FAIL"
DG_ATTACH_PRIORITY = "P1"

# Ticket lifecycle.
REOPEN_WINDOW_HOURS = 24
AUTO_CLOSE_HOURS = 24
ENFORCE_TIME_ORDER = True

# The brief does not explicitly specify circle restrictions
# for engineer assignment.
ENFORCE_ENGINEER_CIRCLE = False

# Response SLA: OPEN -> ASSIGNED, in minutes.
RESPONSE_SLA_MINUTES = {
    "P1": 120,
    "P2": 240,
    "P3": 1440,
}

# Resolution SLA: OPEN -> RESOLVED, in hours.
RESOLUTION_SLA_HOURS = {
    "P1": 6,
    "P2": 24,
    "P3": 72,
}

# Penalty per FULL hour beyond resolution SLA.
PENALTY_RATE_PER_HOUR = {
    "P1": 500,
    "P2": 200,
    "P3": 50,
}

PENALTY_CAP_RS = 10000

# Preserve the existing output formatting configuration.
NONE_TEXT = "NONE"
PENALTY_DECIMALS = 2

# Remaining ambiguities not explicitly settled by the brief.
UNCONFIRMED = [
    "Standalone DG_NOT_STARTED priority: P3 assumed.",
    "TX_POWER_LOW classification: P3 assumed as another RF alarm.",
    "Monthly report date assignment: opened_at assumed.",
    "Treatment of unassigned/unresolved tickets at report cutoff "
    "is not explicitly specified.",
]
