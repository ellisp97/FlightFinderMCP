# Flight Finder MCP

A production-grade MCP server that enables Claude to search and compare flights across multiple providers directly from your conversations.

## Features

- **Multi-Provider Search** - Aggregates results from Skyscanner, Google Flights, and Kiwi.com
- **Smart Caching** - Reduces API calls with configurable TTL caching
- **Parallel Queries** - Searches multiple providers simultaneously with deduplication
- **Flexible Filtering** - Filter by price, stops, airlines, cabin class
- **Result Analysis** - Get recommendations for cheapest, fastest, and best value flights

## Installation

### Prerequisites

- Python 3.11+
- Claude Desktop or any MCP-compatible client
- At least one flight API key (Skyscanner, Google Flights, or Kiwi)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/FlightFinderMCP.git
cd FlightFinderMCP
```

2. Install dependencies:
```bash
pip install -e .
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your API key(s)
```

4. Add to Claude Desktop config (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "flight-finder": {
      "command": "flight-finder-mcp",
      "env": {
        "FLIGHT_FINDER_SKYSCANNER_API_KEY": "your_key_here"
      }
    }
  }
}
```

## Usage

Once configured, you can ask Claude to search for flights naturally in conversation. Claude will use the MCP tools to:

- Search across multiple flight providers
- Compare prices and flight times
- Filter by your preferences (non-stop, cabin class, etc.)
- Recommend the best options

### Available Tools

The server exposes three MCP tools:

- `search_flights` - Search for flights between airports
- `get_cache_stats` - View cache performance metrics
- `clear_cache` - Clear cached search results

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLIGHT_FINDER_SKYSCANNER_API_KEY` | Skyscanner API key | - |
| `FLIGHT_FINDER_GOOGLE_FLIGHTS_API_KEY` | Google Flights API key | - |
| `FLIGHT_FINDER_KIWI_API_KEY` | Kiwi.com API key | - |
| `FLIGHT_FINDER_CACHE_TTL_SECONDS` | Cache duration | 300 |
| `FLIGHT_FINDER_MAX_SEARCH_RESULTS` | Result limit per search | 50 |
| `FLIGHT_FINDER_LOG_LEVEL` | Logging level | INFO |

See `.env.example` for all available options.

## Architecture

Built using clean architecture principles:

- **Domain Layer** - Flight entities, search criteria, value objects
- **Application Layer** - Use cases for search, filtering, recommendations
- **Infrastructure Layer** - API clients, caching, rate limiting
- **Presentation Layer** - MCP server handlers and schemas

Uses the Result monad pattern for error handling and Pydantic for validation.

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=src/flight_finder
```

### Code Quality

```bash
# Format code
black src tests
isort src tests

# Type checking
mypy src

# Linting
ruff check src tests
```

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
