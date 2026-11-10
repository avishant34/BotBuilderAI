"""Unit tests for validators and schemas — no LLM required."""
from __future__ import annotations

import pytest

from core.schemas import Requirements, GeneratedPackage
from core.validators import (
    check_dangerous_patterns,
    check_python_syntax,
    check_required_files,
    validate_package,
)


def test_required_files_missing():
    issues = check_required_files({"main.py": "x"})
    assert any("requirements.txt" in i for i in issues)


def test_required_files_ok():
    files = {
        "main.py": "print(1)",
        "requirements.txt": "aiogram\n",
        ".env.example": "BOT_TOKEN=\n",
        "README.md": "# bot\n",
    }
    assert check_required_files(files) == []


def test_dangerous_eval():
    files = {"main.py": "x = eval(user_input)\n"}
    issues = check_dangerous_patterns(files)
    assert any("eval" in i.lower() for i in issues)


def test_dangerous_hardcoded_token():
    files = {"config.py": "BOT_TOKEN = '1234567890:AAHardCodedTokenValueHere'\n"}
    issues = check_dangerous_patterns(files)
    assert any("Hardcoded" in i for i in issues)


def test_syntax_error():
    files = {"main.py": "def broken(\n"}
    issues = check_python_syntax(files)
    assert len(issues) == 1
    assert "syntax error" in issues[0]


def test_syntax_ok():
    files = {"main.py": "async def main():\n    return 1\n"}
    assert check_python_syntax(files) == []


def test_validate_package_happy():
    files = {
        "main.py": (
            "import asyncio\n"
            "from aiogram import Bot, Dispatcher\n"
            "from os import getenv\n"
            "TOKEN = getenv('BOT_TOKEN')\n"
            "async def main():\n"
            "    bot = Bot(token=TOKEN)\n"
            "    dp = Dispatcher()\n"
            "    await dp.start_polling(bot)\n"
        ),
        "requirements.txt": "aiogram>=3.0\npython-dotenv\n",
        ".env.example": "BOT_TOKEN=\n",
        "README.md": "# Test Bot\n",
    }
    ok, issues = validate_package(files)
    assert ok, issues


def test_validate_package_blocks_eval():
    files = {
        "main.py": "eval('1')\n",
        "requirements.txt": "aiogram\n",
        ".env.example": "BOT_TOKEN=\n",
        "README.md": "# x\n",
    }
    ok, issues = validate_package(files)
    assert not ok


def test_requirements_schema():
    r = Requirements(
        bot_name="My Cool Bot!",
        display_name="Cool",
        category="game",
    )
    assert r.bot_name == "my_cool_bot"
    assert r.estimated_complexity == "simple"


def test_generated_package_normalizes_paths():
    pkg = GeneratedPackage(files={"./bot\\handlers\\a.py": "x"})
    assert "bot/handlers/a.py" in pkg.files
