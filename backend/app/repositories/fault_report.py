from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fault_report import FaultReport


async def upsert(db: AsyncSession, ride_id: int, result: dict) -> FaultReport:
    """Create or update a fault report for a ride.

    `result` should be a dict with keys matching FaultReport columns:
        wheel_wobble_detected, wheel_wobble_confidence, wheel_wobble_detail,
        chain_noise_detected, chain_noise_confidence, chain_noise_detail,
        handlebar_detected, handlebar_confidence, handlebar_detail
    """
    q = select(FaultReport).where(FaultReport.ride_id == ride_id)
    existing = (await db.execute(q)).scalar_one_or_none()

    if existing:
        for key, value in result.items():
            setattr(existing, key, value)
        report = existing
    else:
        report = FaultReport(ride_id=ride_id, **result)

    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_by_ride_id(db: AsyncSession, ride_id: int) -> FaultReport | None:
    q = select(FaultReport).where(FaultReport.ride_id == ride_id)
    return (await db.execute(q)).scalar_one_or_none()
