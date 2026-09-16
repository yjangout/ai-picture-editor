import enum
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDBase, enum_column


class CreditKind(enum.StrEnum):
    SIGNUP = "signup"
    RECHARGE = "recharge"
    GIFT = "gift"
    CONSUME = "consume"
    REFUND = "refund"


class CreditLedger(UUIDBase):
    """积分流水。amount 带符号：入账为正，消耗为负。"""

    __tablename__ = "credit_ledger"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[int]
    balance_after: Mapped[int]
    kind: Mapped[CreditKind] = mapped_column(enum_column(CreditKind))
    reason: Mapped[str] = mapped_column(String(120))
    ref_type: Mapped[str | None] = mapped_column(String(32), default=None)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
