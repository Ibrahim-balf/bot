import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- [1] إعداد السيرفر ---
app = Flask('')
@app.route('/')
def home(): return "Factory System: Online"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات وقاعدة البيانات ---
TOKEN = "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class BotStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_welcome = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- [3] لوحات التحكم الفعالة ---

def get_start_kb(uid):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
    has_bot = cur.fetchone()
    cur.close(); conn.close()
    
    buttons = []
    if has_bot:
        buttons.append([InlineKeyboardButton(text="🎮 إدارة بوطي", callback_data="user_manage")])
    else:
        buttons.append([InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="user_create")])
    
    if uid == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="🛠 لوحة المطور", callback_data="admin_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- [4] معالجات الأوامر والأزرار ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🤖 أهلاً بك في المصنع المتكامل.\nاختر من القائمة أدناه:", 
                         reply_markup=get_start_kb(message.from_user.id))

# --- قسم المطور (Admin) ---
@dp.callback_query(F.data == "admin_main")
async def admin_panel(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ريستارت السيرفر", callback_data="reboot")],
        [InlineKeyboardButton(text="🧹 تنظيف التضارب", callback_data="clear")],
        [InlineKeyboardButton(text="🔙 عودة", callback_data="back_home")]
    ])
    await call.message.edit_text("🛠 لوحة المطور السيادية:", reply_markup=kb)

# --- قسم صنع البوت (User) ---
@dp.callback_query(F.data == "user_create")
async def create_bot_step(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer("🚀 أرسل الآن توكن البوت الذي حصلت عليه من @BotFather:")
    await state.set_state(BotStates.waiting_for_token)

@dp.message(BotStates.waiting_for_token)
async def save_bot(message: Message, state: FSMContext):
    token = message.text
    # هنا يتم تخزين التوكن في القاعدة (تبسيطاً للمثال)
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s)', (message.from_user.id, token))
        conn.commit()
        await message.answer("✅ تم صنع بوتك بنجاح! سيتم تشغيله خلال ثوانٍ.")
    except:
        await message.answer("⚠️ لديك بوت بالفعل أو التوكن مستخدم.")
    cur.close(); conn.close()
    await state.clear()

# --- قسم إدارة البوت (User Manage) ---
@dp.callback_query(F.data == "user_manage")
async def manage_panel(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 تغيير الترحيب", callback_data="change_w")],
        [InlineKeyboardButton(text="🗑 حذف البوت", callback_data="delete_b")],
        [InlineKeyboardButton(text="🔙 عودة", callback_data="back_home")]
    ])
    await call.message.edit_text("🎮 لوحة إدارة بوتك:", reply_markup=kb)

# --- الأزرار العامة ---
@dp.callback_query(F.data == "back_home")
async def go_home(call: CallbackQuery):
    await call.message.edit_text("🤖 اختر من القائمة أدناه:", reply_markup=get_start_kb(call.from_user.id))

@dp.callback_query(F.data == "reboot")
async def reboot_sys(call: CallbackQuery):
    await call.answer("🔄 Rebooting...", show_alert=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "clear")
async def clear_sys(call: CallbackQuery):
    await bot.delete_webhook(drop_pending_updates=True)
    await call.answer("🧹 تم التنظيف!", show_alert=True)

# --- [5] التشغيل ---
async def start_app():
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Full Factory System is LIVE")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(start_app())
