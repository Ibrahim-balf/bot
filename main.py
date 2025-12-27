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
    return "Bot Factory is Running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- الإعدادات الأساسية ---
TOKEN = os.getenv("BOT_TOKEN", "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6556184974"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# --- المتغيرات العامة وحالات الـ FSM ---
MAINTENANCE_MODE = False

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

# --- وظائف قاعدة البيانات ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY);')
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT);')
    conn.commit()
    cur.close()
    conn.close()

# --- لوحة تحكم الأدمن ---
def get_admin_kb(u_count, b_count):
    status_text = "🟢 المصنع: يعمل" if not MAINTENANCE_MODE else "🔴 المصنع: صيانة"
    buttons = [
        [
            InlineKeyboardButton(text=f"👥 مستخدمين: {u_count}", callback_data="none"),
            InlineKeyboardButton(text=f"🤖 بوتات: {b_count}", callback_data="none")
        ],
        [InlineKeyboardButton(text="📢 إرسال إذاعة عامة", callback_data="start_broadcast")],
        [InlineKeyboardButton(text=status_text, callback_data="toggle_maintenance")],
        [InlineKeyboardButton(text="🔄 تحديث البيانات", callback_data="refresh_admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- معالجة الأوامر ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if MAINTENANCE_MODE and message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ البوت قيد الصيانة حالياً لتطوير ميزات جديدة. عد لاحقاً!")
        return

    uid = message.from_user.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING;', (uid,))
    conn.commit()
    cur.close()
    conn.close()
    
    await message.answer(f"أهلاً بك {message.from_user.first_name} في مصنع بوتات التواصل! 🤖\n\nاستخدم /admin إذا كنت المطور.")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM users;')
        u_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM sub_bots;')
        b_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        await message.answer("🛠 **لوحة تحكم المطور المتقدمة**", 
                           reply_markup=get_admin_kb(u_count, b_count), 
                           parse_mode="Markdown")
    else:
        await message.answer("❌ هذا الأمر مخصص للمطور فقط.")

# --- معالجة الأزرار التفاعلية ---

@dp.callback_query(F.data == "refresh_admin")
async def refresh_admin(callback: types.CallbackQuery):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users;')
    u_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM sub_bots;')
    b_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    await callback.message.edit_text("🛠 **لوحة تحكم المطور المتقدمة**", 
                                   reply_markup=get_admin_kb(u_count, b_count), 
                                   parse_mode="Markdown")
    await callback.answer("تم التحديث ✅")

@dp.callback_query(F.data == "toggle_maintenance")
async def toggle_maint(callback: types.CallbackQuery):
    global MAINTENANCE_MODE
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    await refresh_admin(callback)
    status = "تعطيل" if MAINTENANCE_MODE else "تفعيل"
    await callback.answer(f"تم {status} وضع الصيانة", show_alert=True)

@dp.callback_query(F.data == "start_broadcast")
async def br_step1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📥 أرسل الرسالة الآن (نص، صورة، فيديو..)")
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast)
async def br_step2(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users;')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    count = 0
    status_msg = await message.answer("⏳ جاري الإرسال...")
    
    for row in rows:
        try:
            await message.copy_to(chat_id=row[0])
            count += 1
            await asyncio.sleep(0.05)
        except:
            pass
            
    await status_msg.edit_text(f"✅ تمت الإذاعة بنجاح لـ {count} مستخدم.")
    await state.clear()

# --- التشغيل ---
async def main():
    init_db()
    keep_alive()
    print("🚀 البوت يعمل الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
