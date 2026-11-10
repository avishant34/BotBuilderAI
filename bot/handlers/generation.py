from __future__ import annotations

import json
from typing import Any, Dict

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from loguru import logger

from bot.keyboards.inline import (
    after_generation_kb,
    language_kb,
    main_menu_kb,
    step_confirm_kb,
    templates_kb,
)
from bot.services.user_service import UserService
from bot.states.generation import GenerationStates
from core.code_generator import code_generator
from core.config import get_settings
from core.packager import create_zip_from_files, get_deploy_instructions, push_to_github
from database.db import async_session

router = Router(name="generation")
settings = get_settings()


TEMPLATES: Dict[str, str] = {
    "adventure": (
        "Ek text-based jungle adventure game banao. Player jungle mein lost hai. "
        "Har step pe 3 choices hain. Health system (100 se start), inventory system, "
        "aur kam se kam 3 different endings (good, bad, secret). Hindi + English mixed."
    ),
    "quiz": (
        "Ek trivia / quiz bot banao. 10 questions, multiple choice, score system, "
        "leaderboard (memory based), categories (general, science, movies). Hindi support bhi ho."
    ),
    "aichat": (
        "Ek AI chatbot banao jiska personality friendly Indian developer hai. "
        "User se coding, career, aur general baatein kare. Context yaad rakhe (simple memory)."
    ),
    "weather": (
        "Ek weather bot banao. User city name de to current weather + 3-day forecast dikhaye. "
        "OpenWeatherMap API use kare (API key .env se). Hindi responses."
    ),
    "habit": (
        "Ek habit tracker bot banao. User habits add kar sake, daily check-in kare, "
        "streak count dikhe, weekly summary aaye. Simple SQLite use karo."
    ),
    "moderation": (
        "Ek group moderation bot banao. Welcome message, anti-spam (link + flood), "
        "warn / mute / ban commands (admin only), rules command."
    ),
    "calculator": (
        "Ek utility bot banao jo calculator + unit converter ho. "
        "Basic math, currency (USD/INR), length, weight convert kare. Inline buttons se mode choose."
    ),
    "reminder": (
        "Ek reminder / todo bot banao. User reminder set kar sake (time + text), "
        "list dekh sake, delete kar sake. Simple in-memory ya SQLite. Hindi support."
    ),
    "rps": (
        "Ek Rock-Paper-Scissors game bot banao. Score track kare (win/lose/draw), "
        "best of 5 mode, fun messages. Inline buttons se choice."
    ),
    "study": (
        "Ek study helper bot banao. User topic de to short explanation + 3 practice questions de. "
        "Flashcard mode bhi ho. Hindi + English."
    ),
    "shop": (
        "Ek simple lead collection / shop style bot banao. Products list, price, "
        "user order/interest form (name, phone, product). Admin ko notification. SQLite."
    ),
    "rpg": (
        "Ek simple text RPG mini-game banao. Player ke paas health, gold, inventory. "
        "Explore, fight (simple), shop, level up. 4-5 locations, FSM states clearly defined."
    ),
}


# ───────────────────── New Idea Flow ─────────────────────

@router.callback_query(F.data == "action:new")
@router.message(Command("new"))
async def start_new_idea(event: Message | CallbackQuery, state: FSMContext) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = event.from_user.id

    async with async_session() as session:
        service = UserService(session)
        user = await service.get_or_create_user(user_id)
        if user.is_blocked:
            await message.answer("🚫 Aapka account blocked hai. Admin se contact karo.")
            return

    await state.set_state(GenerationStates.waiting_idea)
    await message.answer(
        "✨ **Apna bot idea detail mein likho:**\n\n"
        "Example:\n"
        "`Ek jungle adventure game banao jisme player lost hai. "
        "Har step pe 3 choices, health system, inventory, aur different endings.`\n\n"
        "Jitna clear idea doge, utna better code aayega.\n"
        "Complex games ke liye step-by-step generation automatically start hogi.",
        parse_mode="Markdown",
    )


