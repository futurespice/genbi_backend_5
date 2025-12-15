from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware  # 🟢 Импорт Middleware для хостов
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logger import logger
from app.core.rate_limit import limiter, RateLimitMiddleware
from app.api.v1.api import api_router

# ============================================
# APPLICATION INITIALIZATION
# ============================================

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
)

# ============================================
# 🟢 ALLOWED HOSTS MIDDLEWARE (Добавляем первым или перед CORS)
# ============================================
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# ============================================
# RATE LIMITING
# ============================================

# Добавляем limiter в app state
app.state.limiter = limiter

# Middleware для логирования rate limit нарушений
app.add_middleware(RateLimitMiddleware)


# Exception handler для rate limit
@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc):
    logger.warning(f"Rate limit exceeded for {request.client.host} on {request.url.path}")
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later."
        }
    )


# ============================================
# CORS MIDDLEWARE
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Использует обновленный список из конфига
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ... (Остальной код без изменений: ERROR HANDLERS, MIDDLEWARE LOGGING и т.д.) ...

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработка ошибок валидации Pydantic"""
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": list(error.get("loc", [])),
            "msg": str(error.get("msg", "")),
            "type": error.get("type", "")
        })

    logger.error(f"Validation error on {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Обработка ошибок базы данных"""
    logger.error(f"Database error on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработка всех остальных ошибок"""
    logger.error(f"Unexpected error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error"
        }
    )


# ============================================
# MIDDLEWARE - Request/Response Logging
# ============================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех запросов и ответов"""
    logger.info(f"➡️  {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"⬅️  {request.method} {request.url.path} - Status: {response.status_code}")
    return response


# ============================================
# STARTUP/SHUTDOWN EVENTS
# ============================================

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}")
    logger.info(f"📚 Documentation: http://localhost:8000{settings.API_V1_STR}/docs")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔒 CORS Origins: {settings.CORS_ORIGINS}")
    logger.info(f"🏠 Allowed Hosts: {settings.ALLOWED_HOSTS}")  # Можно добавить в лог для проверки
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("=" * 50)
    logger.info(f"🛑 Shutting down {settings.PROJECT_NAME}")
    logger.info("=" * 50)


# ============================================
# ROUTES
# ============================================

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": f"{settings.API_V1_STR}/docs",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }