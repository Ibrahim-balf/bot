import os, sys, asyncio, psycopg2, logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- [1] إعدادات السيرفر لمنع التوقف ---
app = Flask('')
@app.route('/')
def home(): return "Factory System: Live"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات الأساسية ---
TOKEN = "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_for_token = State()
    waiting_for_broadcast = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- [3] لوحات التحكم ---

def get_start_kb(uid):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
    res = cur.fetchone()
    cur.close(); conn.close()
    
    btns = []
    if res: btns.append([InlineKeyboardButton(text="🎮 إدارة بوطي", callback_data="user_manage")])
    else: btns.append([InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="user_create")])
    
    if uid == ADMIN_ID: btns.append([InlineKeyboardButton(text="🛠 لوحة المطور", callback_data="admin_main")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

# --- [4] معالجات المطور (الإذاعة والتحكم) ---

@dp.callback_query(F.data == "admin_main")
async def admin_panel(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 إذاعة عامة", callback_data="admin_bc")],
        [InlineKeyboardButton(text="🔄 ريستارت", callback_data="reboot"), InlineKeyboardButton(text="🧹 تنظيف", callback_data="clear")],
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton(text="🔙 عودة", callback_data="back_home")]
    ])
    await call.message.edit_text("🛠 **لوحة التحكم السيادية**", reply_markup=kb)

@dp.callback_query(F.data == "admin_bc")
async def bc_req(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📣 أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين:")
    await state.set_state(States.waiting_for_broadcast)

@dp.message(States.waiting_for_broadcast)
async def bc_exec(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT DISTINCT owner_id FROM sub_bots') # مثال لجلب المستخدمين
    users = cur.fetchall(); cur.close(); conn.close()
    count = 0
    for user in users:
        try:
            await bot.send_message(user[0], message.text)
            count += 1
        except: pass
    await message.answer(f"✅ تم إرسال الإذاعة إلى {count} مستخدم.")
    await state.clear()

# --- [5] نظام تشغيل البوتات الفرعية (Sub-Bots) ---

async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher()
        await s_bot.delete_webhook(drop_pending_updates=True)
        
        @s_dp.message(Command("start"))
        async def s_start(m: Message): await m.answer("مرحباً بك في بوت التواصل الخاص بي!")

        @s_dp.message()
        async def s_handler(m: Message):
            if m.from_user.id != owner_id: await m.forward(owner_id)
            elif m.reply_to_message and m.reply_to_message.forward_from:
                await m.copy_to(m.reply_to_message.forward_from.id)
        
        await s_dp.start_polling(s_bot)
    except: pass

# --- [6] التشغيل الرئيسي ---

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("🤖 أهلاً بك في المصنع المتكامل!", reply_markup=get_start_kb(message.from_user.id))

@dp.callback_query(F.data == "reboot")
async def reboot_call(call: CallbackQuery):
    await call.answer("🔄 جاري إعادة التشغيل...")
    os.execl(sys.executable, sys.executable, *sys.argv)

async def main():
    # إنشاء الجداول إذا لم تكن موجودة
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT)')
    conn.commit()
    
    # تشغيل البوتات المشتركة سابقاً تلقائياً
    cur.execute('SELECT token, owner_id FROM sub_bots')
    all_bots = cur.fetchall(); cur.close(); conn.close()
    for t, o in all_bots: asyncio.create_task(start_sub_bot(t, o))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
