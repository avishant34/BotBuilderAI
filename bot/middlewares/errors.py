"""Global error middleware — never crash the bot on handler exceptions."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger

from core.metrics import metrics


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            metrics.error("handler", str(e))
            logger.exception(f"Handler error: {e}")
            text = "⚠️ Kuch technical error aa gaya. /cancel karke phir try karo."
            try:
                if isinstance(event, Message):
                    await event.answer(text)
                elif isinstance(event, CallbackQuery):
                    await event.answer("Error", show_alert=True)
                    if event.message:
                        await event.message.answer(text)
            except Exception:
                pass
            return None
