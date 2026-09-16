import httpx
import pytest
from sqlalchemy import select

from app.db import SessionFactory
from app.models import User, UserRole


@pytest.fixture
async def signed_in(client: httpx.AsyncClient, credentials):
    await client.post("/api/auth/register", json=credentials)
    return client


async def _promote(username: str) -> None:
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.username == username))
        user.role = UserRole.ADMIN
        await session.commit()


async def test_admin_routes_reject_regular_users(signed_in: httpx.AsyncClient):
    assert (await signed_in.get("/api/admin/users")).status_code == 403
    assert (await signed_in.get("/api/admin/ledger")).status_code == 403


async def test_admin_can_list_users_and_gift_credits(
    client: httpx.AsyncClient, credentials, other_credentials
):
    await client.post("/api/auth/register", json=other_credentials)
    target_id = (await client.get("/api/auth/me")).json()["id"]
    await client.post("/api/auth/logout")

    await client.post("/api/auth/register", json=credentials)
    await _promote(credentials["username"])

    listing = await client.get("/api/admin/users")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] >= 2
    assert any(item["username"] == other_credentials["username"] for item in body["items"])

    gifted = await client.post(
        f"/api/admin/users/{target_id}/gift",
        json={"amount": 40, "reason": "活动赠送"},
    )
    assert gifted.status_code == 200
    assert gifted.json()["credits"] == 140

    await client.post("/api/auth/logout")
    await client.post("/api/auth/login", json=other_credentials)
    me = (await client.get("/api/auth/me")).json()
    assert me["credits"] == 140
    ledger = (await client.get("/api/credits/ledger")).json()
    assert ledger[0]["kind"] == "gift"
    assert ledger[0]["amount"] == 40
    assert ledger[0]["reason"] == "活动赠送"


async def test_admin_cannot_gift_missing_user(signed_in: httpx.AsyncClient, credentials):
    await _promote(credentials["username"])
    response = await signed_in.post(
        "/api/admin/users/00000000-0000-0000-0000-000000000000/gift",
        json={"amount": 10, "reason": "测试"},
    )
    assert response.status_code == 404


async def test_admin_search_filters_users(
    client: httpx.AsyncClient, credentials, other_credentials
):
    await client.post("/api/auth/register", json=other_credentials)
    await client.post("/api/auth/logout")
    await client.post("/api/auth/register", json=credentials)
    await _promote(credentials["username"])

    found = await client.get(f"/api/admin/users?q={other_credentials['username']}")
    assert found.status_code == 200
    names = [item["username"] for item in found.json()["items"]]
    assert names == [other_credentials["username"]]


async def test_admin_can_promote_and_cannot_demote_self(
    signed_in: httpx.AsyncClient, credentials, other_credentials
):
    await _promote(credentials["username"])
    me = (await signed_in.get("/api/auth/me")).json()

    denied = await signed_in.patch(f"/api/admin/users/{me['id']}", json={"role": "user"})
    assert denied.status_code == 409

    await signed_in.post("/api/auth/logout")
    await signed_in.post("/api/auth/register", json=other_credentials)
    other_id = (await signed_in.get("/api/auth/me")).json()["id"]
    await signed_in.post("/api/auth/logout")
    await signed_in.post("/api/auth/login", json=credentials)

    promoted = await signed_in.patch(f"/api/admin/users/{other_id}", json={"role": "admin"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "admin"
