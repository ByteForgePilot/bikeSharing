import math
import random

import pytest


@pytest.mark.asyncio
async def test_full_ride_lifecycle(client):
    """End-to-end: register → login → start ride → end ride → list rides → get ride."""
    # Register & login
    await client.post(
        "/api/auth/register",
        json={"username": "rider1", "password": "testpass"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        data={"username": "rider1", "password": "testpass"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Start ride
    resp = await client.post(
        "/api/rides/start?bike_id=bike001&lat=39.9042&lng=116.4074",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Ride started"
    ride_id = data["ride"]["id"]
    assert data["ride"]["bike_id"] == "bike001"
    assert data["ride"]["status"] == "active"

    # End ride
    resp = await client.post(
        f"/api/rides/{ride_id}/end?lat=39.9142&lng=116.4174",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # List rides
    resp = await client.get("/api/rides/", headers=headers)
    assert resp.status_code == 200
    rides_data = resp.json()
    assert rides_data["total"] >= 1
    assert any(r["id"] == ride_id for r in rides_data["rides"])

    # Get ride detail
    resp = await client.get(f"/api/rides/{ride_id}", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()["ride"]
    assert detail["id"] == ride_id
    assert detail["status"] == "completed"
    assert detail["end_lat"] is not None


@pytest.mark.asyncio
async def test_list_rides_pagination(client):
    """Test pagination: create 3 rides, verify limit/offset."""
    await client.post(
        "/api/auth/register",
        json={"username": "rider2", "password": "testpass"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        data={"username": "rider2", "password": "testpass"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(3):
        await client.post(
            f"/api/rides/start?bike_id=bike_{i}&lat=0&lng=0",
            headers=headers,
        )
        await client.post(
            f"/api/rides/{i+1}/end",
            headers=headers,
        )

    # First page
    resp = await client.get("/api/rides/?limit=2&offset=0", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["rides"]) == 2

    # Second page
    resp = await client.get("/api/rides/?limit=2&offset=2", headers=headers)
    assert len(resp.json()["rides"]) == 1


@pytest.mark.asyncio
async def test_ride_isolation_between_users(client):
    """User A cannot see User B's rides."""
    # User A
    await client.post(
        "/api/auth/register",
        json={"username": "userA", "password": "testpass"},
    )
    resp_a = await client.post(
        "/api/auth/login",
        data={"username": "userA", "password": "testpass"},
    )
    token_a = resp_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    await client.post(
        "/api/rides/start?bike_id=bike_A",
        headers=headers_a,
    )

    # User B
    await client.post(
        "/api/auth/register",
        json={"username": "userB", "password": "testpass"},
    )
    resp_b = await client.post(
        "/api/auth/login",
        data={"username": "userB", "password": "testpass"},
    )
    token_b = resp_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B tries to access User A's ride
    resp = await client.get("/api/rides/1", headers=headers_b)
    assert resp.status_code == 404

    # User B's list is empty
    resp = await client.get("/api/rides/", headers=headers_b)
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_ride_not_found(client):
    """Accessing non-existent ride returns 404."""
    await client.post(
        "/api/auth/register",
        json={"username": "rider404", "password": "testpass"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        data={"username": "rider404", "password": "testpass"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/rides/99999", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_username_registration(client):
    """Registering the same username twice returns 400."""
    await client.post(
        "/api/auth/register",
        json={"username": "dup_user", "password": "testpass"},
    )
    resp = await client.post(
        "/api/auth/register",
        json={"username": "dup_user", "password": "testpass"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_detection_with_ride(client):
    """Run wheel wobble detection within a ride context."""
    await client.post(
        "/api/auth/register",
        json={"username": "detector", "password": "testpass"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        data={"username": "detector", "password": "testpass"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Start a ride
    resp = await client.post(
        "/api/rides/start?bike_id=bike_detect",
        headers=headers,
    )
    ride_id = resp.json()["ride"]["id"]

    # Submit sensor data for wobble detection
    samples = []
    for i in range(125):
        t = i / 50.0
        wobble = 0.5 * math.sin(2 * math.pi * 3 * t) + 0.1 * random.random()
        samples.append({"x": wobble, "y": 0.1, "z": 0.2, "timestamp": t})

    resp = await client.post(
        f"/api/detection/wheel-wobble/{ride_id}",
        json={"accelerometer_data": samples, "sample_rate": 50.0},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["wheel_wobble"]["detected"] in ("normal", "suspect", "fault")

    # End the ride
    await client.post(f"/api/rides/{ride_id}/end", headers=headers)

    # Report
    resp = await client.get(f"/api/detection/report/{ride_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["overall_status"] == "pending"
