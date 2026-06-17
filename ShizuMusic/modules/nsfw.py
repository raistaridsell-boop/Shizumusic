# --------------------------------------------------------------------------------
#  ShizuMusic © 2026
#  Developed by Bad Munda ❤️
#
#  Unauthorized copying, editing, re-uploading or removing credits
#  from this source code is strictly prohibited.
# --------------------------------------------------------------------------------

import asyncio
import json
import os

import aiohttp
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

import config
from ShizuMusic import bot, LOGGER
from ShizuMusic.modules.block import user_allowed
from ShizuMusic.utils.db import (
    is_nsfw_enabled,
    set_nsfw_enabled,
    approve_nsfw_user,
    disapprove_nsfw_user,
    is_nsfw_approved,
    get_nsfw_approved_users,
)
from ShizuMusic.utils.permissions import is_user_authorized

DOWNLOAD_DIR = "downloads/nsfw"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

REPORT_AUTO_DELETE = 20   # seconds — scan report message auto-deletes after this


# ── Filters ──────────────────────────────────────────────────────────────────

def _is_plain_text(_, __, message: Message) -> bool:
    """Text messages that are NOT commands."""
    return bool(message.text) and not message.text.startswith("/")


not_command = filters.create(_is_plain_text)

MEDIA_FILTER = (
    filters.photo
    | filters.video
    | filters.animation
    | filters.sticker
    | filters.document
)


# ── API Helpers ──────────────────────────────────────────────────────────────

