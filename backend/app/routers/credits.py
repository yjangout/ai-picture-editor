from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.db import SessionDep
from app.deps import CurrentUser
from app.models import CreditKind
from app.schemas.credits import CreditCatalogOut, LedgerOut, RechargeIn
from app.services import credits

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/catalog")
async def catalog(user: CurrentUser) -> CreditCatalogOut:
    return credits.catalog_of(user.credits)


@router.get("/ledger")
async def ledger(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[LedgerOut]:
    entries = await credits.list_for_user(session, user.id, limit=limit)
    return [LedgerOut.of(entry) for entry in entries]


@router.post("/recharge")
async def recharge(
    payload: RechargeIn, user: CurrentUser, session: SessionDep
) -> CreditCatalogOut:
    try:
        amount = credits.pack_credits(payload.pack_id)
    except credits.UnknownPack:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "该充值套餐已关闭") from None
    updated = await credits.grant(
        session,
        user.id,
        amount,
        kind=CreditKind.RECHARGE,
        reason=f"充值{credits.PACK_LABELS[payload.pack_id]}",
    )
    await session.commit()
    return credits.catalog_of(updated.credits)
