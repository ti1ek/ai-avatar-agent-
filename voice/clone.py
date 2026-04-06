"""
Voice cloning via fal.ai MiniMax Voice Clone.

Run this script ONCE to clone your voice and get a voice_id.
Then put the voice_id into .env as MINIMAX_VOICE_ID.

Usage:
    python voice/clone.py
"""
import asyncio
import os
import sys
from pathlib import Path

import fal_client

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import FAL_KEY, VOICE_CLONE_MODEL, VOICE_SAMPLE_PATH

os.environ["FAL_KEY"] = FAL_KEY


async def upload_voice_sample(local_path: str) -> str:
    """Upload local audio file to fal.ai storage and return public URL."""
    print(f"[clone] Uploading voice sample: {local_path}")
    url = await fal_client.upload_file_async(local_path)
    print(f"[clone] Uploaded → {url}")
    return url


async def clone_voice(audio_url: str, preview_text: str = "Привет! Это тест клонированного голоса.") -> str:
    """
    Clone voice from audio sample.
    Returns voice_id string — save this to .env as MINIMAX_VOICE_ID.
    """
    print(f"[clone] Cloning voice from {audio_url}...")
    result = await fal_client.subscribe_async(
        VOICE_CLONE_MODEL,
        arguments={
            "audio_url": audio_url,
            "preview_text": preview_text,
            "language": "Russian",
        },
        with_logs=True,
    )
    voice_id = result.get("custom_voice_id") or result.get("voice_id") or result.get("id", "")
    print(f"[clone] Voice cloned! voice_id = {voice_id}")
    print(f'\nAdd this to your .env file:\n  MINIMAX_VOICE_ID={voice_id}\n')
    return voice_id


async def main() -> None:
    sample_path = VOICE_SAMPLE_PATH
    if not Path(sample_path).exists():
        print(f"ERROR: Voice sample not found at '{sample_path}'")
        print("Please record at least 10 seconds of your voice and save it as:")
        print(f"  {sample_path}")
        sys.exit(1)

    audio_url = await upload_voice_sample(sample_path)
    voice_id = await clone_voice(audio_url)
    return voice_id


if __name__ == "__main__":
    asyncio.run(main())
