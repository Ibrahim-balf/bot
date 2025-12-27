import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- [1] إعداد السيرفر لضمان العمل 24 ساعة ---
app = Flask('')
@app.route('/')
def home(): return "Admin Panel: Running"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات الأساسية ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_bc = State()
    waiting_for_vip = State()
    waiting_for_del = State()

def get_conn(): return psycopg2.connect(DATABASE_URL)

# --- [3] لوحة التحكم السيادية ---
def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات العامة", callback_data="st_stats")],
        [InlineKeyboardButton(text="📢 إذاعة (نص)", callback_data="st_bc")],
        [InlineKeyboardButton(text="🌟 منح VIP (بواسطة ID)", callback_data="st_vip")],
        [InlineKeyboardButton(text="🗑 حذف بوت مخالف", callback_data="st_del")],
        [InlineKeyboardButton(text="🔄 ريستارت", callback_data="st_reboot"), InlineKeyboardButton(text="🧹 تنظيف", callback_data="st_clear")]
    ])

# --- [4] معالجات الأوامر (Handlers) ---

@dp.message(Command("admin"))
async def open_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 **مرحباً بك يا مطور في غرفتك الخاصة**\nتحكم في النظام بالكامل من هنا:", reply_markup=get_admin_kb())

# 1. الإحصائيات
@dp.callback_query(F.data == "st_stats")
async def show_stats(call: CallbackQuery):
    conn = get_conn(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM sub_bots')
    b_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM sub_bots WHERE is_vip = TRUE')
    v_count = cur.fetchone()[0]
    cur.close(); conn.close()
    await call.message.answer(f"📊 **إحصائيات المصنع:**\n\n- البوتات الكلية: {b_count}\n- المشتركين VIP: {v_count}")
    await call.answer()

# 2. الإذاعة
@dp.callback_query(F.data == "st_bc")
async def bc_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📢 أرسل نص الإذاعة الآن:")
    await state.set_state(AdminStates.waiting_for_bc)
    await call.answer()

@dp.message(AdminStates.waiting_for_bc)
async def bc_exec(message: Message, state: FSMContext):
    conn = get_conn(); cur = conn.cursor()
    cur.execute('SELECT owner_id FROM sub_bots')
    users = cur.fetchall(); cur.close(); conn.close()
    for user in users:
        try: await bot.send_message(user[0], message.text)
        except: pass
    await message.answer("✅ تم إرسال الإذاعة للجميع.")
    await state.clear()

# 3. تفعيل VIP
@dp.callback_query(F.data == "st_vip")
async def vip_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🌟 أرسل ID المستخدم لتفعيله VIP:")
    await state.set_state(AdminStates.waiting_for_vip)
    await call.answer()

@dp.message(AdminStates.waiting_for_vip)
async def vip_exec(message: Message, state: FSMContext):
    conn = get_conn(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET is_vip = TRUE WHERE owner_id = %s', (message.text.strip(),))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"✅ تم منح VIP للـ ID: {message.text}")
    await state.clear()

# 4. العمليات التقنية (ريستارت وتنظيف)
@dp.callback_query(F.data == "st_reboot")
async def sys_reboot(call: CallbackQuery):
    await call.answer("🔄 جاري إعادة التشغيل...", show_alert=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "st_clear")
async def sys_clear(call: CallbackQuery):
    await bot.delete_webhook(drop_pending_updates=True)
    await call.answer("🧹 تم تنظيف التضارب!", show_alert=True)

# --- [5] التشغيل ---
async def main():
    # تأكد من وجود عمود is_vip لتجنب الخطأ
    conn = get_conn(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT, is_vip BOOLEAN DEFAULT FALSE)')
    try: cur.execute('ALTER TABLE sub_bots ADD COLUMN is_vip BOOLEAN DEFAULT FALSE')
    except: conn.rollback()
    conn.commit(); cur.close(); conn.close()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
