import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except (TypeError, ValueError):
    logging.error("ADMIN_ID не найден или имеет неверный формат в .env!")
    ADMIN_ID = 0

bot = Bot(token=TOKEN)
dp = Dispatcher()


# --- СОСТОЯНИЯ (FSM) ---
class Feedback(StatesGroup):
    waiting_for_answer = State()  # Админ пишет ответ


# --- КЛАВИАТУРЫ ---
def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📅 Подать заявку на отпуск"))
    builder.row(types.KeyboardButton(text="📊 Мои отпуска"))
    return builder.as_markup(resize_keyboard=True)


def cancel_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


# --- ОСНОВНОЙ БЛОК ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()  # Сбрасываем любые состояния при старте
    await message.answer(
        f"Привет, коллега из «Ньютошки»! 👋\nЯ твой помощник по планированию отпусков.",
        reply_markup=main_menu_kb()
    )


@dp.message(F.text == "❌ Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_kb())


# --- БЛОК АДМИНИСТРАТОРА (Оставляем для возможности отвечать по ID) ---

@dp.message(F.text.startswith("/reply_"))
async def start_reply(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        target_user_id = message.text.replace("/reply_", "").strip()
        if target_user_id.isdigit():
            await state.update_data(reply_to_user_id=target_user_id)
            await message.answer(
                f"Введите текст сообщения для пользователя {target_user_id}:",
                reply_markup=cancel_kb()
            )
            await state.set_state(Feedback.waiting_for_answer)
        else:
            await message.answer("Неверный формат ID.")
    else:
        await message.answer("Доступ запрещен.")


@dp.message(Feedback.waiting_for_answer, F.text)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отправка отменена.", reply_markup=main_menu_kb())
        return

    data = await state.get_data()
    target_user_id = data.get("reply_to_user_id")

    if target_user_id:
        try:
            await bot.send_message(
                int(target_user_id),
                f"✉️ **Сообщение от администрации «Ньютошки»:**\n\n{message.text}"
            )
            await message.answer("✅ Сообщение отправлено!", reply_markup=main_menu_kb())
            logging.info(f"Сообщение отправлено пользователю {target_user_id}")
        except Exception as e:
            await message.answer(f"❌ Ошибка отправки: {e}", reply_markup=main_menu_kb())

    await state.clear()


# --- ЗАПУСК ---

async def main():
    logging.info("--- БОТ ЗАПУЩЕН ---")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass