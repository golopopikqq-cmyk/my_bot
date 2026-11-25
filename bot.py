import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

# ==========================================
# ВСТАВЬ СВОИ ДАННЫЕ ТУТ:
# ==========================================
BOT_TOKEN = "9280008802:AAGS6UVNDe4cRktFtv9JUisJdR1bhlhfPFI" 
CHAT_ID = --1004395845186# ID чата "Курилка" (начинается с -100)
# ==========================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS chat_stats (user_id INTEGER PRIMARY KEY, username TEXT, msgs INTEGER)')
    conn.commit()
    conn.close()

def add_message_stat(user_id, username):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO chat_stats (user_id, username, msgs) VALUES (?, ?, 0)', (user_id, username))
    cursor.execute('UPDATE chat_stats SET msgs = msgs + 1, username = ? WHERE user_id = ?', (username, user_id))
    conn.commit()
    conn.close()

def get_chat_stats():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # ТУТ УБРАН ЛИМИТ, ЧТОБЫ ТОП БЫЛ БЕСКОНЕЧНЫМ
    cursor.execute('SELECT username, msgs FROM chat_stats ORDER BY msgs DESC')
    result = cursor.fetchall()
    conn.close()
    return [{"name": row[0], "msgs": row[1]} for row in result]

# --- СЧЕТЧИК СООБЩЕНИЙ ---
@dp.message(F.chat.id == CHAT_ID)
async def count_messages(message: types.Message):
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    add_message_stat(message.from_user.id, username)

# --- API ДЛЯ САЙТА ---
async def handle_stats(request):
    return web.json_response(get_chat_stats(), headers={"Access-Control-Allow-Origin": "*"})

async def start_web_server():
    app = web.Application()
    app.router.add_get('/stats', handle_stats)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print(f"Веб-сервер запущен на порту {port}")

async def main():
    init_db()
    print("Бот-счетчик запущен!")
    await asyncio.gather(dp.start_polling(bot), start_web_server())

if __name__ == "__main__":
    asyncio.run(main())
