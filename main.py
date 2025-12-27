import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# --- [1] Flask لضمان استقرار السيرفر ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Active"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات (استخدم التوكن الشغال حالياً) ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- [3] معالجات الأزرار (تأكد من مطابقة الـ callback_data) ---

@dp.message(Command("start"))
async def start_cmd(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 لوحة المطور", callback_data="admin_panel")],
        [InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="create_bot")]
    ])
    await message.answer("🤖 أهلاً بك في مصنع البوتات.\nالآن الأزرار ستعمل فوراً، اختر:", reply_markup=kb)

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if message.from_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 ريستارت السيرفر", callback_data="reboot_now")],
            [InlineKeyboardButton(text="🧹 تنظيف التضارب", callback_data="fix_conflict")]
        ])
        await message.answer("🛠 لوحة تحكم المطور السيادية:", reply_markup=kb)

# --- تفعيل استجابة الأزرار ---

@dp.callback_query(F.data == "admin_panel")
async def handle_admin_btn(call: CallbackQuery):
    # إرسال إشعار لتلجرام بأن الطلب تم استلامه (يحل مشكلة عدم الاستجابة)
    await call.answer() 
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ريستارت السيرفر", callback_data="reboot_now")],
        [InlineKeyboardButton(text="🧹 تنظيف التضارب", callback_data="fix_conflict")]
    ])
    await call.message.edit_text("🛠 لوحة التحكم:", reply_markup=kb)

@dp.callback_query(F.data == "reboot_now")
async def handle_reboot(call: CallbackQuery):
    await call.answer("🔄 جاري إعادة التشغيل...", show_alert=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "fix_conflict")
async def handle_fix(call: CallbackQuery):
    await bot.delete_webhook(drop_pending_updates=True)
    await call.answer("🧹 تم تنظيف التضارب بنجاح!", show_alert=True)

@dp.callback_query(F.data == "create_bot")
async def handle_create(call: CallbackQuery):
    await call.answer()
    await call.message.answer("🚀 قريباً: سيطلب منك البوت التوكن هنا.")

# --- [4] التشغيل ---
async def start_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ System is Active and Responding to buttons!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(start_bot())
