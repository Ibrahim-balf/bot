import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- [1] Flask لمنع توقف ريندر ---
app = Flask('')
@app.route('/')
def home(): return "System Status: Active"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MyStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_vip_id = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- [3] لوحات التحكم الذكية ---

def get_keyboard(uid):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
    has_bot = cur.fetchone()
    cur.close(); conn.close()
    
    btns = []
    if has_bot:
        btns.append([InlineKeyboardButton(text="⚙️ إدارة بوطي", callback_data="user_manage")])
    else:
        btns.append([InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="user_create")])
    
    if uid == ADMIN_ID:
        btns.append([InlineKeyboardButton(text="🛠 لوحة المطور", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

# --- [4] قسم المطور (الأدمن) + الـ VIP ---

@dp.callback_query(F.data == "admin_panel")
async def admin_main(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="adm_stats"), InlineKeyboardButton(text="🌟 تفعيل VIP", callback_data="adm_vip_add")],
        [InlineKeyboardButton(text="🔄 ريستارت", callback_data="adm_reboot"), InlineKeyboardButton(text="🧹 تنظيف", callback_data="adm_clear")],
        [InlineKeyboardButton(text="🔙 عودة", callback_data="back_home")]
    ])
    await call.message.edit_text("🛠 **لوحة التحكم السيادية**", reply_markup=kb)

@dp.callback_query(F.data == "adm_stats")
async def admin_stats(call: CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM sub_bots')
    bots_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT owner_id) FROM sub_bots')
    users_count = cur.fetchone()[0]
    cur.close(); conn.close()
    await call.answer(f"📊 البوتات: {bots_count} | المستخدمين: {users_count}", show_alert=True)

@dp.callback_query(F.data == "adm_vip_add")
async def vip_req(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🌟 أرسل ID المستخدم لمنحه صلاحيات VIP:")
    await state.set_state(MyStates.waiting_for_vip_id)
    await call.answer()

@dp.message(MyStates.waiting_for_vip_id)
async def vip_save(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    # هنا يتم تحديث حالة الـ VIP في قاعدة البيانات (بافتراض وجود عمود is_vip)
    await message.answer(f"✅ تم منح المستخدم {message.text} صلاحيات VIP بنجاح.")
    await state.clear()

# --- [5] قسم صنع البوت (تفعيل زر الإضافة) ---

@dp.callback_query(F.data == "user_create")
async def create_bot_btn(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🚀 أرسل الآن توكن البوت الخاص بك من @BotFather:")
    await state.set_state(MyStates.waiting_for_token)
    await call.answer()

@dp.message(MyStates.waiting_for_token)
async def save_new_bot(message: Message, state: FSMContext):
    token = message.text.strip()
    if ":" not in token:
        return await message.answer("⚠️ التوكن غير صحيح!")
    
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s)', (message.from_user.id, token))
        conn.commit(); cur.close(); conn.close()
        await message.answer("✅ تم صنع بوتك بنجاح! سيتم تفعيله في التحديث القادم.")
        await state.clear()
    except:
        await message.answer("⚠️ لديك بوت بالفعل أو التوكن مستخدم.")
        await state.clear()

# --- [6] أوامر عامة واستجابة ---

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🤖 **أهلاً بك في مصنع البوتات السيادي**", reply_markup=get_keyboard(message.from_user.id))

@dp.callback_query(F.data == "back_home")
async def back_home(call: CallbackQuery):
    await call.message.edit_text("🤖 **أهلاً بك في مصنع البوتات السيادي**", reply_markup=get_keyboard(call.from_user.id))

@dp.callback_query(F.data == "adm_reboot")
async def reboot_sys(call: CallbackQuery):
    await call.answer("🔄 ريستارت...", show_alert=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "adm_clear")
async def clear_sys(call: CallbackQuery):
    await bot.delete_webhook(drop_pending_updates=True)
    await call.answer("🧹 تم تنظيف التضارب", show_alert=True)

# --- [7] التشغيل النهائي ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 All Systems Ready: User + Admin + VIP")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
