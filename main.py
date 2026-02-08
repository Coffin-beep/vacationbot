import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

# Включаем логирование, чтобы видеть всё в docker logs
logging.basicConfig(level=logging.INFO)

load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID"))
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Состояния для админки
class Feedback(StatesGroup):
    waiting_for_answer = State()

# Клавиатура главного меню
def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📅 Подать заявку на отпуск"))
    builder.row(
        types.KeyboardButton(text="📊 Мои отпуска"),
        types.KeyboardButton(text="❓ Помощь")
    )
    return builder.as_markup(resize_keyboard=True)

# --- БЛОК ПОЛЬЗОВАТЕЛЯ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет, коллега из \"Ньютошки\"! 👋\nЯ твой автоматический помощник.",
        reply_markup=main_menu_kb()
    )

@dp.message(F.text == "❓ Помощь")
async def help_command(message: types.Message):
    await message.answer("Напишите ваш вопрос ниже, и администратор «Ньютошки» ответит вам в ближайшее время.")

# Ловим любой текст, который не команда (вопрос админу)
@dp.message(F.text, ~F.text.startswith("/"))
async def forward_to_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"📩 **Новый вопрос!**\nОт: {message.from_user.full_name} (ID: `{message.from_user.id}`)\n\n"
            f"Текст: {message.text}\n\n"
            f"Чтобы ответить, введите команду: /reply_{message.from_user.id}"
        )
        await message.answer("Ваш вопрос отправлен администрации. Ожидайте ответа! ✨")

# --- БЛОК АДМИНИСТРАТОРА ---

@dp.message(F.text.regexp(r"/reply_(\d+)"))
async def start_reply(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        parts = message.text.split("_")
        if len(parts) > 1:
            user_id = parts[1]
            await state.update_data(reply_to_user_id=user_id)
            await message.answer(f"Пишите ответ для пользователя {user_id}:")
            await state.set_state(Feedback.waiting_for_answer)

@dp.message(Feedback.waiting_for_answer)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("reply_to_user_id")

    try:
        await bot.send_message(user_id, f"✉️ **Ответ от администрации «Ньютошки»:**\n\n{message.text}")
        await message.answer("✅ Ответ успешно отправлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}")

    await state.clear()

# --- ЗАПУСК ---

async def main():
    logging.info("--- БОТ ЗАПУСКАЕТСЯ ---")
    # Удаляем вебхуки, если они были, и запускаем опрос серверов
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Бот упал с ошибкой: {e}")