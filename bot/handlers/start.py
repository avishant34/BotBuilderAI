from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.inline import main_menu_kb
from bot.services.user_service import UserService
from core.config import get_settings
from database.db import async_session

router = Router(name="start")
settings = get_settings()


WELCOME_TEXT = """
🤖 **BotBuilderAI**

Main kisi bhi idea se **complete Telegram bot** bana sakta hoon!

**Examples:**
• Text-based jungle adventure game
• Quiz / Trivia with score
• Weather / Currency converter
• AI Chatbot with personality
• Habit tracker / Reminder
• Group moderation bot
• RPG mini-game, Shop, Study helper...

**Kaise use karein:**
1. "✨ New Bot Idea" dabao
2. Apna idea detail mein likho
3. Complex games pe **step-by-step** generation hogi
4. Complete ready-to-run code + ZIP + Deploy help milega

Self-Correction + Safety filters se code quality high rehti hai ✅

Shuru karo 👇
""".strip()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        service = UserService(session)
        user = await service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        await service.clear_context(message.from_user.id)
        if user.is_blocked:
            await message.answer("🚫 Aapka account blocked hai.")
            return

    is_admin = message.from_user.id in settings.admin_ids_list
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(is_admin=is_admin), parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    help_text = """
📖 **Help & Commands**

/start – Main menu
/new – Naya bot banana shuru karo
/history – Pehle banaye bots dekho
/admin – Admin panel (admins only)
/cancel – Current process cancel

**Tips:**
• Idea clear aur detailed do
• Complex games automatically step-by-step banenge
• Agar kuch break ho to "Fix / Improve" use karo
• Templates se jaldi start kar sakte ho

Bot aiogram 3 + proper structure + .env + README + Dockerfile deta hai.
""".strip()
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        service = UserService(session)
        await service.clear_context(message.from_user.id)
    await message.answer("❌ Process cancel ho gaya. /start se wapas menu pe jao.")
