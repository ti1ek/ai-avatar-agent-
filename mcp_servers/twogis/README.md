# MCP #1: 2GIS

Search restaurants in Almaty by scraping [2gis.kz](https://2gis.kz).

## Tool

### `search_restaurants`

Returns a list of restaurants matching a search query.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | `"рестораны"` | Search query: `рестораны`, `суши`, `кофейня`, `бизнес-ланч`, `итальянская кухня`, etc. |
| `city` | string | `"almaty"` | City slug for the 2GIS URL |

**Example response:**

```json
[
  {
    "name": "Lova Kitchen",
    "category": "Lounge bar",
    "rating": "4.7",
    "reviews": "4403 ratings",
    "address": "Oraza Zhandosova st., 57, Almaty",
    "url": "https://2gis.kz/almaty/firm/..."
  }
]
```

## Implementation

- **Scraping**: Playwright (headless Chromium) — the site renders dynamically
- **Card selector**: `[class*="_1kf6gff"]`
- **Limit**: first 8 results per query
- **Cache**: 5 minutes (`CACHE_TTL = 300`)
- **Protocol**: MCP stdio

## Run (for debugging)

```bash
python mcp_servers/twogis/server.py
```
