from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass
