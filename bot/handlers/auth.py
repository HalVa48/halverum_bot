from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.keyboards import get_main_menu_keyboard
from database.database import async_session_maker
from database.models import User

router = Router()


class AuthState(StatesGroup):
    waiting_password = State()


@router.message(AuthState.waiting_password)
async def process_password(message: Message, state: FSMContext):
    """Handle password input"""
    password = message.text.strip()

    try:
        await message.delete()
    except Exception:
        pass

    if password == config.ACCESS_PASSWORD:
        async with async_session_maker() as session:
            from sqlalchemy import select

            stmt = select(User).where(User.telegram_id == message.from_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                user = User(telegram_id=message.from_user.id, is_authorized=True)
                session.add(user)
            else:
                user.is_authorized = True

            await session.commit()

        await state.clear()

        last_message = await state.get_data()
        last_msg_id = last_message.get("last_message_id")

        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="✅ <b>Доступ разрешен!</b>\n\nДобро пожаловать в VPN сервис!",
                    parse_mode="HTML",
                )
                await message.bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    reply_markup=get_main_menu_keyboard(),
                )
            except Exception:
                await message.answer(
                    "✅ <b>Доступ разрешен!</b>\n\nДобро пожаловать в VPN сервис!",
                    parse_mode="HTML",
                    reply_markup=get_main_menu_keyboard(),
                )
        else:
            await message.answer(
                "✅ <b>Доступ разрешен!</b>\n\nДобро пожаловать в VPN сервис!",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(),
            )
    else:
        last_message = await state.get_data()
        last_msg_id = last_message.get("last_message_id")

        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ <b>Неверный пароль!</b>\n\nПопробуйте еще раз:",
                    parse_mode="HTML",
                )
            except Exception:
                pass


@router.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Handle cancel button"""
    await state.clear()
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(),
    )
