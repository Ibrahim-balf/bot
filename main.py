import os, logging, asyncio, psycopg2, requests
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
def home(): return "Bot Factory Pro is Running!"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web).start()

# --- الإعدادات الأساسية ---
TOKEN = os.getenv("BOT_TOKEN", "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6556184974"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

class States(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_token = State()
    waiting_for_welcome_msg = State()

# --- وظائف قاعدة البيانات مع نظام الإصلاح التلقائي ---
def get_db_connection(): return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection(); cur = conn.cursor()
    # إنشاء الجداول الأساسية
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY);')
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT);')
    conn.commit()
    
    # تحديث الأعمدة الناقصة (حل مشكلة الخطأ UndefinedColumn)
    try:
        cur.execute('ALTER TABLE sub_bots ADD COLUMN IF NOT EXISTS welcome_msg TEXT DEFAULT %s;', ('مرحباً بك في بوت التواصل! أرسل رسالتك هنا.',))
        cur.execute('ALTER TABLE sub_bots ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;')
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.warning(f"Database adjustment skipped or failed: {e}")
    
    cur.close(); conn.close()

# --- منطق البوتات المصنوعة ---
async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher()
        
        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('SELECT welcome_msg, is_active FROM sub_bots WHERE owner_id = %s', (owner_id,))
            data = cur.fetchone(); cur.close(); conn.close()
            if data and data[1]: await m.answer(data[0])
            elif data and not data[1]: await m.answer("⚠️ البوت مغلق حالياً.")

        @s_dp.message()
        async def s_forward(m: Message):
            if m.from_user.id != owner_id:
                await s_bot.send_message(owner_id, f"👤 رسالة من: {m.from_user.full_name}\n🆔 ID: `{m.from_user.id}`", parse_mode="Markdown")
                await m.copy_to(owner_id)
            else:
                if m.reply_to_message and m.reply_to_message.forward_from:
                    await m.copy_to(m.reply_to_message.forward_from.id)
                    await m.answer("✅ تم الرد.")

        await s_dp.start_polling(s_bot)
    except: pass

# --- لوحات المفاتيح ---
def get_user_panel(is_active):
    status_btn = "🔴 إيقاف الاستقبال" if is_active else "🟢 تشغيل الاستقبال"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 تغيير رسالة الترحيب", callback_data="set_welcome")],
        [InlineKeyboardButton(text=status_btn, callback_data="toggle_bot")],
        [InlineKeyboardButton(text="🗑 حذف البوت", callback_data="delete_bot")]
    ])

# --- معالجة الأوامر ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (uid,))
    cur.execute('SELECT is_active FROM sub_bots WHERE owner_id = %s', (uid,))
    bot_exists = cur.fetchone(); conn.commit(); cur.close(); conn.close()

    if bot_exists:
        await message.answer("🛠 **لوحة تحكم بوتك:**", reply_markup=get_user_panel(bot_exists[0]))
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 صنع بوت تواصل", callback_data="make_bot")]])
        await message.answer(f"أهلاً {message.from_user.first_name}! 🤖\nاصنع بوت تواصلك الآن مجاناً.", reply_markup=kb)

# --- معالجة طلب صنع بوت ---
@dp.callback_query(F.data == "make_bot")
async def ask_token(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📥 أرسل الآن توكن بوتك من @BotFather:")
    await state.set_state(States.waiting_for_token); await call.answer()

@dp.message(States.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    token = message.text.strip()
    res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
    if not res.get("ok"): return await message.answer("❌ التوكن خاطئ!")
    
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s) ON CONFLICT (owner_id) DO UPDATE SET token = %s', (message.from_user.id, token, token))
    conn.commit(); cur.close(); conn.close()
    
    await message.answer(f"✅ تم تشغيل بوتك: @{res['result']['username']}")
    asyncio.create_task(start_sub_bot(token, message.from_user.id))
    await state.clear()

# --- معالجة إعدادات المستخدم ---
@dp.callback_query(F.data == "set_welcome")
async def set_wel(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📥 أرسل نص الترحيب الجديد:"); await state.set_state(States.waiting_for_welcome_msg); await call.answer()

@dp.message(States.waiting_for_welcome_msg)
async def save_wel(message: Message, state: FSMContext):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET welcome_msg = %s WHERE owner_id = %s', (message.text, message.from_user.id))
    conn.commit(); cur.close(); conn.close()
    await message.answer("✅ تم تحديث الترحيب."); await state.clear()

@dp.callback_query(F.data == "toggle_bot")
async def toggle(call: types.CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET is_active = NOT is_active WHERE owner_id = %s RETURNING is_active', (call.from_user.id,))
    res = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
    await call.message.edit_reply_markup(reply_markup=get_user_panel(res)); await call.answer("تم تغيير الحالة.")

@dp.callback_query(F.data == "delete_bot")
async def delete(call: types.CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('DELETE FROM sub_bots WHERE owner_id = %s', (call.from_user.id,))
    conn.commit(); cur.close(); conn.close()
    await call.message.edit_text("✅ تم حذف البوت."); await call.answer()

# --- لوحة الأدمن ---
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID: return
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users;'); u_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM sub_bots;'); b_count = cur.fetchone()[0]
    cur.close(); conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👥 مستخدمين: {u_count}", callback_data="none"), InlineKeyboardButton(text=f"🤖 بوتات: {b_count}", callback_data="none")],
        [InlineKeyboardButton(text="📢 إذاعة عامة", callback_data="start_broadcast")]
    ])
    await message.answer("🛠 لوحة تحكم المطور", reply_markup=kb)

@dp.callback_query(F.data == "start_broadcast")
async def br_1(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📥 أرسل رسالة الإذاعة:"); await state.set_state(States.waiting_for_broadcast); await call.answer()

@dp.message(States.waiting_for_broadcast)
async def br_2(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT user_id FROM users;'); users = cur.fetchall(); cur.close(); conn.close()
    for u in users:
        try: await message.copy_to(u[0]); await asyncio.sleep(0.05)
        except: pass
    await message.answer("✅ تمت الإذاعة."); await state.clear()

# --- التشغيل الرئيسي ---
async def main():
    init_db()
    keep_alive()
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token, owner_id FROM sub_bots'); bots = cur.fetchall(); cur.close(); conn.close()
    for b in bots: asyncio.create_task(start_sub_bot(b[0], b[1]))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
