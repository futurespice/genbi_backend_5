from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Tour(Base):
    __tablename__ = "tours"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    image_url = Column(String)
    description = Column(Text)
    schedule = Column(JSON)
    price = Column(Float, nullable=False)
    location = Column(String, index=True)
    duration = Column(String)
    rating = Column(Float, default=0.0)
    capacity = Column(Integer, default=50, nullable=False)  # ✅ ДОБАВЛЕНО
    is_active = Column(Boolean, default=True)  # ✅ ДОБАВЛЕНО для soft delete
    company_id = Column(Integer, ForeignKey("companies.id"))

    company = relationship("Company", back_populates="tours")
    bookings = relationship("Booking", back_populates="tour")
