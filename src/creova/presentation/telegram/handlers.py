from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from creova.application.access import AccessContext
from creova.config import Settings
from creova.infrastructure.db.session import SqlAlchemyUnitOfWork
from creova.presentation.telegram import messages

router = Router(name="creova")


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(messages.START)


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(messages.HELP)


@router.message(Command("whoami"))
async def whoami_handler(message: Message, access_context: AccessContext) -> None:
    username = (
        f"@{message.from_user.username}"
        if message.from_user and message.from_user.username
        else "—"
    )
    await message.answer(
        "<b>Your access</b>\n"
        f"Telegram ID: <code>{access_context.telegram_user_id}</code>\n"
        f"Informational username: {username}\n"
        f"Role: <code>{access_context.role.value}</code>\n"
        "Status: active"
    )


@router.message(Command("create"))
async def create_handler(
    message: Message,
    access_context: AccessContext,
    settings: Settings,
    unit_of_work: SqlAlchemyUnitOfWork | None = None,
) -> None:
    if unit_of_work is None:
        await message.answer(messages.CREATE_PENDING_STORAGE)
        return
    async with unit_of_work as unit:
        user = await unit.users.upsert_telegram_user(
            telegram_user_id=access_context.telegram_user_id,
            telegram_username=message.from_user.username if message.from_user else None,
            display_name=message.from_user.full_name if message.from_user else None,
        )
        await unit.conversations.start_image_conversation(
            user_id=user.id,
            chat_id=message.chat.id,
            expires_at=datetime.now(UTC)
            + timedelta(minutes=settings.conversation_ttl_minutes),
        )
    await message.answer(messages.CREATE_STARTED)


@router.message(Command("status"))
async def status_handler(message: Message) -> None:
    await message.answer(messages.STATUS_PENDING)


@router.message(Command("history"))
async def history_handler(message: Message) -> None:
    await message.answer(messages.HISTORY_PENDING)


@router.message(Command("cancel"))
async def cancel_handler(message: Message) -> None:
    await message.answer(messages.CANCEL_PENDING)


async def configure_bot_commands(bot: Bot) -> None:
    from aiogram.types import BotCommand

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Introduce Creova"),
            BotCommand(command="create", description="Start an assisted image request"),
            BotCommand(command="status", description="Check generation status"),
            BotCommand(command="history", description="View your recent images"),
            BotCommand(command="cancel", description="Cancel a draft or request"),
            BotCommand(command="whoami", description="Show your identity and role"),
            BotCommand(command="help", description="Show help"),
        ]
    )
