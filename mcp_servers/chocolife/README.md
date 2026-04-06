# MCP #2: Chocolife

Search deals and discounts for Almaty restaurants by scraping [chocolife.me](https://chocolife.me).

## Tool

### `search_deals`

Returns a list of current deals from Chocolife.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | `"рестораны"` | Deal category: `рестораны`, `суши`, `бизнес-ланч`, etc. |
| `city` | string | `"Алматы"` | City name |

**Example response:**

```json
[
  {
    "title": "30% off entire menu at Flamingo!",
    "restaurant_name": "Flamingo",
    "original_price": 5000,
    "discount_price": 3500,
    "discount_percent": 30,
    "description": "30% off entire menu at Flamingo!",
    "url": "https://chocolife.me/12345-flamingo/"
  }
]
```

## Implementation

- **Scraping**: Playwright (headless Chromium) — the site uses Angular SSR
- **Selectors**: `<cl-deal>` component, restaurant name from `.deal__desc span:first-child`
- **Limit**: first 10 deals per query
- **Cache**: 5 minutes (`CACHE_TTL = 300`)
- **Protocol**: MCP stdio

## Run (for debugging)

```bash
python mcp_servers/chocolife/server.py
```
