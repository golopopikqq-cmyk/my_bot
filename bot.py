import asyncio
import logging
import sqlite3
import random
import string
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9280008802:AAGS6UVNDe4cRktFtv9JUisJdR1bhlhfPFI" 
ADMIN_ID = 7594357975 
ADMIN_USERNAME = "@dolya_codeina" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ГЕНЕРАТОР КЛЮЧЕЙ ---
def generate_key():
    # Генерирует ключ типа DOLYA-A1B2-C3D4
    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"DOLYA-{part1}-{part2}"

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Теперь таблица хранит: ID юзера, дату окончания и КЛЮЧ
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (user_id INTEGER PRIMARY KEY, sub_end TEXT, license_key TEXT)''')
    conn.commit()
    conn.close()

def set_subscription(user_id, days):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if days == 0:
        end_date = "9999-12-31 23:59:59"
    else:
        end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    
    new_key = generate_key()
    
    cursor.execute('INSERT OR REPLACE INTO users (user_id, sub_end, license_key) VALUES (?, ?, ?)', 
                   (user_id, end_date, new_key))
    conn.commit()
    conn.close()
    
    with open("keys.txt", "a", encoding="utf-8") as f:
        f.write(f"\n{new_key}")
    
    return new_key


def get_subscription(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT sub_end, license_key FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        end_date_str, key = result
        if end_date_str == "9999-12-31 23:59:59":
            return f"Активна НАВСЕГДА!\nВаш ключ: {key}"
        
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
        if end_date > datetime.now():
            days_left = (end_date - datetime.now()).days
            return f"Активна до {end_date.strftime('%d.%m.%Y')} (Осталось дней: {days_left})\nВаш ключ: {key}"
    return "У вас нет активной подписки."

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Купить подписку", callback_data="buy_menu")
    builder.button(text="Мои подписки (Ключ)", callback_data="my_subs")
    return builder.as_markup()

def get_tariffs_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="7 дней - 150 звезд", callback_data="buy_7")
    builder.button(text="14 дней - 250 звезд (скидка 50)", callback_data="buy_14")
    builder.button(text="30 дней - 400 звезд (скидка 100)", callback_data="buy_30")
    builder.button(text="Навсегда - 700 звезд", callback_data="buy_0")
    builder.button(text="Назад", callback_data="back_to_main")
    builder.adjust(1) 
    return builder.as_markup()

def get_admin_menu(user_id, days):
    builder = InlineKeyboardBuilder()
    builder.button(text="ОДОБРИТЬ", callback_data=f"approve_{user_id}_{days}")
    builder.button(text="ОТКЛОНИТЬ", callback_data=f"reject_{user_id}")
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n"
        "Выбери действие:",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "buy_menu")
async def process_buy_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Выбери тарифный план:", reply_markup=get_tariffs_menu())@dp.callback_query(F.data == "back_to_main")
async def process_back(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(f"Привет, {callback.from_user.first_name}!\nВыбери действие:", reply_markup=get_main_menu())

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy_tariff(callback: types.CallbackQuery):
    await callback.answer()
    days = int(callback.data.split("_")[1])
    
    prices = {7: 150, 14: 250, 30: 400, 0: 700}
    names = {7: "7 дней", 14: "14 дней", 30: "30 дней", 0: "Навсегда"}
    
    price = prices[days]
    name = names[days]
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"НОВАЯ ЗАЯВКА!\n\n"
                 f"Пользователь: @{callback.from_user.username} (ID: {callback.from_user.id})\n"
                 f"Тариф: {name}\n"
                 f"Цена: {price} звезд\n\n"
                 f"Проверь перевод и подтверди:",
            reply_markup=get_admin_menu(callback.from_user.id, days)
        )
        
        await callback.message.edit_text(
            f"Вы выбрали тариф: {name}\n"
            f"Сумма к оплате: {price} звезд\n\n"
            f"Отправьте {price} звезд на аккаунт {ADMIN_USERNAME}.\n\n"
            f"После отправки нажмите кнопку ниже и ожидайте подтверждения.",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        await callback.message.answer("Ошибка: Администратор не найден.")
        print(f"ОШИБКА: {e}")

@dp.callback_query(F.data == "my_subs")
async def process_my_subs(callback: types.CallbackQuery):
    await callback.answer()
    status = get_subscription(callback.from_user.id)
    await callback.message.answer(f"Ваш статус:\n{status}")

@dp.callback_query(F.data.startswith("approve_"))
async def process_approve(callback: types.CallbackQuery):
    await callback.answer()
    _, user_id, days = callback.data.split("_")
    user_id = int(user_id)
    days = int(days)
    
    # Выдаем подписку и получаем сгенерированный ключ
    key = set_subscription(user_id, days)
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"Оплата подтверждена! Ваша подписка активирована.\n\n"
                 f"Ваш ключ для входа в софт:\n{key}\n\n"
                 f"Скопируйте его и введите при запуске программы.",
            parse_mode="Markdown"
        )
        await callback.message.edit_text(f"Подписка для ID {user_id} выдана.\nКлюч: {key}")
    except Exception:
        await callback.message.edit_text(f"Выдано для ID {user_id}. Ключ: {key} (юзер заблокировал бота).")

@dp.callback_query(F.data.startswith("reject_"))
async def process_reject(callback: types.CallbackQuery):
    await callback.answer()
    _, user_id = callback.data.split("_")
    try:
        await bot.send_message(chat_id=int(user_id), text="Оплата не найдена. Отказано.")
        await callback.message.edit_text(f"Отказано ID {user_id}.")
    except Exception:
        await callback.message.edit_text(f"Отказано (юзер заблокировал).")

# --- ЗАПУСК ---
async def main():
    init_db()
    print("Бот запущен! Система ключей активна.")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
