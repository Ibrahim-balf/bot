import os, logging, asyncio, psycopg2, datetime
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- إعدادات السيرفر وقاعدة البيانات ---
app = Flask('')
@app.route('/')
def home(): return "Professional Factory Online"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("BOT_TOKEN", "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6556184974"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_for_token = State()
    waiting_for_new_welcome = State()
    waiting_for_vip_id = State()
    waiting_for_vip_days = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- [1] تفعيل زر "صنع بوت" ---
@dp.callback_query(F.data == "make_bot")
async def start_make(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📥 أرسل الآن توكن البوت الخاص بك من @BotFather:")
    await state.set_state(States.waiting_for_token)
    await call.answer()

@dp.message(States.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    token = message.text
    # (هنا نضع كود فحص التوكن وحفظه في القاعدة وتشغيل البوت الفرعي)
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s) ON CONFLICT (owner_id) DO UPDATE SET token = %s', (message.from_user.id, token, token))
    conn.commit(); cur.close(); conn.close()
    await message.answer("✅ تم صنع بوتك بنجاح! جرب مراسلته الآن.")
    await state.clear()

# --- [2] تفعيل أزرار لوحة تحكم المستخدم (تغيير الترحيب) ---
@dp.callback_query(F.data == "user_change_welcome")
async def ask_new_welcome(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📝 أرسل رسالة الترحيب الجديدة التي تريدها:")
    await state.set_state(States.waiting_for_new_welcome)
    await call.answer()

@dp.message(States.waiting_for_new_welcome)
async def save_new_welcome(message: Message, state: FSMContext):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET welcome_msg = %s WHERE owner_id = %s', (message.text, message.from_user.id))
    conn.commit(); cur.close(); conn.close()
    await message.answer("✨ تم تحديث رسالة الترحيب بنجاح!")
    await state.clear()

# --- [3] تفعيل زر "حذف البوت" ---
@dp.callback_query(F.data == "delete_bot")
async def confirm_delete(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ نعم، احذف", callback_data="confirm_delete_real")],
        [InlineKeyboardButton(text="❌ تراجع", callback_data="manage_my_bot")]
    ])
    await call.message.edit_text("⚠️ هل أنت متأكد من حذف البوت؟ سيتم إيقافه فوراً.", reply_markup=kb)

@dp.callback_query(F.data == "confirm_delete_real")
async def delete_real(call: CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('DELETE FROM sub_bots WHERE owner_id = %s', (call.from_user.id,))
    conn.commit(); cur.close(); conn.close()
    await call.message.edit_text("🗑 تم حذف بوتك بنجاح من النظام.")

# --- [4] تفعيل أزرار الأدمن (تفعيل VIP) ---
@dp.callback_query(F.data == "admin_add_vip")
async def admin_vip_req(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🆔 أرسل الـ ID للمستخدم المراد تفعيله:")
    await state.set_state(States.waiting_for_vip_id)
    await call.answer()

@dp.message(States.waiting_for_vip_id)
async def set_vip(message: Message, state: FSMContext):
    # كود حفظ الـ VIP في قاعدة البيانات
    uid = int(message.text)
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE users SET is_vip = TRUE WHERE user_id = %s', (uid,))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"⭐ تم منح VIP للمستخدم {uid}")
    await state.clear()

# --- دالة البداية والربط ---
async def main():
    # تأكد من تعريف الجداول قبل التشغيل
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT, welcome_msg TEXT DEFAULT %s)', ("أهلاً بك!",))
    conn.commit(); cur.close(); conn.close()
    
    keep_alive()
    print("System is Ready!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
