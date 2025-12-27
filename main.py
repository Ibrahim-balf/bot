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
def home(): return "Multi-Bot Factory is Online!"
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
    waiting_for_token = State()
    waiting_for_vip_id = State()
    waiting_for_welcome_msg = State() 
    waiting_for_broadcast = State()   

# --- قاعدة البيانات ---
def get_db_connection(): return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, is_vip BOOLEAN DEFAULT FALSE);')
    cur.execute('''CREATE TABLE IF NOT EXISTS sub_bots (
        owner_id BIGINT PRIMARY KEY, 
        token TEXT, 
        welcome_msg TEXT DEFAULT 'أهلاً بك في بوت التواصل الخاص بي!',
        is_active BOOLEAN DEFAULT TRUE
    );''')
    cur.execute('CREATE TABLE IF NOT EXISTS bot_clients (bot_owner_id BIGINT, client_id BIGINT, UNIQUE(bot_owner_id, client_id));')
    conn.commit(); cur.close(); conn.close()

# --- منطق البوتات المصنوعة (Sub-Bots) ---
async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher(storage=MemoryStorage())
        
        # جلب معلومات البوت الأساسي لمرة واحدة
        main_bot_info = await bot.get_me()
        main_bot_username = main_bot_info.username

        def get_sub_control_panel():
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 تغيير رسالة الترحيب", callback_data="sub_set_welcome")],
                [InlineKeyboardButton(text="📢 إذاعة للمشتركين", callback_data="sub_broadcast")],
                [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="sub_stats")],
                [InlineKeyboardButton(text="⚙️ إدارة من المصنع", url=f"https://t.me/{main_bot_username}")]
            ])

        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            if m.from_user.id == owner_id:
                await m.answer("👋 أهلاً بك يا مالك البوت في لوحة تحكمك الداخلية:", 
                               reply_markup=get_sub_control_panel())
            else:
                conn = get_db_connection(); cur = conn.cursor()
                cur.execute('INSERT INTO bot_clients (bot_owner_id, client_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (owner_id, m.from_user.id))
                cur.execute('SELECT welcome_msg FROM sub_bots WHERE owner_id = %s', (owner_id,))
                msg = cur.fetchone()[0]; cur.close(); conn.close()
                await m.answer(msg)

        @s_dp.callback_query(F.data == "sub_stats")
        async def s_stats(call: types.CallbackQuery):
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM bot_clients WHERE bot_owner_id = %s', (owner_id,))
            count = cur.fetchone()[0]; cur.close(); conn.close()
            await call.message.answer(f"📊 عدد الأشخاص الذين راسلوا بوتك: {count}")
            await call.answer()

        @s_dp.callback_query(F.data == "sub_set_welcome")
        async def s_wel_req(call: types.CallbackQuery, state: FSMContext):
            await call.message.answer("📥 أرسل الآن رسالة الترحيب الجديدة:")
            await state.set_state(States.waiting_for_welcome_msg); await call.answer()

        @s_dp.message(States.waiting_for_welcome_msg)
        async def s_wel_save(m: Message, state: FSMContext):
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('UPDATE sub_bots SET welcome_msg = %s WHERE owner_id = %s', (m.text, owner_id))
            conn.commit(); cur.close(); conn.close()
            await m.answer("✅ تم تحديث رسالة الترحيب بنجاح.")
            await state.clear()

        @s_dp.callback_query(F.data == "sub_broadcast")
        async def s_br_req(call: types.CallbackQuery, state: FSMContext):
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('SELECT is_vip FROM users WHERE user_id = %s', (owner_id,))
            res = cur.fetchone()
            is_vip = res[0] if res else False
            cur.close(); conn.close()
            if not is_vip: return await call.answer("❌ ميزة الإذاعة للـ VIP فقط!", show_alert=True)
            await call.message.answer("📢 أرسل الرسالة التي تريد إذاعتها لجميع مشتركيك:"); await state.set_state(States.waiting_for_broadcast); await call.answer()

        @s_dp.message(States.waiting_for_broadcast)
        async def s_br_run(m: Message, state: FSMContext):
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('SELECT client_id FROM bot_clients WHERE bot_owner_id = %s', (owner_id,))
            clients = cur.fetchall(); cur.close(); conn.close()
            success = 0
            for c in clients:
                try: await m.copy_to(c[0]); success += 1; await asyncio.sleep(0.05)
                except: pass
            await m.answer(f"✅ تمت الإذاعة لـ {success} مشترك."); await state.clear()

        @s_dp.message()
        async def s_forward(m: Message):
            if m.from_user.id != owner_id:
                await m.forward(owner_id)
                await s_bot.send_message(owner_id, f"👤 من: {m.from_user.full_name}\n🆔: `{m.from_user.id}`", parse_mode="Markdown")
            elif m.reply_to_message and m.reply_to_message.forward_from:
                try:
                    await m.copy_to(m.reply_to_message.forward_from.id)
                    await m.answer("✅ تم الرد.")
                except: await m.answer("❌ تعذر الرد.")

        await s_dp.start_polling(s_bot)
    except Exception as e:
        logging.error(f"Error in sub-bot {owner_id}: {e}")

# --- منطق المصنع ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (uid,))
    cur.execute('SELECT owner_id FROM sub_bots WHERE owner_id = %s', (uid,))
    has_bot = cur.fetchone() is not None
    cur.execute('SELECT is_vip FROM users WHERE user_id = %s', (uid,))
    is_vip = cur.fetchone()[0]; cur.close(); conn.close()

    if has_bot:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 حذف بـوتي", callback_data="delete_bot")],
            [InlineKeyboardButton(text="⭐ ترقية لـ VIP", callback_data="buy_vip")]
        ])
        await message.answer(f"🛠 **إدارة حسابك في المصنع**\nوضع الحساب: {'VIP ⭐' if is_vip else 'مجاني 🆓'}\n\nملاحظة: إدارة البوت أصبحت الآن من داخل بوطه مباشرة!", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 صنع بوت تواصل", callback_data="make_bot")]])
        await message.answer("أهلاً بك! اصنع بوت تواصلك الآن وادر كل شيء من داخله.", reply_markup=kb)

@dp.callback_query(F.data == "make_bot")
async def m_bot(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📥 أرسل توكن بوتك من @BotFather:"); await state.set_state(States.waiting_for_token); await call.answer()

@dp.message(States.waiting_for_token)
async def save_bot(message: Message, state: FSMContext):
    token = message.text.strip()
    try:
        res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
        if not res.get("ok"): return await message.answer("❌ التوكن خاطئ!")
        
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s) ON CONFLICT (owner_id) DO UPDATE SET token = %s', (message.from_user.id, token, token))
        conn.commit(); cur.close(); conn.close()
        
        await message.answer(f"✅ تم تشغيل بوتك: @{res['result']['username']}\n\nقم بالدخول إليه الآن لتجد لوحة التحكم!")
        asyncio.create_task(start_sub_bot(token, message.from_user.id))
        await state.clear()
    except: await message.answer("❌ حدث خطأ في الاتصال.")

@dp.callback_query(F.data == "delete_bot")
async def del_bot(call: types.CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('DELETE FROM sub_bots WHERE owner_id = %s', (call.from_user.id,))
    conn.commit(); cur.close(); conn.close()
    await call.message.edit_text("✅ تم حذف بوتك بنجاح."); await call.answer()

@dp.message(Command("setvip"))
async def admin_vip(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("أرسل ID المستخدم لترقيته للـ VIP:"); await state.set_state(States.waiting_for_vip_id)

@dp.message(States.waiting_for_vip_id)
async def process_vip(message: Message, state: FSMContext):
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('UPDATE users SET is_vip = TRUE WHERE user_id = %s', (int(message.text),))
        conn.commit(); cur.close(); conn.close()
        await message.answer("✅ تم التفعيل بنجاح."); await state.clear()
    except: await message.answer("❌ خطأ في الـ ID."); await state.clear()

# --- التشغيل الرئيسي ---
async def main():
    init_db(); keep_alive()
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token, owner_id FROM sub_bots'); bots = cur.fetchall(); cur.close(); conn.close()
    for b in bots: asyncio.create_task(start_sub_bot(b[0], b[1]))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
