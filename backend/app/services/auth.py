import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionFactory
from app.models import CreditKind, User, UserRole
from app.security import hash_password, verify_password
from app.services import credits


class UsernameTaken(Exception):
    pass


class InvalidCredentials(Exception):
    pass


async def register(session: AsyncSession, username: str, password: str) -> User:
    user = User(username=username, password_hash=hash_password(password))
    session.add(user)
    try:
        await session.flush()
        bonus = get_settings().credit_signup_bonus
        if bonus > 0:
            await credits.grant(
                session, user.id, bonus, kind=CreditKind.SIGNUP, reason="注册赠送"
            )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise UsernameTaken from exc
    return user


async def authenticate(session: AsyncSession, username: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentials
    return user


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def ensure_bootstrap_admin() -> None:
    """启动时确保引导管理员存在。已有同名用户只提升角色，不改密码。"""
    settings = get_settings()
    username = settings.bootstrap_admin_username.strip()
    password = settings.bootstrap_admin_password
    if not username or not password:
        return

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
            session.add(user)
            await session.flush()
            bonus = settings.credit_signup_bonus
            if bonus > 0:
                await credits.grant(
                    session, user.id, bonus, kind=CreditKind.SIGNUP, reason="注册赠送"
                )
        elif user.role is not UserRole.ADMIN:
            user.role = UserRole.ADMIN
        await session.commit()
