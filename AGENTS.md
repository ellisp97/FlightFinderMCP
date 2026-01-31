# FlightFinderMCP Agent Context

## Environment

- Python 3.11+ on Windows (MINGW64)
- Package not installed in shared env - use `sys.path.insert(0, 'src')` for imports
- No pip available in this environment
- Run tests manually with inline Python, not pytest directly

## Running Code

```python
import sys
sys.path.insert(0, 'src')
from flight_finder.infrastructure.cache import InMemoryCache
# ... your code
```

For async code:
```python
import asyncio
asyncio.run(your_async_function())
```

## Architecture

Hexagonal/Clean Architecture:
- `domain/` - Entities, Value Objects, Protocols (interfaces), Errors
- `application/` - Use cases
- `infrastructure/` - Implementations (cache, http, providers)
- `presentation/` - MCP server handlers

## Patterns

**Result Monad**: All fallible operations return `Result[T, E]` not exceptions
```python
from flight_finder.domain.common.result import Ok, Err, unwrap
result = await cache.get("key")  # Returns Ok(value) or Ok(None)
value = unwrap(result)
```

**Pydantic Models**: All domain objects use frozen Pydantic models
```python
from pydantic import BaseModel
class MyEntity(BaseModel):
    model_config = {"frozen": True}
```

**Async with asyncio.Lock**: Not threading.Lock for async code

## Code Style

- No docstrings unless complex logic requires explanation
- No inline comments for obvious code
- Minimal `__init__.py` - only export public API
- Type hints required (strict mypy)
- Use `from __future__ import annotations` for forward refs

## Key Domain Objects

- `SearchCriteria` - flight search parameters
- `Flight` - flight result entity
- `Airport` - 3-letter IATA code value object
- `Price` - currency-aware decimal
- `PassengerConfig` - adults/children/infants
- `CabinClass` - ECONOMY/PREMIUM_ECONOMY/BUSINESS/FIRST

## Testing

Run inline tests since pytest can't find the module:
```python
import sys
sys.path.insert(0, 'src')
# ... test code
import asyncio
asyncio.run(test_function())
```

Test files go in `tests/` mirroring `src/` structure.
Only write tests that verify actual behavior, not coverage padding.

**Important**: When testing with external dependencies (structlog, httpx), mock them:
```python
# Mock structlog before importing modules that use it
class MockLogger:
    def bind(self, **kwargs): return self
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass

class MockStructlog:
    @staticmethod
    def get_logger(): return MockLogger()

sys.modules['structlog'] = MockStructlog()
```

**Date Validation**: SearchCriteria validates that departure_date is not in the past.
Always use future dates in tests:
```python
from datetime import date, timedelta
future_date = date.today() + timedelta(days=30)
```

## Infrastructure Components

**HTTP Client** (`infrastructure/http/`):
- `AsyncHTTPClient` - Async HTTP with retry, user agent rotation
- `RateLimiter` - Token bucket rate limiter
- `RetryConfig` - Exponential backoff configuration

**Providers** (`infrastructure/providers/`):
- `BaseFlightProvider` - Abstract base class for flight providers
  - Template method pattern: `search()` handles rate limiting, logging, error mapping
  - Subclasses implement: `provider_name`, `_perform_search()`, `_map_error()`

## Domain Errors

- `ProviderError` - Base provider error (provider, message, original exception)
- `RateLimitError(ProviderError)` - Rate limit exceeded (retry_after)
- `TimeoutError(ProviderError)` - Operation timed out (timeout_seconds)
- `ValidationError` - Invalid input data
- `CacheError` - Cache operation failure

## Skyscanner Provider

**Location**: `infrastructure/providers/skyscanner/`

**Files**:
- `constants.py` - API URLs, polling config, CSS selectors for scraping
- `api_client.py` - Session creation and polling for Live Pricing API
- `response_mapper.py` - Maps Skyscanner API response to Flight entities
- `skyscanner_provider.py` - Main provider class extending BaseFlightProvider

**Usage**:
```python
from flight_finder.infrastructure.providers.skyscanner import SkyscannerProvider
from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient
from flight_finder.infrastructure.http.rate_limiter import RateLimiter

http_client = AsyncHTTPClient()
rate_limiter = RateLimiter(rate=1, per=3.0)  # 1 request per 3 seconds
provider = SkyscannerProvider(
    api_key="your_api_key",
    http_client=http_client,
    rate_limiter=rate_limiter,
)

result = await provider.search(criteria)
# Result is Ok[list[Flight]] or Err[ProviderError]
```

