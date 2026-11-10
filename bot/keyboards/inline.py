from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✨ New Bot Idea", callback_data="action:new"),
    )
    builder.row(
        InlineKeyboardButton(text="📜 My Bots History", callback_data="action:history"),
        InlineKeyboardButton(text="📚 Templates", callback_data="action:templates"),
    )
    builder.row(
        InlineKeyboardButton(text="❓ Help", callback_data="action:help"),
        InlineKeyboardButton(text="⚙️ Settings", callback_data="action:settings"),
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="🛡 Admin Panel", callback_data="admin:panel"),
        )
    return builder.as_markup()


def after_generation_kb(bot_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📦 Download ZIP", callback_data=f"dl:{bot_id}"),
        InlineKeyboardButton(text="🐙 Push to GitHub", callback_data=f"gh:{bot_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🚀 Deploy Help", callback_data=f"deploy:{bot_id}"),
        InlineKeyboardButton(text="🔧 Fix / Improve", callback_data=f"fix:{bot_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🧪 Test Simulation", callback_data=f"sim:{bot_id}"),
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="action:menu"),
    )
    return builder.as_markup()


def confirm_kb(yes_data: str = "confirm:yes", no_data: str = "confirm:no") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes", callback_data=yes_data),
        InlineKeyboardButton(text="❌ No", callback_data=no_data),
    )
    return builder.as_markup()


def step_confirm_kb(step_index: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="▶️ Next Step", callback_data=f"step:next:{step_index}"),
        InlineKeyboardButton(text="⏹ Cancel", callback_data="step:cancel"),
    )
    return builder.as_markup()


def templates_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    templates = [
        ("🎮 Text Adventure", "tpl:adventure"),
        ("❓ Quiz / Trivia", "tpl:quiz"),
        ("💬 AI Chatbot", "tpl:aichat"),
        ("🌤️ Weather Bot", "tpl:weather"),
        ("✅ Habit Tracker", "tpl:habit"),
        ("🛡️ Group Moderation", "tpl:moderation"),
        ("🧮 Calculator / Converter", "tpl:calculator"),
        ("📅 Reminder Bot", "tpl:reminder"),
        ("🎲 Rock-Paper-Scissors", "tpl:rps"),
        ("📚 Study Helper", "tpl:study"),
        ("🛒 Simple Shop / Leads", "tpl:shop"),
        ("🎯 RPG Mini (inventory)", "tpl:rpg"),
    ]
    for text, data in templates:
        builder.row(InlineKeyboardButton(text=text, callback_data=data))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="action:menu"))
    return builder.as_markup()


def language_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇮🇳 Hindi", callback_data="lang:hi"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        InlineKeyboardButton(text="🔀 Mixed", callback_data="lang:mixed"),
    )
    return builder.as_markup()


def admin_panel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Stats", callback_data="admin:stats"),
        InlineKeyboardButton(text="📈 Metrics", callback_data="admin:metrics"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Recent Users", callback_data="admin:users"),
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Block User", callback_data="admin:block"),
        InlineKeyboardButton(text="✅ Unblock User", callback_data="admin:unblock"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="action:menu"),
    )
    return builder.as_markup()
