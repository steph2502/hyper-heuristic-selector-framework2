"""Human-friendly display labels for timetable day/period values."""

from __future__ import annotations

DAY_NAMES: dict[int, str] = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
}

TIME_SLOTS: dict[int, str] = {
    0: "8:00 AM - 10:00 AM",
    1: "10:00 AM - 12:00 PM",
    2: "12:00 PM - 2:00 PM",
    3: "3:00 PM - 5:00 PM",
    4: "5:00 PM - 7:00 PM",
}

BREAK_LABEL = "BREAK"
BREAK_TIME = "2:00 PM - 3:00 PM"


def get_day_name(day: int | None) -> str:
    """Return display name for a day index."""
    if day is None:
        return "UNSCHEDULED"
    return DAY_NAMES.get(day, f"Day {day}")


def get_time_slot(period: int | None) -> str:
    """Return display label for a period index."""
    if period is None:
        return "UNSCHEDULED"
    return TIME_SLOTS.get(period, f"Period {period}")


def getDayName(day: int | None) -> str:
    """Camel-case wrapper used by display callers."""
    return get_day_name(day)


def getTimeSlot(period: int | None) -> str:
    """Camel-case wrapper used by display callers."""
    return get_time_slot(period)
