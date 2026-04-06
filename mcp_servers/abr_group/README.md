# MCP №2: ABR Group

Информация о ресторанах сети ABR Group через парсинг [abr.kz](https://abr.kz).

## Инструмент

### `get_restaurant_info`

Возвращает детальную информацию о ресторане ABR Group по названию.

**Параметры:**

| Параметр | Тип | Обязателен | Описание |
|----------|-----|------------|----------|
| `name` | string | да | Название ресторана, например `Del Papa`, `AUYL`, `SPIROS` |

**Доступные рестораны:**
Del Papa, AUYL, SPIROS, cafe Alma, Astra Grand Cafe, CANTEEN, PALOMAR, Ami, Aroma, JINAU, Broadway Burger, Кафе Афиша, Cafeteria, Огонёк, Luckee Yu, Дареджани, COCO, RAW

**Пример ответа:**

```json
{
  "name": "Del Papa",
  "address": [
    "б-р. Бухар жырау, 66",
    "ул. Гоголя, 87",
    "ТРЦ Dostyk Plaza"
  ],
  "phone": "+7 771 722 82 21",
  "working_hours": "Пн-Вс с 10:00 до 23:00",
  "booking_url": "https://booking-web.abr.dev/",
  "description": "Сеть уютных итальянских ресторанов с классикой итальянской кухни.",
  "menu_highlights": [],
  "average_check": ""
}
```

## Реализация

- **Парсинг**: Playwright (headless Chromium)
- **Slug-поиск**: динамически определяется через парсинг главной страницы `abr.kz`
- **Адреса**: поддерживает одно- и многолокационные рестораны (паттерн: город → адрес → Контакты → телефон → Работаем → часы)
- **Кэш**: 10 минут (`CACHE_TTL = 600`)
- **Протокол**: MCP stdio

## Запуск (для отладки)

```bash
python mcp_servers/abr_group/server.py
```
