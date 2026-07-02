# -*- coding: utf-8 -*-
import os
import logging
import urllib.parse
import sqlite3
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ======================== 配置区 ========================
TOKEN = "8849318486:AAGcNFV4F3PZ8t-lW8sUEQcM4RVbf1MyXfw"  # 龙岗机器人的 Token
ADMIN_ID = 7140260550  # 统一管理员 ID

name_map = {
    "songbai": "94松白会所部长",
    "honghua": "94红花会所部长",
    "minsheng": "94民生会所部长",
    "huafa": "94华发会所部长",
    "tianyuan": "94田园会所部长",
    "tianliao": "94田寮会所部长",
    "jinyuwan": "94金御湾会所部长",
    "kangle": "95-96康乐会所部长",
    "gongming": "光明链接",
    "jinyu": "金鱼",
}

# =======================================================================

DB_DIR = "/app/data"
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "data.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            source TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_click(user_id, source):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO clicks (user_id, source, created_at) VALUES (?, ?, ?)",
        (str(user_id), source, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_total_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT source, COUNT(*) FROM clicks GROUP BY source ORDER BY COUNT(*) DESC")
    results = c.fetchall()
    total = c.execute("SELECT COUNT(*) FROM clicks").fetchone()[0] if results else 0
    c.execute("SELECT MIN(created_at), MAX(created_at) FROM clicks")
    min_date, max_date = c.fetchone()
    conn.close()
    return results, total, min_date, max_date


def get_today_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute("SELECT source, COUNT(*) FROM clicks WHERE date(created_at) = ? GROUP BY source ORDER BY COUNT(*) DESC", (today,))
    results = c.fetchall()
    total = c.execute("SELECT COUNT(*) FROM clicks WHERE date(created_at) = ?", (today,)).fetchone()[0]
    conn.close()
    return results, total


init_db()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "无用户名"
    raw_param = context.args[0] if context.args else None
    if raw_param:
        try:
            param = urllib.parse.unquote(raw_param)
        except:
            param = raw_param
    else:
        param = None

    if param and param in name_map:
        source = name_map[param]
        save_click(user_id, source)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 新用户来源：\n用户ID: {user_id}\n用户名: @{username}\n来源: {source}"
        )
    elif param:
        save_click(user_id, param)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 新用户来源：\n用户ID: {user_id}\n用户名: @{username}\n来源: {param}"
        )
    # 不再回复任何消息给用户


async def getlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法：/getlink 中文名称\n例如：/getlink 微信")
        return
    chinese = " ".join(context.args)
    encoded = urllib.parse.quote(chinese)
    link = f"https://t.me/{context.bot.username}?start={encoded}"
    await update.message.reply_text(f"新链接：\n{link}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("只有管理员可以使用此命令。")
        return

    today_results, today_total = get_today_stats()
    total_results, total_count, min_date, max_date = get_total_stats()

    if total_count == 0:
        await update.message.reply_text("暂无点击数据。")
        return

    today_str = date.today().strftime("%m月%d日")
    if min_date and max_date:
        try:
            min_d = datetime.fromisoformat(min_date).strftime("%m月%d日")
            max_d = datetime.fromisoformat(max_date).strftime("%m月%d日")
            range_str = f"{min_d} - {max_d}"
        except:
            range_str = "暂无"
    else:
        range_str = "暂无"

    msg = "📊 来源点击统计\n\n"
    msg += f"📅 今日新增（{today_str}）\n"
    if today_total == 0:
        msg += "  暂无新增\n"
    else:
        for source, count in today_results:
            msg += f"• {source}: {count} 次\n"
    msg += f"  小计: {today_total} 次\n\n"

    msg += f"📆 总点击（{range_str}）\n"
    for source, count in total_results:
        msg += f"• {source}: {count} 次\n"
    msg += f"  总计: {total_count} 次"

    await update.message.reply_text(msg)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getlink", getlink))
    app.add_handler(CommandHandler("stats", stats_command))
    logger.info("机器人已启动")
    app.run_polling()


if __name__ == "__main__":
    main()
