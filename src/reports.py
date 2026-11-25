"""Monthly circle-wise SLA report."""
import config
from . import sla

REPORT_COLUMNS = ["month", "circle", "p1_tickets", "p2_tickets", "p3_tickets",
                  "response_breaches", "resolution_breaches", "penalty_rs"]


def format_money(amount):
    return f"{amount:.{config.PENALTY_DECIMALS}f}"


def build_monthly_report(tickets, month, circles):
    """One row per circle.  A ticket belongs to the month it was OPENED in."""
    rows = []
    for circle in sorted(circles):
        p_count = {"P1": 0, "P2": 0, "P3": 0}
        response = resolution = 0
        penalty = 0
        for ticket in tickets:
            if ticket.circle != circle:
                continue
            if ticket.opened_at.strftime("%Y-%m") != month:
                continue
            p_count[ticket.priority] += 1
            result = sla.evaluate(ticket)
            response += result.response_breached
            resolution += result.resolution_breached
            penalty += result.penalty_rs
        rows.append([month, circle, p_count["P1"], p_count["P2"],
                     p_count["P3"], response, resolution,
                     format_money(penalty)])
    return rows
