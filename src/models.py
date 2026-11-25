"""Plain data classes used across the engine."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import config

# Ticket lifecycle states.
OPEN = "OPEN"
ASSIGNED = "ASSIGNED"
RESOLVED = "RESOLVED"
CLOSED = "CLOSED"


@dataclass
class Site:
    site_id: str
    circle: str
    dependent_sites: int

    @property
    def is_hub(self):
        """Hub rule from the README: dependent_sites >= 3."""
        return self.dependent_sites >= config.HUB_MIN_DEPENDENT_SITES


@dataclass
class Engineer:
    engineer_id: str
    circle: str


@dataclass
class Alarm:
    alarm_id: str
    site_id: str
    timestamp: datetime
    alarm_type: str
    measured_value: float


@dataclass
class Ticket:
    ticket_id: str
    opening_alarm_id: str
    site_id: str
    circle: str
    alarm_type: str
    priority: str
    opened_at: datetime
    status: str = OPEN
    engineer_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    attached_alarm_ids: List[str] = field(default_factory=list)
    last_event_at: Optional[datetime] = None  # for time-order validation
