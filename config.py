import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
FAL_KEY = os.getenv("FAL_KEY", "")

# ── Voice / Avatar ─────────────────────────────────────────────────────────────
MINIMAX_VOICE_ID = os.getenv("MINIMAX_VOICE_ID", "")   # already cloned voice id
AVATAR_PHOTO_PATH = os.getenv("AVATAR_PHOTO_PATH", "avatar/my_photo.jpg")
VOICE_SAMPLE_PATH = os.getenv("VOICE_SAMPLE_PATH", "voice/my_voice_sample.wav")

# ── Models ─────────────────────────────────────────────────────────────────────
LLM_MODEL = "gpt-4o-mini"           # cheap, fast, tool calling, vision
ASR_MODEL = "whisper-1"

TTS_MODEL = "fal-ai/minimax/speech-02-hd"
VOICE_CLONE_MODEL = "fal-ai/minimax/voice-clone"
AVATAR_MODEL = "fal-ai/kling-video/ai-avatar/v2"        # primary ~$0.014/sec


# ── Generation params ──────────────────────────────────────────────────────────
TTS_LANGUAGE = "Russian"

# ── Cost optimisation ──────────────────────────────────────────────────────────
IMAGE_DETAIL = "low"          # pass to vision calls  → cheaper
MAX_RESPONSE_CHARS = 600      # keep TTS audio short (~20-30 sec)

# ── MCP server commands ────────────────────────────────────────────────────────
MCP_SERVERS = {
    "chocolife": {
        "command": "python",
        "args": ["mcp_servers/chocolife/server.py"],
        "description": "Find deals, discounts and coupons for Almaty restaurants via Chocolife",
    },
    "abr_group": {
        "command": "python",
        "args": ["mcp_servers/abr_group/server.py"],
        "description": "Get info about ABR Group restaurants (Bochka, Del Papa, etc.)",
    },
}
