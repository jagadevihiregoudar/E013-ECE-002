"""SLA breach, hours-late and penalty calculation (BR: response + resolution)."""
from collections import namedtuple
from datetime import timedelta

import config

SlaResult = namedtuple("SlaResult",
                       "response_breached resolution_breached "
                       "hours_late penalty_rs")


def evaluate(ticket):
    """Return the SLA outcome of one ticket in its current state.

    * Response SLA: ASSIGN time - opened_at, breached if STRICTLY greater.
    * Resolution SLA: RESOLVE time - ORIGINAL opened_at, breached if STRICTLY
      greater than the SLA (resolving exactly at the deadline is on time).
    * hours_late = FULL hours beyond the deadline (rounded down).
    * penalty = hours_late * rate, capped per ticket.
    * A check is skipped (not breached) when its SLA value is None or the
      ticket has not reached that step yet.
    """
    response_limit = config.RESPONSE_SLA_MINUTES.get(ticket.priority)
    response_breached = False
    if response_limit is not None and ticket.assigned_at is not None:
        waited = ticket.assigned_at - ticket.opened_at
        response_breached = waited > timedelta(minutes=response_limit)

    resolution_limit = config.RESOLUTION_SLA_HOURS.get(ticket.priority)
    resolution_breached = False
    hours_late = 0
    if resolution_limit is not None and ticket.resolved_at is not None:
        deadline = ticket.opened_at + timedelta(hours=resolution_limit)
        if ticket.resolved_at > deadline:
            resolution_breached = True
            hours_late = int((ticket.resolved_at - deadline)
                             // timedelta(hours=1))

    rate = config.PENALTY_RATE_PER_HOUR.get(ticket.priority)
    penalty = 0 if rate is None else min(hours_late * rate,
                                         config.PENALTY_CAP_RS)
    return SlaResult(response_breached, resolution_breached,
                     hours_late, penalty)
