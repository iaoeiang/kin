"""Kin API — Auth & Registration Tests"""
import pytest
from httpx import AsyncClient, ASGITransport
from agentnet.main import app

BASE = "/api"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def test_email():
    import uuid
    return f"test_{uuid.uuid4().hex[:8]}@kin-test.dev"


@pytest.mark.asyncio(loop_scope="session")
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio(loop_scope="session")
async def test_send_code_rejects_bad_email():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(f"{BASE}/auth/send-code", json={"email": "not-an-email"})
        assert r.status_code == 422  # validation error


@pytest.mark.asyncio(loop_scope="session")
async def test_registration_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing fields in verify-code
        r = await client.post(f"{BASE}/auth/verify-code", json={"email": "a@b.com"})
        assert r.status_code == 422

        # Weak password
        r = await client.post(f"{BASE}/auth/complete-registration", json={
            "verification_token": "t", "password": "123", "display_name": "T",
        })
        assert r.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
async def test_send_code():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(f"{BASE}/auth/send-code", json={
            "email": f"test_{__import__('uuid').uuid4().hex[:8]}@kin-test.dev"
        })
        # Accept any 2xx response (the endpoint sends via Agent Mail)
        assert 200 <= r.status_code < 300, f"send-code failed: {r.text}"
