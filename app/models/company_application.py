from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class CompanyApplication(Base):
    """Заявка на регистрацию компании"""
    __tablename__ = "company_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Данные компании
    company_name = Column(String, nullable=False)
    company_address = Column(String, nullable=False)
    company_website = Column(String, nullable=True)
    work_hours = Column(String, nullable=True)

    # Статус заявки
    status = Column(
        SQLEnum('pending', 'approved', 'rejected', name='applicationstatus', native_enum=False),
        default='pending',
        nullable=False
    )

    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    applicant = relationship("User", foreign_keys=[user_id], backref="applications")
    reviewer = relationship("User", foreign_keys=[reviewed_by_admin_id])