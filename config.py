import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
FAL_KEY = os.getenv("FAL_KEY", "")

# fal_client reads FAL_KEY from env
os.environ.setdefault("FAL_KEY", FAL_KEY)

# Voice / Avatar
MINIMAX_VOICE_ID = os.getenv("MINIMAX_VOICE_ID", "")
AVATAR_PHOTO_PATH = os.getenv("AVATAR_PHOTO_PATH", "avatar/my_photo.jpg")
VOICE_SAMPLE_PATH = os.getenv("VOICE_SAMPLE_PATH", "voice/my_voice_sample.wav")

# Models
LLM_MODEL = "gpt-4o-mini"
ASR_MODEL = "whisper-1"
TTS_MODEL = "fal-ai/minimax/speech-02-hd"
VOICE_CLONE_MODEL = "fal-ai/minimax/voice-clone"
AVATAR_MODEL = "fal-ai/kling-video/v1/pro/ai-avatar"

# Generation params
TTS_LANGUAGE = "Russian"
IMAGE_DETAIL = "low"
MAX_RESPONSE_CHARS = 600

# MCP server paths (launched as subprocesses via stdio)
MCP_SERVERS = {
    "twogis": {
        "args": ["mcp_servers/twogis/server.py"],
    },
    "chocolife": {
        "args": ["mcp_servers/chocolife/server.py"],
    },
    "abr_group": {
        "args": ["mcp_servers/abr_group/server.py"],
    },
}
