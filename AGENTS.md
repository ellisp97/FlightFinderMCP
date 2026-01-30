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
