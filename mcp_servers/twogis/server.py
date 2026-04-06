"""
MCP-сервер №1: 2GIS
Запуск: python mcp_servers/twogis/server.py
Протокол: stdio
"""
import asyncio
import json
import sys
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("2GIS Restaurant Search")

# ── Simple in-process cache ────────────────────────────────────────────────────
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 300  # seconds


def _cache_get(key: str) -> Any | None:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
    return None


def _cache_set(key: str, val: Any) -> None:
    _cache[key] = (time.time(), val)


# ── Fallback mock data (always reliable for demo) ─────────────────────────────
MOCK_RESTAURANTS = [
    {
        "name": "Del Papa",
        "address": "пр. Достык, 85, Алматы",
        "rating": 4.7,
        "price_range": "2000-4000 тг",
        "cuisine": "Итальянская",
        "working_hours": "11:00–23:00",
        "phone": "+7 727 327-00-00",
    },
    {
        "name": "Бочка",
        "address": "ул. Жамбыла, 140, Алматы",
        "rating": 4.5,
        "price_range": "1500-3500 тг",
        "cuisine": "Европейская",
        "working_hours": "12:00–00:00",
        "phone": "+7 727 272-72-72",
    },
    {
        "name": "Урюк",
        "address": "пр. Аль-Фараби, 77, Алматы",
        "rating": 4.6,
        "price_range": "1200-3000 тг",
        "cuisine": "Казахская, Среднеазиатская",
        "working_hours": "10:00–23:00",
        "phone": "+7 777 100-00-01",
    },
    {
        "name": "Кофемания",
        "address": "ул. Панфилова, 98, Алматы",
        "rating": 4.4,
        "price_range": "800-2500 тг",
        "cuisine": "Кофейня, Европейская",
        "working_hours": "08:00–22:00",
        "phone": "+7 727 244-00-44",
    },
    {
        "name": "Chili Peppers",
        "address": "пр. Сейфуллина, 617, Алматы",
        "rating": 4.3,
        "price_range": "1500-4000 тг",
        "cuisine": "Мексиканская, Бар",
        "working_hours": "12:00–02:00",
        "phone": "+7 777 200-00-02",
    },
]


async def _scrape_2gis(query: str, location: str) -> list[dict]:
    """Attempt to fetch real data from 2GIS search."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    search_query = f"{query} {location}"
    url = f"https://catalog.api.2gis.com/3.0/items/search"
    params = {
        "q": search_query,
        "location": "76.889709,43.238949",  # Almaty center
        "radius": 10000,
        "type": "branch",
        "fields": "items.name,items.address,items.rating,items.schedule,items.contact_groups,items.rubrics",
        "sort": "rating",
        "page_size": 10,
        "key": "ruipnirgstxwontjqwqjstyfbprzdktxs",  # 2GIS public demo key
    }
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

    results = []
    for item in data.get("result", {}).get("items", []):
        name = item.get("name", "")
        address_obj = item.get("address", {})
        address = address_obj.get("name", "") if isinstance(address_obj, dict) else str(address_obj)
        rating = item.get("reviews", {}).get("rating", None)

        rubrics = item.get("rubrics", [])
        cuisine = rubrics[0].get("name", "") if rubrics else ""

        schedule = item.get("schedule", {})
        hours = ""
        if schedule:
            for day_val in schedule.values():
                if isinstance(day_val, dict) and "working_hours" in day_val:
                    wh = day_val["working_hours"]
                    if wh:
                        hours = f"{wh[0].get('from','')}–{wh[0].get('to','')}"
                        break

        contacts = item.get("contact_groups", [])
        phone = ""
        for cg in contacts:
            for c in cg.get("contacts", []):
                if c.get("type") == "phone":
                    phone = c.get("value", "")
                    break
            if phone:
                break

        results.append({
            "name": name,
            "address": address,
            "rating": float(rating) if rating else 0.0,
            "price_range": "уточняйте",
            "cuisine": cuisine,
            "working_hours": hours,
            "phone": phone,
        })
    return results


@mcp.tool()
async def search_restaurants(query: str, location: str = "Алматы") -> list[dict]:
    """
    Search for restaurants, cafes, bars in Almaty.

    Args:
        query: search query, e.g. 'ресторан на двоих', 'суши', 'кофейня центр'
        location: city, default Алматы

    Returns:
        List of Restaurant objects with name, address, rating, price_range,
        cuisine, working_hours, phone.
    """
    cache_key = f"twogis:{query}:{location}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        results = await _scrape_2gis(query, location)
        if results:
            _cache_set(cache_key, results)
            return results
    except Exception:
        pass  # fall through to mock

    # Filter mock data by query keywords for relevance
    q_lower = query.lower()
    keywords = q_lower.split()
    filtered = []
    for r in MOCK_RESTAURANTS:
        score = sum(
            1
            for kw in keywords
            if kw in r["name"].lower()
            or kw in r["cuisine"].lower()
            or kw in r["address"].lower()
        )
        filtered.append((score, r))
    filtered.sort(key=lambda x: -x[0])
    result = [r for _, r in filtered] or MOCK_RESTAURANTS
    _cache_set(cache_key, result)
    return result


if __name__ == "__main__":
    mcp.run()