**API Flow**:
1. Create session via POST to `/flights/live/search/create`
2. Poll results via GET to `/flights/live/search/poll/{sessionToken}`
3. Poll max 10 times with 2 second intervals until `RESULT_STATUS_COMPLETE`
4. Map response to Flight entities
5. Apply filters (non_stop_only, max_stops) and sort by price

**Response Structure**:
The Skyscanner API returns a nested structure:
- `content.results.itineraries` - pricing and leg references
- `content.results.legs` - flight timing and segment references
- `content.results.segments` - carrier and flight number details
- `content.results.places` - airport information (IATA codes)
- `content.results.carriers` - airline information

**Price Handling**:
API returns prices in cents (e.g., "29900" = $299.00). The mapper divides by 100.

**Testing**:
Tests are in `tests/infrastructure/providers/skyscanner/`. Run with:
```python
python tests/infrastructure/providers/skyscanner/test_skyscanner_provider.py
python tests/infrastructure/providers/skyscanner/test_api_client.py
python tests/infrastructure/providers/skyscanner/test_response_mapper.py
```

Use MockHTTPClient and MockRateLimiter for unit tests. Mock responses should include
session token for create, and full API structure for poll results.

## RapidAPI Skyscanner Provider

**Location**: `infrastructure/providers/rapidapi_skyscanner/`

**Purpose**: Alternative to the direct Skyscanner Partner API using RapidAPI as an intermediary.
This is useful when the Skyscanner Partner API key is difficult to obtain, as RapidAPI provides
easier access to Skyscanner flight data through their marketplace.

**Files**:
- `constants.py` - RapidAPI host, API URLs, polling config, cabin class mappings
- `api_client.py` - Session creation and polling via RapidAPI headers
- `response_mapper.py` - Maps RapidAPI/Skyscanner response to Flight entities
- `rapidapi_provider.py` - Main provider class extending BaseFlightProvider

**Usage**:
```python
from flight_finder.infrastructure.providers.rapidapi_skyscanner import RapidAPISkyscannerProvider
from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient
from flight_finder.infrastructure.http.rate_limiter import RateLimiter

http_client = AsyncHTTPClient()
rate_limiter = RateLimiter(rate=1, per=3.0)  # 1 request per 3 seconds
provider = RapidAPISkyscannerProvider(
    api_key="your_rapidapi_key",
    http_client=http_client,
    rate_limiter=rate_limiter,
)

result = await provider.search(criteria)
# Result is Ok[list[Flight]] or Err[ProviderError]
```

**Configuration**:
Set `FLIGHT_FINDER_RAPIDAPI_KEY` environment variable with your RapidAPI key.
Set `FLIGHT_FINDER_DEFAULT_PROVIDER=rapidapi_skyscanner` to use as default.

**API Flow**:
1. Create session via POST to `/v3/flights/live/search/create` with RapidAPI headers
2. Poll results via GET to `/v3/flights/live/search/poll/{sessionToken}`
3. Poll max 10 times with 2 second intervals until `RESULT_STATUS_COMPLETE`
4. Map response to Flight entities (same structure as partner API)
5. Apply filters (non_stop_only, max_stops) and sort by price

**Key Difference from Partner API**:
The main difference is authentication - RapidAPI uses `X-RapidAPI-Key` and `X-RapidAPI-Host`
headers instead of the `X-API-Key` header used by the partner API. The response structure
is identical, so the same response mapper logic applies.

**RapidAPI Headers**:
```python
headers = {
    "X-RapidAPI-Key": "your_rapidapi_key",
    "X-RapidAPI-Host": "skyscanner-api.p.rapidapi.com",
    "Content-Type": "application/json",
}
```

**Rate Limiting**:
RapidAPI free tier: ~500 requests/month
Rate limiter configured at 1 request per 3 seconds to avoid hitting limits.

**Testing**:
Tests follow the same pattern as the Skyscanner provider:
```python
python tests/infrastructure/providers/rapidapi_skyscanner/test_rapidapi_provider.py
python tests/infrastructure/providers/rapidapi_skyscanner/test_api_client.py
python tests/infrastructure/providers/rapidapi_skyscanner/test_response_mapper.py
```

## Provider Factory & Aggregation

**Location**: `infrastructure/providers/`

The provider factory and aggregation system manages multiple flight providers with caching,
parallel execution, and deduplication.

**Components**:

1. **CacheDecorator** (`cache_decorator.py`):
   - Wraps any `IFlightProvider` with automatic caching
   - Checks cache before making provider call
   - Stores successful results, skips caching errors
   - Provider name becomes `{original}_cached`

