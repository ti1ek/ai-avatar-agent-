"""
MCP-сервер №3: ABR Group
Информация о ресторанах сети ABR Group через парсинг abr.kz (Playwright).
Запуск: python mcp_servers/abr_group/server.py
Протокол: stdio
"""
import asyncio
import json
import re
import time
from typing import Any

from playwright.async_api import async_playwright
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


async def _get_restaurant_slugs() -> dict[str, str]:
    """Get all restaurant name→slug mappings from abr.kz."""
    slugs = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://abr.kz", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            links = await page.query_selector_all("a[href*='/restaurant/']")
            for link in links:
                href = await link.get_attribute("href") or ""
                text = (await link.inner_text()).strip()
                match = re.search(r"/restaurant/([^/]+)", href)
                if match and text:
                    slugs[text.lower()] = match.group(1)
        finally:
            await browser.close()
    return slugs


async def _scrape_restaurant(name: str) -> dict:
    """Scrape restaurant info from abr.kz using Playwright."""
    result = {
        "name": name,
        "address": [],
        "menu_highlights": [],
        "average_check": "",
        "booking_url": "https://booking-web.abr.dev/",
        "description": "",
        "working_hours": "",
        "phone": "",
    }

    # Find the slug for this restaurant
    name_lower = name.lower().strip()
    slugs = await _get_restaurant_slugs()

    slug = None
    for rname, rslug in slugs.items():
        if name_lower in rname or rname in name_lower:
            slug = rslug
            result["name"] = rname.title()
            break

    if not slug:
        # Return list of available restaurants
        result["description"] = f"Ресторан '{name}' не найден в ABR Group."
        result["available_restaurants"] = list(set(slugs.keys()))
        return result

    url = f"https://abr.kz/restaurant/{slug}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)

            text = await page.inner_text("body")
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            # Description (first long line after restaurant name)
            for line in lines:
                if len(line) > 60 and name_lower[:4] not in line.lower()[:10]:
                    result["description"] = line[:300]
                    break

            # Addresses, phones, hours
            addresses = []
            i = 0
            while i < len(lines):
                line = lines[i]
                # Address patterns
                if any(kw in line for kw in ["ул.", "б-р.", "пр.", "мкр.", "ТРЦ", "микрорайон"]):
                    addr_info = {"address": line}
                    # Look ahead for phone and hours
                    for j in range(i + 1, min(i + 6, len(lines))):
                        if lines[j].startswith("+7"):
                            addr_info["phone"] = lines[j]
                        if "с " in lines[j] and ":00" in lines[j]:
                            addr_info["hours"] = lines[j]
                    addresses.append(addr_info)
                i += 1

            if addresses:
                result["address"] = [a["address"] for a in addresses]
                result["phone"] = addresses[0].get("phone", "")
                result["working_hours"] = addresses[0].get("hours", "")

        finally:
            await browser.close()

    return result


@mcp.tool()
async def get_restaurant_info(name: str) -> str:
    """
    Get detailed info about an ABR Group restaurant by parsing abr.kz.
    Available restaurants: Del Papa, AUYL, SPIROS, cafe Alma, Astra Grand Cafe,
    CANTEEN, PALOMAR, Aroma, JINAU, Broadway Burger, Cafeteria, and more.

    Args:
        name: restaurant name, e.g. 'Del Papa', 'AUYL', 'SPIROS'

    Returns:
        JSON with name, address, menu_highlights, average_check,
        booking_url, description, working_hours, phone.
    """
    cache_key = f"abr:{name.lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        result = await _scrape_restaurant(name)
        result_json = json.dumps(result, ensure_ascii=False, indent=2)
        _cache_set(cache_key, result_json)
        return result_json
    except Exception as e:
        return json.dumps(
            {"error": f"Ошибка при поиске {name}: {str(e)}"},
            ensure_ascii=False,
        )


if __name__ == "__main__":
    mcp.run()
