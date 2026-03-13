import base64
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.vpn_client import VPNAPIError, vpn_client
from bot.config import config
from bot.keyboards import (
    get_back_keyboard,
    get_cancel_keyboard,
    get_config_actions_keyboard,
    get_configs_keyboard,
    get_confirm_keyboard,
    get_main_menu_keyboard,
    get_servers_keyboard,
)
from database.models import User, UserConfig

router = Router()


async def safe_edit_text(
    message, text: str, parse_mode: str = "HTML", reply_markup=None
):
    """Edit message, ignoring 'message is not modified' error"""
    with suppress(TelegramBadRequest):
        await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)


class CreateConfigState(StatesGroup):
    selecting_server = State()
    entering_name = State()
    confirming = State()


def format_bytes(size: int) -> str:
    """Format bytes to human readable string"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


@router.callback_query(F.data == "my_configs")
async def show_my_configs(
    callback: CallbackQuery,
    db_user: User | None,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Show user's configs"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    async with session_pool() as session:
        stmt = select(UserConfig).where(UserConfig.user_id == db_user.id)
        result = await session.execute(stmt)
        configs = result.scalars().all()

    if not configs:
        await safe_edit_text(
            callback.message,
            "📁 <b>Мои конфиги</b>\n\n"
            "У вас пока нет конфигов.\n"
            "Нажмите 'Создать конфиг' чтобы добавить новый.",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(),
        )
        return

    configs_list = [{"id": cfg.id, "name": cfg.name} for cfg in configs]

    await safe_edit_text(
        callback.message,
        "📁 <b>Мои конфиги</b>\n\n"
        f"Всего конфигов: {len(configs_list)}/{config.MAX_CONFIGS_PER_USER}",
        parse_mode="HTML",
        reply_markup=get_configs_keyboard(configs_list),
    )


@router.callback_query(F.data.startswith("config_"))
async def show_config_details(
    callback: CallbackQuery,
    db_user: User | None,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Show config details"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    config_id = int(callback.data.split("_")[1])

    async with session_pool() as session:
        stmt = select(UserConfig).where(
            UserConfig.id == config_id, UserConfig.user_id == db_user.id
        )
        result = await session.execute(stmt)
        user_config = result.scalar_one_or_none()

    if not user_config:
        await callback.answer("Конфиг не найден", show_alert=True)
        return

    try:
        details = await vpn_client.get_client_details(user_config.client_id)
        client_info = details.get("client", {})
        stats = details.get("stats", {})

        is_revoked = client_info.get("is_revoked", False)
        expires_at = client_info.get("expires_at")
        traffic_used = stats.get("total_bytes", 0)

        text = (
            f"📁 <b>{user_config.name}</b>\n\n"
            f"🆔 ID: {user_config.client_id}\n"
            f"🖥️ Сервер: {client_info.get('server_name', 'N/A')}\n"
            f"📊 Трафик: {format_bytes(traffic_used)}\n"
            f"📅 Истекает: {expires_at or 'Не ограничено'}\n"
            f"{'⚠️ <b>ОТКЛЮЧЕН</b>' if is_revoked else '✅ Активен'}"
        )

        await safe_edit_text(
            callback.message,
            text,
            parse_mode="HTML",
            reply_markup=get_config_actions_keyboard(config_id, is_revoked),
        )
    except VPNAPIError as e:
        await safe_edit_text(
            callback.message,
            f"❌ Ошибка получения данных: {e.message}",
            parse_mode="HTML",
            reply_markup=get_back_keyboard("my_configs"),
        )


@router.callback_query(F.data.startswith("copy_config_"))
async def copy_config(
    callback: CallbackQuery,
    db_user: User | None,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Send config text to copy"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    config_id = int(callback.data.split("_")[2])

    async with session_pool() as session:
        stmt = select(UserConfig).where(
            UserConfig.id == config_id, UserConfig.user_id == db_user.id
        )
        result = await session.execute(stmt)
        user_config = result.scalar_one_or_none()

    if not user_config:
        await callback.answer("Конфиг не найден", show_alert=True)
        return

    try:
        details = await vpn_client.get_client_details(user_config.client_id)
        config_text = details.get("config", "")

        # Отправляем конфиг файлом
        config_bytes = config_text.encode("utf-8")
        config_file = BufferedInputFile(
            config_bytes, filename=f"{user_config.name}.conf"
        )
        await callback.message.answer_document(
            config_file,
            caption=f"📋 <b>Конфигурация:</b> {user_config.name}",
            parse_mode="HTML",
        )
        await callback.answer("Конфиг отправлен выше")
    except VPNAPIError as e:
        await callback.answer(f"Ошибка: {e.message}", show_alert=True)


@router.callback_query(F.data.startswith("qr_config_"))
async def show_qr_config(
    callback: CallbackQuery,
    db_user: User | None,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Show QR code for config"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    config_id = int(callback.data.split("_")[2])

    async with session_pool() as session:
        stmt = select(UserConfig).where(
            UserConfig.id == config_id, UserConfig.user_id == db_user.id
        )
        result = await session.execute(stmt)
        user_config = result.scalar_one_or_none()

    if not user_config:
        await callback.answer("Конфиг не найден", show_alert=True)
        return

    try:
        qr_data = await vpn_client.get_client_qr(user_config.client_id)

        # Проверяем разные возможные ключи
        qr_b64 = (
            qr_data.get("qr_code_base64") or qr_data.get("qr_code") or qr_data.get("qr")
        )

        if isinstance(qr_b64, str) and qr_b64.startswith("data:image/"):
            # Извлекаем base64 из data URI
            qr_b64 = qr_b64.split(",", 1)[1] if "," in qr_b64 else qr_b64

        if qr_b64:
            # Декодируем base64
            qr_bytes = base64.b64decode(qr_b64)
            photo = BufferedInputFile(qr_bytes, filename=f"qr_{user_config.name}.png")

            await callback.message.answer_photo(
                photo,
                caption=f"📱 QR-код для конфига: <b>{user_config.name}</b>",
                parse_mode="HTML",
            )
            await callback.answer("QR-код отправлен выше")
        else:
            await callback.answer("QR-код недоступен", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("revoke_config_"))
async def revoke_config(
    callback: CallbackQuery,
    db_user: User | None,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Revoke config"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    config_id = int(callback.data.split("_")[2])

    async with session_pool() as session:
        stmt = select(UserConfig).where(
            UserConfig.id == config_id, UserConfig.user_id == db_user.id
        )
        result = await session.execute(stmt)
        user_config = result.scalar_one_or_none()

    if not user_config:
        await callback.answer("Конфиг не найден", show_alert=True)
        return

    try:
        await vpn_client.revoke_client(user_config.client_id)
        await callback.answer("Конфиг отключен")
        await show_config_details(callback, db_user, session_pool)
    except VPNAPIError as e:
        await callback.answer(f"Ошибка: {e.message}", show_alert=True)


@router.callback_query(F.data.startswith("restore_config_"))
async def restore_config(
    callback: CallbackQuery,
    db_user: User | None,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Restore config"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    config_id = int(callback.data.split("_")[2])

    async with session_pool() as session:
        stmt = select(UserConfig).where(
            UserConfig.id == config_id, UserConfig.user_id == db_user.id
        )
        result = await session.execute(stmt)
        user_config = result.scalar_one_or_none()

    if not user_config:
        await callback.answer("Конфиг не найден", show_alert=True)
        return

    try:
        await vpn_client.restore_client(user_config.client_id)
        await callback.answer("Конфиг восстановлен")
        await show_config_details(callback, db_user, session_pool)
    except VPNAPIError as e:
        await callback.answer(f"Ошибка: {e.message}", show_alert=True)


@router.callback_query(F.data.startswith("delete_config_"))
async def delete_config_confirm(callback: CallbackQuery, db_user: User | None):
    """Ask for confirmation before deleting config"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    config_id = int(callback.data.split("_")[2])

    await safe_edit_text(
        callback.message,
        "⚠️ <b>Подтверждение удаления</b>\n\n"
        "Вы уверены, что хотите удалить этот конфиг?\n"
        "Это действие нельзя отменить.",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard(
            f"confirm_delete_{config_id}", f"config_{config_id}"
        ),
    )


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_config(
    callback: CallbackQuery,
    db_user: User | None,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Delete config after confirmation"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    config_id = int(callback.data.split("_")[2])

    async with session_pool() as session:
        stmt = select(UserConfig).where(
            UserConfig.id == config_id, UserConfig.user_id == db_user.id
        )
        result = await session.execute(stmt)
        user_config = result.scalar_one_or_none()

        if not user_config:
            await callback.answer("Конфиг не найден", show_alert=True)
            return

        try:
            await vpn_client.delete_client(user_config.client_id)
        except VPNAPIError:
            pass  # Клиент уже удален на сервере — не страшно

        await session.delete(user_config)
        await session.commit()
        await callback.answer("Конфиг удален")
        await show_my_configs(callback, db_user, session_pool)


@router.callback_query(F.data == "create_config")
async def start_create_config(
    callback: CallbackQuery,
    db_user: User | None,
    state: FSMContext,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Start config creation process"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    async with session_pool() as session:
        stmt = select(UserConfig).where(UserConfig.user_id == db_user.id)
        result = await session.execute(stmt)
        configs_count = len(result.scalars().all())

    if configs_count >= config.MAX_CONFIGS_PER_USER:
        await callback.answer(
            f"Максимум {config.MAX_CONFIGS_PER_USER} конфигов", show_alert=True
        )
        return

    try:
        servers = await vpn_client.get_servers()

        if not servers:
            await safe_edit_text(
                callback.message,
                "❌ Нет доступных серверов",
                parse_mode="HTML",
                reply_markup=get_back_keyboard(),
            )
            return

        await state.set_state(CreateConfigState.selecting_server)
        await state.update_data(servers=servers)

        await safe_edit_text(
            callback.message,
            "➕ <b>Создание конфига</b>\n\nВыберите сервер:",
            parse_mode="HTML",
            reply_markup=get_servers_keyboard(servers),
        )
    except VPNAPIError as e:
        await safe_edit_text(
            callback.message,
            f"❌ Ошибка получения серверов: {e.message}",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(),
        )


@router.callback_query(CreateConfigState.selecting_server, F.data.startswith("server_"))
async def select_server_for_config(
    callback: CallbackQuery,
    state: FSMContext,
    db_user: User | None,
):
    """Handle server selection"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    server_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    servers = data.get("servers", [])

    server_name = next((s["name"] for s in servers if s["id"] == server_id), "Unknown")

    await state.update_data(server_id=server_id, server_name=server_name)
    await state.set_state(CreateConfigState.entering_name)

    await safe_edit_text(
        callback.message,
        "➕ <b>Создание конфига</b>\n\n"
        f"Сервер: {server_name}\n\n"
        "Введите название для конфига:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(CreateConfigState.entering_name)
async def enter_config_name(
    message: Message,
    state: FSMContext,
    db_user: User | None,
):
    """Handle config name input"""
    if not db_user or not db_user.is_authorized:
        return

    name = message.text.strip()

    if len(name) > 50:
        await message.answer(
            "❌ Название слишком длинное (макс. 50 символов)",
            reply_markup=get_cancel_keyboard(),
        )
        return

    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    await state.update_data(config_name=name, last_message_id=message.message_id)

    await state.set_state(CreateConfigState.confirming)

    await message.answer(
        "➕ <b>Создание конфига</b>\n\n"
        f"Сервер: {data.get('server_name')}\n"
        f"Название: {name}\n\n"
        "Подтвердите создание:",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard("confirm_create", "cancel"),
    )


@router.callback_query(CreateConfigState.confirming, F.data == "confirm_create")
async def confirm_create_config(
    callback: CallbackQuery,
    state: FSMContext,
    db_user: User | None,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Create config after confirmation"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    data = await state.get_data()
    server_id = data.get("server_id")
    config_name = data.get("config_name")

    try:
        result = await vpn_client.create_client(server_id=server_id, name=config_name)

        client_id = result.get("client", {}).get("id") or result.get("id")
        config_text = result.get("config", "")

        # Получаем QR-код
        qr_data = await vpn_client.get_client_qr(client_id)
        qr_b64 = (
            qr_data.get("qr_code_base64") or qr_data.get("qr_code") or qr_data.get("qr")
        )

        if isinstance(qr_b64, str) and qr_b64.startswith("data:image/"):
            qr_b64 = qr_b64.split(",", 1)[1] if "," in qr_b64 else qr_b64

        async with session_pool() as session:
            user_config = UserConfig(
                user_id=db_user.id,
                client_id=client_id,
                server_id=server_id,
                name=config_name,
            )
            session.add(user_config)
            await session.commit()

        await state.clear()

        # Отправляем конфиг файлом
        config_bytes = config_text.encode("utf-8")
        config_file = BufferedInputFile(config_bytes, filename=f"{config_name}.conf")
        await callback.message.answer_document(
            config_file,
            caption=f"✅ <b>Конфиг создан!</b>\n\n📁 Название: {config_name}",
            parse_mode="HTML",
        )

        # Отправляем QR-код если есть
        if qr_b64:
            try:
                qr_bytes = base64.b64decode(qr_b64)
                photo = BufferedInputFile(qr_bytes, filename=f"qr_{config_name}.png")
                await callback.message.answer_photo(
                    photo,
                    caption=f"📱 QR-код для конфига: <b>{config_name}</b>",
                    parse_mode="HTML",
                )
            except Exception:
                pass

        await callback.message.delete()
        await callback.message.answer(
            "🏠 Главное меню", reply_markup=get_main_menu_keyboard()
        )

    except VPNAPIError as e:
        await callback.answer(f"Ошибка создания: {e.message}", show_alert=True)
        await state.clear()


@router.callback_query(F.data == "stats")
async def show_stats(
    callback: CallbackQuery,
    db_user: User | None,
    session_pool: async_sessionmaker[AsyncSession],
):
    """Show user statistics"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    async with session_pool() as session:
        stmt = select(UserConfig).where(UserConfig.user_id == db_user.id)
        result = await session.execute(stmt)
        configs = result.scalars().all()

    total_traffic = 0
    active_configs = 0

    for cfg in configs:
        try:
            details = await vpn_client.get_client_details(cfg.client_id)
            stats = details.get("stats", {})
            total_traffic += stats.get("total_bytes", 0)
            if not details.get("client", {}).get("is_revoked", False):
                active_configs += 1
        except VPNAPIError:
            pass

    await safe_edit_text(
        callback.message,
        "📊 <b>Статистика</b>\n\n"
        f"📁 Всего конфигов: {len(configs)}/{config.MAX_CONFIGS_PER_USER}\n"
        f"✅ Активных: {active_configs}\n"
        f"📈 Всего трафика: {format_bytes(total_traffic)}",
        parse_mode="HTML",
        reply_markup=get_back_keyboard(),
    )
