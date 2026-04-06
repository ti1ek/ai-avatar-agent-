"""
MCP-сервер №3: 2GIS
Поиск ресторанов Алматы через парсинг 2gis.kz (Playwright).
Запуск: python mcp_servers/twogis/server.py
Протокол: stdio
"""
import json
import re
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


async def _scrape_2gis(query: str, city: str) -> list[dict]:
    """Scrape 2GIS for restaurants using Playwright."""
    results = []
    encoded = query.replace(" ", "%20")
    url = f"https://2gis.kz/{city.lower()}/search/{encoded}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(5000)

            cards = await page.query_selector_all("[class*='_1kf6gff']")

            for card in cards[:8]:
                try:
                    text = await card.inner_text()
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    if not lines:
                        continue

                    name = lines[0].replace("\xa0", " ").strip()
                    if not name:
                        continue

                    # Category (line after name, before rating)
                    category = ""
                    rating = ""
                    reviews = ""
                    address = ""

                    for i, line in enumerate(lines[1:], 1):
                        line_clean = line.replace("\xa0", " ").strip()
                        # Rating: single float like "4.7"
                        if re.match(r"^\d\.\d$", line_clean):
                            rating = line_clean
                        # Reviews count
                        elif "оценк" in line_clean or "отзыв" in line_clean:
                            reviews = line_clean
                        # Address: contains "улица", "проспект", "переулок", "ТРЦ", "мкр"
                        elif any(kw in line_clean for kw in ["улица", "проспект", "переулок", "ТРЦ", "мкр", "бульвар", "Алматы"]):
                            address = line_clean
                        # Category: first non-empty line after name that isn't rating/address
                        elif not category and not re.match(r"^\d", line_clean):
                            category = line_clean

                    # Link
                    link_el = await card.query_selector("a[href*='/firm/']")
                    link = ""
                    if link_el:
                        href = await link_el.get_attribute("href") or ""
                        link = "https://2gis.kz" + href if href.startswith("/") else href

                    results.append({
                        "name": name,
                        "category": category,
                        "rating": rating,
                        "reviews": reviews,
                        "address": address,
                        "url": link,
                    })
                except Exception:
                    continue
        finally:
            await browser.close()

    return results


@mcp.tool()
async def search_restaurants(query: str = "рестораны", city: str = "almaty") -> str:
    """
    Search for restaurants in Almaty using 2GIS.

    Args:
        query: search query, e.g. 'рестораны', 'суши', 'кофейня', 'бизнес-ланч'
        city: city slug for 2GIS URL, default 'almaty'

    Returns:
        JSON list of restaurants with name, category, rating, reviews, address, url.
    """
    cache_key = f"2gis:{query}:{city}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        results = await _scrape_2gis(query, city)
        if results:
            result_json = json.dumps(results, ensure_ascii=False, indent=2)
            _cache_set(cache_key, result_json)
            return result_json
    except Exception as e:
        return json.dumps({"error": f"Ошибка 2GIS: {str(e)}"}, ensure_ascii=False)

    return json.dumps({"error": "Рестораны не найдены"}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
