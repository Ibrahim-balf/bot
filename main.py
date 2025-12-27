import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- 1. تشغيل السيرفر لضمان الاستقرار ---
app = Flask('')
@app.route('/')
def home(): return "Ready"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- 2. الإعدادات ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    get_token = State()
    get_vip = State()

def get_conn(): return psycopg2.connect(DATABASE_URL)

# --- 3. إصلاح تلقائي لقاعدة البيانات (أهم خطوة) ---
def fix_db():
    conn = get_conn(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT, is_vip BOOLEAN DEFAULT FALSE)')
    try: cur.execute('ALTER TABLE sub_bots ADD COLUMN is_vip BOOLEAN DEFAULT FALSE')
    except: conn.rollback()
    conn.commit(); cur.close(); conn.close()

# --- 4. لوحات التحكم ---
def main_kb(uid):
    kb = [[InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="make")]]
    if uid == ADMIN_ID:
        kb.append([InlineKeyboardButton(text="🛠 لوحة المطور", callback_data="adm")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- 5. الأوامر والمعالجات ---

@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("🤖 **أهلاً بك في المصنع الذكي**", reply_markup=main_kb(m.from_user.id))

# لوحة الأدمن
@dp.callback_query(F.data == "adm")
async def adm_p(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="stats"), InlineKeyboardButton(text="🌟 تفعيل VIP", callback_data="vip")],
        [InlineKeyboardButton(text="🔄 ريستارت", callback_data="reset")]
    ])
    await call.message.edit_text("🛠 لوحة المطور:", reply_markup=kb)

# تفعيل VIP
@dp.callback_query(F.data == "vip")
async def vip_p(call: CallbackQuery, state: FSMContext):
    await call.message.answer("أرسل ID المستخدم لتفعيله VIP:")
    await state.set_state(States.get_vip)

@dp.message(States.get_vip)
async def vip_done(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    conn = get_conn(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET is_vip = TRUE WHERE owner_id = %s', (m.text.strip(),))
    conn.commit(); cur.close(); conn.close()
    await m.answer(f"✅ تم تفعيل VIP للـ ID: {m.text}")
    await state.clear()

# صنع بوت
@dp.callback_query(F.data == "make")
async def make_p(call: CallbackQuery, state: FSMContext):
    await call.message.answer("أرسل توكن بوتك الآن:")
    await state.set_state(States.get_token)

@dp.message(States.get_token)
async def token_done(m: Message, state: FSMContext):
    token = m.text.strip()
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s)', (m.from_user.id, token))
        conn.commit(); cur.close(); conn.close()
        await m.answer("✅ تم صنع بوتك بنجاح!")
    except: await m.answer("⚠️ البوت مسجل مسبقاً.")
    await state.clear()

@dp.callback_query(F.data == "reset")
async def reset_p(call: CallbackQuery):
    await call.answer("🔄 ريستارت...")
    os.execl(sys.executable, sys.executable, *sys.argv)

# --- 6. التشغيل ---
async def main():
    fix_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
