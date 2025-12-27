import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- [1] إعداد السيرفر (Flask) لضمان الاستقرار ---
app = Flask('')
@app.route('/')
def home(): return "Bot Factory System: Online"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات وقاعدة البيانات ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MyStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_broadcast = State()
    waiting_for_welcome = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- [3] نظام اللوحات الذكي ---

def get_keyboard(uid):
    # التحقق من وجود بوت للمستخدم
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
    has_bot = cur.fetchone()
    cur.close(); conn.close()
    
    btns = []
    # لوحة المستخدم
    if has_bot:
        btns.append([InlineKeyboardButton(text="⚙️ إدارة بوطي", callback_data="user_manage")])
    else:
        btns.append([InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="user_create")])
    
    # لوحة المطور (تظهر لك فقط)
    if uid == ADMIN_ID:
        btns.append([InlineKeyboardButton(text="🛠 لوحة المطور (أنت)", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=btns)

# --- [4] المعالجات (Handlers) ---

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🤖 **مرحباً بك في مصنع البوتات الذكي**\nالنظام تعرف على صلاحياتك بنجاح. اختر من القائمة:", 
                         reply_markup=get_keyboard(message.from_user.id))

# --- قسم المطور (Admin Logic) ---
@dp.callback_query(F.data == "admin_panel")
async def admin_main(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 إذاعة عامة", callback_data="adm_bc")],
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="adm_stats")],
        [InlineKeyboardButton(text="🔄 ريستارت", callback_data="adm_reboot"), InlineKeyboardButton(text="🧹 تنظيف", callback_data="adm_clear")]
    ])
    await call.message.edit_text("🛠 **لوحة التحكم السيادية**", reply_markup=kb)

# --- قسم المستخدم (User Logic) ---
@dp.callback_query(F.data == "user_create")
async def create_flow(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🚀 أرسل توكن بوتك من @BotFather الآن:")
    await state.set_state(MyStates.waiting_for_token)
    await call.answer()

@dp.message(MyStates.waiting_for_token)
async def save_token(message: Message, state: FSMContext):
    token = message.text.strip()
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s)', (message.from_user.id, token))
        conn.commit(); cur.close(); conn.close()
        await message.answer("✅ تم صنع بوتك بنجاح!")
    except:
        await message.answer("⚠️ حدث خطأ أو لديك بوت بالفعل.")
    await state.clear()

@dp.callback_query(F.data == "user_manage")
async def manage_flow(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 تغيير الترحيب", callback_data="user_edit_w")],
        [InlineKeyboardButton(text="🗑 حذف البوت", callback_data="user_del")]
    ])
    await call.message.edit_text("⚙️ **إدارة بوت التواصل الخاص بك:**", reply_markup=kb)

# --- أزرار الصيانة ---
@dp.callback_query(F.data == "adm_reboot")
async def reboot_sys(call: CallbackQuery):
    await call.answer("🔄 جاري إعادة التشغيل...", show_alert=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "adm_clear")
async def clear_sys(call: CallbackQuery):
    await bot.delete_webhook(drop_pending_updates=True)
    await call.answer("🧹 تم تنظيف التضارب!", show_alert=True)

# --- [5] التشغيل النهائي ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Factory System is Fully Integrated (Admin + User)")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
