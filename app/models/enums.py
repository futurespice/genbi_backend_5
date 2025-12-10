import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    COMPANY = "company"
    CLIENT = "client"

class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    CANCELLED = "cancelled"

class ReviewTargetType(str, enum.Enum):
    TOUR = "tour"
    COMPANY = "company"
