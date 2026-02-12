import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

# Настройка логирования для отображения в Docker logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
# Приводим к int сразу, чтобы избежать ошибок сравнения
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except (TypeError, ValueError):
    logging.error("ADMIN_ID не найден или имеет неверный формат в .env!")
    ADMIN_ID = 0

bot = Bot(token=TOKEN)
dp = Dispatcher()


# --- СОСТОЯНИЯ (FSM) ---
class Feedback(StatesGroup):
    waiting_for_feedback = State()  # Ожидание вопроса от пользователя
    waiting_for_answer = State()  # Ожидание текста ответа от админа


# --- КЛАВИАТУРЫ ---
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
        f"Привет, коллега из «Ньютошки»! 👋\n"
        f"Я твой автоматический помощник для планирования отдыха.\n"
        f"Чем могу помочь?",
        reply_markup=main_menu_kb()
    )


@dp.message(F.text == "❓ Помощь")
async def help_command(message: types.Message, state: FSMContext):
    await message.answer(
        "Напишите ваш вопрос ниже, и администратор ответит вам в ближайшее время."
    )
    # Включаем режим ожидания вопроса
    await state.set_state(Feedback.waiting_for_feedback)


@dp.message(Feedback.waiting_for_feedback)
async def forward_to_admin(message: types.Message, state: FSMContext):
    # Если пишет не админ — пересылаем админу
    if message.from_user.id != ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"📩 **Новый вопрос!**\n"
            f"От: {message.from_user.full_name} (ID: `{message.from_user.id}`)\n\n"
            f"Текст: {message.text}\n\n"
            f"Чтобы ответить, введите: /reply_{message.from_user.id}"
        )
        await message.answer("Ваш вопрос отправлен администрации. Ожидайте ответа! ✨")
    else:
        await message.answer("Вы администратор. Сообщение не переслано самому себе.")

    # Сбрасываем состояние после отправки
    await state.clear()


# --- БЛОК АДМИНИСТРАТОРА ---

# Ловим команду ответа (регулярное выражение для извлечения ID)
@dp.message(F.text.regexp(r"/reply_(\d+)"))
async def start_reply(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        parts = message.text.split("_")
        if len(parts) > 1:
            target_user_id = parts[1]
            await state.update_data(reply_to_user_id=target_user_id)
            await message.answer(f"Пишите ответ для пользователя {target_user_id}:")
            await state.set_state(Feedback.waiting_for_answer)
    else:
        await message.answer("У вас нет прав администратора.")


# Ловим сам текст ответа от админа
@dp.message(Feedback.waiting_for_answer)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("reply_to_user_id")

    try:
        await bot.send_message(
            target_user_id,
            f"✉️ **Ответ от администрации «Ньютошки»:**\n\n{message.text}"
        )
        await message.answer("✅ Ответ успешно отправлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке пользователю: {e}")
        logging.error(f"Error sending reply: {e}")

    await state.clear()


# --- ЗАПУСК ---

async def main():
    logging.info("--- БОТ «НЬЮТОШКА» ЗАПУСКАЕТСЯ ---")
    # Удаляем старые сообщения, пришедшие пока бот был офлайн
    await bot.delete_webhook(drop_pending_updates=True)
    # Запуск polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен вручную.")
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске: {e}")