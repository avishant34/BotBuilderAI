from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import admin_panel_kb, main_menu_kb
from bot.services.user_service import UserService
from bot.states.generation import AdminStates
from core.config import get_settings
from database.db import async_session

router = Router(name="admin")
settings = get_settings()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


@router.message(Command("admin"))
@router.callback_query(F.data == "admin:panel")
async def admin_panel(event: Message | CallbackQuery) -> None:
    user_id = event.from_user.id
    if not is_admin(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("Access denied", show_alert=True)
        else:
            await event.answer("🚫 Admin only.")
        return

    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event

    await message.answer(
        "🛡 **Admin Panel**\n\nStats, block/unblock users, recent activity.",
        parse_mode="Markdown",
        reply_markup=admin_panel_kb(),
    )


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return
    await callback.answer()

    async with async_session() as session:
        service = UserService(session)
        stats = await service.get_stats()

    text = (
        "📊 **System Stats**\n\n"
        f"• Total users: `{stats['total_users']}`\n"
        f"• Blocked users: `{stats['blocked_users']}`\n"
        f"• Total bots generated: `{stats['total_bots']}`\n"
        f"• Bots today: `{stats['bots_today']}`\n"
    )
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=admin_panel_kb())



@router.callback_query(F.data == "admin:metrics")
async def admin_metrics(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return
    await callback.answer()
    from core.metrics import metrics
    snap = metrics.snapshot()
    lines = ["📈 **Runtime Metrics**\n"]
    for k, v in sorted(snap.get("counters", {}).items()):
        lines.append(f"• `{k}`: {v}")
    avg = snap.get("avg_timing_ms") or {}
    if avg:
        lines.append("\n**Avg timings (ms)**")
        for k, v in sorted(avg.items()):
            lines.append(f"• `{k}`: {v}")
    await callback.message.answer("\n".join(lines), parse_mode="Markdown", reply_markup=admin_panel_kb())

@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return
    await callback.answer()

    async with async_session() as session:
        service = UserService(session)
        users = await service.get_recent_users(15)

    if not users:
        await callback.message.answer("No users yet.")
        return

    lines = ["👥 **Recent Users**\n"]
    for u in users:
        status = "🚫" if u.is_blocked else "✅"
        uname = f"@{u.username}" if u.username else u.full_name or "—"
        lines.append(
            f"{status} `{u.telegram_id}` {uname} (bots today: {u.bots_created_today})"
        )
    await callback.message.answer("\n".join(lines), parse_mode="Markdown", reply_markup=admin_panel_kb())


@router.callback_query(F.data == "admin:block")
async def admin_block_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_block_id)
    await callback.message.answer("🚫 Block karne ke liye Telegram user ID bhejo (number):")


@router.message(AdminStates.waiting_block_id)
async def admin_block_process(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        tid = int((message.text or "").strip())
    except ValueError:
        await message.answer("Invalid ID. Number bhejo.")
        return

    async with async_session() as session:
        service = UserService(session)
        ok = await service.set_blocked(tid, True)

    await state.clear()
    if ok:
        await message.answer(f"✅ User `{tid}` blocked.", parse_mode="Markdown", reply_markup=admin_panel_kb())
    else:
        await message.answer(f"User `{tid}` not found in DB. Pehle /start karwao.", parse_mode="Markdown")


@router.callback_query(F.data == "admin:unblock")
async def admin_unblock_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_unblock_id)
    await callback.message.answer("✅ Unblock karne ke liye Telegram user ID bhejo:")


@router.message(AdminStates.waiting_unblock_id)
async def admin_unblock_process(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        tid = int((message.text or "").strip())
    except ValueError:
        await message.answer("Invalid ID.")
        return

    async with async_session() as session:
        service = UserService(session)
        ok = await service.set_blocked(tid, False)

    await state.clear()
    if ok:
        await message.answer(f"✅ User `{tid}` unblocked.", parse_mode="Markdown", reply_markup=admin_panel_kb())
    else:
        await message.answer(f"User `{tid}` not found.", parse_mode="Markdown")
