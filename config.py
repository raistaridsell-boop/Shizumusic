"""
config.py — All environment variables in one place.
Copy sample.env → .env and fill in your values.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Required ──────────────────────────────────────────────────────────────────
API_ID          = int(os.environ["API_ID"])
API_HASH        = os.environ["API_HASH"]
BOT_TOKEN       = os.environ["BOT_TOKEN"]
STRING_SESSION  = os.environ["STRING_SESSION"]
MONGO_DB_URL    = os.environ["MONGO_DB_URL"]
OWNER_ID        = int(os.environ["OWNER_ID"])

# ── Optional ──────────────────────────────────────────────────────────────────
BOT_NAME         = os.getenv("BOT_NAME", "BMW Music")
BOT_LINK         = os.getenv("BOT_LINK", "https://t.me/BmwsongBot")
UPDATES_CHANNEL  = os.getenv("UPDATES_CHANNEL", "https://t.me/Axynetwork")
SUPPORT_GROUP    = os.getenv("SUPPORT_GROUP", "https://t.me/AxychATS")
LOGGER_ID        = int(os.getenv("LOGGER_ID", "0"))
PING_IMG_URL     = os.getenv("PING_IMG_URL", "https://files.catbox.moe/35tfwv.jpg",)
SESSION_NAME     = os.getenv("SESSION_NAME", "bmwMusic")
PORT             = int(os.getenv("PORT", 10000))

# ── NSFW Moderation API ─────────────────────────────────────────────────────
NSFW_API_URL = os.getenv("NSFW_API_URL", "https://ai-moderation-api-khyr.onrender.com")
NSFW_API_KEY = os.getenv("NSFW_API_KEY", "nsfwBad")

# Custom detection thresholds — sent with every /detect/upload call.
NSFW_THRESHOLDS = {
    "porn": float(os.getenv("NSFW_THRESHOLD_PORN", "0.7")),
    "sexy": float(os.getenv("NSFW_THRESHOLD_SEXY", "0.8")),
}

#── Start ───────────────────────────────────────────────────────────────────────
START_ANIMATIONS = [
    "https://files.catbox.moe/35tfwv.jpg",
    "https://files.catbox.moe/sm18vd.jpg",
    "https://files.catbox.moe/35tfwv.jpg",
    "https://files.catbox.moe/sm18vd.jpg",
    "https://files.catbox.moe/sm18vd.jpg",
    "https://files.catbox.moe/35tfwv.jpg",
    "https://files.catbox.moe/sm18vd.jpg",
]

# ── Limits ────────────────────────────────────────────────────────────────────
MAX_DURATION_SECONDS = 1800   # 30 minutes
QUEUE_LIMIT          = 20
COOLDOWN             = 10     # seconds between /play per chat