2. **ProviderRegistry** (`provider_registry.py`):
   - Manages multiple providers with priority and enable/disable
   - `register(provider, priority=0, enabled=True, weight=1.0)`
   - `get_by_priority(limit=None)` - returns enabled providers sorted by priority
   - `enable(name)` / `disable(name)` - dynamic provider control

3. **MultiProviderAggregator** (`multi_provider_aggregator.py`):
   - Queries multiple providers in parallel using `asyncio.gather`
   - Handles partial failures (returns results if at least one succeeds)
   - Deduplicates similar flights across providers
   - Sorts results by price

4. **ProviderFactory** (`provider_factory.py`):
   - Creates providers with proper dependencies
   - Wraps with cache decorator if enabled
   - Registers providers in internal registry
   - Creates aggregator with all available providers

**Usage**:
```python
from flight_finder.infrastructure.providers import ProviderFactory

# Create factory
factory = ProviderFactory()

# Option 1: Use single provider
provider = factory.create_skyscanner_provider()
result = await provider.search(criteria)

# Option 2: Use multi-provider aggregator (recommended)
aggregator = factory.create_aggregator()
result = await aggregator.search(criteria)

# Access cache and registry
cache = factory.get_cache()
registry = factory.get_registry()

# Cleanup
await factory.close()
```

**Provider Priorities**:
- Skyscanner: 90 (highest)
- Google Flights: 80
- RapidAPI Skyscanner: 70

**Deduplication Criteria**:
Two flights are considered duplicates if ALL of these match:
- Same origin and destination airports
- Same airline
- Departure within 30 minutes
- Arrival within 30 minutes
- Price within 5%

**Configuration**:
Environment variables for API keys:
- `FLIGHT_FINDER_SKYSCANNER_API_KEY`
- `FLIGHT_FINDER_SEARCHAPI_KEY` (for Google Flights)
- `FLIGHT_FINDER_RAPIDAPI_KEY` (for RapidAPI Skyscanner)

Cache configuration:
- `FLIGHT_FINDER_CACHE_TTL_SECONDS` (default: 300)
- `FLIGHT_FINDER_CACHE_MAX_SIZE` (default: 1000)

**Testing**:
Run the provider infrastructure tests:
```python
python tests/infrastructure/providers/run_provider_tests.py
```

**Exports** from `infrastructure/providers/__init__.py`:
- `BaseFlightProvider`
- `CacheDecorator`
- `GoogleFlightsProvider`
- `MultiProviderAggregator`
- `ProviderFactory`
- `ProviderMetadata`
- `ProviderRegistry`
- `RapidAPISkyscannerProvider`
- `SkyscannerProvider`

## Application Layer

**Location**: `application/`

The application layer contains use cases that orchestrate domain logic and infrastructure.

**Structure**:
```
application/
├── __init__.py         # Exports all use cases and DTOs
├── dtos/               # Data Transfer Objects
│   ├── flight_dtos.py  # FlightSearchResult, FlightFilters, FlightRecommendations
│   └── provider_dtos.py # CacheStats, ProviderHealth
└── use_cases/
    ├── search_flights.py      # SearchFlightsUseCase
    ├── filter_flights.py      # FilterFlightsUseCase
    ├── get_recommendations.py # GetRecommendationsUseCase
    └── manage_cache.py        # ManageCacheUseCase
```

**Use Cases**:

1. **SearchFlightsUseCase** - Main search orchestration
   - Receives `SearchCriteria` (domain model)
   - Delegates to `IFlightProvider` (typically MultiProviderAggregator)
   - Applies max results limit from settings
   - Returns `Result[FlightSearchResult, SearchError]`

2. **FilterFlightsUseCase** - Post-search filtering
   - Pure function: filters and sorts existing flights
   - Supports price range, max stops, airlines, sort options
   - Returns `Result[list[Flight], FilterError]`

3. **GetRecommendationsUseCase** - Flight recommendations
   - Analyzes flights to find cheapest, fastest, best value
   - Returns `Result[FlightRecommendations, RecommendationError]`

4. **ManageCacheUseCase** - Cache operations
   - Get cache statistics
   - Clear cache
   - Returns `Result[CacheStats, CacheManagementError]` or `Result[dict, CacheManagementError]`

**Usage Pattern**:
```python
from flight_finder.application import SearchFlightsUseCase, FlightSearchResult
from flight_finder.config import get_settings
from flight_finder.infrastructure.providers import ProviderFactory

factory = ProviderFactory()
aggregator = factory.create_aggregator()
settings = get_settings()

search_use_case = SearchFlightsUseCase(provider=aggregator, settings=settings)
result = await search_use_case.execute(criteria)

match result:
    case Ok(search_result):
        # search_result.flights, search_result.total_results, etc.
        pass
    case Err(error):
        # error.message, error.providers_failed, etc.
        pass
```

