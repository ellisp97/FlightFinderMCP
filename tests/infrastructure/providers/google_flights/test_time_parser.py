"""Tests for time_parser module."""

import sys
sys.path.insert(0, "src")

from datetime import date, datetime

from flight_finder.infrastructure.providers.google_flights.time_parser import (
    format_duration,
    parse_duration,
    parse_flight_time,
)


def test_parse_simple_am_time():
    base_date = date(2026, 6, 15)
    result = parse_flight_time("11:35 AM", base_date)

    assert result.year == 2026
    assert result.month == 6
    assert result.day == 15
    assert result.hour == 11
    assert result.minute == 35


def test_parse_simple_pm_time():
    base_date = date(2026, 6, 15)
    result = parse_flight_time("2:40 PM", base_date)

    assert result.year == 2026
    assert result.month == 6
    assert result.day == 15
    assert result.hour == 14
    assert result.minute == 40


def test_parse_time_with_day_offset():
    base_date = date(2026, 6, 15)
    result = parse_flight_time("2:40 AM+1", base_date)

    assert result.year == 2026
    assert result.month == 6
    assert result.day == 16
    assert result.hour == 2
    assert result.minute == 40


def test_parse_time_auto_adjust_next_day():
    base_date = date(2026, 6, 15)
    previous = datetime(2026, 6, 15, 23, 0)

    result = parse_flight_time("2:40 AM", base_date, previous_time=previous)

    assert result.day == 16


def test_format_duration():
    assert format_duration(365) == "6h 5m"
    assert format_duration(300) == "5h 0m"
    assert format_duration(45) == "0h 45m"


def test_parse_duration():
    assert parse_duration("6h 5m") == 365
    assert parse_duration("5h") == 300
    assert parse_duration("45m") == 45
    assert parse_duration("365") == 365


if __name__ == "__main__":
    test_parse_simple_am_time()
    test_parse_simple_pm_time()
    test_parse_time_with_day_offset()
    test_parse_time_auto_adjust_next_day()
    test_format_duration()
    test_parse_duration()
    print("All time_parser tests passed!")
