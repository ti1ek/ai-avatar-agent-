"""
MCP-сервер №3: ABR Group (бонус)
Информация о ресторанах сети ABR Group: Бочка, Del Papa, Pinta, и др.
Запуск: python mcp_servers/abr_group/server.py
Протокол: stdio
"""
import asyncio
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ABR Group Restaurants")

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 600


def _cache_get(key: str) -> Any | None:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
    return None


def _cache_set(key: str, val: Any) -> None:
    _cache[key] = (time.time(), val)


ABR_DB: dict[str, dict] = {
    "del papa": {
        "name": "Del Papa",
        "address": "пр. Достык, 85; пр. Аль-Фараби, 34",
        "menu_highlights": [
            "Пицца Маргарита — 2 500 тг",
            "Паста Карбонара — 3 200 тг",
            "Тирамису — 1 400 тг",
            "Стейк Рибай — 6 800 тг",
        ],
        "average_check": "3 000–5 000 тг",
        "booking_url": "https://delpapa.kz/booking",
        "description": "Уютный итальянский ресторан с аутентичной кухней. Подходит для романтического ужина и семейных встреч.",
    },
    "бочка": {
        "name": "Бочка",
        "address": "ул. Жамбыла, 140, Алматы",
        "menu_highlights": [
            "Бургер Классик — 2 200 тг",
            "Крылышки BBQ — 2 800 тг",
            "Пиво разливное — от 900 тг",
            "Картофель фри — 700 тг",
        ],
        "average_check": "2 000–4 000 тг",
        "booking_url": "https://bochka.kz/booking",
        "description": "Популярный паб-ресторан. Живая музыка по выходным. Большой выбор пива и американской кухни.",
    },
    "pinta": {
        "name": "Pinta",
        "address": "пр. Абая, 52, Алматы",
        "menu_highlights": [
            "Крафтовое пиво — от 1 100 тг",
            "Рёбрышки BBQ — 4 200 тг",
            "Сырная тарелка — 2 900 тг",
        ],
        "average_check": "2 500–4 500 тг",
        "booking_url": "https://pinta.kz/booking",
        "description": "Крафтовый бар с широким выбором пива. Уютная атмосфера для дружеских встреч.",
    },
    "chagala": {
        "name": "Chagala",
        "address": "пр. Достык, 212, Алматы",
        "menu_highlights": [
            "Бешбармак — 3 500 тг",
            "Казы — 2 800 тг",
            "Манты — 1 200 тг",
            "Лагман — 1 500 тг",
        ],
        "average_check": "2 000–4 000 тг",
        "booking_url": "https://abr.kz/chagala",
        "description": "Ресторан казахской и центральноазиатской кухни. Идеально для знакомства с национальной едой.",
    },
}


async def _scrape_abr(name: str) -> dict | None:
    """Try to fetch from ABR Group website."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://abr.kz/restaurants", headers=headers)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                for card in soup.select("[class*='restaurant']"):
                    title = card.select_one("h2, h3, .name")
                    if title and name.lower() in title.get_text().lower():
                        return {"name": title.get_text(strip=True), "description": "ABR Group restaurant"}
    except Exception:
        pass
    return None


@mcp.tool()
async def get_restaurant_info(name: str) -> dict:
    """
    Get detailed info about an ABR Group restaurant (Del Papa, Bochka, Pinta, Chagala).

    Args:
        name: restaurant name, e.g. 'Del Papa', 'Бочка', 'Pinta'

    Returns:
        RestaurantInfo with name, address, menu_highlights, average_check,
        booking_url, description.
    """
    cache_key = f"abr:{name.lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Check local DB first
    name_lower = name.lower()
    for key, info in ABR_DB.items():
        if key in name_lower or name_lower in key:
            _cache_set(cache_key, info)
            return info

    # Try scraping
    scraped = await _scrape_abr(name)
    if scraped:
        _cache_set(cache_key, scraped)
        return scraped

    # Not found
    result = {
        "name": name,
        "address": "Алматы",
        "menu_highlights": [],
        "average_check": "уточняйте",
        "booking_url": "https://abr.kz",
        "description": f"Ресторан {name} сети ABR Group.",
    }
    _cache_set(cache_key, result)
    return result


if __name__ == "__main__":
    mcp.run()
