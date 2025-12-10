from sqlalchemy import Column, Integer, String, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    # ✅ ИСПРАВЛЕНО: используем напрямую строковые значения
    role = Column(
        SQLEnum('admin', 'company', 'client', name='userrole', native_enum=False),
        default='client',
        nullable=False
    )
    is_active = Column(Boolean, default=True)

    bookings = relationship("Booking", back_populates="user")
    reviews = relationship("Review", back_populates="author")
    company = relationship("Company", back_populates="owner", uselist=False)
