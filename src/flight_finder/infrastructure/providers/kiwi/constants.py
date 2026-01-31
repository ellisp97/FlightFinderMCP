from __future__ import annotations

# RapidAPI Flights Scraper API
API_BASE_URL = "https://flights-scraper-real-time.p.rapidapi.com"
API_SEARCH_ONEWAY_PATH = "/flights/search-oneway"
API_SEARCH_RETURN_PATH = "/flights/search-return"

# RapidAPI headers
RAPIDAPI_HOST = "flights-scraper-real-time.p.rapidapi.com"

# Rate limiting
RATE_LIMIT_REQUESTS_PER_WINDOW = 1
RATE_LIMIT_WINDOW_SECONDS = 2.0

# Default search parameters
DEFAULT_LIMIT = 50
DEFAULT_CURRENCY = "USD"
DEFAULT_LOCALE = "en-US"
DEFAULT_MARKET = "US"

# Cabin class mapping (API uses these exact values)
CABIN_CLASS_ECONOMY = "ECONOMY"
CABIN_CLASS_PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
CABIN_CLASS_BUSINESS = "BUSINESS"
CABIN_CLASS_FIRST = "FIRST_CLASS"

# Sort options
SORT_QUALITY = "QUALITY"
SORT_PRICE = "PRICE"
SORT_DURATION = "DURATION"
SORT_DEPARTURE = "SOURCE_TAKEOFF"
SORT_ARRIVAL = "DESTINATION_LANDING"