@router.message(GenerationStates.waiting_idea)
async def process_idea(message: Message, state: FSMContext) -> None:
    idea = (message.text or "").strip()
    if len(idea) < 10:
        await message.answer("Idea thoda short hai. Please 1-2 lines mein detail do.")
        return

    async with async_session() as session:
        service = UserService(session)
        user = await service.get_or_create_user(
            message.from_user.id, message.from_user.username, message.from_user.full_name
        )
        if user.is_blocked:
            await message.answer("🚫 Account blocked.")
            await state.clear()
            return
        if not await service.can_generate(user):
            await message.answer(
                f"⚠️ Aaj ka limit complete ho gaya. Kal try karo."
            )
            await state.clear()
            return

    status_msg = await message.answer("🧠 Idea samajh raha hoon... thoda wait karo.")

    try:
        result = await code_generator.full_pipeline(idea)

        if result.get("needs_clarification"):
            questions = result.get("clarifying_questions", [])
            q_text = "\n".join(f"• {q}" for q in questions)
            await state.update_data(idea=idea, requirements=result["requirements"])
            await state.set_state(GenerationStates.waiting_clarification)
            await status_msg.edit_text(
                f"🤔 Idea almost clear hai, lekin kuch details chahiye:\n\n{q_text}\n\n"
                "Apne answers ek message mein bhej do."
            )
            return

        if result.get("needs_step_by_step"):
            plan = result.get("generation_plan") or []
            plan_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan))
            await state.update_data(
                idea=idea,
                requirements=result["requirements"],
                step_files={},
                step_index=0,
                generation_plan=plan,
            )
            await state.set_state(GenerationStates.step_confirm)
            await status_msg.edit_text(
                f"🧩 **Complex bot detected!** Step-by-step generation better quality degi.\n\n"
                f"**Plan ({len(plan)} steps):**\n{plan_text}\n\n"
                "Pehla step start karein?",
                parse_mode="Markdown",
                reply_markup=step_confirm_kb(0),
            )
            return

        await _finalize_and_send(message, state, status_msg, idea, result, user_id=message.from_user.id)

    except Exception as e:
        logger.exception("Generation failed")
        await status_msg.edit_text(
            f"❌ Generation fail ho gaya: `{str(e)[:200]}`\n\nPhir se try karo.",
            parse_mode="Markdown",
        )
        await state.clear()


@router.message(GenerationStates.waiting_clarification)
async def process_clarification(message: Message, state: FSMContext) -> None:
    answers = (message.text or "").strip()
    data = await state.get_data()
    idea = data.get("idea", "")
    prev_req = data.get("requirements", {})

    status_msg = await message.answer("🔄 Answers merge karke aage badh raha hoon...")

    try:
        updated_req = await code_generator.apply_clarifications(prev_req, answers)
        if updated_req.get("needs_clarification"):
            questions = updated_req.get("clarifying_questions", [])
            q_text = "\n".join(f"• {q}" for q in questions)
            await state.update_data(requirements=updated_req)
            await status_msg.edit_text(f"Abhi bhi thodi clarity chahiye:\n\n{q_text}")
            return

        # Check if now complex
        if code_generator._is_complex(updated_req):
            plan = updated_req.get("generation_plan") or [
                "Define structure + states",
                "Keyboards + handlers",
                "Core logic",
                "Polish + README",
            ]
            updated_req["generation_plan"] = plan
            await state.update_data(
                requirements=updated_req,
                step_files={},
                step_index=0,
                generation_plan=plan,
            )
            await state.set_state(GenerationStates.step_confirm)
            plan_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan))
            await status_msg.edit_text(
                f"🧩 Complex bot → Step-by-step\n\n{plan_text}\n\nStart?",
                reply_markup=step_confirm_kb(0),
            )
            return

        generated = await code_generator.generate_code(updated_req)
        generated = await code_generator.self_review(generated)
        is_safe, _ = code_generator._static_safety_check(generated.get("files", {}))
        result = {
            "requirements": updated_req,
            "code": generated,
            "review": generated.get("review", {}),
            "is_safe": is_safe,
        }
        await _finalize_and_send(message, state, status_msg, idea, result, user_id=message.from_user.id)

    except Exception as e:
        logger.exception("Clarification pipeline failed")
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")
        await state.clear()


# ───────────────────── Step-by-step ─────────────────────

