import uuid

import httpx
import pytest
from sqlalchemy import select

from app.db import SessionFactory
from app.models import CreditKind, User
from app.models.tool_run import RunStatus
from app.providers import ProviderError
from app.services import runs
from app.tasks.tools import run_tool


@pytest.fixture
async def signed_in(client: httpx.AsyncClient, credentials):
    await client.post("/api/auth/register", json=credentials)
    return client


async def test_register_grants_signup_bonus(signed_in: httpx.AsyncClient):
    me = (await signed_in.get("/api/auth/me")).json()

    assert me["role"] == "user"
    assert me["credits"] == 100

    catalog = (await signed_in.get("/api/credits/catalog")).json()
    assert catalog["balance"] == 100
    assert catalog["costs"]["generate"] == 10
    assert {pack["id"] for pack in catalog["packs"]} == {"starter", "standard", "pro"}


async def test_generation_deducts_credits_per_image(signed_in: httpx.AsyncClient):
    response = await signed_in.post(
        "/api/generations", json={"prompt": "浅木色桌面上的白色马克杯", "count": 2}
    )

    assert response.status_code == 202
    me = (await signed_in.get("/api/auth/me")).json()
    assert me["credits"] == 80


async def test_generation_rejected_when_balance_is_too_low(
    signed_in: httpx.AsyncClient, credentials
):
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.username == credentials["username"]))
        user.credits = 5
        await session.commit()

    response = await signed_in.post(
        "/api/generations", json={"prompt": "杯子", "ratio": "1:1", "count": 1}
    )

    assert response.status_code == 402
    assert "积分不足" in response.json()["detail"]
    me = (await signed_in.get("/api/auth/me")).json()
    assert me["credits"] == 5


async def test_failed_generation_refunds_credits(signed_in: httpx.AsyncClient, monkeypatch):
    class Boom:
        async def generate(self, request, on_progress=None):
            raise ProviderError("模型失败")

    monkeypatch.setattr("app.services.generation.get_image_provider", lambda: Boom())

    response = await signed_in.post(
        "/api/generations", json={"prompt": "杯子", "ratio": "1:1", "count": 1}
    )
    assert response.status_code == 202
    assert (await signed_in.get("/api/auth/me")).json()["credits"] == 90

    run_id = uuid.UUID(response.json()["id"])
    await run_tool({}, run_id)

    async with SessionFactory() as session:
        run = await runs.load(session, run_id)
        assert run.status is RunStatus.FAILED

    assert (await signed_in.get("/api/auth/me")).json()["credits"] == 100
    ledger = (await signed_in.get("/api/credits/ledger")).json()
    kinds = [item["kind"] for item in ledger]
    assert CreditKind.REFUND.value in kinds
    assert CreditKind.CONSUME.value in kinds


async def test_free_tool_still_works_without_credits(
    signed_in: httpx.AsyncClient, credentials
):
    from tests.test_sessions import open_session

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.username == credentials["username"]))
        user.credits = 0
        await session.commit()

    session_id = (await open_session(signed_in))["id"]
    response = await signed_in.post(
        f"/api/sessions/{session_id}/tools",
        json={"tool": "flip_layer", "params": {"direction": "horizontal"}},
    )

    assert response.status_code == 202
    assert response.json()["run"]["status"] == "succeeded"
    assert (await signed_in.get("/api/auth/me")).json()["credits"] == 0


async def test_recharge_pack_credits_account(signed_in: httpx.AsyncClient):
    response = await signed_in.post("/api/credits/recharge", json={"pack_id": "starter"})

    assert response.status_code == 200
    assert response.json()["balance"] == 150
    assert (await signed_in.get("/api/auth/me")).json()["credits"] == 150

    ledger = (await signed_in.get("/api/credits/ledger")).json()
    assert ledger[0]["kind"] == "recharge"
    assert ledger[0]["amount"] == 50


async def test_ledger_is_isolated_per_user(
    client: httpx.AsyncClient, credentials, other_credentials
):
    await client.post("/api/auth/register", json=credentials)
    await client.post("/api/credits/recharge", json={"pack_id": "pro"})
    mine = (await client.get("/api/credits/ledger")).json()
    assert any(item["kind"] == "recharge" and item["amount"] == 500 for item in mine)

    await client.post("/api/auth/logout")
    await client.post("/api/auth/register", json=other_credentials)
    other = (await client.get("/api/credits/ledger")).json()
    assert all(item["kind"] == "signup" for item in other)


async def test_catalog_requires_login(client: httpx.AsyncClient):
    assert (await client.get("/api/credits/catalog")).status_code == 401
    assert (await client.post("/api/credits/recharge", json={"pack_id": "starter"})).status_code == 401
