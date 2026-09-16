import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.credit import CreditKind, CreditLedger

PackId = Literal["starter", "standard", "pro"]


class CreditCostsOut(BaseModel):
    generate: int
    edit: int
    upscale: int
    marketing: int


class CreditPackOut(BaseModel):
    id: PackId
    label: str
    credits: int


class CreditCatalogOut(BaseModel):
    balance: int
    costs: CreditCostsOut
    packs: list[CreditPackOut]


class RechargeIn(BaseModel):
    pack_id: PackId


class LedgerOut(BaseModel):
    id: uuid.UUID
    amount: int
    balance_after: int
    kind: CreditKind
    reason: str
    created_at: datetime

    @classmethod
    def of(cls, entry: CreditLedger) -> "LedgerOut":
        return cls(
            id=entry.id,
            amount=entry.amount,
            balance_after=entry.balance_after,
            kind=entry.kind,
            reason=entry.reason,
            created_at=entry.created_at,
        )


class GiftIn(BaseModel):
    amount: int = Field(gt=0, le=10_000)
    reason: str = Field(default="管理员赠送", max_length=120)

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        return value.strip() or "管理员赠送"
