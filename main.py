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
def home(): return "Bot Factory Pro is Running!"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web).start()

# --- الإعدادات ---
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

# --- قاعدة البيانات ---
def get_db_connection(): return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY);')
    cur.execute('''CREATE TABLE IF NOT EXISTS sub_bots (
        owner_id BIGINT PRIMARY KEY, 
        token TEXT, 
        welcome_msg TEXT DEFAULT 'مرحباً بك في بوت التواصل! أرسل رسالتك هنا.',
        is_active BOOLEAN DEFAULT TRUE
    );''')
    conn.commit(); cur.close(); conn.close()

# --- منطق البوتات المصنوعة ---
async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher()
        
        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('SELECT welcome_msg, is_active FROM sub_bots WHERE owner_id = %s', (owner_id,))
            data = cur.fetchone()
            cur.close(); conn.close()
            
            if data and data[1]: # إذا كان البوت نشطاً
                await m.answer(data[0])
            elif data and not data[1]:
                await m.answer("⚠️ عذراً، هذا البوت مغلق مؤقتاً من قبل المالك.")

        @s_dp.message()
        async def s_forward(m: Message):
            if m.from_user.id != owner_id:
                await s_bot.send_message(owner_id, f"👤 رسالة من: {m.from_user.full_name}\n🆔 ID: `{m.from_user.id}`", parse_mode="Markdown")
                await m.copy_to(owner_id)
            else:
                if m.reply_to_message:
                    # محاولة استخراج ID المستخدم من الرسالة المحولة (تبسيط)
                    try:
                        user_id = m.reply_to_message.forward_from.id
                        await m.copy_to(user_id)
                        await m.answer("✅ تم الرد.")
                    except:
                        await m.answer("❌ فشل الرد. يجب أن تكون الرسالة محولة من المستخدم مباشرة.")

        await s_dp.start_polling(s_bot)
    except: pass

# --- لوحات المفاتيح ---
def get_user_panel(is_active):
    status_btn = "🔴 إيقاف استقبال الرسائل" if is_active else "🟢 تشغيل استقبال الرسائل"
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
    bot_exists = cur.fetchone()
    conn.commit(); cur.close(); conn.close()

    if bot_exists:
        await message.answer("🛠 **لوحة التحكم الخاصة ببوتك:**", reply_markup=get_user_panel(bot_exists[0]))
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 صنع بوت تواصل", callback_data="make_bot")]])
        await message.answer(f"أهلاً بك {message.from_user.first_name}! 🤖\nليس لديك بوت حالياً، اضغط على الزر للبدء.", reply_markup=kb)

# --- معالجة لوحة التحكم ---
@dp.callback_query(F.data == "set_welcome")
async def change_welcome_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📥 أرسل الآن رسالة الترحيب الجديدة:")
    await state.set_state(States.waiting_for_welcome_msg)
    await call.answer()

@dp.message(States.waiting_for_welcome_msg)
async def save_welcome_msg(message: Message, state: FSMContext):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET welcome_msg = %s WHERE owner_id = %s', (message.text, message.from_user.id))
    conn.commit(); cur.close(); conn.close()
    await message.answer("✅ تم تحديث رسالة الترحيب بنجاح.")
    await state.clear()

@dp.callback_query(F.data == "toggle_bot")
async def toggle_bot_status(call: types.CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET is_active = NOT is_active WHERE owner_id = %s RETURNING is_active', (call.from_user.id,))
    new_status = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    await call.message.edit_reply_markup(reply_markup=get_user_panel(new_status))
    await call.answer("تم تغيير حالة البوت.")

@dp.callback_query(F.data == "delete_bot")
async def delete_user_bot(call: types.CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('DELETE FROM sub_bots WHERE owner_id = %s', (call.from_user.id,))
    conn.commit(); cur.close(); conn.close()
    await call.message.edit_text("✅ تم حذف بوتك من السيرفر. يمكنك إنشاء واحد جديد دائماً.")

# (أضف هنا كود الإذاعة ولوحة الأدمن السابق كما هو)

async def main():
    init_db()
    keep_alive()
    # كود إعادة تشغيل البوتات عند بدء السيرفر
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token, owner_id FROM sub_bots'); bots = cur.fetchall()
    cur.close(); conn.close()
    for b in bots: asyncio.create_task(start_sub_bot(b[0], b[1]))
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
