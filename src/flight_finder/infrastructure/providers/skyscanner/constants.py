from __future__ import annotations

API_BASE_URL = "https://partners.api.skyscanner.net/apiservices/v3"
API_SESSION_CREATE_PATH = "/flights/live/search/create"
API_POLL_PATH_TEMPLATE = "/flights/live/search/poll/{session_token}"

MAX_POLL_ATTEMPTS = 10
POLL_INTERVAL_SECONDS = 2.0
POLL_TIMEOUT_SECONDS = 20.0

RATE_LIMIT_REQUESTS_PER_WINDOW = 1
RATE_LIMIT_WINDOW_SECONDS = 3.0

SCRAPE_BASE_URL = "https://www.skyscanner.com"
SCRAPE_TIMEOUT_MS = 30000

FLIGHT_CARD_SELECTORS = (
    '[data-testid="itinerary-card"]',
    ".itinerary-card",
    '[class*="itinerary"]',
    '[class*="flight-card"]',
)

PRICE_SELECTORS = (
    '[data-testid="price"]',
    ".price",
    '[class*="price"]',
    'span[class*="Price"]',
)

AIRLINE_SELECTORS = (
    '[data-testid="carrier"]',
    '[class*="carrier"]',
)

DURATION_SELECTORS = (
    '[data-testid="duration"]',
    '[class*="duration"]',
)

STOPS_SELECTORS = (
    '[data-testid="stops"]',
    '[class*="stops"]',
)

STATUS_COMPLETE = "RESULT_STATUS_COMPLETE"
STATUS_IN_PROGRESS = "RESULT_STATUS_IN_PROGRESS"
STATUS_FAILED = "RESULT_STATUS_FAILED"
