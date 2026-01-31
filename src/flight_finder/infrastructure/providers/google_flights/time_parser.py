from __future__ import annotations

import re
from datetime import date, datetime, time as datetime_time, timedelta

import structlog

logger = structlog.get_logger()


def parse_flight_time(
    time_str: str,
    base_date: date,
    previous_time: datetime | None = None,
) -> datetime:
    """Parse SearchAPI time format to datetime.

    Handles formats like:
        "11:35 AM" -> datetime(base_date, 11, 35)
        "2:40 PM+1" -> datetime(base_date + 1 day, 14, 40)
        "4:40 AM+2" -> datetime(base_date + 2 days, 4, 40)
        "21:25" -> datetime(base_date, 21, 25) (24-hour format)
    """
    offset_match = re.search(r"\+(\d+)$", time_str)
    day_offset = int(offset_match.group(1)) if offset_match else 0

    clean_time = re.sub(r"\+\d+$", "", time_str).strip()

    parsed_time: datetime_time | None = None

    # Try 24-hour format first (e.g., "21:25")
    try:
        parsed_time = datetime.strptime(clean_time, "%H:%M").time()
    except ValueError:
        pass

    # Try 12-hour format with AM/PM (e.g., "11:35 AM")
    if parsed_time is None:
        try:
            parsed_time = datetime.strptime(clean_time, "%I:%M %p").time()
        except ValueError:
            pass

    if parsed_time is None:
        logger.warning("failed_to_parse_time", time_str=time_str)
        parsed_time = datetime_time(12, 0)

    result = datetime.combine(base_date, parsed_time)
    result += timedelta(days=day_offset)

    if previous_time and result < previous_time and day_offset == 0:
        logger.debug(
            "auto_adjusting_next_day",
            time_str=time_str,
            previous=previous_time.isoformat(),
            adjusted=(result + timedelta(days=1)).isoformat(),
        )
        result += timedelta(days=1)

    return result


def parse_airport_datetime(airport_data: dict[str, str]) -> datetime:
    """Parse airport data with date and time fields.

    Handles SearchAPI format:
        {"date": "2026-03-15", "time": "21:25"}
    """
    date_str = airport_data.get("date", "")
    time_str = airport_data.get("time", "")

    if date_str and time_str:
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            logger.warning(
                "failed_to_parse_airport_datetime",
                date=date_str,
                time=time_str,
            )

    # Fallback to base parsing
    if time_str:
        base = date.fromisoformat(date_str) if date_str else date.today()
        return parse_flight_time(time_str, base)

    logger.warning("missing_time_data", airport_data=airport_data)
    return datetime.now()


def format_duration(minutes: int) -> str:
    """Convert minutes to 'Xh Ym' format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"


def parse_duration(duration_str: str) -> int:
    """Parse duration string to minutes.

    Handles formats like:
        "4h 30m" -> 270
        "5h" -> 300
        "45m" -> 45
        365 (int as str) -> 365 (already minutes from API)
    """
    if duration_str.isdigit():
        return int(duration_str)

    hours = 0
    minutes = 0

    hour_match = re.search(r"(\d+)h", duration_str)
    if hour_match:
        hours = int(hour_match.group(1))

    min_match = re.search(r"(\d+)m", duration_str)
    if min_match:
        minutes = int(min_match.group(1))

    return hours * 60 + minutes
