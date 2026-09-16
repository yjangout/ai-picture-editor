from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from app.db import SessionDep
from app.models import User, UserRole
from app.security import SESSION_COOKIE, read_token
from app.services import auth as auth_service

_UNAUTHENTICATED = HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或会话已过期")
_FORBIDDEN = HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")


async def current_user(
    session: SessionDep,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    if token is None:
        raise _UNAUTHENTICATED

    user_id = read_token(token)
    if user_id is None:
        raise _UNAUTHENTICATED

    user = await auth_service.get_by_id(session, user_id)
    if user is None:
        raise _UNAUTHENTICATED
    return user


async def current_admin(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role is not UserRole.ADMIN:
        raise _FORBIDDEN
    return user


CurrentUser = Annotated[User, Depends(current_user)]
CurrentAdmin = Annotated[User, Depends(current_admin)]
