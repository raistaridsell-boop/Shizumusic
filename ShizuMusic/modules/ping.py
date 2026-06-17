# --------------------------------------------------------------------------------
#  ShizuMusic © 2026
#  Developed by Bad Munda ❤️
#
#  Unauthorized copying, editing, re-uploading or removing credits
#  from this source code is strictly prohibited.
# --------------------------------------------------------------------------------

import asyncio
import os
import time
from datetime import timedelta

import psutil
import speedtest
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from ShizuMusic import bot, assistant, bot_start_time
from ShizuMusic.modules.block import user_allowed


def supp_markup():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(text="🍬 sᴜᴘᴘᴏʀᴛ 🍬", url=config.SUPPORT_GROUP),
    ]])


# ── /ping ──────────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("ping") & user_allowed)
async def ping_cmd(client, message: Message) -> None:

    start   = time.perf_counter()
    pm      = await message.reply_text(
        f"<b>❍ {client.me.first_name} ɪs ᴘɪɴɢɪɴɢ...</b>",
        parse_mode=ParseMode.HTML,
    )
    latency = round((time.perf_counter() - start) * 1000)
    uptime  = str(timedelta(seconds=int(time.time() - bot_start_time)))
    cpu     = psutil.cpu_percent(interval=1)

    process = psutil.Process(os.getpid())
    ram     = process.memory_info().rss / 1024 / 1024

    disk    = psutil.disk_usage("/")
    disk_str = (
        f"{disk.used // (1024**3)}GB / "
        f"{disk.total // (1024**3)}GB "
        f"({disk.percent}%)"
    )

    try:
        pytg_start = time.perf_counter()
        await assistant.get_me()
        pytg = round((time.perf_counter() - pytg_start) * 1000)
    except Exception:
        pytg = "N/A"

    await pm.delete()

    caption = (
        f"<b>🏓 ᴘᴏɴɢ : <code>{latency}ms</code></b>\n\n"
        f"<b><u>{client.me.first_name} sʏsᴛᴇᴍ sᴛᴀᴛs :</u></b>\n\n"
        f"<b>❍ ᴜᴘᴛɪᴍᴇ :</b> <code>{uptime}</code>\n"
        f"<b>❍ ʀᴀᴍ :</b> <code>{ram:.2f} MB</code>\n"
        f"<b>❍ ᴄᴘᴜ :</b> <code>{cpu}%</code>\n"
        f"<b>❍ ᴅɪsᴋ :</b> <code>{disk_str}</code>\n"
        f"<b>❍ ᴘʏᴛɢᴄ :</b> <code>{pytg}ms</code>\n\n"
        f"<b>❍ 𝖡ʏ » <a href=\"{config.SUPPORT_GROUP}\">sʜɪᴢᴜ-ᴍᴜsɪᴄ™</a></b>"
    )

    await message.reply_photo(
        photo=config.PING_IMG_URL,
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=supp_markup(),
    )


# ── /speedtest ─────────────────────────────────────────────────────────────────

def _run_speedtest(m):
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        st.download()
        st.upload()
        st.results.share()
        return st.results.dict()
    except Exception as e:
        return None


@bot.on_message(
    filters.command(["speedtest", "spt"])
    & filters.user(config.OWNER_ID)
)
async def speedtest_cmd(client, message: Message) -> None:

    m = await message.reply_text(
        "<b>❍ sᴛᴀʀᴛɪɴɢ sᴘᴇᴇᴅ ᴛᴇsᴛ, ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>",
        parse_mode=ParseMode.HTML,
    )

    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_speedtest, m)

    if result is None:
        await m.edit_text("<b>❍ Speedtest failed. Please try again.</b>", parse_mode=ParseMode.HTML)
        return

    download = result["download"] / 1_000_000
    upload   = result["upload"]   / 1_000_000
    ping     = result["ping"]
    isp      = result["client"]["isp"]
    country  = result["client"]["country"]
    server   = result["server"]["name"]
    sponsor  = result["server"]["sponsor"]
    s_cc     = result["server"]["cc"]
    s_lat    = result["server"]["latency"]
    share    = result["share"]

    caption = (
        "<b>⚡ sᴘᴇᴇᴅᴛᴇsᴛ ʀᴇsᴜʟᴛs</b>\n\n"
        "<b><u>ᴄʟɪᴇɴᴛ ɪɴғᴏ :</u></b>\n"
        f"<b>❍ ɪsᴘ     :</b> <code>{isp}</code>\n"
        f"<b>❍ ᴄᴏᴜɴᴛʀʏ :</b> <code>{country}</code>\n\n"
        "<b><u>sᴇʀᴠᴇʀ ɪɴғᴏ :</u></b>\n"
        f"<b>❍ ɴᴀᴍᴇ    :</b> <code>{server}</code>\n"
        f"<b>❍ sᴘᴏɴsᴏʀ :</b> <code>{sponsor}</code>\n"
        f"<b>❍ ᴄᴏᴜɴᴛʀʏ :</b> <code>{s_cc}</code>\n"
        f"<b>❍ ʟᴀᴛᴇɴᴄʏ :</b> <code>{s_lat} ms</code>\n\n"
        "<b><u>sᴘᴇᴇᴅ :</u></b>\n"
        f"<b>❍ ᴘɪɴɢ     :</b> <code>{ping:.2f} ms</code>\n"
        f"<b>❍ ᴅᴏᴡɴʟᴏᴀᴅ :</b> <code>{download:.2f} Mbps</code>\n"
        f"<b>❍ ᴜᴘʟᴏᴀᴅ   :</b> <code>{upload:.2f} Mbps</code>\n\n"
        f"<b>❍ 𝖡ʏ » <a href=\"{config.SUPPORT_GROUP}\">sʜɪᴢᴜ-ᴍᴜsɪᴄ™</a></b>"
    )

    await m.delete()
    await message.reply_photo(
        photo=share,
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=supp_markup(),
    )
