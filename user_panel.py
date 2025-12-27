import os, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- 1. إعدادات البيئة ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# حالات المستخدم
class UserStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_welcome_msg = State()

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- 2. لوحات التحكم للمستخدم ---

def get_user_main_kb(has_bot):
    btns = []
    if has_bot:
        btns.append([InlineKeyboardButton(text="📝 تعديل رسالة الترحيب", callback_data="edit_welcome")])
        btns.append([InlineKeyboardButton(text="🗑 حذف بوطي نهائياً", callback_data="delete_bot")])
    else:
        btns.append([InlineKeyboardButton(text="➕ صنع بوت تواصل جديد", callback_data="create_new")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

# --- 3. المعالجات (Handlers) ---

@dp.message(Command("start"))
async def user_start(message: Message):
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token FROM sub_bots WHERE owner_id = %s', (uid,))
    res = cur.fetchone(); cur.close(); conn.close()
    
    msg = "👋 أهلاً بك في خدمة صنع بوتات التواصل.\n\n"
    if res:
        msg += "✅ لديك بوت فعال حالياً، يمكنك إدارته من الأسفل:"
    else:
        msg += "❌ ليس لديك بوت حالياً، اضغط على الزر للبدء:"
        
    await message.answer(msg, reply_markup=get_user_main_kb(res is not None))

# --- مسار صنع بوت جديد ---
@dp.callback_query(F.data == "create_new")
async def start_creation(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🚀 أرسل الآن **توكن البوت** الذي حصلت عليه من @BotFather:")
    await state.set_state(UserStates.waiting_for_token)
    await call.answer()

@dp.message(UserStates.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    token = message.text.strip()
    if ":" not in token:
        return await message.answer("⚠️ التوكن غير صحيح، تأكد من إرساله بشكل كامل.")
    
    uid = message.from_user.id
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('INSERT INTO sub_bots (owner_id, token) VALUES (%s, %s)', (uid, token))
        conn.commit(); cur.close(); conn.close()
        await message.answer("✅ تم ربط بوتك بنجاح! سيتم تفعيله فوراً.")
        await state.clear()
    except Exception as e:
        await message.answer("⚠️ حدث خطأ (ربما لديك بوت مسجل بالفعل).")

# --- مسار تعديل الترحيب ---
@dp.callback_query(F.data == "edit_welcome")
async def start_welcome_edit(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📝 أرسل نص الترحيب الجديد الذي سيظهر لمستخدمي بوتك:")
    await state.set_state(UserStates.waiting_for_welcome_msg)
    await call.answer()

@dp.message(UserStates.waiting_for_welcome_msg)
async def save_welcome(message: Message, state: FSMContext):
    new_msg = message.text
    uid = message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET welcome_msg = %s WHERE owner_id = %s', (new_msg, uid))
    conn.commit(); cur.close(); conn.close()
    await message.answer("✅ تم تحديث رسالة الترحيب بنجاح.")
    await state.clear()

# --- حذف البوت ---
@dp.callback_query(F.data == "delete_bot")
async def delete_confirm(call: CallbackQuery):
    uid = call.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('DELETE FROM sub_bots WHERE owner_id = %s', (uid,))
    conn.commit(); cur.close(); conn.close()
    await call.message.edit_text("🗑 تم حذف بيانات بوتك من النظام.")
    await call.answer()

# --- 4. تشغيل السيرفر ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("👤 User Panel is LIVE")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
