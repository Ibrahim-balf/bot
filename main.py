import os
import logging
import asyncio
import psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- إعدادات السيرفر الوهمي لـ Render ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- الإعدادات الأساسية ---
# اسحب القيم من إعدادات ريندر أو ضعها هنا مباشرة
TOKEN = os.getenv("BOT_TOKEN", "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6556184974"))الخاص بك

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# --- نظام حالات الأدمن (FSM) ---
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

# --- وظائف قاعدة البيانات ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # جدول المستخدمين
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY);')
    # جدول البوتات المصنوعة (للتطوير القادم)
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT);')
    conn.commit()
    cur.close()
    conn.close()

# --- لوحة تحكم الأدمن ---
def admin_keyboard(user_count):
    buttons = [
        [InlineKeyboardButton(text=f"📊 مستخدمين القاعدة: {user_count}", callback_data="stats")],
        [InlineKeyboardButton(text="📢 إرسال إذاعة عامة", callback_data="start_broadcast")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- معالجة الأوامر ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING;', (uid,))
    conn.commit()
    cur.close()
    conn.close()
    await message.answer(f"مرحباً {message.from_user.first_name} في مصنع بوتات التواصل! 🤖\nقريباً ستتمكن من إنشاء بوتك الخاص هنا.")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM users;')
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        await message.answer("🛠 لوحة تحكم المطور:", reply_markup=admin_keyboard(count))
    else:
        await message.answer("❌ عذراً، هذا الأمر للمطور فقط.")

# --- معالجة الأزرار والإذاعة ---

@dp.callback_query(F.data == "start_broadcast")
async def broadcast_step1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📥 أرسل الآن الرسالة التي تريد إذاعتها (نص، صورة، أو فيديو):")
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast)
async def broadcast_step2(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users;')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    success = 0
    failed = 0
    msg = await message.answer("⏳ جاري الإرسال...")

    for row in rows:
        try:
            await message.copy_to(chat_id=row[0])
            success += 1
            await asyncio.sleep(0.05) # تجنب حظر التليجرام
        except:
            failed += 1
    
    await msg.edit_text(f"✅ اكتملت الإذاعة:\n\nتم الإرسال لـ: {success}\nفشل الإرسال لـ: {failed} (قاموا بحظر البوت)")
    await state.clear()

# --- تشغيل التطبيق ---
async def main():
    init_db()     # تهيئة القاعدة
    keep_alive()  # تشغيل السيرفر الوهمي
    print("🚀 البوت بدأ العمل بنجاح...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("تم إيقاف البوت.")
