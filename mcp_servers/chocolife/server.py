"""
MCP-сервер №1: Chocolife
Поиск скидок и акций на рестораны в Алматы через парсинг chocolife.me (Playwright).
Запуск: python mcp_servers/chocolife/server.py
Протокол: stdio
"""
import asyncio
import json
import time
from typing import Any

from playwright.async_api import async_playwright
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Chocolife Deals Search")

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


async def _scrape_chocolife(category: str, city: str) -> list[dict]:
    """Scrape Chocolife for restaurant deals using Playwright."""
    deals = []
    url = "https://chocolife.me/restorany-kafe-i-bary/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(4000)

            # Each deal is a <cl-deal> component containing .deal div
            cards = await page.query_selector_all("cl-deal")

            for card in cards[:10]:
                try:
                    # Title
                    title_el = await card.query_selector(".deal__title")
                    title = await title_el.inner_text() if title_el else ""
                    if not title:
                        continue

                    # Restaurant name — first span inside .deal__desc
                    name_el = await card.query_selector(".deal__desc span:first-child")
                    restaurant = await name_el.inner_text() if name_el else ""

                    # Description — the deal title is the offer description
                    description = title

                    # Location
                    place_el = await card.query_selector(".deal__place span")
                    location = await place_el.inner_text() if place_el else ""

                    # Discount percent
                    percent_el = await card.query_selector(".deal__percent")
                    percent_text = await percent_el.inner_text() if percent_el else ""
                    discount_percent = 0
                    digits = "".join(c for c in percent_text if c.isdigit())
                    if digits:
                        discount_percent = int(digits)

                    # Prices
                    price_els = await card.query_selector_all(".deal__price")
                    prices = []
                    for pel in price_els:
                        text = await pel.inner_text()
                        d = "".join(c for c in text if c.isdigit())
                        if d:
                            prices.append(int(d))

                    original_price = prices[0] if len(prices) > 0 else 0
                    discount_price = prices[1] if len(prices) > 1 else 0

                    # Link
                    link_el = await card.query_selector("a.deal__inner")
                    link = ""
                    if link_el:
                        href = await link_el.get_attribute("href") or ""
                        if href:
                            link = "https://chocolife.me" + href if not href.startswith("http") else href

                    deals.append({
                        "title": title.strip(),
                        "restaurant_name": restaurant.strip().replace("\xa0", " "),
                        "original_price": original_price,
                        "discount_price": discount_price,
                        "discount_percent": discount_percent,
                        "description": (description.strip() + (f" ({location})" if location else ""))[:200],
                        "url": link or url,
                    })
                except Exception:
                    continue
        finally:
            await browser.close()

    return deals


@mcp.tool()
async def search_deals(category: str = "рестораны", city: str = "Алматы") -> str:
    """
    Find deals, discounts and coupons for restaurants in Almaty via Chocolife.

    Args:
        category: deal category, e.g. 'рестораны', 'кафе', 'суши'
        city: city name, default Алматы

    Returns:
        JSON list of deals with title, restaurant_name, original_price,
        discount_price, discount_percent, description, url.
    """
    cache_key = f"chocolife:{category}:{city}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        results = await _scrape_chocolife(category, city)
        if results:
            result_json = json.dumps(results, ensure_ascii=False, indent=2)
            _cache_set(cache_key, result_json)
            return result_json
    except Exception as e:
        return json.dumps({"error": f"Ошибка Chocolife: {str(e)}"}, ensure_ascii=False)

    return json.dumps({"error": "Акции не найдены"}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
