import os, logging, asyncio, psycopg2, requests
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- إعدادات السيرفر ---
app = Flask('')
@app.route('/')
def home(): return "Professional Factory Admin Panel Online!"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web).start()

# --- الإعدادات الأساسية ---
TOKEN = os.getenv("BOT_TOKEN", "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6556184974"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

ERROR_LOGS = []

class States(StatesGroup):
    waiting_for_token = State()
    waiting_for_vip_id = State()
    waiting_for_welcome_msg = State() 
    waiting_for_broadcast = State()
    waiting_for_factory_welcome = State() # تغيير ترحيب المصنع

# --- قاعدة البيانات ---
def get_db_connection(): return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);')
    cur.execute('INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT DO NOTHING;', ("factory_welcome", "أهلاً بك في مصنع البوتات الاحترافي! 🤖"))
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, is_vip BOOLEAN DEFAULT FALSE);')
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT, welcome_msg TEXT DEFAULT %s, is_active BOOLEAN DEFAULT TRUE);', ("أهلاً بك!",))
    cur.execute('CREATE TABLE IF NOT EXISTS bot_clients (bot_owner_id BIGINT, client_id BIGINT, UNIQUE(bot_owner_id, client_id));')
    try:
        cur.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS is_vip BOOLEAN DEFAULT FALSE;')
        conn.commit()
    except: conn.rollback()
    cur.close(); conn.close()

# --- لوحات التحكم الجمالية ---
def get_admin_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات العامة", callback_data="admin_stats"), InlineKeyboardButton(text="🔍 كشف المشاكل", callback_data="check_errors")],
        [InlineKeyboardButton(text="📢 إذاعة للمستخدمين", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⭐ تفعيل VIP", callback_data="admin_set_vip"), InlineKeyboardButton(text="📝 ترحيب المصنع", callback_data="admin_set_factory_welcome")],
        [InlineKeyboardButton(text="🔄 تحديث النظام", callback_data="admin_refresh")]
    ])

# --- معالجة أوامر الأدمن ---
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(
        "✨ **مرحباً بك في لوحة تحكم المطور**\n"
        "━━━━━━━━━━━━━━\n"
        "يمكنك إدارة المصنع والبوتات الفرعية من هنا بكفاءة عالية.",
        reply_markup=get_admin_main_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: types.CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users;'); u_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM sub_bots;'); b_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM users WHERE is_vip = TRUE;'); vip_count = cur.fetchone()[0]
    cur.close(); conn.close()
    
    stats_text = (
        "📈 **إحصائيات المصنع الحالية:**\n"
        "━━━━━━━━━━━━━━\n"
        f"👤 إجمالي المستخدمين: `{u_count}`\n"
        f"🤖 البوتات المصنوعة: `{b_count}`\n"
        f"⭐ أعضاء VIP: `{vip_count}`\n"
        "━━━━━━━━━━━━━━"
    )
    await call.message.edit_text(stats_text, reply_markup=get_admin_main_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_set_factory_welcome")
async def req_factory_welcome(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📥 أرسل الآن رسالة الترحيب الجديدة التي ستظهر لمستخدمي المصنع:")
    await state.set_state(States.waiting_for_factory_welcome); await call.answer()

@dp.message(States.waiting_for_factory_welcome)
async def save_factory_welcome(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE settings SET value = %s WHERE key = %s', (message.text, "factory_welcome"))
    conn.commit(); cur.close(); conn.close()
    await message.answer("✅ تم تحديث ترحيب المصنع بنجاح!")
    await state.clear()

@dp.callback_query(F.data == "admin_broadcast")
async def req_broadcast(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📢 أرسل الرسالة التي تريد إذاعتها لجميع مستخدمي المصنع:"); await state.set_state(States.waiting_for_broadcast); await call.answer()

@dp.message(States.waiting_for_broadcast)
async def run_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT user_id FROM users;'); users = cur.fetchall(); cur.close(); conn.close()
    success = 0
    for u in users:
        try: await message.copy_to(u[0]); success += 1; await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ تمت الإذاعة لـ `{success}` مستخدم بنجاح.", parse_mode="Markdown")
    await state.clear()

# --- تعديل الـ Start ليستخدم الترحيب القابل للتغيير ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (uid,))
    cur.execute('SELECT value FROM settings WHERE key = %s', ("factory_welcome",))
    welcome_text = cur.fetchone()[0]
    cur.execute('SELECT owner_id FROM sub_bots WHERE owner_id = %s', (uid,))
    has_bot = cur.fetchone() is not None
    conn.commit(); cur.close(); conn.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 صنع بوت تواصل", callback_data="make_bot")]] if not has_bot else [[InlineKeyboardButton(text="🗑 حذف بـوتي", callback_data="delete_bot")]])
    await message.answer(welcome_text, reply_markup=kb)

# --- بقية الدوال (إصلاح المشاكل، صنع البوت، تفعيل VIP) كما في الكود السابق ---

async def main():
    init_db(); keep_alive()
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token, owner_id FROM sub_bots'); bots = cur.fetchall(); cur.close(); conn.close()
    for b in bots: asyncio.create_task(start_sub_bot(b[0], b[1])) # دالة البوتات الفرعية السابقة
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
