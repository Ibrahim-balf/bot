import os, sys, asyncio, psycopg2
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# --- الإعدادات ---
TOKEN = "6759608260:AAECDG35CuB6l2_uIaJZCnM5inidwGnINkw"
ADMIN_ID = 6556184974  # تأكد أن هذا هو معرفك الصحيح
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- 1. لوحة الأدمن (المطور) ---
def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 إعادة تشغيل السيرفر", callback_data="reboot_sys")],
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="stats_sys")],
        [InlineKeyboardButton(text="🧹 تنظيف التضارب", callback_data="clear_conf")],
        [InlineKeyboardButton(text="🔙 خروج", callback_data="close_panel")]
    ])

# --- 2. لوحة المستخدم (صاحب البوت) ---
def user_keyboard(has_bot):
    buttons = []
    if has_bot:
        buttons.append([InlineKeyboardButton(text="🎮 إدارة بوطي", callback_data="manage_bot")])
        buttons.append([InlineKeyboardButton(text="🗑 حذف البوت", callback_data="del_bot")])
    else:
        buttons.append([InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="create_bot")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- المعالجات (Handlers) ---

@dp.message(Command("start"))
async def start_cmd(message: Message):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
    has_bot = cur.fetchone() is not None
    cur.close(); conn.close()
    
    text = "🤖 أهلاً بك في مصنع البوتات.\n\n"
    if uid == ADMIN_ID:
        text += "🛠 أنت المطور، يمكنك استخدام /admin لفتح لوحة التحكم."
    
    await message.answer(text, reply_markup=user_keyboard(has_bot))

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 **لوحة تحكم المطور السيادية**", reply_markup=admin_keyboard())

# --- تفعيل الأزرار (Actions) ---

@dp.callback_query(F.data == "reboot_sys")
async def action_reboot(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("🔄 جاري إعادة التشغيل الآن...")
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "clear_conf")
async def action_clear(call: CallbackQuery):
    await bot.delete_webhook(drop_pending_updates=True)
    await call.answer("🧹 تم تنظيف التضارب بنجاح!", show_alert=True)

@dp.callback_query(F.data == "stats_sys")
async def action_stats(call: CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM sub_bots'); count = cur.fetchone()[0]
    cur.close(); conn.close()
    await call.answer(f"📊 عدد البوتات المصنوعة: {count}", show_alert=True)

@dp.callback_query(F.data == "close_panel")
async def action_close(call: CallbackQuery):
    await call.message.delete()

# --- التشغيل ---
async def main():
    # تنظيف أي تضارب قديم فور التشغيل
    await bot.delete_webhook(drop_pending_updates=True)
    print("Bot is started and Keyboards are active!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
