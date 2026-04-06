"""
MCP-сервер №1: 2GIS
Поиск ресторанов, кафе, баров в Алматы через парсинг 2gis.kz (Playwright).
Запуск: python mcp_servers/twogis/server.py
Протокол: stdio
"""
import asyncio
import json
import time
from typing import Any

from playwright.async_api import async_playwright
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("2GIS Restaurant Search")

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 300


def _cache_get(key: str) -> Any | None:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
    return None


def _cache_set(key: str, val: Any) -> None:
    _cache[key] = (time.time(), val)


async def _search_2gis(query: str, location: str) -> list[dict]:
    """Search restaurants on 2gis.kz using Playwright."""
    results = []
    search_url = f"https://2gis.kz/{location.lower()}/search/{query}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)

            # Parse search result cards
            cards = await page.query_selector_all("[class*='_1hf6gk']")
            if not cards:
                cards = await page.query_selector_all("[class*='_1h3cgb']")
            if not cards:
                cards = await page.query_selector_all("div._1kf6gk, div._zjunba")

            for card in cards[:10]:
                try:
                    # Name
                    name_el = await card.query_selector("[class*='_1al0wlf'], [class*='_16s5yj6'], a[class*='_1rehek']")
                    name = await name_el.inner_text() if name_el else ""
                    if not name:
                        continue

                    # Address
                    addr_el = await card.query_selector("[class*='_14quei'], [class*='_1w9o2igt']")
                    address = await addr_el.inner_text() if addr_el else ""

                    # Rating
                    rating_el = await card.query_selector("[class*='_y10azs'], [class*='_1fkin5c']")
                    rating_text = await rating_el.inner_text() if rating_el else "0"
                    try:
                        rating = float(rating_text.replace(",", "."))
                    except ValueError:
                        rating = 0.0

                    # Category/cuisine
                    cat_el = await card.query_selector("[class*='_1h3cgb'], [class*='_oqoid']")
                    cuisine = await cat_el.inner_text() if cat_el else ""

                    # Working hours
                    hours_el = await card.query_selector("[class*='_flyehy'], [class*='_b0ke8']")
                    hours = await hours_el.inner_text() if hours_el else ""

                    results.append({
                        "name": name.strip(),
                        "address": address.strip(),
                        "rating": rating,
                        "price_range": "уточняйте",
                        "cuisine": cuisine.strip(),
                        "working_hours": hours.strip(),
                        "phone": "",
                    })
                except Exception:
                    continue
        finally:
            await browser.close()

    return results


@mcp.tool()
async def search_restaurants(query: str, location: str = "Алматы") -> str:
    """
    Search for restaurants, cafes, bars in Almaty via 2GIS.

    Args:
        query: search query, e.g. 'ресторан на двоих', 'суши', 'кофейня центр'
        location: city, default Алматы

    Returns:
        JSON list of restaurants with name, address, rating, price_range,
        cuisine, working_hours, phone.
    """
    cache_key = f"twogis:{query}:{location}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        results = await _search_2gis(query, location)
        if results:
            result_json = json.dumps(results, ensure_ascii=False, indent=2)
            _cache_set(cache_key, result_json)
            return result_json
    except Exception as e:
        return json.dumps({"error": f"Ошибка поиска 2GIS: {str(e)}"}, ensure_ascii=False)

    return json.dumps({"error": "Ничего не найдено"}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
