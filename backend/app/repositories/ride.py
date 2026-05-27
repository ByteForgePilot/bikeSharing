from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ride import Ride


async def create(
    db: AsyncSession, user_id: int, bike_id: str, lat: float, lng: float
) -> Ride:
    ride = Ride(user_id=user_id, bike_id=bike_id, start_lat=lat, start_lng=lng)
    db.add(ride)
    await db.commit()
    await db.refresh(ride)
    return ride


async def get_by_id(db: AsyncSession, ride_id: int) -> Ride | None:
    return await db.get(Ride, ride_id)


async def end(db: AsyncSession, ride: Ride, lat: float, lng: float) -> Ride:
    ride.end_lat = lat
    ride.end_lng = lng
    ride.ended_at = datetime.now(timezone.utc)
    ride.status = "completed"
    await db.commit()
    return ride


async def list_by_user(
    db: AsyncSession, user_id: int, limit: int, offset: int
) -> tuple[list[Ride], int]:
    count_q = select(func.count()).select_from(Ride).where(Ride.user_id == user_id)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Ride)
        .where(Ride.user_id == user_id)
        .order_by(Ride.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(q)
    return result.scalars().all(), total
