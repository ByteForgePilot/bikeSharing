import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_and_login(client):
    # Register
    resp = await client.post(
        "/api/auth/register",
        json={"username": "testuser", "password": "testpass"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"

    # Login
    resp = await client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpass"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    token = resp.json()["access_token"]

    # Me
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_wheel_wobble_detection(client):
    # Register & login
    await client.post(
        "/api/auth/register",
        json={"username": "testuser2", "password": "testpass"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        data={"username": "testuser2", "password": "testpass"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate 2.5 seconds of sample data (125 samples at 50 Hz)
    import math, random
    samples = []
    for i in range(125):
        t = i / 50.0
        # Simulate wobble: 3 Hz sinusoid with noise
        wobble = 0.5 * math.sin(2 * math.pi * 3 * t) + 0.1 * random.random()
        samples.append({"x": wobble, "y": 0.1, "z": 0.2, "timestamp": t})

    resp = await client.post(
        "/api/detection/wheel-wobble/1",
        json={"accelerometer_data": samples, "sample_rate": 50.0},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "wheel_wobble" in data
    assert data["wheel_wobble"]["detected"] in ("normal", "suspect", "fault")
