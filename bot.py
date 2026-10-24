import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.com")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    button = KeyboardButton(
        text="🎵 Открыть плеер",
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    keyboard = ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)
    await message.answer(
        "Привет! Нажми на кнопку ниже, чтобы открыть музыкальный плеер.",
        reply_markup=keyboard
    )

async def main():
    print("Бот запущен. Иди в Telegram и напиши /start")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())