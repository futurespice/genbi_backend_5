from sqlalchemy import Column, Integer, ForeignKey, Enum as SQLEnum, DateTime, Text, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"))
    # ✅ ИСПРАВЛЕНО
    target_type = Column(
        SQLEnum('tour', 'company', name='reviewtargettype', native_enum=False),
        nullable=False
    )
    tour_id = Column(Integer, ForeignKey("tours.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_moderated = Column(Boolean, default=False)

    author = relationship("User", back_populates="reviews")

    __table_args__ = (
        CheckConstraint(
            '(tour_id IS NOT NULL AND company_id IS NULL) OR (tour_id IS NULL AND company_id IS NOT NULL)',
            name='check_review_target'
        ),
    )
