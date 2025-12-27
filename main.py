import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- [1] Flask لضمان استقرار السيرفر في Render ---
app = Flask('')
@app.route('/')
def home(): return "Admin System: Online"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات الأساسية ---
# تأكد أن هذا هو التوكن الصحيح من BotFather
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
# تأكد أن هذا هو الـ ID الخاص بك
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_bc = State()
    waiting_for_vip = State()

def get_conn(): return psycopg2.connect(DATABASE_URL)

# --- [3] لوحة التحكم السيادية ---
def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="st_stats"), InlineKeyboardButton(text="📢 إذاعة", callback_data="st_bc")],
        [InlineKeyboardButton(text="🌟 تفعيل VIP", callback_data="st_vip")],
        [InlineKeyboardButton(text="🔄 ريستارت", callback_data="st_reboot"), InlineKeyboardButton(text="🧹 تنظيف", callback_data="st_clear")]
    ])

# --- [4] المعالجات (Handlers) ---

# أمر فحص الـ ID والاستجابة
@dp.message(Command("start"))
async def start_check(message: Message):
    uid = message.from_user.id
    if uid == ADMIN_ID:
        await message.answer(f"✅ أهلاً بك يا مطور (ID: {uid})\nلوحة التحكم جاهزة، أرسل /admin لفتحها.")
    else:
        await message.answer(f"👤 مرحباً بك مستخدم جديد.\nالـ ID الخاص بك هو: `{uid}`\n(أرسل هذا الرقم للمطور لتفعيل صلاحياتك).", parse_mode="Markdown")

# فتح اللوحة
@dp.message(Command("admin"))
async def open_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 **لوحة التحكم السيادية**", reply_markup=get_admin_kb())
    else:
        await message.answer("⚠️ عذراً، هذا الأمر مخصص للمطور فقط.")

# معالجة الأزرار
@dp.callback_query(F.data == "st_stats")
async def show_stats(call: CallbackQuery):
    conn = get_conn(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM sub_bots')
    count = cur.fetchone()[0]
    cur.close(); conn.close()
    await call.message.answer(f"📊 عدد البوتات في القاعدة: {count}")
    await call.answer()

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
    # التأكد من قاعدة البيانات
    conn = get_conn(); cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS sub_bots (owner_id BIGINT PRIMARY KEY, token TEXT, is_vip BOOLEAN DEFAULT FALSE)')
    conn.commit(); cur.close(); conn.close()
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Admin Controller is LIVE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
