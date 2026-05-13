import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models import Base


class FaultReport(Base):
    __tablename__ = "fault_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ride_id = Column(Integer, ForeignKey("rides.id"), nullable=False)

    # Detection results
    wheel_wobble_detected = Column(String(20), default="unknown")  # normal, suspect, fault
    wheel_wobble_confidence = Column(Float, nullable=True)
    wheel_wobble_detail = Column(Text, nullable=True)

    chain_noise_detected = Column(String(20), default="unknown")
    chain_noise_confidence = Column(Float, nullable=True)
    chain_noise_detail = Column(Text, nullable=True)

    handlebar_detected = Column(String(20), default="unknown")
    handlebar_confidence = Column(Float, nullable=True)
    handlebar_detail = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    ride = relationship("Ride", back_populates="fault_reports")
