"""
BotBuilderAI – Production pure Telegram bot.
Default: polling. Optional webhook via aiohttp (no web UI).
"""
from __future__ import annotations

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from bot.handlers import setup_routers
from bot.middlewares import ErrorMiddleware
from core.config import get_settings
from core.metrics import metrics
from database.db import init_db


def setup_logging() -> None:
    settings = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    )
    try:
        logger.add(
            "logs/bot_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            level="DEBUG",
            encoding="utf-8",
        )
    except Exception:
        pass


def validate_startup() -> None:
    """Fail fast on bad config."""
    s = get_settings()
    errors = []
    if not s.BOT_TOKEN or s.BOT_TOKEN.startswith("your_"):
        errors.append("BOT_TOKEN missing or placeholder")
    if not s.LLM_API_KEY or s.LLM_API_KEY.startswith("sk-your"):
        errors.append("LLM_API_KEY missing or placeholder")
    if s.USE_WEBHOOK and (not s.WEBHOOK_HOST or "your-domain" in s.WEBHOOK_HOST):
        errors.append("USE_WEBHOOK=true but WEBHOOK_HOST not set")
    if errors:
        for e in errors:
            logger.error(f"Config: {e}")
        raise SystemExit("Invalid configuration — fix .env and restart")


async def create_storage():
    settings = get_settings()
    if settings.USE_REDIS:
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            from redis.asyncio import Redis

            redis = Redis.from_url(settings.REDIS_URL)
            await redis.ping()
            logger.info("Redis FSM connected")
            return RedisStorage(redis=redis)
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), MemoryStorage fallback")
    return MemoryStorage()


async def run_bot() -> None:
    setup_logging()
    validate_startup()
    settings = get_settings()

    logger.info("BotBuilderAI starting")
    logger.info(f"env={settings.ENVIRONMENT} llm={settings.LLM_PROVIDER}/{settings.LLM_MODEL}")

    await init_db()
    logger.info("DB ready")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    storage = await create_storage()
    dp = Dispatcher(storage=storage)
    dp.update.middleware(ErrorMiddleware())
    dp.include_router(setup_routers())

    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    logger.info(f"Bot online as @{me.username} (id={me.id})")
    metrics.incr("bot.starts")

    if settings.USE_WEBHOOK:
        from aiohttp import web
        from aiogram.types import Update

        async def handle_webhook(request: web.Request) -> web.Response:
            secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if settings.WEBHOOK_SECRET and secret != settings.WEBHOOK_SECRET:
                return web.Response(status=403, text="Forbidden")
            data = await request.json()
            update = Update.model_validate(data, context={"bot": bot})
            await dp.feed_update(bot=bot, update=update)
            return web.Response(text="OK")

        async def health(_: web.Request) -> web.Response:
            return web.json_response(
                {"status": "ok", "bot": me.username, "metrics": metrics.snapshot()}
            )

        app = web.Application()
        app.router.add_post(settings.WEBHOOK_PATH, handle_webhook)
        app.router.add_get("/health", health)

        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.WEBHOOK_SECRET or None,
            drop_pending_updates=True,
        )
        logger.info(f"Webhook → {settings.webhook_url}")

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, settings.WEBAPP_HOST, settings.WEBAPP_PORT)
        await site.start()
        try:
            await asyncio.Event().wait()
        finally:
            await bot.delete_webhook()
            await runner.cleanup()
            await bot.session.close()
    else:
        logger.info("POLLING mode")
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        finally:
            await bot.session.close()
            logger.info(f"Stopped | metrics={metrics.snapshot()}")


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Stopped.")
