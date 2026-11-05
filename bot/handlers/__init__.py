from aiogram import Router

from bot.handlers import start, generation, admin


def setup_routers() -> Router:
    root = Router()
    root.include_router(start.router)
    root.include_router(generation.router)
    root.include_router(admin.router)
    return root
