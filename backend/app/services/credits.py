import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models import CreditKind, CreditLedger, User
from app.schemas.credits import CreditCatalogOut, CreditCostsOut, CreditPackOut

PACK_LABELS = {
    "starter": "体验包",
    "standard": "标准包",
    "pro": "专业包",
}

_MODEL_BATCH_TOOLS = {
    "replace_background": "edit",
    "expand_canvas": "edit",
    "upscale_image": "upscale",
}


class InsufficientCredits(Exception):
    def __init__(self, needed: int, balance: int):
        self.needed = needed
        self.balance = balance
        super().__init__(f"积分不足，需要 {needed}，当前余额 {balance}")


class UnknownPack(Exception):
    pass


def costs_of(settings: Settings | None = None) -> CreditCostsOut:
    settings = settings or get_settings()
    return CreditCostsOut(
        generate=settings.credit_cost_generate,
        edit=settings.credit_cost_edit,
        upscale=settings.credit_cost_upscale,
        marketing=settings.credit_cost_marketing,
    )


def packs_of(settings: Settings | None = None) -> list[CreditPackOut]:
    settings = settings or get_settings()
    raw = {
        "starter": settings.credit_pack_starter,
        "standard": settings.credit_pack_standard,
        "pro": settings.credit_pack_pro,
    }
    return [
        CreditPackOut(id=pack_id, label=PACK_LABELS[pack_id], credits=credits)
        for pack_id, credits in raw.items()
        if credits > 0
    ]


def catalog_of(balance: int, settings: Settings | None = None) -> CreditCatalogOut:
    settings = settings or get_settings()
    return CreditCatalogOut(balance=balance, costs=costs_of(settings), packs=packs_of(settings))


def pack_credits(pack_id: str, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    mapping = {
        "starter": settings.credit_pack_starter,
        "standard": settings.credit_pack_standard,
        "pro": settings.credit_pack_pro,
    }
    credits = mapping.get(pack_id, 0)
    if credits <= 0:
        raise UnknownPack
    return credits


def _count(params: dict, key: str = "count") -> int:
    raw = params.get(key, 1)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 1


def _unit(settings: Settings, kind: str) -> int:
    if kind == "generate":
        return settings.credit_cost_generate
    if kind == "edit":
        return settings.credit_cost_edit
    if kind == "upscale":
        return settings.credit_cost_upscale
    if kind == "marketing":
        return settings.credit_cost_marketing
    return 0


def _batch_cost(params: dict, settings: Settings) -> int:
    assets = params.get("asset_ids") or []
    per_image = 0
    for operation in params.get("operations") or []:
        name = operation.get("tool") if isinstance(operation, dict) else None
        kind = _MODEL_BATCH_TOOLS.get(name or "")
        if kind:
            per_image += _unit(settings, kind)
    return len(assets) * per_image


def cost_of(tool: str, params: dict | None = None) -> int:
    """按工具与参数计算应扣积分。本地处理为 0。"""
    settings = get_settings()
    params = params or {}
    if tool == "generate_image":
        return _unit(settings, "generate") * _count(params)
    if tool in {"replace_background", "expand_canvas", "erase_region", "replace_region"}:
        return _unit(settings, "edit") * _count(params)
    if tool == "upscale_image":
        return _unit(settings, "upscale")
    if tool == "generate_marketing":
        return _unit(settings, "marketing") * _count(params)
    if tool == "batch_process":
        return _batch_cost(params, settings)
    return 0


async def _lock_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id, with_for_update=True)
    if user is None:
        raise RuntimeError("用户不存在")
    return user


async def grant(
    session: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
    *,
    kind: CreditKind,
    reason: str,
    ref_type: str | None = None,
    ref_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
) -> User:
    if amount <= 0:
        raise ValueError("入账积分必须为正数")
    user = await _lock_user(session, user_id)
    user.credits += amount
    session.add(
        CreditLedger(
            user_id=user.id,
            amount=amount,
            balance_after=user.credits,
            kind=kind,
            reason=reason,
            ref_type=ref_type,
            ref_id=ref_id,
            actor_id=actor_id,
        )
    )
    return user


async def require_balance(session: AsyncSession, user_id: uuid.UUID, amount: int) -> User:
    user = await _lock_user(session, user_id)
    if amount > 0 and user.credits < amount:
        raise InsufficientCredits(amount, user.credits)
    return user


async def consume(
    session: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
    *,
    reason: str,
    ref_type: str | None = None,
    ref_id: uuid.UUID | None = None,
) -> User:
    if amount < 0:
        raise ValueError("扣费积分不能为负")
    if amount == 0:
        return await _lock_user(session, user_id)
    user = await _lock_user(session, user_id)
    if user.credits < amount:
        raise InsufficientCredits(amount, user.credits)
    user.credits -= amount
    session.add(
        CreditLedger(
            user_id=user.id,
            amount=-amount,
            balance_after=user.credits,
            kind=CreditKind.CONSUME,
            reason=reason,
            ref_type=ref_type,
            ref_id=ref_id,
        )
    )
    return user


async def refund_run(session: AsyncSession, run) -> None:
    amount = run.credits_charged
    if amount <= 0:
        return
    existing = await session.scalar(
        select(CreditLedger.id).where(
            CreditLedger.ref_id == run.id,
            CreditLedger.kind == CreditKind.REFUND,
        )
    )
    if existing is not None:
        return
    await grant(
        session,
        run.user_id,
        amount,
        kind=CreditKind.REFUND,
        reason="任务失败退回",
        ref_type="tool_run",
        ref_id=run.id,
    )
    await session.commit()


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[CreditLedger]:
    result = await session.scalars(
        select(CreditLedger)
        .where(CreditLedger.user_id == user_id)
        .order_by(CreditLedger.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result)
