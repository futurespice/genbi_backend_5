from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    tour_id = Column(Integer, ForeignKey("tours.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    participants_count = Column(Integer, default=1)
    date = Column(DateTime(timezone=True))
    # ✅ ИСПРАВЛЕНО
    status = Column(
        SQLEnum('pending', 'confirmed', 'paid', 'cancelled', name='bookingstatus', native_enum=False),
        default='pending',
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tour = relationship("Tour", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
