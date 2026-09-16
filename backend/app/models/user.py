import enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDBase, enum_column


class UserRole(enum.StrEnum):
    USER = "user"
    ADMIN = "admin"


class User(UUIDBase):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole), default=UserRole.USER)
    credits: Mapped[int] = mapped_column(default=0)
