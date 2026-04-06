"""
Text-to-Speech via fal.ai MiniMax Speech-02-HD using cloned voice.
"""
import asyncio
import os
import tempfile
from pathlib import Path

import fal_client
import httpx

from config import FAL_KEY, TTS_MODEL, MINIMAX_VOICE_ID, TTS_LANGUAGE

os.environ["FAL_KEY"] = FAL_KEY


async def generate_tts(text: str) -> str:
    """
    Convert text to speech using the cloned MiniMax voice.

    Args:
        text: text to synthesize (keep under 600 chars for short audio)

    Returns:
        Path to a local .mp3 file with the generated audio.
    """
    if not MINIMAX_VOICE_ID:
        raise ValueError(
            "MINIMAX_VOICE_ID is not set. "
            "Run 'python voice/clone.py' first, then add the voice_id to .env"
        )

    # Truncate to safe length
    if len(text) > 800:
        text = text[:800].rsplit(".", 1)[0] + "."

    print(f"[TTS] Generating audio ({len(text)} chars)...")

    result = await fal_client.subscribe_async(
        TTS_MODEL,
        arguments={
            "text": text,
            "voice_id": MINIMAX_VOICE_ID,
            "language": TTS_LANGUAGE,
            "speed": 1.0,
            "pitch": 0,
        },
        with_logs=False,
    )

    audio_url = (
        result.get("audio", {}).get("url")
        or result.get("audio_url")
        or result.get("url")
        or ""
    )

    if not audio_url:
        raise RuntimeError(f"TTS returned no audio URL. Result: {result}")

    print(f"[TTS] Audio ready → {audio_url}")
    return await _download_audio(audio_url)


async def _download_audio(url: str) -> str:
    """Download audio from URL to a temporary local file."""
    suffix = ".mp3" if "mp3" in url else ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(tmp.name, "wb") as f:
                async for chunk in r.aiter_bytes(8192):
                    f.write(chunk)

    print(f"[TTS] Saved audio → {tmp.name}")
    return tmp.name
