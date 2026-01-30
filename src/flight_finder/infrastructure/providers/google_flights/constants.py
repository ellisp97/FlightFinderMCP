from __future__ import annotations

from flight_finder.domain.value_objects.cabin_class import CabinClassType

SEARCHAPI_BASE_URL = "https://www.searchapi.io/api/v1/search"
SEARCHAPI_ENGINE = "google_flights"

GOOGLE_FLIGHTS_BASE_URL = "https://www.google.com/flights"

RATE_LIMIT_DELAY_SECONDS = 2.0

HTTP_TIMEOUT_SECONDS = 30
SCRAPE_TIMEOUT_MS = 60000

FLIGHT_CARD_SELECTORS = (
    '[data-testid="itinerary-card"]',
    ".pIav2d",
    ".BbR8Ec",
    '[class*="itinerary"]',
    '[class*="flight-card"]',
)

PRICE_SELECTORS = (
    '[data-testid="flt_searchresult_pricecontainer"]',
    ".YMlIFe",
    '[class*="price"]',
)

AIRLINE_SELECTORS = (
    '[data-testid="airline"]',
    ".sSHqwe .Ylwywf",
    '[class*="carrier"]',
)

DURATION_SELECTORS = (
    '[data-testid="duration"]',
    ".AdWm27",
    '[class*="duration"]',
)

STOPS_SELECTORS = (
    '[data-testid="stops"]',
    ".EWp0qd",
    '[class*="stops"]',
)

USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)

CABIN_CLASS_MAPPING: dict[CabinClassType, str] = {
    CabinClassType.ECONOMY: "economy",
    CabinClassType.PREMIUM_ECONOMY: "premium_economy",
    CabinClassType.BUSINESS: "business",
    CabinClassType.FIRST: "first",
}
