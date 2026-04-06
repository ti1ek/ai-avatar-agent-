"""
Avatar video generation via fal.ai Kling Avatar V2.
Combines student photo + cloned TTS audio → talking avatar video.
"""
from pathlib import Path

import fal_client

from config import AVATAR_MODEL, AVATAR_PHOTO_PATH

_avatar_photo_url: str | None = None


async def _upload_photo() -> str:
    global _avatar_photo_url
    if _avatar_photo_url:
        return _avatar_photo_url

    photo_path = AVATAR_PHOTO_PATH
    if not Path(photo_path).exists():
        raise FileNotFoundError(
            f"Avatar photo not found at '{photo_path}'. "
            "Place your frontal portrait photo there (min 512x512px)."
        )

    print(f"[Avatar] Uploading photo: {photo_path}")
    url = await fal_client.upload_file_async(photo_path)
    print(f"[Avatar] Photo uploaded → {url}")
    _avatar_photo_url = url
    return url


async def generate_avatar_video(audio_path: str) -> str:
    """
    Generate talking avatar video from student photo + TTS audio.
    Uses Kling Avatar V2 (~$0.014/sec).

    Returns:
        URL of the generated video (.mp4)
    """
    image_url = await _upload_photo()

    print(f"[Avatar] Uploading audio: {audio_path}")
    audio_url = await fal_client.upload_file_async(audio_path)
    print(f"[Avatar] Audio uploaded → {audio_url}")

    print("[Avatar] Generating video with Kling Avatar V2...")
    result = await fal_client.subscribe_async(
        AVATAR_MODEL,
        arguments={
            "image_url": image_url,
            "audio_url": audio_url,
            "prompt": (
                "A calm, composed person speaking naturally. "
                "Minimal head movement, subtle and relaxed facial expressions. "
                "No exaggerated eyebrow raises or wide eye movements. "
                "Steady posture, gentle lip sync, professional and neutral demeanor."
            ),
        },
        with_logs=True,
    )

    video_url = (
        result.get("video", {}).get("url")
        or result.get("video_url")
        or result.get("url")
        or ""
    )

    if not video_url:
        raise RuntimeError(f"Avatar generation returned no video URL. Result: {result}")

    print(f"[Avatar] Video ready → {video_url}")
    return video_url
