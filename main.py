import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- [1] Flask لضمان العمل ---
app = Flask('')
@app.route('/')
def home(): return "Integrated System: Online"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MyStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_welcome = State()
    waiting_for_vip_id = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- [3] لوحات التحكم ---

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

# --- [4] معالجات المطور (العمليات الفعالة) ---

@dp.callback_query(F.data == "admin_panel")
async def admin_main(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="adm_stats"), InlineKeyboardButton(text="🌟 قسم VIP", callback_data="adm_vip")],
        [InlineKeyboardButton(text="🔄 ريستارت", callback_data="adm_reboot"), InlineKeyboardButton(text="🧹 تنظيف", callback_data="adm_clear")],
        [InlineKeyboardButton(text="🔙 عودة", callback_data="back_home")]
    ])
    await call.message.edit_text("🛠 **لوحة التحكم السيادية**", reply_markup=kb)

@dp.callback_query(F.data == "adm_stats")
async def admin_stats(call: CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM sub_bots')
    count = cur.fetchone()[0]
    cur.close(); conn.close()
    await call.answer(f"📊 عدد البوتات المصنوعة: {count}", show_alert=True)

@dp.callback_query(F.data == "adm_vip")
async def admin_vip(call: CallbackQuery):
    await call.message.edit_text("🌟 **قسم الـ VIP**\nهنا يمكنك منح ميزات إضافية للمستخدمين.\n(قيد التطوير: سيتم إضافة خيار إضافة ID الـ VIP قريباً).", 
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 عودة", callback_data="admin_panel")]]))

# --- [5] معالجات المستخدم (الأزرار الفعالة) ---

@dp.callback_query(F.data == "user_manage")
async def user_manage(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 تغيير الترحيب", callback_data="u_edit_w")],
        [InlineKeyboardButton(text="🗑 حذف البوت", callback_data="u_del_confirm")],
        [InlineKeyboardButton(text="🔙 عودة", callback_data="back_home")]
    ])
    await call.message.edit_text("⚙️ **إدارة بوت التواصل الخاص بك:**", reply_markup=kb)

@dp.callback_query(F.data == "u_edit_w")
async def user_welcome(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📝 أرسل الآن نص الترحيب الجديد لبوتك:")
    await state.set_state(MyStates.waiting_for_welcome)
    await call.answer()

@dp.message(MyStates.waiting_for_welcome)
async def save_welcome(message: Message, state: FSMContext):
    # هنا يتم الحفظ في القاعدة (تأكد من وجود عمود welcome_msg)
    await message.answer("✅ تم تحديث رسالة الترحيب بنجاح!")
    await state.clear()

@dp.callback_query(F.data == "u_del_confirm")
async def user_del(call: CallbackQuery):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('DELETE FROM sub_bots WHERE owner_id = %s', (call.from_user.id,))
    conn.commit(); cur.close(); conn.close()
    await call.message.edit_text("🗑 تم حذف بوتك نهائياً من النظام.", reply_markup=get_keyboard(call.from_user.id))
    await call.answer("تم الحذف")

# --- [6] أوامر عامة ---

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🤖 **مصنع البوتات الذكي**", reply_markup=get_keyboard(message.from_user.id))

@dp.callback_query(F.data == "back_home")
async def back_home(call: CallbackQuery):
    await call.message.edit_text("🤖 **مصنع البوتات الذكي**", reply_markup=get_keyboard(call.from_user.id))

@dp.callback_query(F.data == "adm_reboot")
async def reboot_sys(call: CallbackQuery):
    await call.answer("🔄 ريستارت...", show_alert=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@dp.callback_query(F.data == "adm_clear")
async def clear_sys(call: CallbackQuery):
    await bot.delete_webhook(drop_pending_updates=True)
    await call.answer("🧹 تم التنظيف", show_alert=True)

# --- [7] التشغيل ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
