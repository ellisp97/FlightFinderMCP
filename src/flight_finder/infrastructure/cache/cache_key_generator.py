"""Cache key generation for search criteria."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flight_finder.domain.entities.search_criteria import SearchCriteria


def generate_cache_key(criteria: SearchCriteria, provider: str = "all") -> str:
    """Generate deterministic cache key from search criteria.

    Creates a short hash key based on all search parameters that affect results.
    """
    data = {
        "provider": provider,
        "origin": criteria.origin.code,
        "destination": criteria.destination.code,
        "departure_date": criteria.departure_date.isoformat(),
        "return_date": criteria.return_date.isoformat() if criteria.return_date else None,
        "passengers": {
            "adults": criteria.passengers.adults,
            "children": criteria.passengers.children,
            "infants": criteria.passengers.infants,
        },
        "cabin_class": criteria.cabin_class.class_type.value,
        "max_stops": criteria.effective_max_stops,
        "flexible_dates": criteria.flexible_dates,
        "date_flexibility_days": criteria.date_flexibility_days if criteria.flexible_dates else None,
    }

    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]
