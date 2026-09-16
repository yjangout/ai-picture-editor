from datetime import datetime

from pydantic import BaseModel

from app.models.user import User, UserRole
from app.schemas.auth import UserOut
from app.schemas.credits import LedgerOut


class AdminUserOut(UserOut):
    created_at: datetime


class AdminUserListOut(BaseModel):
    items: list[AdminUserOut]
    total: int
    admin_count: int
    credits_total: int


class AdminLedgerListOut(BaseModel):
    items: list[LedgerOut]
    total: int


class RoleIn(BaseModel):
    role: UserRole


def admin_user_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        credits=user.credits,
        created_at=user.created_at,
    )
