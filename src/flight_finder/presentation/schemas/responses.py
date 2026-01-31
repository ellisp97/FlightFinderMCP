"""Response schemas for MCP tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PriceDTO(BaseModel):
    """Price data transfer object."""

    model_config = ConfigDict(frozen=True)

    amount: str = Field(..., description="Price amount as string")
    currency: str = Field(default="USD", description="Currency code")


class FlightDTO(BaseModel):
    """Flight data transfer object for JSON serialization."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Flight ID")
    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_time: str = Field(..., description="Departure time (ISO format)")
    arrival_time: str = Field(..., description="Arrival time (ISO format)")
    duration_minutes: int = Field(..., ge=0, description="Duration in minutes")
    price: PriceDTO = Field(..., description="Flight price")
    airline: str = Field(..., description="Airline code")
    airline_name: str | None = Field(default=None, description="Airline name")
    flight_number: str | None = Field(default=None, description="Flight number")
    cabin_class: str = Field(..., description="Cabin class")
    stops: int = Field(..., ge=0, description="Number of stops")
    is_non_stop: bool = Field(..., description="Whether flight is non-stop")
    booking_url: str | None = Field(default=None, description="URL to book this flight")
