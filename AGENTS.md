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
