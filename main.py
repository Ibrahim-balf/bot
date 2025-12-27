import os, sys, asyncio, psycopg2
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# --- إعدادات أساسية ---
# تأكد من وضع التوكن الجديد هنا أو في إعدادات ريندر
TOKEN = "6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- لوحة المطور (الأدمن) ---
def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ريستارت السيرفر", callback_data="reboot_all")],
        [InlineKeyboardButton(text="🧹 تنظيف التضارب", callback_data="fix_conflict")],
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="get_stats")]
    ])

# --- لوحة المستخدم (صاحب البوت) ---
def get_user_panel(has_bot):
    buttons = []
    if has_bot:
        buttons.append([InlineKeyboardButton(text="📝 تغيير الترحيب", callback_data="edit_welcome")])
        buttons.append([InlineKeyboardButton(text="📢 إذاعة للمستخدمين", callback_data="user_broadcast")])
        buttons.append([InlineKeyboardButton(text="🗑 حذف بوطي", callback_data="del_my_bot")])
    else:
        buttons.append([InlineKeyboardButton(text="➕ صنع بوت تواصل", callback_data="create_new_bot")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- المعالجات الرئيسية ---

@dp.message(Command("start"))
async def start_handler(message: Message):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
    has_bot = cur.fetchone()
    cur.close(); conn.close()

    text = "🤖 **مرحباً بك في المصنع الذكي**\n"
    if uid == ADMIN_ID:
        text += "\n🛠 أنت المطور، استخدم /admin للتحكم."
    
    await message.answer(text, reply_markup=get_user_panel(has_bot), parse_mode="Markdown")

@dp.message(Command("admin"))
async def admin_handler(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 لوحة التحكم السيادية:", reply_markup=get_admin_kb())

# --- أفعال الأزرار (Actions) ---

@dp.callback_query(F.data == "reboot_all")
async def reboot_action(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("🔄 جاري إعادة تشغيل النظام بالكامل...")
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "fix_conflict")
async def fix_action(call: CallbackQuery):
    await bot.delete_webhook(drop_pending_updates=True)
    await call.answer("🧹 تم تنظيف الجلسات وإسقاط الرسائل القديمة!", show_alert=True)

@dp.callback_query(F.data == "edit_welcome")
async def edit_welcome_action(call: CallbackQuery):
    await call.message.answer("📝 أرسل الآن نص الترحيب الجديد لبوتك:")
    # هنا تضع حالة الـ FSM لاستقبال النص كما فعلنا سابقاً

# --- التشغيل النهائي المضمون ---
async def main():
    try:
        # هذه الخطوة ستمسح أي تضارب (Conflict) وتتأكد من التوكن
        await bot.delete_webhook(drop_pending_updates=True)
        print("🚀 البوت انطلق بنجاح!")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"❌ خطأ حرج: {e}")

if __name__ == "__main__":
    asyncio.run(main())
