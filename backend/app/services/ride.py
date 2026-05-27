from fastapi import HTTPException

from app.models.user import User
from app.repositories import ride as ride_repo


async def start_ride(db, user: User, bike_id: str, lat: float, lng: float):
    return await ride_repo.create(db, user_id=user.id, bike_id=bike_id, lat=lat, lng=lng)


async def end_ride(db, user: User, ride_id: int, lat: float, lng: float):
    ride = await ride_repo.get_by_id(db, ride_id)
    if not ride or ride.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ride not found")
    return await ride_repo.end(db, ride, lat, lng)


async def list_user_rides(db, user: User, limit: int, offset: int):
    rides, total = await ride_repo.list_by_user(db, user.id, limit, offset)
    return {
        "rides": [
            {
                "id": r.id,
                "bike_id": r.bike_id,
                "start_lat": r.start_lat,
                "start_lng": r.start_lng,
                "end_lat": r.end_lat,
                "end_lng": r.end_lng,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                "status": r.status,
            }
            for r in rides
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get_ride_detail(db, user: User, ride_id: int):
    ride = await ride_repo.get_by_id(db, ride_id)
    if not ride or ride.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ride not found")
    return ride


async def verify_ride_ownership(db, user: User, ride_id: int):
    ride = await ride_repo.get_by_id(db, ride_id)
    if not ride or ride.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ride not found")
    return ride
