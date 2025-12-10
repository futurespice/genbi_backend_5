"""
Pytest configuration and fixtures
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.models.enums import UserRole

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

# Create test session maker
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create test admin user"""
    admin = User(
        email="admin@test.com",
        full_name="Test Admin",
        phone="+1234567890",
        password_hash=get_password_hash("Admin123!"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_company_user(db_session: AsyncSession) -> User:
    """Create test company user"""
    company_user = User(
        email="company@test.com",
        full_name="Test Company",
        phone="+1234567891",
        password_hash=get_password_hash("Company123!"),
        role=UserRole.COMPANY,
        is_active=True
    )
    db_session.add(company_user)
    await db_session.commit()
    await db_session.refresh(company_user)
    return company_user


@pytest_asyncio.fixture
async def test_client_user(db_session: AsyncSession) -> User:
    """Create test client user"""
    client_user = User(
        email="client@test.com",
        full_name="Test Client",
        phone="+1234567892",
        password_hash=get_password_hash("Client123!"),
        role=UserRole.CLIENT,
        is_active=True
    )
    db_session.add(client_user)
    await db_session.commit()
    await db_session.refresh(client_user)
    return client_user


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    """Get admin JWT token"""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "admin@test.com", "password": "Admin123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def company_token(client: AsyncClient) -> str:
    """Get company JWT token"""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "company@test.com", "password": "Company123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def client_token(client: AsyncClient) -> str:
    """Get client JWT token"""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "client@test.com", "password": "Client123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]
