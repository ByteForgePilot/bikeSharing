from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.user import User          # noqa: E402
from app.models.ride import Ride          # noqa: E402
from app.models.fault_report import FaultReport  # noqa: E402