@router.callback_query(F.data.startswith("step:next:"))
async def run_next_step(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    requirements = data.get("requirements", {})
    step_files = data.get("step_files") or {}
    step_index = int(callback.data.split(":")[-1])
    plan = data.get("generation_plan") or requirements.get("generation_plan") or []

    if step_index >= len(plan):
        await callback.message.answer("All steps already done.")
        return

    status = await callback.message.answer(
        f"⚙️ Step {step_index + 1}/{len(plan)}: `{plan[step_index]}` ...",
        parse_mode="Markdown",
    )

    try:
        step_result = await code_generator.run_step_pipeline(
            requirements=requirements,
            step_index=step_index,
            previous_files=step_files,
        )
        new_files = step_result["files"]
        await state.update_data(step_files=new_files, step_index=step_index + 1)

        notes = step_result.get("step_notes", "")
        if step_result["is_last"]:
            # Finalize
            result = {
                "requirements": requirements,
                "code": {
                    "files": new_files,
                    "notes": notes,
                    "review": step_result.get("review", {}),
                },
                "review": step_result.get("review", {}),
                "is_safe": step_result.get("is_safe", True),
            }
            await status.edit_text("✅ Final step complete! Packaging...")
            await _finalize_and_send(
                callback.message,
                state,
                status,
                data.get("idea", ""),
                result,
                user_id=callback.from_user.id,
            )
        else:
            next_idx = step_index + 1
            await status.edit_text(
                f"✅ Step {step_index + 1} done.\n_{notes}_\n\n"
                f"Next: **{plan[next_idx]}**",
                parse_mode="Markdown",
                reply_markup=step_confirm_kb(next_idx),
            )
            await state.set_state(GenerationStates.step_confirm)
    except Exception as e:
        logger.exception("Step failed")
        await status.edit_text(f"❌ Step failed: {str(e)[:200]}")
        await state.clear()


@router.callback_query(F.data == "step:cancel")
async def cancel_steps(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer("❌ Step-by-step cancel. /new se dubara shuru karo.")


async def _finalize_and_send(
    message: Message,
    state: FSMContext,
    status_msg: Message,
    idea: str,
    result: Dict[str, Any],
    user_id: int,
) -> None:
    code_pkg = result.get("code") or {}
    files = code_pkg.get("files", {})
    requirements = result.get("requirements", {})
    review = result.get("review") or code_pkg.get("review") or {}

    bot_name = requirements.get("bot_name", "my_telegram_bot")
    display_name = requirements.get("display_name", bot_name)
    category = requirements.get("category", "other")

    async with async_session() as session:
        service = UserService(session)
        user = await service.get_or_create_user(user_id)
        await service.increment_generation(user)

        record = await service.save_generated_bot(
            user=user,
            bot_name=bot_name,
            display_name=display_name,
            category=category,
            idea=idea,
            requirements=requirements,
            files=files,
            review=review,
            is_safe=result.get("is_safe", True),
        )
        await service.save_context(
            telegram_id=user_id,
            state="ready",
            data={
                "bot_id": record.id,
                "requirements": requirements,
                "files": files,
                "idea": idea,
            },
        )

    quality = review.get("overall_quality", "good")
    bugs = review.get("bugs_found", [])
    val_issues = result.get("validation_issues") or []
    safe_emoji = "✅" if result.get("is_safe") else "⚠️"

    summary = (
        f"{safe_emoji} **Bot ready!**\n\n"
        f"**Name:** `{display_name}`\n"
        f"**Category:** {category}\n"
        f"**Quality:** {quality}\n"
        f"**Files:** {len(files)}\n"
        f"**Safe:** {'yes' if result.get('is_safe') else 'review needed'}\n"
    )
    if bugs:
        summary += "**Review notes:** " + ", ".join(str(b) for b in bugs[:3]) + "\n"
    warns = [i for i in val_issues if str(i).startswith("[warn]")]
    critical = [i for i in val_issues if not str(i).startswith("[warn]")]
    if critical:
        summary += "**Validation:** " + str(critical[:2]) + "\n"
    elif warns:
        summary += "**Hints:** " + str(warns[0]) + "\n"
    summary += "\nNeeche se ZIP / GitHub / Deploy / Fix use karo."

    await status_msg.edit_text(summary, parse_mode="Markdown", reply_markup=after_generation_kb(record.id))
    await state.clear()


# ───────────────────── Actions on generated bot ─────────────────────

@router.callback_query(F.data.startswith("dl:"))
async def download_zip(callback: CallbackQuery) -> None:
    await callback.answer()
    bot_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        service = UserService(session)
        record = await service.get_bot_by_id(bot_id, callback.from_user.id)
        if not record:
            await callback.message.answer("Bot not found.")
            return
        files = json.loads(record.files_json)

    zip_bytes = create_zip_from_files(files, record.bot_name)
    document = BufferedInputFile(zip_bytes, filename=f"{record.bot_name}.zip")
    await callback.message.answer_document(
        document,
        caption=f"📦 `{record.display_name}`\n\nExtract → set BOT_TOKEN in .env → python main.py",
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("gh:"))
async def push_github(callback: CallbackQuery) -> None:
    await callback.answer("GitHub pe push ho raha hai...")
    bot_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        service = UserService(session)
        record = await service.get_bot_by_id(bot_id, callback.from_user.id)
        if not record:
            await callback.message.answer("Bot not found.")
            return
        files = json.loads(record.files_json)

    url = await push_to_github(
        files=files,
        repo_name=record.bot_name,
        description=f"Generated by Telegram Bot Generator: {record.display_name}",
    )
    if url:
        async with async_session() as session:
            record.github_url = url
            await session.commit()
        await callback.message.answer(f"🐙 Successfully pushed!\n{url}")
    else:
        await callback.message.answer(
            "❌ GitHub push fail. Check GITHUB_TOKEN & GITHUB_USERNAME in .env"
        )


@router.callback_query(F.data.startswith("deploy:"))
async def deploy_help(callback: CallbackQuery) -> None:
    await callback.answer()
    bot_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        service = UserService(session)
        record = await service.get_bot_by_id(bot_id, callback.from_user.id)
        if not record:
            await callback.message.answer("Bot not found.")
            return
    text = get_deploy_instructions(record.bot_name)
    await callback.message.answer(text, parse_mode="Markdown")


@router.callback_query(F.data.startswith("fix:"))
async def start_fix(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    bot_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        service = UserService(session)
        record = await service.get_bot_by_id(bot_id, callback.from_user.id)
        if not record:
            await callback.message.answer("Bot not found.")
            return
        await state.update_data(
            bot_id=bot_id,
            requirements=json.loads(record.requirements_json),
            files=json.loads(record.files_json),
        )
    await state.set_state(GenerationStates.waiting_feedback)
    await callback.message.answer(
        "🔧 Kya problem hai ya kya improve karna hai?\n\n"
        "Example: `Health system theek se nahi chal raha, score bhi add kar do`"
    )


@router.message(GenerationStates.waiting_feedback)
async def process_feedback(message: Message, state: FSMContext) -> None:
    feedback = (message.text or "").strip()
    data = await state.get_data()
    requirements = data.get("requirements", {})
    previous_files = data.get("files", {})

    status = await message.answer("🔄 Feedback ke hisaab se improve kar raha hoon...")

    try:
        improved = await code_generator.improve_from_feedback(
            requirements=requirements,
            previous_files=previous_files,
            feedback=feedback,
        )
        files = improved["code"].get("files", {})
        review = improved.get("review", {})

        async with async_session() as session:
            service = UserService(session)
            user = await service.get_or_create_user(message.from_user.id)
            record = await service.save_generated_bot(
                user=user,
                bot_name=requirements.get("bot_name", "improved_bot"),
                display_name=requirements.get("display_name", "Improved Bot") + " (v2)",
                category=requirements.get("category", "other"),
                idea=feedback,
                requirements=requirements,
                files=files,
                review=review,
                is_safe=improved.get("is_safe", True),
            )
            await service.save_context(
                telegram_id=message.from_user.id,
                state="ready",
                data={"bot_id": record.id, "requirements": requirements, "files": files},
            )

        await status.edit_text(
            f"✅ Improved version ready!\nQuality: {review.get('overall_quality', 'good')}",
            reply_markup=after_generation_kb(record.id),
        )
        await state.clear()
    except Exception as e:
        logger.exception("Improve failed")
        await status.edit_text(f"❌ Improve fail: {str(e)[:200]}")
        await state.clear()


@router.callback_query(F.data.startswith("sim:"))
async def test_simulation(callback: CallbackQuery) -> None:
    await callback.answer()
    bot_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        service = UserService(session)
        record = await service.get_bot_by_id(bot_id, callback.from_user.id)
        if not record:
            await callback.message.answer("Bot not found.")
            return
        files = json.loads(record.files_json)

    main_content = files.get("main.py", "")[:800]
    text = (
        f"🧪 **Simulation / Structure Preview**\n\n"
        f"**Bot:** {record.display_name}\n"
        f"**Key files:** {', '.join(list(files.keys())[:8])}\n\n"
        f"**main.py (preview):**\n```python\n{main_content}...\n```\n\n"
        "Actual runtime ke liye ZIP download karke locally run karo."
    )
    await callback.message.answer(text, parse_mode="Markdown")


# ───────────────────── Menu & Templates ─────────────────────

@router.callback_query(F.data == "action:menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    is_admin = callback.from_user.id in settings.admin_ids_list
    await callback.message.answer("🏠 Main Menu", reply_markup=main_menu_kb(is_admin=is_admin))


@router.callback_query(F.data == "action:history")
@router.message(Command("history"))
async def show_history(event: Message | CallbackQuery) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = event.from_user.id

    async with async_session() as session:
        service = UserService(session)
        bots = await service.get_user_bots(user_id, limit=8)

    if not bots:
        await message.answer("Abhi tak koi bot nahi banaya. /new se shuru karo!")
        return

    lines = ["📜 **Your Generated Bots:**\n"]
    for b in bots:
        safe = "✅" if b.is_safe else "⚠️"
        lines.append(f"{safe} `{b.display_name}` ({b.category}) – id:{b.id}")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.callback_query(F.data == "action:templates")
async def show_templates(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "📚 **Ready Templates** – ek click se idea prefill hoga:",
        reply_markup=templates_kb(),
    )


@router.callback_query(F.data.startswith("tpl:"))
async def use_template(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    tpl = callback.data.split(":")[1]
    idea = TEMPLATES.get(tpl, "Simple utility bot")
    await state.set_state(GenerationStates.waiting_idea)
    await callback.message.answer(
        f"Template selected:\n\n`{idea}`\n\nGenerating...",
        parse_mode="Markdown",
    )
    status_msg = await callback.message.answer("🧠 Generating from template...")
    try:
        result = await code_generator.full_pipeline(idea)
        if result.get("needs_clarification"):
            questions = result.get("clarifying_questions", [])
            q_text = "\n".join(f"• {q}" for q in questions)
            await state.update_data(idea=idea, requirements=result["requirements"])
            await state.set_state(GenerationStates.waiting_clarification)
            await status_msg.edit_text(f"Clarifications needed:\n\n{q_text}")
            return
        if result.get("needs_step_by_step"):
            plan = result.get("generation_plan") or []
            plan_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan))
            await state.update_data(
                idea=idea,
                requirements=result["requirements"],
                step_files={},
                step_index=0,
                generation_plan=plan,
            )
            await state.set_state(GenerationStates.step_confirm)
            await status_msg.edit_text(
                f"🧩 Complex → Step-by-step\n\n{plan_text}\n\nStart?",
                reply_markup=step_confirm_kb(0),
            )
            return
        await _finalize_and_send(
            callback.message, state, status_msg, idea, result, user_id=callback.from_user.id
        )
    except Exception as e:
        logger.exception("Template generation failed")
        await status_msg.edit_text(f"❌ Error: {e}")
        await state.clear()


@router.callback_query(F.data == "action:help")
async def help_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("❓ /help ya /start use karo.")


@router.callback_query(F.data == "action:settings")
async def settings_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️ Preferred language choose karo:",
        reply_markup=language_kb(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":")[1]
    await callback.answer(f"Language set to {lang}")
    async with async_session() as session:
        service = UserService(session)
        user = await service.get_or_create_user(callback.from_user.id)
        user.language = lang
        await session.commit()
    await callback.message.answer(f"✅ Preferred language: **{lang}**", parse_mode="Markdown")
