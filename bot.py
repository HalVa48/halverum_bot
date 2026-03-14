import asyncio
import datetime
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiohttp import ClientTimeout
from sqlalchemy import select

from api.vpn_client import vpn_client
from bot import scheduler
from bot.config import config
from bot.handlers import auth_router, configs_router, instruction_router, menu_router
from bot.keyboards import get_cancel_keyboard
from bot.middlewares import AuthMiddleware
from database.database import async_session_maker, init_db
from database.models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_ATTEMPTS_BEFORE_LOCK = 3
MAX_ATTEMPTS_BEFORE_BAN = 9
LOCK_DURATION_HOURS = 18


class StartState(StatesGroup):
    waiting_password = State()


async def _edit_last_message(
    message: Message, state: FSMContext, text: str, reply_markup=None
):
    """Edit the last bot message or send a new one"""
    last_data = await state.get_data()
    last_msg_id = last_data.get("last_message_id")

    if last_msg_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return
        except Exception:
            pass

    try:
        await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    except TelegramNetworkError:
        # Игнорируем ошибки сети — Telegram доставит сообщение позже
        pass


async def start_handler(message: Message, state: FSMContext, db_user: User | None):
    """Handle /start command"""
    if db_user and db_user.is_blocked:
        try:
            await message.answer(
                "🚫 <b>Доступ заблокирован.</b>",
                parse_mode="HTML",
            )
        except TelegramNetworkError:
            pass
        return

    if db_user and db_user.is_authorized:
        from bot.keyboards import get_main_menu_keyboard

        try:
            await message.answer(
                "🏠 <b>Главное меню</b>",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(),
            )
        except TelegramNetworkError:
            pass
        return

    # Проверяем временную блокировку
    if db_user and db_user.locked_until:
        now = datetime.datetime.utcnow()
        if now < db_user.locked_until:
            remaining = db_user.locked_until - now
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            try:
                await message.answer(
                    f"⏳ <b>Слишком много неверных попыток.</b>\n\n"
                    f"Попробуйте через {hours}ч {minutes}мин.",
                    parse_mode="HTML",
                )
            except TelegramNetworkError:
                pass
            return

    try:
        msg = await message.answer(
            "🔒 <b>VPN Service</b>\n\nДля доступа к сервису введите пароль:",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard(),
        )
    except TelegramNetworkError:
        # Не переходим в состояние ожидания, если не смогли отправить сообщение
        return

    await state.update_data(last_message_id=msg.message_id)
    await state.set_state(StartState.waiting_password)


async def password_handler(message: Message, state: FSMContext, db_user: User | None):
    """Handle password input for unauthorized users"""
    password = message.text.strip()

    try:
        await message.delete()
    except Exception:
        pass

    async with async_session_maker() as session:
        # Получаем или создаем пользователя
        if db_user:
            stmt = select(User).where(User.id == db_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
        else:
            user = None

        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.flush()

        # Проверяем перманентный бан
        if user.is_blocked:
            await state.clear()
            await _edit_last_message(
                message,
                state,
                "🚫 <b>Доступ заблокирован.</b>",
            )
            return

        # Проверяем временную блокировку
        now = datetime.datetime.utcnow()
        if user.locked_until and now < user.locked_until:
            remaining = user.locked_until - now
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await _edit_last_message(
                message,
                state,
                f"⏳ <b>Слишком много неверных попыток.</b>\n\n"
                f"Попробуйте через {hours}ч {minutes}мин.",
            )
            await state.clear()
            await session.commit()
            return

        # Сбрасываем блокировку если время прошло
        if user.locked_until and now >= user.locked_until:
            user.locked_until = None

        if password == config.ACCESS_PASSWORD:
            user.is_authorized = True
            user.failed_attempts = 0
            user.locked_until = None
            await session.commit()

            await state.clear()

            from bot.keyboards import get_main_menu_keyboard

            await _edit_last_message(
                message,
                state,
                "✅ <b>Доступ разрешен!</b>\n\nДобро пожаловать в VPN сервис!",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            user.failed_attempts += 1
            attempts = user.failed_attempts

            # 9+ попыток — перманентный бан
            if attempts >= MAX_ATTEMPTS_BEFORE_BAN:
                user.is_blocked = True
                await session.commit()
                await state.clear()
                await _edit_last_message(
                    message,
                    state,
                    "🚫 <b>Доступ заблокирован навсегда.</b>\n\n"
                    "Слишком много неверных попыток.",
                )
                return

            # Каждые 3 попытки — блокировка на 18 часов
            if attempts % MAX_ATTEMPTS_BEFORE_LOCK == 0:
                user.locked_until = now + datetime.timedelta(hours=LOCK_DURATION_HOURS)
                await session.commit()
                await state.clear()
                await _edit_last_message(
                    message,
                    state,
                    f"⏳ <b>Слишком много неверных попыток.</b>\n\n"
                    f"Попробуйте через {LOCK_DURATION_HOURS} часов.",
                )
                return

            await session.commit()
            remaining_attempts = MAX_ATTEMPTS_BEFORE_LOCK - (
                attempts % MAX_ATTEMPTS_BEFORE_LOCK
            )
            await _edit_last_message(
                message,
                state,
                f"❌ <b>Неверный пароль!</b>\n\n"
                f"Осталось попыток: {remaining_attempts}\n"
                f"Попробуйте еще раз:",
            )


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set!")
        return

    await init_db()

    # Запускаем планировщик бэкапов
    await scheduler.start_scheduler()

    # Настраиваем сессию с увеличенным таймаутом и прокси
    timeout = ClientTimeout(total=120, connect=30, sock_read=60)

    # Используем SOCKS5 прокси с hostname resolution
    connector = ProxyConnector.from_url(
        "socks5://5.180.97.31:1080",
        ssl=False,
    )
    session = AiohttpSession(
        connector=connector,
        timeout=timeout,
    )
    bot = Bot(token=config.BOT_TOKEN, session=session)
    dp = Dispatcher()

    dp.workflow_data["session_pool"] = async_session_maker

    dp.message.middleware(AuthMiddleware(async_session_maker))
    dp.callback_query.middleware(AuthMiddleware(async_session_maker))

    dp.message.register(start_handler, CommandStart())
    dp.message.register(password_handler, StartState.waiting_password)

    # Регистрируем команды из роутеров
    dp.include_router(auth_router)
    dp.include_router(menu_router)
    dp.include_router(configs_router)
    dp.include_router(instruction_router)

    logger.info("Starting bot...")

    try:
        await dp.start_polling(bot)
    finally:
        await vpn_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
