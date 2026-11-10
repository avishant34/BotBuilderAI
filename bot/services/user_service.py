from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from database.models import ConversationContext, GeneratedBot, User


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def get_or_create_user(
        self, telegram_id: int, username: Optional[str] = None, full_name: Optional[str] = None
    ) -> User:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        else:
            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                changed = True
            if changed:
                await self.session.commit()
        return user

    async def can_generate(self, user: User) -> bool:
        if user.is_blocked:
            return False
        today = date.today().isoformat()
        if user.last_generation_date != today:
            user.bots_created_today = 0
            user.last_generation_date = today
            await self.session.commit()
        return user.bots_created_today < self.settings.MAX_BOTS_PER_DAY

    async def increment_generation(self, user: User) -> None:
        today = date.today().isoformat()
        if user.last_generation_date != today:
            user.bots_created_today = 0
            user.last_generation_date = today
        user.bots_created_today += 1
        await self.session.commit()

    async def save_generated_bot(
        self,
        user: User,
        bot_name: str,
        display_name: str,
        category: str,
        idea: str,
        requirements: Dict[str, Any],
        files: Dict[str, str],
        review: Dict[str, Any],
        is_safe: bool,
        github_url: Optional[str] = None,
    ) -> GeneratedBot:
        record = GeneratedBot(
            user_id=user.id,
            telegram_id=user.telegram_id,
            bot_name=bot_name,
            display_name=display_name,
            category=category,
            idea=idea,
            requirements_json=json.dumps(requirements, ensure_ascii=False),
            files_json=json.dumps(files, ensure_ascii=False),
            review_json=json.dumps(review, ensure_ascii=False) if review else None,
            is_safe=is_safe,
            github_url=github_url,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_user_bots(self, telegram_id: int, limit: int = 10) -> List[GeneratedBot]:
        result = await self.session.execute(
            select(GeneratedBot)
            .where(GeneratedBot.telegram_id == telegram_id)
            .order_by(GeneratedBot.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_bot_by_id(self, bot_id: int, telegram_id: int) -> Optional[GeneratedBot]:
        result = await self.session.execute(
            select(GeneratedBot).where(
                GeneratedBot.id == bot_id, GeneratedBot.telegram_id == telegram_id
            )
        )
        return result.scalar_one_or_none()

    async def save_context(self, telegram_id: int, state: str, data: Dict[str, Any]) -> None:
        result = await self.session.execute(
            select(ConversationContext).where(ConversationContext.telegram_id == telegram_id)
        )
        ctx = result.scalar_one_or_none()
        if ctx is None:
            ctx = ConversationContext(
                telegram_id=telegram_id,
                state=state,
                data_json=json.dumps(data, ensure_ascii=False),
            )
            self.session.add(ctx)
        else:
            ctx.state = state
            ctx.data_json = json.dumps(data, ensure_ascii=False)
        await self.session.commit()

    async def get_context(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            select(ConversationContext).where(ConversationContext.telegram_id == telegram_id)
        )
        ctx = result.scalar_one_or_none()
        if ctx is None:
            return None
        return {
            "state": ctx.state,
            "data": json.loads(ctx.data_json or "{}"),
        }

    async def clear_context(self, telegram_id: int) -> None:
        result = await self.session.execute(
            select(ConversationContext).where(ConversationContext.telegram_id == telegram_id)
        )
        ctx = result.scalar_one_or_none()
        if ctx:
            await self.session.delete(ctx)
            await self.session.commit()

    # ─── Admin helpers ───

    async def get_stats(self) -> Dict[str, Any]:
        total_users = (await self.session.execute(select(func.count(User.id)))).scalar() or 0
        blocked = (
            await self.session.execute(select(func.count(User.id)).where(User.is_blocked == True))  # noqa: E712
        ).scalar() or 0
        total_bots = (await self.session.execute(select(func.count(GeneratedBot.id)))).scalar() or 0
        today = date.today().isoformat()
        bots_today = (
            await self.session.execute(
                select(func.count(GeneratedBot.id)).where(
                    func.date(GeneratedBot.created_at) == today
                )
            )
        ).scalar() or 0
        return {
            "total_users": total_users,
            "blocked_users": blocked,
            "total_bots": total_bots,
            "bots_today": bots_today,
        }

    async def get_recent_users(self, limit: int = 15) -> List[User]:
        result = await self.session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def set_blocked(self, telegram_id: int, blocked: bool) -> bool:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.is_blocked = blocked
        await self.session.commit()
        return True

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()
