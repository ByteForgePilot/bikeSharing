import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fault_report import FaultReport


async def get_by_ride_id(db: AsyncSession, ride_id: int) -> Optional[FaultReport]:
    result = await db.execute(
        select(FaultReport).where(FaultReport.ride_id == ride_id)
    )
    return result.scalar_one_or_none()


async def upsert(db: AsyncSession, ride_id: int, data: dict) -> FaultReport:
    """Insert or update a fault report for a ride.

    data keys can include: tire_score, chain_score, handlebar_score,
    total_score, recommendation, details_json, wheel_wobble_detail,
    chain_noise_detail, handlebar_detail, and legacy detected/confidence fields.
    """
    report = await get_by_ride_id(db, ride_id)
    if report is None:
        report = FaultReport(ride_id=ride_id)
        db.add(report)

    # Update provided fields
    for key, value in data.items():
        if hasattr(report, key):
            setattr(report, key, value)

    await db.commit()
    await db.refresh(report)
    return report


async def delete_by_ride_id(db: AsyncSession, ride_id: int) -> None:
    report = await get_by_ride_id(db, ride_id)
    if report is not None:
        await db.delete(report)
        await db.commit()