**DTOs**:
- `FlightSearchResult` - Contains flights, total_results, providers_used, search_duration_ms, cache_hit
- `FlightFilters` - max_price, min_price, max_stops, airlines, sort_by, sort_descending
- `FlightRecommendations` - cheapest, fastest, best_value (Flight or None)
- `CacheStats` - size, max_size, hits, misses, hit_rate

## Presentation Layer (MCP Server)

**Location**: `presentation/`

The presentation layer exposes the flight finder as an MCP (Model Context Protocol) server.

**Structure**:
```
presentation/
├── __init__.py         # Exports create_server, main
├── server.py           # Main entry point, FastMCP setup
├── handlers/
│   ├── search_handler.py # SearchHandler for search_flights tool
│   └── cache_handler.py  # CacheHandler for cache tools
├── schemas/
│   ├── requests.py     # SearchFlightsRequest, PassengerCount
│   ├── responses.py    # FlightDTO, PriceDTO
│   └── converters.py   # Domain ↔ DTO converters
└── utils/
    └── error_formatter.py # format_error_response
```

**Entry Point** (defined in pyproject.toml):
```bash
flight-finder-mcp = "flight_finder.presentation.server:main"
```

**MCP Tools Exposed**:

1. **search_flights** - Search for flights between airports
   - Parameters: origin, destination, departure_date, return_date, adults, children, infants, cabin_class, max_stops, non_stop_only
   - Returns: JSON with flight results or error

2. **get_cache_stats** - Get cache statistics
   - Returns: JSON with cache size, hits, misses, hit rate

3. **clear_cache** - Clear all cached search results
   - Returns: JSON confirmation

**Server Lifecycle**:
```python
from flight_finder.presentation.server import create_server, main

# Option 1: Run directly
main()  # Starts STDIO server

# Option 2: Create server for testing
mcp, factory = create_server()
# mcp is FastMCP instance, factory is ProviderFactory for cleanup
```

**Handler Pattern**:
```python
class SearchHandler:
    def __init__(self, search_use_case: SearchFlightsUseCase) -> None:
        self._search_use_case = search_use_case

    async def handle_search(self, origin: str, destination: str, ...) -> str:
        # 1. Parse parameters (date strings → date objects)
        # 2. Convert to domain model (to_search_criteria_from_params)
        # 3. Execute use case
        # 4. Convert result to JSON response
        pass
```

**Schema Converters**:
```python
from flight_finder.presentation.schemas.converters import (
    to_search_criteria_from_params,  # Raw params → SearchCriteria
    flight_to_dto,                    # Flight → FlightDTO
    flights_to_dtos,                  # list[Flight] → list[FlightDTO]
)
```

**Error Formatting**:
```python
from flight_finder.presentation.utils.error_formatter import format_error_response

# Converts any exception to JSON error response
error_json = format_error_response(some_exception)
# Returns: {"success": false, "error": {"code": "...", "message": "..."}}
```

**Logging**:
All logs go to stderr (required for MCP STDIO transport).
Stdout is reserved for JSON-RPC protocol messages.
```python
from flight_finder.config import configure_logging
configure_logging(level="INFO", log_format="console")
```

**Configuration**:
Environment variables (all prefixed with `FLIGHT_FINDER_`):
- `SKYSCANNER_API_KEY`, `RAPIDAPI_KEY`, `SEARCHAPI_KEY` - At least one required
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR, CRITICAL
- `LOG_FORMAT` - console or json
- `CACHE_TTL_SECONDS`, `CACHE_MAX_SIZE`
- `MAX_SEARCH_RESULTS` - Limit returned flights
- `SERVER_NAME`, `SERVER_VERSION`

**Claude Desktop Configuration**:
```json
{
  "mcpServers": {
    "flight-finder": {
      "command": "flight-finder-mcp",
      "env": {
        "FLIGHT_FINDER_RAPIDAPI_KEY": "your_key_here"
      }
    }
  }
}
```

**Testing Presentation Layer**:
```python
import sys
sys.path.insert(0, 'src')

# Mock structlog first (see Testing section)
# ... structlog mock setup ...

from flight_finder.presentation.schemas.converters import to_search_criteria_from_params
from datetime import date, timedelta

future_date = date.today() + timedelta(days=30)
criteria = to_search_criteria_from_params(
    origin="JFK",
    destination="LAX",
    departure_date=future_date,
)
```
