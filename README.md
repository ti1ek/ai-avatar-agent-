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
   ┌────┼────────────────────┐
   │    │                    │
   ▼    ▼                    ▼
MCP №1       MCP №2     Custom Skill
Chocolife    ABR Group  analyze_restaurant_photo
search_deals get_        (GPT-4o-mini vision)
             restaurant_
             info
        │
        ▼
   Текстовый ответ
        │
        ├──→ TTS (fal.ai MiniMax Speech-02-HD, клонированный голос)
        │                    │
        │                    ▼
        └──→ Avatar Video (fal.ai Kling AI Avatar V2) ← фото студента
                             │
                             ▼
                       Gradio UI (текст + видео)
```

## Компоненты

| Компонент | Технология |
|-----------|-----------|
| ASR | OpenAI Whisper-1 |
| LLM Brain | GPT-4o-mini (tool calling + vision) |
| MCP №1 | Chocolife — скидки и акции на рестораны |
| MCP №2 | ABR Group — детальная информация о ресторанах |
| Custom Skill | Ресторанный критик (analyze_restaurant_photo) |
| TTS | fal.ai MiniMax Speech-02-HD |
| Voice Clone | fal.ai MiniMax Voice Clone |
| Avatar Video | fal.ai Kling AI Avatar V2 |
| Frontend | Gradio |

## Быстрый старт

### 1. Клонировать и установить зависимости

```bash
git clone <repo>
cd video-ai
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
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

**Фото** — сохрани фронтальный портрет (минимум 512×512, нейтральный фон) в `avatar/my_photo.jpg`

### 4. Запустить приложение

```bash
python app.py
```

Открой в браузере: http://localhost:7860

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
│   ├── chocolife/
│   │   ├── server.py        # MCP №1: Chocolife (акции и скидки)
│   │   └── README.md        # Документация инструмента
│   └── abr_group/
│       ├── server.py        # MCP №2: ABR Group (рестораны)
│       └── README.md        # Документация инструмента
├── voice/
│   ├── clone.py             # Скрипт клонирования голоса
│   ├── tts.py               # Генерация TTS
│   └── my_voice_sample.wav  # (добавить самостоятельно)
├── avatar/
│   ├── generate.py          # Генерация видео через Kling Avatar V2
│   └── my_photo.jpg         # (добавить самостоятельно)
└── assets/
    └── demo.mp4             # (добавить после записи)
```

## Примеры запросов

- «Где поужинать в центре Алматы на двоих, бюджет 15 000 тг?»
- «Найди скидки на суши»
- «Что есть в Del Papa?»
- *(прислать фото ресторана)* → агент определит уровень заведения

## Оптимизация стоимости

- **Model routing**: GPT-4o-mini для всего (vision + text) — дешевле GPT-4o
- **Caching**: результаты Chocolife кэшируются на 5 минут (`CACHE_TTL = 300`), ABR Group — на 10 минут (`CACHE_TTL = 600`)
- **`detail: "low"`** для всех vision-вызовов — экономия токенов
- **Видео генерируется по запросу** — чекбокс «Видео-ответ» по умолчанию выключен
- Ответы ограничены 600 символами → короткое аудио → короткое видео

## Примерный бюджет

| Сервис | Стоимость |
|--------|-----------|
| fal.ai (Kling Avatar V2) | ~$0.05–0.10 за видео |
| fal.ai (MiniMax TTS) | ~$0.03–0.05 за ответ |
| fal.ai (Voice Clone) | ~$0.50 (один раз) |
| OpenAI (GPT-4o-mini + Whisper) | ~$0.01–0.02 за запрос |
| **Итого на проект** | **~$5–15** |
