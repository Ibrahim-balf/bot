from fastapi import FastAPI, Request
from aiogram import Bot

app = FastAPI()

@app.post("/webhook/{bot_token}")
async def handle_message(bot_token: str, request: Request):
    # 1. استلام الرسالة من تيليجرام
    data = await request.json()
    
    # 2. تجهيز البوت للرد
    bot = Bot(token=bot_token)
    
    # 3. معرفة رقم الشخص المرسل ونص رسالته
    chat_id = data['message']['chat']['id']
    user_text = data['message'].get('text', '')

    # 4. الرد عليه
    await bot.send_message(chat_id, f"أهلاً بك! لقد استلمت رسالتك: {user_text}")
    
    return {"ok": True}
