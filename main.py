import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# 1. ضع التوكن الخاص بك هنا
API_TOKEN = '6759608260:AAE5BrVUBRJv2xVNwBNcXfx75-QQUPTZ5Ms'

# 2. ضع الـ ID الخاص بك (الذي حصلت عليه من الخطوة 1)
ADMIN_ID = 6556184974  # استبدل هذا الرقم برقم الـ ID الخاص بك

# إعداد البوت
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- لوحة التحكم (الأزرار الشفافة) ---
def admin_menu():
    buttons = [
        [InlineKeyboardButton(text="📊 عدد المستخدمين", callback_data="show_users")],
        [InlineKeyboardButton(text="📢 إرسال إذاعة (Broadcast)", callback_data="send_msg")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- الأوامر ---

# أمر البداية للمستخدمين العاديين
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(f"مرحباً {message.from_user.first_name} في مصنع بوتات التواصل!\nقريباً ستتمكن من صنع بوتك الخاص.")

# أمر الأدمن (يفتح لك اللوحة)
@dp.message(Command("admin"))
async def open_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 أهلاً بك يا مطور.. اختر من القائمة:", reply_markup=admin_menu())
    else:
        await message.answer("❌ هذا الأمر خاص بالأدمن فقط.")

# معالجة ضغط الأزرار في لوحة الأدمن
@dp.callback_query()
async def process_admin_buttons(callback: types.CallbackQuery):
    if callback.data == "show_users":
        # مؤقتاً سنضع رقماً وهمياً حتى نربط قاعدة البيانات
        await callback.message.answer("📊 عدد المستخدمين حالياً: 1 (أنت فقط)")
    
    if callback.data == "send_msg":
        await callback.message.answer("📝 أرسل الرسالة التي تريد توزيعها للجميع:")
    
    await callback.answer() # لإخفاء علامة التحميل من الزر

# تشغيل البوت
async def main():
    print("البوت يعمل الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
