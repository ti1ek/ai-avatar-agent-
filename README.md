# AI Avatar Agent — Мультимодальный ресторанный гид Алматы

Персональный ИИ-ассистент по ресторанам Алматы с говорящим аватаром.

## Архитектура

```
Пользователь (текст / голос / фото)
        │
        ▼
   ASR (Whisper)          ← расшифровка голоса
        │
        ▼
   LLM GPT-4o-mini        ← мозг агента + memory сессии
   + Function Calling
        │
   ┌────┴────────────────────┐
   │                         │
   ▼                         ▼
MCP: 2GIS             MCP: Chocolife        MCP: ABR Group (бонус)
search_restaurants    search_deals          get_restaurant_info
        │
        ▼
   Текстовый ответ
        │
        ├──→ TTS (fal.ai MiniMax Speech-02-HD, клонированный голос)
        │                    │
        │                    ▼
        └──→ Avatar Video (fal.ai Creatify Aurora) ← фото студента
                             │
                             ▼
                       Gradio UI (текст + аудио + видео)
```

## Компоненты

| Компонент | Технология |
|-----------|-----------|
| ASR | OpenAI Whisper-1 |
| LLM Brain | GPT-4o-mini (tool calling + vision) |
| MCP №1 | 2GIS — поиск ресторанов Алматы |
| MCP №2 | Chocolife — скидки и акции |
| MCP №3 | ABR Group — детали ресторанов (бонус) |
| Custom Skill | Ресторанный критик (analyze_restaurant_photo) |
| TTS | fal.ai MiniMax Speech-02-HD |
| Voice Clone | fal.ai MiniMax Voice Clone |
| Avatar Video | fal.ai Creatify Aurora |
| Frontend | Gradio |

## Быстрый старт

### 1. Клонировать и установить зависимости

```bash
git clone <repo>
cd video-ai
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
# Открыть .env и заполнить ключи
```

Заполни `.env`:
```
OPENAI_API_KEY=sk-...
FAL_KEY=...
MINIMAX_VOICE_ID=your_voice_id    # см. шаг 3
AVATAR_PHOTO_PATH=avatar/my_photo.jpg
VOICE_SAMPLE_PATH=voice/my_voice_sample.wav
```

### 3. Подготовить голос и фото

**Голос** — если voice_id ещё нет:
1. Запиши аудиосэмпл своего голоса (минимум 10 секунд, чистый звук)
2. Сохрани в `voice/my_voice_sample.wav`
3. Запусти клонирование:
   ```bash
   python voice/clone.py
   ```
4. Скопируй полученный `voice_id` в `.env` → `MINIMAX_VOICE_ID`

**Фото** — если photo уже есть:
- Сохрани фронтальный портрет (минимум 512×512, нейтральный фон) в `avatar/my_photo.jpg`

### 4. Запустить приложение

```bash
python app.py
```

Открой в браузере: http://localhost:7860

## Запуск MCP-серверов (для отладки отдельно)

MCP-серверы запускаются автоматически как subprocess при старте `app.py`.
Для ручного тестирования:

```bash
# Тест 2GIS MCP сервера
python mcp_servers/twogis/server.py

# Тест Chocolife MCP сервера
python mcp_servers/chocolife/server.py

# Тест ABR Group MCP сервера
python mcp_servers/abr_group/server.py
```

Серверы используют stdio транспорт (MCP-протокол).

## Примеры запросов

- «Где поужинать в центре Алматы на двоих, бюджет 15 000 тг?»
- «Найди скидки на суши»
- «Что есть в Del Papa?»
- *(прислать фото ресторана)* → агент определит уровень заведения

## Структура проекта

```
video-ai/
├── app.py                    # Gradio UI (точка входа)
├── config.py                 # Конфигурация моделей и параметров
├── requirements.txt
├── .env.example
├── agent/
│   ├── llm.py               # LLM + MCP клиент + agentic loop
│   ├── tools.py             # Tool schemas + ресторанный критик
│   └── pipeline.py          # Оркестратор: ASR → LLM → TTS → Avatar
├── mcp_servers/
│   ├── twogis/server.py     # MCP сервер 2GIS
│   ├── chocolife/server.py  # MCP сервер Chocolife
│   └── abr_group/server.py  # MCP сервер ABR Group (бонус)
├── voice/
│   ├── clone.py             # Скрипт клонирования голоса
│   ├── tts.py               # Генерация TTS
│   └── my_voice_sample.wav  # (добавить самостоятельно)
├── avatar/
│   ├── generate.py          # Генерация видео через Creatify Aurora
│   └── my_photo.jpg         # (добавить самостоятельно)
└── assets/
    └── demo.mp4             # (добавить после записи)
```

## Оптимизация стоимости (бонус)

- **Model routing**: GPT-4o-mini для всего (vision + text) — дешевле GPT-4o
- **Caching**: результаты MCP-серверов кэшируются на 5 минут (`CACHE_TTL = 300`)
- **`detail: "low"`** для всех vision-вызовов — экономия токенов
- **Видео генерируется по запросу** — чекбокс «Генерировать видео» по умолчанию выключен
- Ответы ограничены 600 символами → короткое аудио → короткое видео

## Примерный бюджет

| Сервис | Стоимость |
|--------|-----------|
| fal.ai (Creatify Aurora) | ~$0.05–0.10 за видео |
| fal.ai (MiniMax TTS) | ~$0.03–0.05 за ответ |
| fal.ai (Voice Clone) | ~$0.50 (один раз) |
| OpenAI (GPT-4o-mini + Whisper) | ~$0.01–0.02 за запрос |
| **Итого на проект** | **~$5–15** |

## Что бы улучшил с большим временем

1. Добавить Playwright для более надёжного парсинга 2GIS в реальном времени
2. Persistent memory (Redis/SQLite) между сессиями
3. Streaming TTS для мгновенного воспроизведения
4. Веб-поиск как дополнительный MCP-инструмент
5. Авторизация пользователей и история чатов
