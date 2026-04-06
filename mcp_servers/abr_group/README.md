# MCP #3: ABR Group

Restaurant info for ABR Group chain by scraping [abr.kz](https://abr.kz).

## Tool

### `get_restaurant_info`

Returns detailed info about an ABR Group restaurant by name.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Restaurant name, e.g. `Del Papa`, `AUYL`, `SPIROS` |

**Available restaurants:**
Del Papa, AUYL, SPIROS, cafe Alma, Astra Grand Cafe, CANTEEN, PALOMAR, Ami, Aroma, JINAU, Broadway Burger, Cafeteria, and more.

**Example response:**

```json
{
  "name": "Del Papa",
  "address": [
    "Bukhar Zhyrau blvd., 66",
    "Gogol st., 87",
    "Dostyk Plaza mall"
  ],
  "phone": "+7 771 722 82 21",
  "working_hours": "Mon-Sun 10:00-23:00",
  "booking_url": "https://booking-web.abr.dev/",
  "description": "Chain of cozy Italian restaurants with classic Italian cuisine.",
  "menu_highlights": [],
  "average_check": ""
}
```

## Implementation

- **Scraping**: Playwright (headless Chromium)
- **Slug lookup**: dynamically resolved by parsing the abr.kz homepage
- **Addresses**: supports single- and multi-location restaurants
- **Cache**: 10 minutes (`CACHE_TTL = 600`)
- **Protocol**: MCP stdio

## Run (for debugging)

```bash
python mcp_servers/abr_group/server.py
```
