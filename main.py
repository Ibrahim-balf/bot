import os
from fastapi import FastAPI, Request
from aiogram import Bot
from databases import Database

# إعداد قاعدة البيانات (Render يعطيك هذا الرابط)
DATABASE_URL = os.getenv("DATABASE_URL")
database = Database(DATABASE_URL)

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()
    # إنشاء الجدول إذا لم يكن موجوداً
    query = """
    CREATE TABLE IF NOT EXISTS bots (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        token TEXT UNIQUE
    )
    """
    await database.execute(query)

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# 1. مسار لإضافة بوت جديد للمصنع
@app.post("/add_bot")
async def add_bot(user_id: int, token: str):
    query = "INSERT INTO bots(user_id, token) VALUES (:user_id, :token)"
    try:
        await database.execute(query=query, values={"user_id": user_id, "token": token})
        
        # تفعيل الـ Webhook لهذا البوت فوراً
        bot = Bot(token=token)
        webhook_path = postgresql://bots_i7s8_user:75IY39cyu03rdVLpzxz5d3fSqXucKEe5@dpg-d5809n15pdvs738gs46g-a/bots_i7s8{token}"
        await bot.set_webhook(webhook_path)
        
        return {"status": "success", "message": "Bot added and activated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 2. المسار الرئيسي لاستقبال رسائل كل البوتات
@app.post("/webhook/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request):
    data = await request.json()
    
    # التأكد أن التوكن موجود عندنا في القاعدة (للأمان)
    query = "SELECT * FROM bots WHERE token = :token"
    bot_record = await database.fetch_one(query=query, values={"token": bot_token})
    
    if bot_record:
        bot = Bot(token=bot_token)
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
            # هنا تضع منطق الرد الخاص ببوتاتك
            await bot.send_message(chat_id, f"رد المصنع الآلي: وصلني نصك '{text}'")
            
    return {"ok": True}
