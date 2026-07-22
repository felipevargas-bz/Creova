from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from creova.application.access import AccessContext

router = Router(name="creova")


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "Hi, I am <b>Creova</b>. I can help you turn a simple idea into a "
        "carefully designed AI image.\n\n"
        "Use /create to begin or /help to see the available commands."
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "<b>Commands</b>\n"
        "/create — start an assisted image request\n"
        "/status &lt;id&gt; — check generation status\n"
        "/history — view your recent images\n"
        "/cancel &lt;id&gt; — cancel a draft or request\n"
        "/whoami — show your identity and role"
    )


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


@router.message(Command("create", "status", "history", "cancel"))
async def pending_feature_handler(message: Message) -> None:
    await message.answer(
        "This assisted image flow will be enabled as the remaining implementation phases land."
    )
