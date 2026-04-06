"""
Tool schemas that the LLM can call via function calling.

Contains:
- MCP tool wrappers (search_restaurants, search_deals, get_restaurant_info)
- Custom skill: analyze_restaurant_photo (restaurant critic)
"""
import base64
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
                "Search for restaurants, cafes, bars in Almaty via 2GIS. "
                "Use this when user asks about where to eat, dining options, "
                "restaurants by cuisine type or location."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'ресторан на двоих', 'суши', 'кофейня центр'",
                    },
                    "location": {
                        "type": "string",
                        "description": "City name, default 'Алматы'",
                        "default": "Алматы",
                    },
                },
                "required": ["query"],
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
                        "description": "Public URL or base64 data URI of the restaurant/food photo",
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
        "You are an expert restaurant critic. Analyze this photo of a restaurant "
        "(interior, food, or signage) and respond ONLY with valid JSON:\n"
        "{\n"
        '  "level": "<fastfood|casual|mid-range|fine dining>",\n'
        '  "status": "<семейный|романтический|бизнес-ланч|молодёжный|fine dining>",\n'
        '  "description": "<2-3 sentence atmosphere and audience description in Russian>",\n'
        '  "confidence": <0.0-1.0>\n'
        "}"
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
