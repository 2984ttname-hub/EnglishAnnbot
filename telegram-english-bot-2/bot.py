import os
import logging
from aiogram import Bot, Dispatcher, types
import asyncio
import openai

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
openai.api_key = OPENAI_API_KEY

# Обробка текстових повідомлень
@dp.message()
async def handle_message(message: types.Message):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        await message.answer("⚠️ Виникла помилка: " + str(e))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
