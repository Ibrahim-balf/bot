import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramUnauthorizedError

# --- [1] إعدادات Flask لمنع Render من إغلاق السيرفر ---
app = Flask('')
@app.route('/')
def home(): return "Bot Factory is running..."
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات الأساسية ---
# ضع التوكن الجديد هنا يدوياً للتجربة
TOKEN = "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- [3] لوحات التحكم والأزرار الفعالة ---
def get_main_kb(uid):
    buttons = []
    # لوحة المطور تظهر فقط لك
    if uid == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="🛠 لوحة المطور", callback_data="admin_panel")])
    
    # هنا نتأكد إذا كان لديه بوت مسبقاً
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
        if cur.fetchone():
            buttons.append([InlineKeyboardButton(text="🎮 إدارة بوطي", callback_data="manage_my_bot")])
        else:
            buttons.append([InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="create_bot")])
        cur.close(); conn.close()
    except:
        buttons.append([InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="create_bot")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("🤖 أهلاً بك في مصنع البوتات.\nالآن الأزرار فعالة تماماً، اختر ما تريد:", 
                         reply_markup=get_main_kb(message.from_user.id))

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ريستارت السيرفر", callback_data="reboot_now")],
        [InlineKeyboardButton(text="🧹 تنظيف التضارب", callback_data="fix_conflict")]
    ])
    await call.message.edit_text("🛠 لوحة تحكم المطور السيادية:", reply_markup=kb)

@dp.callback_query(F.data == "reboot_now")
async def reboot_action(call: CallbackQuery):
    await call.message.edit_text("🔄 جاري إعادة التشغيل...")
    os.execl(sys.executable, sys.executable, *sys.argv)

# --- [4] دالة التشغيل الآمنة ---
async def start_bot():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Telegram Connection Established!")
        await dp.start_polling(bot, skip_updates=True)
    except TelegramUnauthorizedError:
        print("❌ التوكن غلط! يرجى تغييره في الكود.")
    except Exception as e:
        print(f"⚠️ خطأ آخر: {e}")

if __name__ == "__main__":
    # تشغيل Flask في الخلفية
    Thread(target=run_web, daemon=True).start()
    # تشغيل البوت
    asyncio.run(start_bot())
