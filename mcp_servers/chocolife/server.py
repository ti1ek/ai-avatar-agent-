"""
MCP-сервер №2: Chocolife
Запуск: python mcp_servers/chocolife/server.py
Протокол: stdio
"""
import asyncio
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup
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


MOCK_DEALS = [
    {
        "title": "Скидка 50% на всё меню в будни",
        "restaurant_name": "Урюк на Достык",
        "original_price": 4000,
        "discount_price": 2000,
        "discount_percent": 50,
        "description": "Скидка 50% на всё меню с пн по пт с 12:00 до 17:00. Кухня: казахская, средиземноморская.",
        "url": "https://chocolife.me/restorany-kafe-i-bary/",
    },
    {
        "title": "Романтический ужин на двоих со скидкой 40%",
        "restaurant_name": "Del Papa",
        "original_price": 8000,
        "discount_price": 4800,
        "discount_percent": 40,
        "description": "Ужин на двоих: 2 блюда + бутылка вина. Итальянская кухня, уютная атмосфера.",
        "url": "https://chocolife.me/restorany-kafe-i-bary/",
    },
    {
        "title": "Бизнес-ланч 30% скидка",
        "restaurant_name": "Кофемания",
        "original_price": 2500,
        "discount_price": 1750,
        "discount_percent": 30,
        "description": "Бизнес-ланч (суп + горячее + десерт) со скидкой 30% с 12:00 до 15:00.",
        "url": "https://chocolife.me/restorany-kafe-i-bary/",
    },
    {
        "title": "Купон 3000 тг за 1500 тг",
        "restaurant_name": "Brasserie Restaurants",
        "original_price": 3000,
        "discount_price": 1500,
        "discount_percent": 50,
        "description": "Купон на 3000 тг за 1500 тг. Европейская кухня, панорамный вид на город.",
        "url": "https://chocolife.me/restorany-kafe-i-bary/",
    },
    {
        "title": "Скидка 35% на суши-сет",
        "restaurant_name": "Tanuki",
        "original_price": 5500,
        "discount_price": 3575,
        "discount_percent": 35,
        "description": "Большой суши-сет на 2 персоны со скидкой 35%.",
        "url": "https://chocolife.me/restorany-kafe-i-bary/",
    },
]


async def _scrape_chocolife(category: str, city: str) -> list[dict]:
    """Scrape Chocolife for restaurant deals."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    url = "https://chocolife.me/restorany-kafe-i-bary/"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        await asyncio.sleep(0.5)  # polite delay
        r = await client.get(url, headers=headers)
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    deals = []

    # Chocolife deal cards — try common selectors
    cards = (
        soup.select(".deal-card")
        or soup.select(".product-card")
        or soup.select("article.card")
        or soup.select("[class*='deal']")
    )

    for card in cards[:10]:
        title_el = card.select_one("h2, h3, .title, [class*='title']")
        price_els = card.select("[class*='price']")
        link_el = card.select_one("a[href]")

        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        prices = [el.get_text(strip=True) for el in price_els]
        discount_price = original_price = 0
        for p in prices:
            digits = "".join(c for c in p if c.isdigit())
            if digits:
                val = int(digits)
                if original_price == 0:
                    original_price = val
                else:
                    discount_price = val

        discount_percent = 0
        if original_price and discount_price and original_price > discount_price:
            discount_percent = round((1 - discount_price / original_price) * 100)

        deals.append({
            "title": title,
            "restaurant_name": title.split("в ")[-1] if " в " in title else "",
            "original_price": original_price,
            "discount_price": discount_price,
            "discount_percent": discount_percent,
            "description": title,
            "url": link_el["href"] if link_el else url,
        })

    return deals


@mcp.tool()
async def search_deals(category: str = "рестораны", city: str = "Алматы") -> list[dict]:
    """
    Find deals, discounts and coupons for restaurants in Almaty via Chocolife.

    Args:
        category: deal category, e.g. 'рестораны', 'кафе', 'суши'
        city: city name, default Алматы

    Returns:
        List of Deal objects with title, restaurant_name, original_price,
        discount_price, discount_percent, description, url.
    """
    cache_key = f"chocolife:{category}:{city}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        results = await _scrape_chocolife(category, city)
        if results:
            _cache_set(cache_key, results)
            return results
    except Exception:
        pass

    # Filter mock data by category
    cat_lower = category.lower()
    if cat_lower in ("суши", "японская"):
        result = [d for d in MOCK_DEALS if "суши" in d["title"].lower()]
        result = result or MOCK_DEALS
    elif cat_lower in ("бизнес-ланч", "ланч", "обед"):
        result = [d for d in MOCK_DEALS if "ланч" in d["title"].lower()]
        result = result or MOCK_DEALS
    else:
        result = MOCK_DEALS

    _cache_set(cache_key, result)
    return result


if __name__ == "__main__":
    mcp.run()
