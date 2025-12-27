import os, logging, asyncio, psycopg2, datetime
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- 1. إعدادات السيرفر لمنع النوم (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Factory is Alive!"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# --- 2. الإعدادات الأساسية ---
TOKEN = os.getenv("BOT_TOKEN", "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6556184974"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)
ERROR_LOGS = []

# --- 3. حالات FSM ---
class States(StatesGroup):
    waiting_for_token = State()
    waiting_for_search_id = State()
    waiting_for_vip_id = State()
    waiting_for_vip_days = State()
    waiting_for_broadcast = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- 4. لوحات التحكم (Keyboards) ---

# لوحة الأدمن الرئيسية في المصنع
def get_admin_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="admin_stats"),
         InlineKeyboardButton(text="🔍 بحث عن مستخدم", callback_data="admin_search")],
        [InlineKeyboardButton(text="⭐ إدارة VIP", callback_data="admin_vip_panel")],
        [InlineKeyboardButton(text="📢 إذاعة عامة", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚠️ كشف المشاكل", callback_data="check_errors")],
        [InlineKeyboardButton(text="🔙 العودة للمصنع", callback_data="start_back")]
    ])

# لوحة إدارة VIP
def get_vip_mgmt_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ تفعيل اشتراك", callback_data="admin_add_vip")],
        [InlineKeyboardButton(text="➖ سحب اشتراك", callback_data="admin_rem_vip")],
        [InlineKeyboardButton(text="📜 قائمة المشتركين", callback_data="admin_list_vip")],
        [InlineKeyboardButton(text="🔙 العودة للوحة الأدمن", callback_data="admin_main")]
    ])

# --- 5. منطق البوتات المصنوعة (Sub-Bots) ---
async def start_sub_bot(token, owner_id):
    try:
        s_bot = Bot(token=token)
        s_dp = Dispatcher(storage=MemoryStorage())
        factory_info = await bot.get_me()

        @s_dp.message(Command("start"))
        async def s_start(m: Message):
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('SELECT is_vip FROM users WHERE user_id = %s', (owner_id,))
            res = cur.fetchone(); is_vip = res[0] if res else False
            cur.close(); conn.close()
            
            if m.from_user.id == owner_id:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ إدارة المصنع", url=f"https://t.me/{factory_info.username}")]
                ])
                await m.answer("👋 أهلاً بك يا مالك البوت في لوحة تحكم تواصلك.", reply_markup=kb)
            else:
                footer = "" if is_vip else f"\n\n—\n🤖 صنع بواسطة: @{factory_info.username}"
                await m.answer(f"أهلاً بك في بوت التواصل الخاص بـ {m.chat.first_name}!" + footer)

        @s_dp.message()
        async def s_forward(m: Message):
            if m.from_user.id != owner_id:
                await m.forward(owner_id)
            elif m.reply_to_message and m.reply_to_message.forward_from:
                try: await m.copy_to(m.reply_to_message.forward_from.id)
                except: pass

        await s_dp.start_polling(s_bot)
    except Exception as e:
        ERROR_LOGS.append(f"⚠️ خطأ في بوت المالك {owner_id}: {str(e)}")

# --- 6. معالجات لوحة الأدمن (Admin Handlers) ---

@dp.message(Command("admin"))
async def open_admin(message: Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🛠 **مرحباً بك في لوحة تحكم المطور**", reply_markup=get_admin_main_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_main")
async def back_admin(call: types.CallbackQuery):
    await call.message.edit_text("🛠 **لوحة تحكم المطور**", reply_markup=get_admin_main_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: types.CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users'); u_cnt = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM sub_bots'); b_cnt = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM users WHERE is_vip = TRUE'); v_cnt = cur.fetchone()[0]
    cur.close(); conn.close()
    await call.message.edit_text(f"📊 **إحصائيات النظام:**\n\n👤 المستخدمين: {u_cnt}\n🤖 البوتات المصنوعة: {b_cnt}\n⭐ مشتركين VIP: {v_cnt}", reply_markup=get_admin_main_kb())

@dp.callback_query(F.data == "admin_search")
async def search_req(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("🔍 أرسل الـ ID المراد البحث عنه:"); await state.set_state(States.waiting_for_search_id)

@dp.message(States.waiting_for_search_id)
async def search_res(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('SELECT is_vip, vip_expire FROM users WHERE user_id = %s', (int(message.text),))
        user = cur.fetchone()
        cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (int(message.text),))
        bot_data = cur.fetchone(); cur.close(); conn.close()
        
        if not user: await message.answer("❌ مستخدم غير موجود."); return
        txt = f"👤 **معلومات:** `{message.text}`\n━━━━━━━━━━━━\n⭐ الحالة: {'VIP' if user[0] else 'مجاني'}\n📅 الانتهاء: `{user[1]}`\n🤖 يمتلك بوت: {'نعم' if bot_data else 'لا'}"
        await message.answer(txt, parse_mode="Markdown"); await state.clear()
    except: await message.answer("⚠️ ID غير صالح.")

@dp.callback_query(F.data == "admin_vip_panel")
async def vip_panel(call: types.CallbackQuery):
    await call.message.edit_text("🌟 **إدارة الـ VIP**", reply_markup=get_vip_mgmt_kb())

# --- 7. تشغيل المصنع (Main Logic) ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (uid,))
    conn.commit()
    
    buttons = []
    if uid == ADMIN_ID: buttons.append([InlineKeyboardButton(text="🛠 لوحة المطور", callback_data="admin_main")])
    
    cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
    if cur.fetchone(): buttons.append([InlineKeyboardButton(text="🗑 حذف بوطي", callback_data="delete_bot")])
    else: buttons.append([InlineKeyboardButton(text="➕ صنع بوت تواصل", callback_data="make_bot")])
    
    await message.answer("🤖 **مرحباً بك في مصنع البوتات المطوّر**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    cur.close(); conn.close()

# --- 8. النظام الأساسي ---
async def main():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, is_vip BOOLEAN DEFAULT FALSE, vip_expire DATE);')
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT);')
    conn.commit()
    
    keep_alive() # تشغيل Flask
    
    cur.execute('SELECT token, owner_id FROM sub_bots')
    all_bots = cur.fetchall(); cur.close(); conn.close()
    
    for tkn, oid in all_bots:
        asyncio.create_task(start_sub_bot(tkn, oid))
        await asyncio.sleep(1)
        
    logging.info("Starting Main Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
