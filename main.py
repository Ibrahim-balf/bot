import os, sys, logging, asyncio, psycopg2, datetime
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- 1. إعدادات السيرفر لمنع النوم ---
app = Flask('')
@app.route('/')
def home(): return "Factory System: Stable"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# --- 2. الإعدادات ---
TOKEN = os.getenv("BOT_TOKEN", "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6556184974"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_for_token = State()
    waiting_for_new_welcome = State()
    waiting_for_restart_id = State() # حالة إعادة تشغيل بوت معين
    waiting_for_vip_id = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- 3. لوحات التحكم ---

def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 إعادة تشغيل النظام", callback_data="admin_restart_all")],
        [InlineKeyboardButton(text="🤖 ريستارت بوت معين", callback_data="admin_restart_sub")],
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🧹 تنظيف الجلسات", callback_data="admin_clear_sessions")],
        [InlineKeyboardButton(text="🔙 عودة", callback_data="start_back")]
    ])

# --- 4. معالجات الأزرار السيادية (للمطور فقط) ---

@dp.callback_query(F.data == "admin_restart_all")
async def sys_restart(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("🔄 جاري إعادة تشغيل السيرفر بالكامل...\nستعود الخدمة خلال ثوانٍ.")
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "admin_clear_sessions")
async def clear_sessions(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    await bot.delete_webhook(drop_pending_updates=True)
    await call.message.answer("🧹 تم تنظيف جميع الجلسات المعلقة وإسقاط التحديثات المتضاربة.")
    await call.answer()

@dp.callback_query(F.data == "admin_restart_sub")
async def sub_restart_req(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🆔 أرسل الـ ID الخاص بمالك البوت لإعادة تشغيله:")
    await state.set_state(States.waiting_for_restart_id)

@dp.message(States.waiting_for_restart_id)
async def sub_restart_exec(message: Message, state: FSMContext):
    try:
        t_id = int(message.text)
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (t_id,))
        res = cur.fetchone(); cur.close(); conn.close()
        if res:
            asyncio.create_task(start_sub_bot(res[0], t_id))
            await message.answer(f"✅ تم إعادة تشغيل بوت المالك {t_id} بنجاح.")
        else: await message.answer("❌ لا يوجد بوت لهذا الـ ID.")
    except: await message.answer("⚠️ خطأ في الـ ID.")
    await state.clear()

# --- 5. منطق تشغيل البوتات ---

async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher(storage=MemoryStorage())
        # حذف الـ webhook لكل بوت فرعي لمنع التضارب
        await s_bot.delete_webhook(drop_pending_updates=True)
        
        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            await m.answer("أهلاً بك في بوت التواصل!")

        @s_dp.message()
        async def s_forward(m: Message):
            if m.from_user.id != owner_id: await m.forward(owner_id)
            elif m.reply_to_message and m.reply_to_message.forward_from:
                try: await m.copy_to(m.reply_to_message.forward_from.id)
                except: pass

        await s_dp.start_polling(s_bot, skip_updates=True)
    except: pass

# --- 6. التشغيل النهائي ---

async def main():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, is_vip BOOLEAN DEFAULT FALSE);')
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT, welcome_msg TEXT DEFAULT %s);', ("مرحباً!",))
    conn.commit()
    
    keep_alive()
    
    # حل مشكلة الـ Conflict للمصنع الأساسي
    await bot.delete_webhook(drop_pending_updates=True)
    
    cur.execute('SELECT token, owner_id FROM sub_bots')
    all_bots = cur.fetchall(); cur.close(); conn.close()
    
    for tkn, oid in all_bots:
        asyncio.create_task(start_sub_bot(tkn, oid))
    
    # إرسال إشعار للمطور عند التشغيل
    try: await bot.send_message(ADMIN_ID, "🚀 تم تشغيل نظام المصنع بنجاح وجميع البوتات الفرعية تعمل الآن.")
    except: pass

    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
