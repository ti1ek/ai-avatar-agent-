"""
Pipeline orchestrator: ASR → LLM (MCP) → TTS → Avatar Video

Entry point for the Gradio UI.
"""
import asyncio
import base64
import tempfile
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from config import OPENAI_API_KEY, ASR_MODEL
from agent.llm import MCPAgentSession
from voice.tts import generate_tts
from avatar.generate import generate_avatar_video

_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Global MCP session (kept alive for the app lifetime)
_mcp_session: MCPAgentSession | None = None
_session_lock = asyncio.Lock()


async def get_mcp_session() -> MCPAgentSession:
    """Return (or lazily create) the global MCP session."""
    global _mcp_session
    async with _session_lock:
        if _mcp_session is None:
            _mcp_session = MCPAgentSession()
            await _mcp_session.__aenter__()
    return _mcp_session


async def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file using OpenAI Whisper."""
    with open(audio_path, "rb") as f:
        transcript = await _openai.audio.transcriptions.create(
            model=ASR_MODEL,
            file=f,
            language="ru",
        )
    return transcript.text


def _image_to_data_uri(image_path: str) -> str:
    """Convert local image to base64 data URI."""
    path = Path(image_path)
    suffix = path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


async def run_pipeline(
    text_input: str | None,
    audio_path: str | None,
    image_path: str | None,
    conversation_history: list[dict],
    generate_audio: bool = True,
    generate_video: bool = False,
) -> dict[str, Any]:
    """
    Full pipeline: input → text response + audio + (optionally) video.

    Returns dict with keys:
        user_text, assistant_text, tool_calls, audio_path, video_url
    """
    result: dict[str, Any] = {
        "user_text": "",
        "assistant_text": "",
        "tool_calls": [],
        "audio_path": None,
        "video_url": None,
    }

    # ── Step 1: ASR ────────────────────────────────────────────────────────────
    user_text = text_input or ""
    if audio_path:
        try:
            transcribed = await transcribe_audio(audio_path)
            user_text = transcribed if transcribed else user_text
            print(f"[ASR] Transcribed: {user_text!r}")
        except Exception as e:
            print(f"[ASR] Error: {e}")
            result["assistant_text"] = f"Ошибка распознавания речи: {e}"
            return result

    result["user_text"] = user_text

    if not user_text and not image_path:
        result["assistant_text"] = "Пожалуйста, введите текст или запишите голосовое сообщение."
        return result

    # ── Step 2: Build image URL + auto-run restaurant critic skill ───────────
    image_url: str | None = None
    photo_analysis: str = ""
    if image_path:
        try:
            image_url = _image_to_data_uri(image_path)
        except Exception as e:
            print(f"[Image] Error converting image: {e}")

        if image_url:
            try:
                from agent.tools import analyze_restaurant_photo
                import json as _json
                analysis = await analyze_restaurant_photo(image_url)
                photo_analysis = (
                    f"\n\n[Оценка ресторана по фото]: "
                    f"Уровень: {analysis.get('level', '?')}, "
                    f"Статус: {analysis.get('status', '?')}, "
                    f"Описание: {analysis.get('description', '?')} "
                    f"(уверенность: {analysis.get('confidence', 0):.0%})"
                )
                print(f"[Skill] Photo analysis: {analysis}")
            except Exception as e:
                print(f"[Skill] analyze_restaurant_photo error: {e}")

    # Append skill result to user text so LLM uses it
    if photo_analysis:
        if user_text:
            enriched_user_text = user_text + photo_analysis + "\n\nОпираясь на этот анализ, дай рекомендацию."
        else:
            enriched_user_text = (
                "Фото ресторана уже проанализировано автоматически."
                + photo_analysis
                + "\n\nДай краткую рекомендацию по этому ресторану на основе результатов анализа. "
                "НЕ вызывай analyze_restaurant_photo — анализ уже выполнен."
            )
    else:
        enriched_user_text = user_text

    # ── Step 3: LLM + MCP tool calling ────────────────────────────────────────
    # If photo was already analyzed by skill, don't re-send base64 to LLM
    # (saves tokens and avoids silent API failures due to payload size)
    llm_image_url = None if photo_analysis else image_url

    print(f"[LLM] Calling session.chat, text_len={len(enriched_user_text)}, has_image={llm_image_url is not None}", flush=True)
    try:
        import asyncio as _asyncio
        session = await get_mcp_session()
        assistant_text, tool_calls = await _asyncio.wait_for(
            session.chat(
                history=conversation_history,
                user_text=enriched_user_text,
                image_url=llm_image_url,
            ),
            timeout=60.0,
        )
        print(f"[LLM] Done: {assistant_text[:80]!r}", flush=True)
    except _asyncio.TimeoutError:
        print("[LLM] Timeout after 60s", flush=True)
        assistant_text = "Извините, запрос занял слишком много времени. Попробуйте ещё раз."
        tool_calls = []
    except Exception as e:
        import traceback
        print(f"[LLM] Error: {e}", flush=True)
        traceback.print_exc()
        assistant_text = "Произошла ошибка. Попробуйте ещё раз."
        tool_calls = []

    result["assistant_text"] = assistant_text
    result["tool_calls"] = tool_calls

    if not assistant_text:
        return result

    # ── Step 4: TTS ────────────────────────────────────────────────────────────
    print(f"[Pipeline] generate_audio={generate_audio}, generate_video={generate_video}")
    if generate_audio or generate_video:
        try:
            audio_out = await generate_tts(assistant_text)
            result["audio_path"] = audio_out
            print(f"[Pipeline] TTS done: {audio_out}")
        except Exception as e:
            import traceback
            print(f"[TTS] Error: {e}")
            traceback.print_exc()

    # ── Step 5: Avatar video (only when requested and audio is ready) ──────────
    if generate_video and result["audio_path"]:
        try:
            video_url = await generate_avatar_video(result["audio_path"])
            result["video_url"] = video_url
        except Exception as e:
            print(f"[Avatar] Error: {e}")

    return result
