"""
Tests for authentication endpoints
"""
import pytest
from httpx import AsyncClient
from app.core.config import settings


class TestRegistration:
    """Tests for user registration"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful registration"""
        response = await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "newuser@test.com",
                "full_name": "New User",
                "phone": "+9876543210",
                "password": "Password123!",
                "role": "client"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_admin):
        """Test registration with duplicate email"""
        response = await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "admin@test.com",  # Already exists
                "full_name": "Duplicate User",
                "phone": "+1111111111",
                "password": "Password123!",
                "role": "client"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password"""
        response = await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "weak@test.com",
                "full_name": "Weak Password User",
                "phone": "+2222222222",
                "password": "weak",  # Too short, no uppercase, no digit
                "role": "client"
            }
        )
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email"""
        response = await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "not-an-email",
                "full_name": "Invalid Email User",
                "phone": "+3333333333",
                "password": "Password123!",
                "role": "client"
            }
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for user login"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_admin):
        """Test successful login"""
        response = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            data={"username": "admin@test.com", "password": "Admin123!"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_json(self, client: AsyncClient, test_admin):
        """Test login with JSON format"""
        response = await client.post(
            f"{settings.API_V1_STR}/auth/login/json",
            json={"email": "admin@test.com", "password": "Admin123!"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_admin):
        """Test login with wrong password"""
        response = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            data={"username": "admin@test.com", "password": "WrongPassword!"}
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user"""
        response = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            data={"username": "nonexistent@test.com", "password": "Password123!"}
        )
        assert response.status_code == 400


class TestRefreshToken:
    """Tests for token refresh"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_admin):
        """Test successful token refresh"""
        # Login to get tokens
        login_response = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            data={"username": "admin@test.com", "password": "Admin123!"}
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = await client.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refresh with invalid token"""
        response = await client.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        assert response.status_code == 401


class TestCurrentUser:
    """Tests for getting current user info"""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, admin_token):
        """Test getting current user info"""
        response = await client.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting current user without token"""
        response = await client.get(f"{settings.API_V1_STR}/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token"""
        response = await client.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401
