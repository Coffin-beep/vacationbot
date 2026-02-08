import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Настраиваем логирование, чтобы видеть ошибки в консоли OMV
logging.basicConfig(level=logging.INFO)

# Функция для создания главного меню
def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📅 Подать заявку на отпуск"))
    builder.row(
        types.KeyboardButton(text="📊 Мои отпуска"),
        types.KeyboardButton(text="❓ Помощь")
    )
    return builder.as_markup(resize_keyboard=True)

# Обработка команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Тот самый текст, который мы утвердили
    await message.answer(
        f"Привет, коллега из \"Ньютошки\"! 👋\n"
        f"Я твой автоматический помощник для планирования отдыха. "
        f"Готов подобрать лучшие даты?",
        reply_markup=main_menu_kb()
    )

# Запуск бота
async def main():
    print("Бот Ньютошка запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")