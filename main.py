import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- 1. تشغيل ويب لضمان استمرار ريندر ---
app = Flask('')
@app.route('/')
def home(): return "Admin Panel: Online"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- 2. الإعدادات ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- 3. لوحة تحكم المسؤول السيادية ---
def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 إذاعة رسالة للكل", callback_data="bc_all")],
        [InlineKeyboardButton(text="📊 إحصائيات النظام", callback_data="view_stats")],
        [InlineKeyboardButton(text="🔄 ريستارت السيرفر", callback_data="sys_reboot")],
        [InlineKeyboardButton(text="🧹 تنظيف التضارب", callback_data="sys_clear")],
        [InlineKeyboardButton(text="❌ إغلاق اللوحة", callback_data="close_panel")]
    ])

# --- 4. المعالجات (Handlers) ---

@dp.message(Command("admin"))
async def open_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 **مرحباً بك يا مطور في لوحة التحكم السيادية**", reply_markup=admin_kb())

# تنفيذ الإذاعة
@dp.callback_query(F.data == "bc_all")
async def start_bc(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📣 أرسل الآن الرسالة (نص فقط) لإذاعتها لجميع المستخدمين:")
    await state.set_state(AdminStates.waiting_for_broadcast)
    await call.answer()

@dp.message(AdminStates.waiting_for_broadcast)
async def perform_bc(message: Message, state: FSMContext):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT DISTINCT owner_id FROM sub_bots')
    users = cur.fetchall(); cur.close(); conn.close()
    
    success = 0
    for user in users:
        try:
            await bot.send_message(user[0], f"📢 **رسالة من الإدارة:**\n\n{message.text}")
            success += 1
            await asyncio.sleep(0.05) # حماية من الحظر
        except: pass
    
    await message.answer(f"✅ تم الإرسال بنجاح إلى {success} مستخدم.")
    await state.clear()

# الإحصائيات
@dp.callback_query(F.data == "view_stats")
async def show_stats(call: CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM sub_bots')
    bot_count = cur.fetchone()[0]
    cur.close(); conn.close()
    await call.message.answer(f"📊 **إحصائيات حالية:**\n\n- عدد البوتات المشغلة: {bot_count}")
    await call.answer()

# العمليات التقنية
@dp.callback_query(F.data == "sys_reboot")
async def reboot_logic(call: CallbackQuery):
    await call.answer("🔄 جاري إعادة التشغيل...", show_alert=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "sys_clear")
async def clear_logic(call: CallbackQuery):
    await bot.delete_webhook(drop_pending_updates=True)
    await call.answer("🧹 تم تنظيف تضارب الجلسات!", show_alert=True)

@dp.callback_query(F.data == "close_panel")
async def close_logic(call: CallbackQuery):
    await call.message.delete()

# --- 5. تشغيل ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🛡️ Admin Controller is LIVE")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
