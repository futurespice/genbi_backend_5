from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.logger import logger, log_auth_attempt, log_user_action
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token, RefreshTokenRequest
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse)
@limiter.limit(settings.REGISTER_RATE_LIMIT)
async def register(
    request: Request,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя"""
    # Проверка существующего email
    result = await db.execute(select(User).filter(User.email == user_in.email))
    if result.scalars().first():
        logger.warning(f"Registration attempt with existing email: {user_in.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Проверка существующего phone
    if user_in.phone:
        result = await db.execute(select(User).filter(User.phone == user_in.phone))
        if result.scalars().first():
            logger.warning(f"Registration attempt with existing phone: {user_in.phone}")
            raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Создание пользователя - role уже строка из схемы!
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        phone=user_in.phone,
        password_hash=security.get_password_hash(user_in.password),
        role=user_in.role,  # ✅ Уже строка благодаря Literal
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"New user registered: {user.email} (ID: {user.id}, Role: {user.role})")
    
    return user


@router.post("/login", response_model=Token)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login_access_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """OAuth2 compatible login"""
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    
    client_ip = request.client.host if request.client else "unknown"
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        log_auth_attempt(form_data.username, False, client_ip)
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
        log_auth_attempt(form_data.username, False, client_ip)
        raise HTTPException(status_code=400, detail="Inactive user")
    
    log_auth_attempt(form_data.username, True, client_ip)
    
    access_token = security.create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = security.create_refresh_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/login/json", response_model=Token)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login_json(
    request: Request,
    email: str,
    password: str,
    db: AsyncSession = Depends(get_db)
):
    """Login with JSON format"""
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    
    client_ip = request.client.host if request.client else "unknown"
    
    if not user or not security.verify_password(password, user.password_hash):
        log_auth_attempt(email, False, client_ip)
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
        log_auth_attempt(email, False, client_ip)
        raise HTTPException(status_code=400, detail="Inactive user")
    
    log_auth_attempt(email, True, client_ip)
    
    access_token = security.create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = security.create_refresh_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Обновить access token"""
    try:
        payload = security.decode_token(refresh_request.refresh_token)
        user_id: int = int(payload.get("sub"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    access_token = security.create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = security.create_refresh_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    
    logger.info(f"Token refreshed for user: {user.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(deps.get_current_active_user)
):
    """Получить информацию о текущем пользователе"""
    return current_user
