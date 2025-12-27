import os
import logging
import asyncio
import psycopg2
import requests
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- إعدادات السيرفر الوهمي ---
app = Flask('')
@app.route('/')
def home(): return "Bot Factory is Running!"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web).start()

# --- الإعدادات ---
TOKEN = os.getenv("BOT_TOKEN", "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6556184974"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

class States(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_token = State()

MAINTENANCE_MODE = False

# --- قاعدة البيانات ---
def get_db_connection(): return psycopg2.connect(DATABASE_URL)
def init_db():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY);')
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT);')
    conn.commit(); cur.close(); conn.close()

# --- منطق بوتات التواصل المصنوعة ---
async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher()
        
        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            await m.answer("مرحباً بك في بوت التواصل! أرسل رسالتك وسيتم تحويلها للمالك.")

        @s_dp.message()
        async def s_forward(m: Message):
            if m.from_user.id != owner_id:
                await s_bot.send_message(owner_id, f"👤 رسالة من: {m.from_user.full_name}\n🆔 ID: {m.from_user.id}")
                await m.copy_to(owner_id)
            else:
                if m.reply_to_message and m.reply_to_message.forward_from:
                    await m.copy_to(m.reply_to_message.forward_from.id)
                    await m.answer("✅ تم الرد على المستخدم.")

        logging.info(f"Starting sub-bot for {owner_id}")
        await s_dp.start_polling(s_bot)
    except: logging.error(f"Failed to start bot for {owner_id}")

# --- أوامر البوت الأساسي ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if MAINTENANCE_MODE and message.from_user.id != ADMIN_ID:
        return await message.answer("⚠️ وضع الصيانة مفعل.")
    
    # حفظ المستخدم
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING;', (message.from_user.id,))
    conn.commit(); cur.close(); conn.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 صنع بوت تواصل", callback_data="make_bot")]
    ])
    await message.answer(f"أهلاً بك {message.from_user.first_name} في مصنع البوتات! 🤖\nيمكنك الآن صنع بوت تواصل خاص بك مجاناً.", reply_markup=kb)

@dp.callback_query(F.data == "make_bot")
async def ask_token(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📥 حسناً، أرسل الآن 'التوكن' الخاص ببوتك من @BotFather")
    await state.set_state(States.waiting_for_token)
    await callback.answer()

@dp.message(States.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    token = message.text.strip()
    # التحقق من صحة التوكن عبر تليجرام
    res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
    if not res.get("ok"):
        return await message.answer("❌ التوكن غير صحيح! تأكد من إرساله بشكل سليم.")

    # حفظ في القاعدة
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s) ON CONFLICT (owner_id) DO UPDATE SET token = %s;', 
                (message.from_user.id, token, token))
    conn.commit(); cur.close(); conn.close()
    
    await message.answer(f"✅ تم تشغيل بوتك بنجاح باسم: @{res['result']['username']}\n\nأرسل أي رسالة لبوتك لتجربته!")
    asyncio.create_task(start_sub_bot(token, message.from_user.id))
    await state.clear()

# --- لوحة الأدمن (كما هي مع التحديث) ---
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM users;'); u_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM sub_bots;'); b_count = cur.fetchone()[0]
        cur.close(); conn.close()
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"👥 مستخدمين: {u_count}", callback_data="none"),
             InlineKeyboardButton(text=f"🤖 بوتات: {b_count}", callback_data="none")],
            [InlineKeyboardButton(text="📢 إرسال إذاعة عامة", callback_data="start_broadcast")],
            [InlineKeyboardButton(text="🔄 تحديث البيانات", callback_data="refresh_admin")]
        ])
        await message.answer("🛠 لوحة تحكم المصنع المتقدمة", reply_markup=kb)

# --- تشغيل البوتات القديمة عند بدء التشغيل ---
async def reload_bots():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token, owner_id FROM sub_bots;')
    bots_data = cur.fetchall()
    cur.close(); conn.close()
    for token, owner_id in bots_data:
        asyncio.create_task(start_sub_bot(token, owner_id))

async def main():
    init_db()
    keep_alive()
    await reload_bots() # إعادة تشغيل كل البوتات المصنوعة سابقاً
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