async def _scan_file(path: str, content_type: str) -> dict | None:
    """Upload local media file to the moderation API for scanning."""
    try:
        async with aiohttp.ClientSession() as session:
            with open(path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field(
                    "file", f,
                    filename=os.path.basename(path),
                    content_type=content_type,
                )
                # Custom NSFW thresholds — config.NSFW_THRESHOLDS
                data.add_field("thresholds", json.dumps(config.NSFW_THRESHOLDS))
                headers = {"x-api-key": config.NSFW_API_KEY}
                async with session.post(
                    f"{config.NSFW_API_URL}/detect/upload",
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        LOGGER.warning(f"[nsfw] API status {resp.status}")
                        return None
                    return await resp.json()
    except Exception as e:
        LOGGER.error(f"[nsfw] scan_file failed: {e}")
        return None


async def _scan_text(text: str) -> dict | None:
    """Send plain text to the moderation API for bad-word checking."""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"text": text, "x_api_key": config.NSFW_API_KEY}
            async with session.post(
                f"{config.NSFW_API_URL}/text/check",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception as e:
        LOGGER.error(f"[nsfw] scan_text failed: {e}")
        return None


# ── Media Helpers ────────────────────────────────────────────────────────────

def _media_content_type(message: Message) -> str | None:
    """Return a content-type string for the message's media, or None if unsupported."""
    if message.photo:
        return "image/jpeg"
    if message.video:
        return "video/mp4"
    if message.animation:
        return "video/mp4"
    if message.sticker:
        mime = message.sticker.mime_type or ""
        if "tgsticker" in mime:
            return "application/x-tgsticker"
        if "webm" in mime:
            return "video/webm"
        return "image/webp"
    if message.document:
        mime = message.document.mime_type or ""
        if mime.startswith("image/") or mime.startswith("video/") or "tgsticker" in mime:
            return mime
        return None
    return None


async def _auto_delete(message: Message, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


async def _extract_user(client, message: Message, args: list):
    """
    Find the target user:
      1. The sender of the replied-to message
      2. /nsfwapprove <user_id|@username>

    Returns None if nothing matches.
    """
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user

    if args:
        target = args[0]
        try:
            if target.lstrip("-").isdigit():
                return await client.get_users(int(target))
            return await client.get_users(target)
        except Exception:
            return None

    return None


# ── Report Builder ───────────────────────────────────────────────────────────

def _build_report(result: dict) -> tuple[str, bool]:
    """Returns (report_text, should_delete)."""
    nsfw          = result.get("nsfw", {}) or {}
    triggered     = result.get("triggered")
    has_weapon    = result.get("has_weapon", False)
    has_drugs     = result.get("has_drugs", False)
    should_delete = result.get("should_delete", False)
    thresholds    = result.get("thresholds_used", {}) or {}

    threshold_line = ""
    if triggered:
        category   = triggered.capitalize()
        confidence = nsfw.get(triggered, 0) * 100
        thr        = thresholds.get(triggered)
        if thr is not None:
            threshold_line = f"<b>🎯 Threshold:</b> {thr * 100:.0f}%\n"
    elif has_weapon:
        category   = "Weapon"
        confs      = [d["confidence"] for d in result.get("detections", []) if d["type"] == "weapon"]
        confidence = (max(confs) * 100) if confs else 0
    elif has_drugs:
        category   = "Drugs"
        confs      = [d["confidence"] for d in result.get("detections", []) if d["type"] == "drug"]
        confidence = (max(confs) * 100) if confs else 0
    else:
        category   = "Clean"
        confidence = nsfw.get("neutral", 0) * 100

    status      = "NSFW Detected ⚠️" if should_delete else "Safe ✅"
    action      = "Delete 🗑️" if should_delete else "None"
    weapon_str  = "Detected ⚠️" if has_weapon else "Not Detected ✅"
    drugs_str   = "Detected ⚠️" if has_drugs else "Not Detected ✅"

    text = (
        "<b>📊 NSFW Scan Result</b>\n\n"
        f"<b>🔞 Status:</b> {status}\n"
        f"<b>🚨 Category:</b> {category}\n"
        f"<b>📈 Confidence:</b> {confidence:.1f}%\n"
        f"{threshold_line}\n"
        f"<b>⚠️ Recommended Action:</b> {action}\n\n"
        f"<b>🛡️ Weapon:</b> {weapon_str}\n"
        f"<b>💊 Drugs:</b> {drugs_str}"
    )
    return text, should_delete


# ── /nsfw on|off ─────────────────────────────────────────────────────────────

@bot.on_message(filters.command("nsfw") & filters.group & user_allowed)
async def nsfw_toggle_cmd(_, message: Message) -> None:
    args = message.command[1:]

    if not args:
        status = "ON ✅" if is_nsfw_enabled(message.chat.id) else "OFF ❌"
        await message.reply(
            f"<b>❍ NSFW Filter is currently:</b> {status}\n"
            f"<b>❍ Usage:</b> <code>/nsfw on</code> | <code>/nsfw off</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if not await is_user_authorized(message):
        await message.reply(
            "<b>❍ Only admins can change this setting.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    arg = args[0].lower()
    if arg == "on":
        set_nsfw_enabled(message.chat.id, True)
        await message.reply("<b>❍ NSFW Filter Enabled ✅</b>", parse_mode=ParseMode.HTML)
    elif arg == "off":
        set_nsfw_enabled(message.chat.id, False)
        await message.reply("<b>❍ NSFW Filter Disabled ❌</b>", parse_mode=ParseMode.HTML)
    else:
        await message.reply(
            "<b>❍ Usage:</b> <code>/nsfw on</code> | <code>/nsfw off</code>",
            parse_mode=ParseMode.HTML,
        )


# ── /nsfwapprove ──────────────────────────────────────────────────────────────
@bot.on_message(filters.command("nsfwapprove") & filters.group & user_allowed)
async def nsfw_approve_cmd(client, message: Message) -> None:
    if not await is_user_authorized(message):
        await message.reply(
            "<b>❍ Only admins can use this command.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    args = message.command[1:]

    # /nsfwapprove list
    if args and args[0].lower() == "list":
        users = get_nsfw_approved_users(message.chat.id)
        if not users:
            await message.reply(
                "<b>❍ No NSFW-approved users in this chat.</b>",
                parse_mode=ParseMode.HTML,
            )
            return
        lines = "\n".join(f"• <code>{uid}</code>" for uid in users)
        await message.reply(
            f"<b>❍ NSFW-Approved Users:</b>\n{lines}",
            parse_mode=ParseMode.HTML,
        )
        return

    # /nsfwapprove off
    remove = bool(args) and args[-1].lower() in ("off", "remove", "-")
    target_args = args[:-1] if remove else args

    target = await _extract_user(client, message, target_args)
    if target is None:
        await message.reply(
            "<b>❍ Reply to a user's message</b> (or provide their ID/username) "
            "<b>along with</b> <code>/nsfwapprove</code> <b>to whitelist them from the NSFW filter.</b>\n\n"
            "<b>❍ Usage:</b>\n"
            "• <code>/nsfwapprove</code> — reply to approve\n"
            "• <code>/nsfwapprove off</code> — reply to remove approval\n"
            "• <code>/nsfwapprove list</code> — view approved users",
            parse_mode=ParseMode.HTML,
        )
        return

    if remove:
        disapprove_nsfw_user(message.chat.id, target.id)
        await message.reply(
            f"<b>❍</b> {target.mention} <b>removed from the NSFW-approved list ❌</b>\n"
            f"<b>Their media/text will now be scanned again.</b>",
            parse_mode=ParseMode.HTML,
        )
    else:
        approve_nsfw_user(message.chat.id, target.id)
        await message.reply(
            f"<b>❍</b> {target.mention} <b>NSFW-Approved ✅</b>\n"
            f"<b>Their media/text will not be scanned by the NSFW filter.</b>",
            parse_mode=ParseMode.HTML,
        )


# ── Media Scanner — photo / video / gif / sticker / animation ───────────────

@bot.on_message(MEDIA_FILTER & filters.group & user_allowed)
async def nsfw_media_scan(client, message: Message) -> None:
    if not is_nsfw_enabled(message.chat.id):
        return

    if message.from_user and is_nsfw_approved(message.chat.id, message.from_user.id):
        return

    content_type = _media_content_type(message)
    if content_type is None:
        return

    path = None
    try:
        path = await message.download(file_name=f"{DOWNLOAD_DIR}/")
    except Exception as e:
        LOGGER.error(f"[nsfw] download failed: {e}")
        return

    try:
        result = await _scan_file(path, content_type)
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

    if not result:
        return  # API unreachable — fail silently, don't block the chat

    report_text, should_delete = _build_report(result)
    if not should_delete:
        return

    try:
        await message.delete()
    except Exception as e:
        LOGGER.warning(f"[nsfw] could not delete message: {e}")

    user   = message.from_user
    header = f"<b>👤 User:</b> {user.mention}\n\n" if user else ""
    sent = await client.send_message(
        message.chat.id,
        header + report_text,
        parse_mode=ParseMode.HTML,
    )
    asyncio.create_task(_auto_delete(sent, REPORT_AUTO_DELETE))


# ── Text Scanner — bad words ─────────────────────────────────────────────────

@bot.on_message(filters.text & filters.group & not_command & user_allowed)
async def nsfw_text_scan(client, message: Message) -> None:
    if not is_nsfw_enabled(message.chat.id):
        return

    if message.from_user and is_nsfw_approved(message.chat.id, message.from_user.id):
        return

    if len(message.text.strip()) < 2:
        return

    result = await _scan_text(message.text)
    if not result or not result.get("has_bad_words"):
        return

    try:
        await message.delete()
    except Exception as e:
        LOGGER.warning(f"[nsfw] could not delete text message: {e}")

    user      = message.from_user
    mention   = user.mention if user else "Someone"
    toxicity  = result.get("toxicity_score", 0) * 100

    warn_text = (
        "<b>🚫 Message Deleted</b>\n\n"
        f"<b>👤 User:</b> {mention}\n"
        f"<b>⚠️ Reason:</b> Bad word(s) detected\n"
        f"<b>📈 Toxicity:</b> {toxicity:.0f}%"
    )
    sent = await client.send_message(
        message.chat.id,
        warn_text,
        parse_mode=ParseMode.HTML,
    )
    asyncio.create_task(_auto_delete(sent, REPORT_AUTO_DELETE))
