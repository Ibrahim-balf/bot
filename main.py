import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- [1] Flask Setup ---
app = Flask('')
@app.route('/')
def home(): return "Factory System: Online & Fixed"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] Settings ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MyStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_vip_id = State()
    waiting_for_welcome = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- [3] تلقائي: إصلاح وتحديث قاعدة البيانات ---
def init_db():
    conn = get_db_connection(); cur = conn.cursor()
    # إنشاء الجدول إذا لم يوجد
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT)')
    # إضافة الأعمدة الناقصة لتجنب الخطأ
    try: cur.execute('ALTER TABLE sub_bots ADD COLUMN is_vip BOOLEAN DEFAULT FALSE')
    except: conn.rollback()
    try: cur.execute('ALTER TABLE sub_bots ADD COLUMN welcome_msg TEXT DEFAULT NULL')
    except: conn.rollback()
    conn.commit(); cur.close(); conn.close()

# --- [4] تشغيل البوتات الفرعية ---
async def run_sub_bot(token, owner_id, is_vip, welcome_msg):
    try:
        s_bot = Bot(token=token); s_dp = Dispatcher()
        await s_bot.delete_webhook(drop_pending_updates=True)
        
        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            text = welcome_msg if welcome_msg else "👋 أهلاً بك في بوت التواصل."
            if not is_vip: text += "\n\n— صنع بواسطة المصنع —"
            await m.answer(text)

        @s_dp.message()
        async def s_msg(m: Message):
            if m.from_user.id != owner_id: await m.forward(owner_id)
            elif m.reply_to_message and m.reply_to_message.forward_from:
                await m.copy_to(m.reply_to_message.forward_from.id)
        
        await s_dp.start_polling(s_bot)
    except: pass

# --- [5] لوحات التحكم ---
def get_main_kb(uid):
    btns = [[InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="u_create")]]
    if uid == ADMIN_ID:
        btns.append([InlineKeyboardButton(text="🛠 لوحة المطور", callback_data="adm_panel")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("🤖 **مصنع البوتات المتكامل**", reply_markup=get_main_kb(message.from_user.id))

@dp.callback_query(F.data == "adm_panel")
async def adm_panel(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="adm_stats"), InlineKeyboardButton(text="🌟 تفعيل VIP", callback_data="adm_vip")],
        [InlineKeyboardButton(text="🔄 ريستارت", callback_data="reboot")]
    ])
    await call.message.edit_text("🛠 لوحة المطور:", reply_markup=kb)

# تفعيل VIP
@dp.callback_query(F.data == "adm_vip")
async def vip_ask(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🌟 أرسل ID المستخدم لمنحه VIP:")
    await state.set_state(MyStates.waiting_for_vip_id)

@dp.message(MyStates.waiting_for_vip_id)
async def vip_done(message: Message, state: FSMContext):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET is_vip = TRUE WHERE owner_id = %s', (message.text.strip(),))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"✅ تم تفعيل VIP للمستخدم {message.text}")
    await state.clear()

# صنع بوت جديد
@dp.callback_query(F.data == "u_create")
async def create_ask(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🚀 أرسل توكن البوت الآن:")
    await state.set_state(MyStates.waiting_for_token)

@dp.message(MyStates.waiting_for_token)
async def create_done(message: Message, state: FSMContext):
    token = message.text.strip()
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s)', (message.from_user.id, token))
        conn.commit(); cur.close(); conn.close()
        await message.answer("✅ تم تشغيل بوتك بنجاح!")
        asyncio.create_task(run_sub_bot(token, message.from_user.id, False, None))
    except: await message.answer("⚠️ خطأ في التوكن أو مكرر.")
    await state.clear()

# --- [6] التشغيل ---
async def main():
    init_db() # إصلاح القاعدة أولاً
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token, owner_id, is_vip, welcome_msg FROM sub_bots')
    bots = cur.fetchall(); cur.close(); conn.close()
    for t, o, v, w in bots: asyncio.create_task(run_sub_bot(t, o, v, w))
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
