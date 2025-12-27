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
def home(): return "Professional Bot Factory is Online!"
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
    waiting_for_token = State()
    waiting_for_welcome_msg = State()
    waiting_for_broadcast = State() # للأدمن
    waiting_for_user_broadcast = State() # للمستخدم VIP
    waiting_for_channel_id = State() # لقفل الاشتراك
    waiting_for_vip_id = State() # لتفعيل VIP

# --- قاعدة البيانات ---
def get_db_connection(): return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, is_vip BOOLEAN DEFAULT FALSE);')
    cur.execute('''CREATE TABLE IF NOT EXISTS sub_bots (
        owner_id BIGINT PRIMARY KEY, 
        token TEXT, 
        welcome_msg TEXT DEFAULT 'مرحباً بك في بوت التواصل!',
        force_channel TEXT DEFAULT NULL,
        is_active BOOLEAN DEFAULT TRUE
    );''')
    cur.execute('CREATE TABLE IF NOT EXISTS bot_clients (bot_owner_id BIGINT, client_id BIGINT, UNIQUE(bot_owner_id, client_id));')
    conn.commit(); cur.close(); conn.close()

# --- منطق البوتات المصنوعة (Sub-Bots) ---
async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher()

        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            # تسجيل العميل
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('INSERT INTO bot_clients (bot_owner_id, client_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (owner_id, m.from_user.id))
            cur.execute('SELECT welcome_msg, force_channel, is_active FROM sub_bots WHERE owner_id = %s', (owner_id,))
            data = cur.fetchone(); cur.close(); conn.close()

            if not data or not data[2]: return await m.answer("⚠️ البوت متوقف حالياً.")

            # ميزة الاشتراك الإجباري (VIP)
            if data[1]:
                try:
                    check = await s_bot.get_chat_member(chat_id=data[1], user_id=m.from_user.id)
                    if check.status not in ["member", "administrator", "creator"]:
                        return await m.answer(f"❌ يجب عليك الاشتراك في القناة أولاً لاستخدام البوت:\n{data[1]}")
                except: pass

            await m.answer(data[0])

        @s_dp.message()
        async def s_forward(m: Message):
            if m.from_user.id != owner_id:
                await s_bot.send_message(owner_id, f"👤 رسالة من: {m.from_user.full_name}\n🆔: `{m.from_user.id}`", parse_mode="Markdown")
                await m.copy_to(owner_id)
            else: # رد المالك
                if m.reply_to_message and m.reply_to_message.forward_from:
                    await m.copy_to(m.reply_to_message.forward_from.id)
                    await m.answer("✅ تم الرد.")

        await s_dp.start_polling(s_bot)
    except: pass

# --- لوحات التحكم ---
def get_main_kb(is_vip, has_bot):
    buttons = []
    if not has_bot:
        buttons.append([InlineKeyboardButton(text="🛠 صنع بوت تواصل جديد", callback_data="make_bot")])
    else:
        buttons.append([InlineKeyboardButton(text="📝 تغيير الترحيب", callback_data="set_welcome")])
        buttons.append([InlineKeyboardButton(text="📢 إذاعة للمشتركين (VIP)", callback_data="user_broadcast")])
        buttons.append([InlineKeyboardButton(text="🔒 قفل الاشتراك (VIP)", callback_data="set_force_channel")])
        buttons.append([InlineKeyboardButton(text="🗑 حذف البوت", callback_data="delete_bot")])
    
    status = "⭐ VIP مفعّل" if is_vip else "🆓 نسخة مجانية"
    buttons.append([InlineKeyboardButton(text=status, callback_data="none")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- معالجة الأوامر ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (uid,))
    cur.execute('SELECT is_vip FROM users WHERE user_id = %s', (uid,))
    is_vip = cur.fetchone()[0]
    cur.execute('SELECT owner_id FROM sub_bots WHERE owner_id = %s', (uid,))
    has_bot = cur.fetchone() is not None
    conn.commit(); cur.close(); conn.close()
    
    await message.answer(f"أهلاً بك {message.from_user.first_name} في المصنع المتطور! 🤖", 
                         reply_markup=get_main_kb(is_vip, has_bot))

# --- معالجة ميزات VIP ---
@dp.callback_query(F.data == "set_force_channel")
async def channel_step(call: types.CallbackQuery, state: FSMContext):
    # تحقق VIP
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT is_vip FROM users WHERE user_id = %s', (call.from_user.id,))
    if not cur.fetchone()[0]: return await call.answer("❌ هذه الميزة للمطورين VIP فقط!", show_alert=True)
    
    await call.message.answer("📥 أرسل معرف قناتك مع الـ @ (يجب رفع البوت أدمن بالقناة):")
    await state.set_state(States.waiting_for_channel_id); await call.answer()

@dp.message(States.waiting_for_channel_id)
async def save_channel(message: Message, state: FSMContext):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET force_channel = %s WHERE owner_id = %s', (message.text, message.from_user.id))
    conn.commit(); cur.close(); conn.close()
    await message.answer("✅ تم تفعيل قفل الاشتراك الإجباري.")
    await state.clear()

@dp.callback_query(F.data == "user_broadcast")
async def br_vip_step(call: types.CallbackQuery, state: FSMContext):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT is_vip FROM users WHERE user_id = %s', (call.from_user.id,))
    if not cur.fetchone()[0]: return await call.answer("❌ ميزة الإذاعة للـ VIP فقط!", show_alert=True)
    
    await call.message.answer("📥 أرسل الرسالة التي تريد إذاعتها لمشتركيك:")
    await state.set_state(States.waiting_for_user_broadcast); await call.answer()

@dp.message(States.waiting_for_user_broadcast)
async def run_user_br(message: Message, state: FSMContext):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
    token = cur.fetchone()[0]
    cur.execute('SELECT client_id FROM bot_clients WHERE bot_owner_id = %s', (uid,))
    clients = cur.fetchall(); cur.close(); conn.close()
    
    temp_bot = Bot(token=token)
    success = 0
    for c in clients:
        try: await message.copy_to(c[0]); success += 1; await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ تمت الإذاعة بنجاح لـ {success} مشترك.")
    await state.clear()

# --- لوحة الأدمن (تفعيل VIP) ---
@dp.message(Command("setvip"))
async def admin_set_vip(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("أرسل ID المستخدم المراد ترقيته للـ VIP:")
        await state.set_state(States.waiting_for_vip_id)

@dp.message(States.waiting_for_vip_id)
async def process_vip_upgrade(message: Message, state: FSMContext):
    try:
        target = int(message.text)
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('UPDATE users SET is_vip = TRUE WHERE user_id = %s', (target,))
        conn.commit(); cur.close(); conn.close()
        await message.answer(f"✅ تمت ترقية {target} إلى VIP بنجاح.")
        await state.clear()
    except: await message.answer("❌ خطأ في الـ ID.")

# --- بقية الوظائف الأساسية ---
@dp.callback_query(F.data == "make_bot")
async def m_bot(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("أرسل توكن بوتك الآن:"); await state.set_state(States.waiting_for_token); await call.answer()

@dp.message(States.waiting_for_token)
async def save_t(message: Message, state: FSMContext):
    token = message.text.strip()
    res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
    if not res.get("ok"): return await message.answer("❌ توكن خطأ!")
    
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s) ON CONFLICT (owner_id) DO UPDATE SET token = %s', (message.from_user.id, token, token))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"✅ تم تشغيل بوتك: @{res['result']['username']}")
    asyncio.create_task(start_sub_bot(token, message.from_user.id))
    await state.clear()

# --- التشغيل ---
async def main():
    init_db(); keep_alive()
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token, owner_id FROM sub_bots'); bots = cur.fetchall(); cur.close(); conn.close()
    for b in bots: asyncio.create_task(start_sub_bot(b[0], b[1]))
    print("🚀 Factory is ready!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
