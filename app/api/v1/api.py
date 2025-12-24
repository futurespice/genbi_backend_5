from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, companies, tours, bookings, reviews, applications

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(tours.router, prefix="/tours", tags=["tours"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])