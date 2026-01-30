"""Date range value object for flexible date searches."""

from datetime import date, timedelta
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic_core.core_schema import ValidationInfo


class DateRange(BaseModel):
    """Immutable date range value object.

    Represents a valid date range where start <= end.
    Used for flexible date searches.
    """

    model_config = ConfigDict(frozen=True)

    start_date: date = Field(..., description="Start date of range")
    end_date: date = Field(..., description="End date of range")

    @field_validator("end_date")
    @classmethod
    def validate_date_order(cls, end: date, info: ValidationInfo) -> date:
        """Ensure end date is not before start date."""
        if "start_date" in info.data:
            start = info.data["start_date"]
            if end < start:
                raise ValueError(
                    f"End date ({end}) cannot be before start date ({start})"
                )
        return end

    @field_validator("start_date")
    @classmethod
    def validate_not_in_past(cls, start: date) -> date:
        """Ensure start date is not in the past."""
        today = date.today()
        if start < today:
            raise ValueError(
                f"Start date ({start}) cannot be in the past (today: {today})"
            )
        return start

    def __str__(self) -> str:
        """Format as 'YYYY-MM-DD to YYYY-MM-DD'."""
        return f"{self.start_date} to {self.end_date}"

    @property
    def duration_days(self) -> int:
        """Calculate the number of days in the range."""
        return (self.end_date - self.start_date).days + 1

    def contains(self, check_date: date) -> bool:
        """Check if a date falls within this range."""
        return self.start_date <= check_date <= self.end_date

    def overlaps(self, other: "DateRange") -> bool:
        """Check if this range overlaps with another."""
        return (
            self.start_date <= other.end_date
            and other.start_date <= self.end_date
        )

    def is_single_day(self) -> bool:
        """Check if this is a single-day range."""
        return self.start_date == self.end_date
