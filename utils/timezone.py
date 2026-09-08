"""Centralized timezone handling for the entire project."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
TZ = ZoneInfo(TIMEZONE)


def now() -> datetime:
    """Return current datetime in configured timezone."""
    return datetime.now(TZ)


def today_start() -> datetime:
    """Return start of today (00:00:00) in configured timezone."""
    n = now()
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


def month_start() -> datetime:
    """Return start of current month in configured timezone."""
    n = now()
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
