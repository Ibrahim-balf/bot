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
def home(): return "Bot Factory Pro is Online!"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web).start()

# --- الإعدادات ---
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

# --- قاعدة البيانات المطورة (نظام الإصلاح التلقائي) ---
def get_db_connection(): return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection(); cur = conn.cursor()
    # 1. إنشاء الجداول إذا لم تكن موجودة
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY);')
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT);')
    cur.execute('CREATE TABLE IF NOT EXISTS bot_clients (bot_owner_id BIGINT, client_id BIGINT, UNIQUE(bot_owner_id, client_id));')
    conn.commit()

    # 2. تحديث الأعمدة (إضافة is_vip و welcome_msg إذا نقصت)
    try:
        cur.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS is_vip BOOLEAN DEFAULT FALSE;')
        cur.execute('ALTER TABLE sub_bots ADD COLUMN IF NOT EXISTS welcome_msg TEXT DEFAULT %s;', ("أهلاً بك في بوت التواصل!",))
        cur.execute('ALTER TABLE sub_bots ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;')
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.warning(f"DB Fix applied or error: {e}")
        
    cur.close(); conn.close()

# --- منطق البوتات المصنوعة ---
async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher(storage=MemoryStorage())
        main_bot_info = await bot.get_me()

        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            if m.from_user.id == owner_id:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 تغيير الترحيب", callback_data="sub_set_welcome")],
                    [InlineKeyboardButton(text="📢 إذاعة (VIP)", callback_data="sub_broadcast")],
                    [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="sub_stats")],
                    [InlineKeyboardButton(text="⚙️ إدارة المصنع", url=f"https://t.me/{main_bot_info.username}")]
                ])
                await m.answer("👋 لوحة التحكم الداخلية:", reply_markup=kb)
            else:
                conn = get_db_connection(); cur = conn.cursor()
                cur.execute('INSERT INTO bot_clients (bot_owner_id, client_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (owner_id, m.from_user.id))
                cur.execute('SELECT welcome_msg FROM sub_bots WHERE owner_id = %s', (owner_id,))
                res = cur.fetchone()
                msg = res[0] if res else "مرحباً!"
                cur.close(); conn.close()
                await m.answer(msg)

        @s_dp.callback_query(F.data == "sub_stats")
        async def s_stats(call: types.CallbackQuery):
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM bot_clients WHERE bot_owner_id = %s', (owner_id,))
            count = cur.fetchone()[0]; cur.close(); conn.close()
            await call.message.answer(f"📊 عدد المشتركين: {count}"); await call.answer()

        @s_dp.message()
        async def s_forward(m: Message):
            if m.from_user.id != owner_id:
                await m.forward(owner_id)
            elif m.reply_to_message and m.reply_to_message.forward_from:
                try: await m.copy_to(m.reply_to_message.forward_from.id); await m.answer("✅ تم.")
                except: pass

        await s_dp.start_polling(s_bot)
    except Exception as e:
        ERROR_LOGS.append(f"⚠️ بوت {owner_id}: {str(e)}")

# --- لوحة الأدمن ---
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID: return
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users;'); u_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM sub_bots;'); b_count = cur.fetchone()[0]
    cur.close(); conn.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👥 مستخدمين: {u_count}", callback_data="none"), 
         InlineKeyboardButton(text=f"🤖 بوتات: {b_count}", callback_data="none")],
        [InlineKeyboardButton(text="🔍 كشف مشاكل الكود", callback_data="check_errors")],
        [InlineKeyboardButton(text="⭐ تفعيل VIP لمستخدم", callback_data="admin_set_vip")]
    ])
    await message.answer("🛠 **لوحة تحكم المطور**", reply_markup=kb)

@dp.callback_query(F.data == "check_errors")
async def check_errors(call: types.CallbackQuery):
    if not ERROR_LOGS:
        await call.message.answer("✅ النظام سليم 100%.")
    else:
        report = "📋 **الأعطال الأخيرة:**\n\n" + "\n".join(ERROR_LOGS[-5:])
        await call.message.answer(report)
    await call.answer()

# --- الأوامر الأساسية ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (uid,))
    conn.commit()
    
    # التحقق من الرتبة ووجود البوت
    cur.execute('SELECT is_vip FROM users WHERE user_id = %s', (uid,))
    res_vip = cur.fetchone()
    is_vip = res_vip[0] if res_vip else False
    
    cur.execute('SELECT owner_id FROM sub_bots WHERE owner_id = %s', (uid,))
    has_bot = cur.fetchone() is not None
    cur.close(); conn.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 صنع بوت تواصل", callback_data="make_bot")]] if not has_bot else [[InlineKeyboardButton(text="🗑 حذف بـوتي", callback_data="delete_bot")]])
    await message.answer(f"أهلاً بك! {'⭐ عضو VIP' if is_vip else ''}", reply_markup=kb)

@dp.callback_query(F.data == "make_bot")
async def m_bot(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📥 أرسل توكن بوتك:"); await state.set_state(States.waiting_for_token); await call.answer()

@dp.message(States.waiting_for_token)
async def save_bot(message: Message, state: FSMContext):
    token = message.text.strip()
    try:
        res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
        if not res.get("ok"): return await message.answer("❌ التوكن خاطئ!")
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s) ON CONFLICT (owner_id) DO UPDATE SET token = %s', (message.from_user.id, token, token))
        conn.commit(); cur.close(); conn.close()
        await message.answer(f"✅ تم تشغيل بوتك: @{res['result']['username']}")
        asyncio.create_task(start_sub_bot(token, message.from_user.id))
        await state.clear()
    except: await message.answer("❌ خطأ.")

@dp.callback_query(F.data == "admin_set_vip")
async def vip_req(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("أرسل ID المستخدم لترقيته:"); await state.set_state(States.waiting_for_vip_id); await call.answer()

@dp.message(States.waiting_for_vip_id)
async def vip_save(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('UPDATE users SET is_vip = TRUE WHERE user_id = %s', (int(message.text),))
        conn.commit(); cur.close(); conn.close()
        await message.answer("✅ تم التفعيل."); await state.clear()
    except: await message.answer("❌ ID غير صحيح.")

async def main():
    init_db(); keep_alive()
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token, owner_id FROM sub_bots'); bots = cur.fetchall(); cur.close(); conn.close()
    for b in bots: asyncio.create_task(start_sub_bot(b[0], b[1]))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
