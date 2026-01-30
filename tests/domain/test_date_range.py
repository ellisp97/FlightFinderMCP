"""Unit tests for DateRange value object."""

import pytest
from datetime import date, timedelta
from flight_finder.domain.value_objects.date_range import DateRange


class TestDateRangeValidation:
    """Test DateRange validation rules."""

    def test_create_valid_date_range(self):
        """Test creating a valid date range."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        date_range = DateRange(start_date=today, end_date=tomorrow)
        assert date_range.start_date == today
        assert date_range.end_date == tomorrow

    def test_create_single_day_range(self):
        """Test creating a single-day range."""
        tomorrow = date.today() + timedelta(days=1)

        date_range = DateRange(start_date=tomorrow, end_date=tomorrow)
        assert date_range.start_date == tomorrow
        assert date_range.end_date == tomorrow
        assert date_range.is_single_day()

    def test_end_before_start_fails(self):
        """Test that end date before start date fails."""
        start = date.today() + timedelta(days=7)
        end = date.today() + timedelta(days=3)

        with pytest.raises(ValueError, match="cannot be before start date"):
            DateRange(start_date=start, end_date=end)

    def test_start_in_past_fails(self):
        """Test that start date in the past fails."""
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)

        with pytest.raises(ValueError, match="cannot be in the past"):
            DateRange(start_date=yesterday, end_date=tomorrow)

    def test_today_as_start_allowed(self):
        """Test that today as start date is allowed."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        date_range = DateRange(start_date=today, end_date=tomorrow)
        assert date_range.start_date == today

    def test_immutability(self):
        """Test that DateRange is immutable."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        date_range = DateRange(start_date=today, end_date=tomorrow)
        with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
            date_range.start_date = today + timedelta(days=2)


class TestDateRangeProperties:
    """Test DateRange computed properties."""

    def test_duration_days_single_day(self):
        """Test duration_days for single day."""
        tomorrow = date.today() + timedelta(days=1)

        date_range = DateRange(start_date=tomorrow, end_date=tomorrow)
        assert date_range.duration_days == 1

    def test_duration_days_multiple_days(self):
        """Test duration_days for multiple days."""
        start = date.today()
        end = start + timedelta(days=6)

        date_range = DateRange(start_date=start, end_date=end)
        assert date_range.duration_days == 7  # Inclusive of both days

    def test_is_single_day_true(self):
        """Test is_single_day when range is one day."""
        tomorrow = date.today() + timedelta(days=1)

        date_range = DateRange(start_date=tomorrow, end_date=tomorrow)
        assert date_range.is_single_day()

    def test_is_single_day_false(self):
        """Test is_single_day when range spans multiple days."""
        start = date.today()
        end = start + timedelta(days=3)

        date_range = DateRange(start_date=start, end_date=end)
        assert not date_range.is_single_day()


class TestDateRangeMethods:
    """Test DateRange utility methods."""

    def test_contains_date_in_range(self):
        """Test contains with date in range."""
        start = date.today()
        end = start + timedelta(days=6)
        middle = start + timedelta(days=3)

        date_range = DateRange(start_date=start, end_date=end)
        assert date_range.contains(middle)

    def test_contains_start_date(self):
        """Test contains with start date."""
        start = date.today()
        end = start + timedelta(days=6)

        date_range = DateRange(start_date=start, end_date=end)
        assert date_range.contains(start)

    def test_contains_end_date(self):
        """Test contains with end date."""
        start = date.today()
        end = start + timedelta(days=6)

        date_range = DateRange(start_date=start, end_date=end)
        assert date_range.contains(end)

    def test_contains_date_before_range(self):
        """Test contains with date before range."""
        start = date.today() + timedelta(days=3)
        end = start + timedelta(days=6)
        before = date.today()

        date_range = DateRange(start_date=start, end_date=end)
        assert not date_range.contains(before)

    def test_contains_date_after_range(self):
        """Test contains with date after range."""
        start = date.today()
        end = start + timedelta(days=6)
        after = end + timedelta(days=1)

        date_range = DateRange(start_date=start, end_date=end)
        assert not date_range.contains(after)

    def test_overlaps_true(self):
        """Test overlaps when ranges overlap."""
        start1 = date.today()
        end1 = start1 + timedelta(days=10)
        range1 = DateRange(start_date=start1, end_date=end1)

        start2 = start1 + timedelta(days=5)
        end2 = start2 + timedelta(days=10)
        range2 = DateRange(start_date=start2, end_date=end2)

        assert range1.overlaps(range2)
        assert range2.overlaps(range1)

    def test_overlaps_false_no_overlap(self):
        """Test overlaps when ranges don't overlap."""
        start1 = date.today()
        end1 = start1 + timedelta(days=5)
        range1 = DateRange(start_date=start1, end_date=end1)

        start2 = end1 + timedelta(days=2)
        end2 = start2 + timedelta(days=5)
        range2 = DateRange(start_date=start2, end_date=end2)

        assert not range1.overlaps(range2)
        assert not range2.overlaps(range1)

    def test_overlaps_touching_ranges(self):
        """Test overlaps when ranges touch at boundary."""
        start1 = date.today()
        end1 = start1 + timedelta(days=5)
        range1 = DateRange(start_date=start1, end_date=end1)

        start2 = end1
        end2 = start2 + timedelta(days=5)
        range2 = DateRange(start_date=start2, end_date=end2)

        assert range1.overlaps(range2)
        assert range2.overlaps(range1)

    def test_overlaps_one_contains_other(self):
        """Test overlaps when one range contains the other."""
        start1 = date.today()
        end1 = start1 + timedelta(days=20)
        range1 = DateRange(start_date=start1, end_date=end1)

        start2 = start1 + timedelta(days=5)
        end2 = start1 + timedelta(days=10)
        range2 = DateRange(start_date=start2, end_date=end2)

        assert range1.overlaps(range2)
        assert range2.overlaps(range1)


class TestDateRangeFormatting:
    """Test DateRange string formatting."""

    def test_str_format(self):
        """Test string formatting."""
        start = date.today()
        end = start + timedelta(days=7)

        date_range = DateRange(start_date=start, end_date=end)
        expected = f"{start} to {end}"
        assert str(date_range) == expected

    def test_str_format_single_day(self):
        """Test string formatting for single day."""
        tomorrow = date.today() + timedelta(days=1)

        date_range = DateRange(start_date=tomorrow, end_date=tomorrow)
        expected = f"{tomorrow} to {tomorrow}"
        assert str(date_range) == expected


class TestDateRangeRealWorld:
    """Test real-world date range scenarios."""

    def test_weekend_trip(self):
        """Test weekend trip date range."""
        friday = date.today() + timedelta(days=7)  # Next week
        sunday = friday + timedelta(days=2)

        date_range = DateRange(start_date=friday, end_date=sunday)
        assert date_range.duration_days == 3

    def test_week_long_vacation(self):
        """Test week-long vacation."""
        start = date.today() + timedelta(days=30)
        end = start + timedelta(days=6)

        date_range = DateRange(start_date=start, end_date=end)
        assert date_range.duration_days == 7

    def test_flexible_search_window(self):
        """Test flexible search window (±3 days)."""
        target_date = date.today() + timedelta(days=14)
        start = target_date - timedelta(days=3)
        end = target_date + timedelta(days=3)

        # Ensure start is not in past
        if start < date.today():
            start = date.today()

        date_range = DateRange(start_date=start, end_date=end)
        assert date_range.contains(target_date)
