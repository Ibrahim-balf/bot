import os, sys, asyncio, psycopg2
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- [1] Flask ---
app = Flask('')
@app.route('/')
def home(): return "Factory System: Active"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- [2] الإعدادات ---
TOKEN = "6759608260:AAEGMVykzcy1YJ93T362f1T6P3HxVKRrVzk"
ADMIN_ID = 6556184974
DATABASE_URL = "postgresql://bot_factory_db_l19m_user:mX3DiuVVjL17eaUHOTZaJntNfexwP13v@dpg-d57p2hu3jp1c73b3op5g-a/bot_factory_db_l19m"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MyStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_vip_id = State()

def get_db_connection(): return psycopg2.connect(DATABASE_URL)

# --- [3] نظام التشغيل الفوري للبوتات الفرعية ---
async def run_sub_bot(token, owner_id, is_vip):
    try:
        sub_bot = Bot(token=token)
        sub_dp = Dispatcher()
        await sub_bot.delete_webhook(drop_pending_updates=True)
        
        @sub_dp.message(Command("start"))
        async def sub_start(m: Message):
            msg = "👋 أهلاً بك في بوت التواصل."
            if not is_vip: msg += "\n\n— صنع بواسطة مصنع البوتات —"
            await m.answer(msg)

        @sub_dp.message()
        async def sub_handler(m: Message):
            if m.from_user.id != owner_id: await m.forward(owner_id)
            elif m.reply_to_message and m.reply_to_message.forward_from:
                await m.copy_to(m.reply_to_message.forward_from.id)
        
        print(f"✅ Bot {token[:10]}... is now LIVE for user {owner_id}")
        await sub_dp.start_polling(sub_bot)
    except: pass

# --- [4] لوحة المطور والـ VIP ---
@dp.callback_query(F.data == "adm_vip_add")
async def vip_req(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🌟 أرسل ID المستخدم لمنحه صلاحيات VIP وميزات الإذاعة وإزالة الحقوق:")
    await state.set_state(MyStates.waiting_for_vip_id)

@dp.message(MyStates.waiting_for_vip_id)
async def vip_save(message: Message, state: FSMContext):
    target_id = message.text.strip()
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE sub_bots SET is_vip = TRUE WHERE owner_id = %s', (target_id,))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"✅ تم تفعيل ميزات VIP للمستخدم {target_id}.\nالميزات: (إزالة الحقوق + إذاعة خاصة).")
    await state.clear()

# --- [5] صنع البوت وتشغيله فوراً ---
@dp.callback_query(F.data == "user_create")
async def create_btn(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🚀 أرسل توكن بوتك الآن لتشغيله فوراً:")
    await state.set_state(MyStates.waiting_for_token)

@dp.message(MyStates.waiting_for_token)
async def process_new_bot(message: Message, state: FSMContext):
    token = message.text.strip()
    uid = message.from_user.id
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('INSERT INTO sub_bots (owner_id, token, is_vip) VALUES (%s, %s, FALSE)', (uid, token))
        conn.commit(); cur.close(); conn.close()
        
        await message.answer("🚀 تم تشغيل بوتك بنجاح! جرب إرسال /start في بوتك الآن.")
        # تشغيل البوت في الخلفية فوراً
        asyncio.create_task(run_sub_bot(token, uid, False))
        await state.clear()
    except:
        await message.answer("⚠️ حدث خطأ أو البوت مسجل مسبقاً.")

# --- [6] التشغيل الأساسي للمصنع ---
@dp.message(Command("start"))
async def start_main(message: Message):
    # دالة لجلب الكيبورد الذكي
    await message.answer("🤖 **مصنع البوتات السيادي**", reply_markup=get_keyboard_logic(message.from_user.id))

def get_keyboard_logic(uid):
    btns = [[InlineKeyboardButton(text="➕ صنع بوت جديد", callback_data="user_create")]]
    if uid == ADMIN_ID: btns.append([InlineKeyboardButton(text="🛠 لوحة المطور", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

async def on_startup():
    # تشغيل كل البوتات المخزنة عند بداية تشغيل السيرفر
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT token, owner_id, is_vip FROM sub_bots')
    bots = cur.fetchall(); cur.close(); conn.close()
    for t, o, v in bots: asyncio.create_task(run_sub_bot(t, o, v))

async def main():
    await on_startup()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
