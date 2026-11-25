"""Priority calculation (P1/P2/P3) from alarm type, value and site."""
import config

_OPERATORS = {
    "lt": lambda value, limit: value < limit,
    "le": lambda value, limit: value <= limit,
    "gt": lambda value, limit: value > limit,
    "ge": lambda value, limit: value >= limit,
    "always": lambda value, limit: True,
}


def base_priority(alarm_type, measured_value):
    """First matching rule in config.PRIORITY_RULES wins; else the default."""
    for operator, limit, priority in config.PRIORITY_RULES.get(alarm_type, []):
        if _OPERATORS[operator](measured_value, limit):
            return priority
    return config.DEFAULT_PRIORITY


def apply_hub_uplift(priority, site):
    """Hub sites move one level up; P1 stays P1 (there is no P0)."""
    if site.is_hub:
        return config.HUB_UPLIFT[priority]
    return priority


def alarm_priority(alarm, site):
    """Priority a ticket gets when this alarm opens it."""
    return apply_hub_uplift(base_priority(alarm.alarm_type,
                                          alarm.measured_value), site)
