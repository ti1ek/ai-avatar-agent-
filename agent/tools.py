"""
Tool schemas that the LLM can call via function calling.

Contains:
- MCP tool wrappers (search_deals, get_restaurant_info)
- Custom skill: analyze_restaurant_photo (restaurant critic)
"""
import json
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, LLM_MODEL, IMAGE_DETAIL

_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ── OpenAI tool schemas (sent to LLM) ─────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_restaurants",
            "description": (
                "Search for restaurants in Almaty via 2GIS. "
                "Use this for general restaurant searches: by cuisine, area, vibe, or budget. "
                "Returns real restaurant names, ratings, addresses from 2GIS."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'рестораны', 'суши', 'кофейня', 'бизнес-ланч', 'итальянская кухня'",
                        "default": "рестораны",
                    },
                    "city": {
                        "type": "string",
                        "description": "City slug for 2GIS, default 'almaty'",
                        "default": "almaty",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_deals",
            "description": (
                "Find deals, discounts and coupons for Almaty restaurants via Chocolife. "
                "Use this when user asks about discounts, promotions, budget dining, cheap options."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Deal category, e.g. 'рестораны', 'суши', 'бизнес-ланч'",
                        "default": "рестораны",
                    },
                    "city": {
                        "type": "string",
                        "description": "City name, default 'Алматы'",
                        "default": "Алматы",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_restaurant_info",
            "description": (
                "Get detailed info (menu, price, booking) for ABR Group restaurants: "
                "Del Papa, Bochka, Pinta, Chagala. Use when user specifically asks about these restaurants."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Restaurant name, e.g. 'Del Papa', 'Бочка', 'Pinta'",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_restaurant_photo",
            "description": (
                "Analyze a restaurant photo (interior, signage, hall) and determine: "
                "establishment level (fastfood/casual/mid-range/fine dining), "
                "status/vibe (family, romantic, business-lunch, youth, etc.), "
                "and a brief atmosphere description. "
                "ALWAYS use this tool when the user provides a restaurant photo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "image_url": {
                        "type": "string",
                        "description": (
                            "URL of the restaurant photo. "
                            "If the user sent an image directly (not a URL), pass 'current_image' as the value."
                        ),
                    }
                },
                "required": ["image_url"],
            },
        },
    },
]


async def analyze_restaurant_photo(image_url: str) -> dict:
    """
    Custom skill — Ресторанный критик.
    Analyzes restaurant/food photo with GPT-4o-mini vision.
    Returns: level, status, description, confidence.
    """
    prompt = (
        "Ты эксперт-ресторанный критик. Внимательно изучи фото ресторана "
        "(интерьер, вывеска, зал, атмосфера) и ответь ТОЛЬКО валидным JSON без пояснений:\n"
        "{\n"
        '  "level": "<fastfood|casual|mid-range|fine dining>",\n'
        '  "status": "<семейный|романтический|бизнес-ланч|молодёжный|вечеринки>",\n'
        '  "description": "<2-3 предложения: атмосфера заведения и целевая аудитория на русском>",\n'
        '  "confidence": <0.0-1.0>\n'
        "}\n\n"
        "level — уровень заведения: fastfood (фастфуд), casual (повседневный), "
        "mid-range (средний ценовой сегмент), fine dining (высокая кухня).\n"
        "status — основная аудитория и атмосфера: семейный, романтический, бизнес-ланч, молодёжный, вечеринки.\n"
        "description — кратко опиши атмосферу и для кого подходит это заведение."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                        "detail": IMAGE_DETAIL,  # "low" — cheaper
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]

    response = await _openai.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=300,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "level": "mid-range",
            "status": "семейный",
            "description": raw[:200],
            "confidence": 0.5,
        }
