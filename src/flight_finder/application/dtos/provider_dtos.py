"""Provider and cache DTOs for application layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProviderHealth(BaseModel):
    """Health status of a flight provider."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Provider name")
    available: bool = Field(..., description="Whether provider is available")
    priority: int = Field(default=0, description="Provider priority")


class CacheStats(BaseModel):
    """Cache statistics."""

    model_config = ConfigDict(frozen=True)

    size: int = Field(..., ge=0, description="Current cache size")
    max_size: int = Field(..., ge=0, description="Maximum cache size")
    hits: int = Field(default=0, ge=0, description="Cache hits")
    misses: int = Field(default=0, ge=0, description="Cache misses")
    hit_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Cache hit rate")
