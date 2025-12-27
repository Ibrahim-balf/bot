import os, logging, asyncio, psycopg2, requests, datetime
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- 1. إعدادات السيرفر لمنع النوم ---
app = Flask('')
@app.route('/')
def home(): return "Factory is Alive!"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# --- 2. الإعدادات وقاعدة البيانات ---
TOKEN = os.getenv("BOT_TOKEN", "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6556184974"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)
ERROR_LOGS = []

class VIPStates(StatesGroup):
    waiting_for_vip_id = State()
    waiting_for_vip_days = State()
    waiting_for_remove_id = State()
    waiting_for_search_id = State()
    waiting_for_token = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- 3. دالة تشغيل البوتات الفرعية (يجب أن تكون قبل دالة main) ---
async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher(storage=MemoryStorage())
        main_info = await bot.get_me()

        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('SELECT is_vip FROM users WHERE user_id = %s', (owner_id,))
            res = cur.fetchone(); is_vip = res[0] if res else False
            cur.close(); conn.close()
            
            if m.from_user.id == owner_id:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ إدارة المصنع", url=f"https://t.me/{main_info.username}")]
                ])
                await m.answer("👋 أهلاً بك يا مالك البوت.", reply_markup=kb)
            else:
                footer = "" if is_vip else f"\n\n—\n🤖 صنع بواسطة: @{main_info.username}"
                await m.answer("أهلاً بك في بوت التواصل!" + footer)

        @s_dp.message()
        async def s_forward(m: Message):
            if m.from_user.id != owner_id:
                await m.forward(owner_id)
            elif m.reply_to_message and m.reply_to_message.forward_from:
                try: await m.copy_to(m.reply_to_message.forward_from.id)
                except: pass

        await s_dp.start_polling(s_bot)
    except Exception as e:
        ERROR_LOGS.append(f"⚠️ خطأ في بوت {owner_id}: {str(e)}")

# --- 4. الدالة الرئيسية للتشغيل ---
async def main():
    # إنشاء الجداول
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, is_vip BOOLEAN DEFAULT FALSE, vip_expire DATE DEFAULT NULL);')
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT);')
    conn.commit()
    
    # تشغيل Flask في الخلفية
    keep_alive()
    
    # تشغيل البوتات الموجودة في قاعدة البيانات
    cur.execute('SELECT token, owner_id FROM sub_bots')
    all_bots = cur.fetchall()
    cur.close(); conn.close()
    
    for b_token, b_owner in all_bots:
        asyncio.create_task(start_sub_bot(b_token, b_owner))
        await asyncio.sleep(1) # تأخير لتجنب الضغط على السيرفر
    
    # تشغيل البوت الأساسي مع حماية من التوقف
    logging.info("Main Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
