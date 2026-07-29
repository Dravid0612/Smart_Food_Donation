from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base


class NGO(Base):
    __tablename__ = "ngos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    contact_person = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
