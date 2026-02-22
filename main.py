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
    waiting_for_feedback = State()  # Пользователь пишет вопрос
    waiting_for_answer = State()  # Админ пишет ответ


# --- КЛАВИАТУРЫ ---
def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📅 Подать заявку на отпуск"))
    builder.row(
        types.KeyboardButton(text="📊 Мои отпуска"),
        types.KeyboardButton(text="❓ Помощь")
    )
    return builder.as_markup(resize_keyboard=True)


def cancel_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


# --- БЛОК ПОЛЬЗОВАТЕЛЯ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()  # Сбрасываем любые состояния при старте
    await message.answer(
        f"Привет, коллега из «Ньютошки»! 👋\nЯ твой помощник. Чем могу помочь?",
        reply_markup=main_menu_kb()
    )


@dp.message(F.text == "❓ Помощь")
async def help_command(message: types.Message, state: FSMContext):
    await message.answer(
        "Напишите ваш вопрос ниже, и администратор ответит вам в ближайшее время.",
        reply_markup=cancel_kb()
    )
    await state.set_state(Feedback.waiting_for_feedback)


@dp.message(F.text == "❌ Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_kb())


@dp.message(Feedback.waiting_for_feedback, F.text)
async def forward_to_admin(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"📩 **Новый вопрос!**\n"
            f"От: {message.from_user.full_name} (ID: `{message.from_user.id}`)\n\n"
            f"Текст: {message.text}\n\n"
            f"Для ответа нажмите: /reply_{message.from_user.id}"
        )
        await message.answer("Ваш вопрос отправлен! Ожидайте ответа. ✨", reply_markup=main_menu_kb())
    else:
        await message.answer("Вы администратор.", reply_markup=main_menu_kb())
    await state.clear()


# --- БЛОК АДМИНИСТРАТОРА ---

@dp.message(F.text.startswith("/reply_"))
async def start_reply(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        target_user_id = message.text.replace("/reply_", "").strip()
        if target_user_id.isdigit():
            await state.update_data(reply_to_user_id=target_user_id)
            await message.answer(
                f"Введите текст ответа для пользователя {target_user_id}:",
                reply_markup=cancel_kb()
            )
            await state.set_state(Feedback.waiting_for_answer)
        else:
            await message.answer("Неверный формат ID.")
    else:
        await message.answer("Доступ запрещен.")


@dp.message(Feedback.waiting_for_answer, F.text)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    # Если админ нажал отмену
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
                f"✉️ **Ответ от администрации «Ньютошки»:**\n\n{message.text}"
            )
            await message.answer("✅ Ответ отправлен!", reply_markup=main_menu_kb())
            logging.info(f"Ответ отправлен пользователю {target_user_id}")
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