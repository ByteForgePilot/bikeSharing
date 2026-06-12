from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Ride(Base):
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bike_id = Column(String(64), nullable=False, index=True)
    start_lat = Column(Float, default=0.0)
    start_lng = Column(Float, default=0.0)
    end_lat = Column(Float, nullable=True)
    end_lng = Column(Float, nullable=True)
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="active")  # active, completed, cancelled

    user = relationship("User", back_populates="rides")
    fault_reports = relationship("FaultReport", back_populates="ride")
