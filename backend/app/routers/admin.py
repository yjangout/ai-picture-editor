import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.db import SessionDep
from app.deps import CurrentAdmin
from app.models import CreditKind, CreditLedger, User, UserRole
from app.schemas.admin import AdminLedgerListOut, AdminUserListOut, AdminUserOut, RoleIn, admin_user_out
from app.schemas.credits import GiftIn, LedgerOut
from app.services import credits

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    _: CurrentAdmin,
    session: SessionDep,
    q: Annotated[str, Query(max_length=32)] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminUserListOut:
    filtered = select(User)
    keyword = q.strip()
    if keyword:
        filtered = filtered.where(User.username.ilike(f"%{keyword}%"))

    total = await session.scalar(select(func.count()).select_from(filtered.subquery()))
    admin_count = await session.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)
    )
    credits_total = await session.scalar(select(func.coalesce(func.sum(User.credits), 0)))
    items = await session.scalars(
        filtered.order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    return AdminUserListOut(
        items=[admin_user_out(user) for user in items],
        total=total or 0,
        admin_count=admin_count or 0,
        credits_total=int(credits_total or 0),
    )


@router.get("/users/{user_id}")
async def get_user(user_id: uuid.UUID, _: CurrentAdmin, session: SessionDep) -> AdminUserOut:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    return admin_user_out(user)


@router.post("/users/{user_id}/gift")
async def gift_credits(
    user_id: uuid.UUID, payload: GiftIn, admin: CurrentAdmin, session: SessionDep
) -> AdminUserOut:
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    updated = await credits.grant(
        session,
        target.id,
        payload.amount,
        kind=CreditKind.GIFT,
        reason=payload.reason,
        actor_id=admin.id,
    )
    await session.commit()
    await session.refresh(updated)
    return admin_user_out(updated)


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: uuid.UUID, payload: RoleIn, admin: CurrentAdmin, session: SessionDep
):
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    if payload.role is UserRole.USER and target.role is UserRole.ADMIN:
        others = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.ADMIN, User.id != target.id)
        )
        if not others:
            raise HTTPException(status.HTTP_409_CONFLICT, "不能取消最后一名管理员")
        if target.id == admin.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "不能取消自己的管理员身份")
    target.role = payload.role
    await session.commit()
    await session.refresh(target)
    return admin_user_out(target)


@router.get("/ledger")
async def list_ledger(
    _: CurrentAdmin,
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminLedgerListOut:
    stmt = select(CreditLedger)
    count_stmt = select(func.count()).select_from(CreditLedger)
    if user_id is not None:
        stmt = stmt.where(CreditLedger.user_id == user_id)
        count_stmt = count_stmt.where(CreditLedger.user_id == user_id)
    total = await session.scalar(count_stmt)
    entries = await session.scalars(
        stmt.order_by(CreditLedger.created_at.desc()).offset(offset).limit(limit)
    )
    return AdminLedgerListOut(
        items=[LedgerOut.of(entry) for entry in entries],
        total=total or 0,
    )
