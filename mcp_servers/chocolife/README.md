# MCP №1: Chocolife

Поиск скидок и акций на рестораны Алматы через парсинг [chocolife.me](https://chocolife.me).

## Инструмент

### `search_deals`

Возвращает список актуальных акций с сайта Chocolife.

**Параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `category` | string | `"рестораны"` | Категория акции: `рестораны`, `суши`, `бизнес-ланч` и др. |
| `city` | string | `"Алматы"` | Город поиска |

**Пример ответа:**

```json
[
  {
    "title": "Скидка 30% на все меню в ресторане Flamingo!",
    "restaurant_name": "Ресторан Flamingo",
    "original_price": 5000,
    "discount_price": 3500,
    "discount_percent": 30,
    "description": "Скидка 30% на все меню в ресторане Flamingo!",
    "url": "https://chocolife.me/12345-flamingo/"
  }
]
```

## Реализация

- **Парсинг**: Playwright (headless Chromium) — сайт использует Angular SSR
- **Селекторы**: компонент `<cl-deal>`, название ресторана из `.deal__desc span:first-child`
- **Лимит**: первые 10 акций за запрос
- **Кэш**: 5 минут (`CACHE_TTL = 300`)
- **Протокол**: MCP stdio

## Запуск (для отладки)

```bash
python mcp_servers/chocolife/server.py
```
