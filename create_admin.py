"""
Скрипт для создания первого администратора
Запуск: python create_admin.py
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.db.base import User
from app.core.security import get_password_hash


async def create_admin():
    """Создать первого администратора"""
    
    admin_email = "admin@genbi.com"
    admin_password = "Admin123!"
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).filter(User.email == admin_email)
        )
        existing_admin = result.scalars().first()
        
        if existing_admin:
            print(f"❌ Администратор с email {admin_email} уже существует!")
            return
        
        admin = User(
            email=admin_email,
            full_name="Главный Администратор",
            password_hash=get_password_hash(admin_password),
            role='admin',
            is_active=True
        )
        
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        
        print("=" * 60)
        print("✅ Администратор успешно создан!")
        print("=" * 60)
        print(f"📧 Email: {admin_email}")
        print(f"🔑 Пароль: {admin_password}")
        print("=" * 60)
        print("⚠️  ВАЖНО: Смените пароль после первого входа!")
        print("=" * 60)


async def create_test_users():
    """Создать тестовых пользователей (опционально)"""
    
    test_users = [
        {
            "email": "company@test.com",
            "password": "Company123!",
            "full_name": "Тестовая Компания",
            "role": "company",
        },
        {
            "email": "client@test.com",
            "password": "Client123!",
            "full_name": "Тестовый Клиент",
            "role": "client",
        }
    ]
    
    async with AsyncSessionLocal() as db:
        for user_data in test_users:
            result = await db.execute(
                select(User).filter(User.email == user_data["email"])
            )
            if result.scalars().first():
                print(f"⚠️  Пользователь {user_data['email']} уже существует")
                continue
            
            user = User(
                email=user_data["email"],
                full_name=user_data["full_name"],
                password_hash=get_password_hash(user_data["password"]),
                role=user_data["role"],
                is_active=True
            )
            
            db.add(user)
            await db.commit()
            print(f"✅ Создан пользователь: {user_data['email']} / {user_data['password']}")


# ✅ ИСПРАВЛЕНО: используем один async.run для обеих функций
async def main():
    """Главная функция"""
    print("\n🚀 Создание администратора...\n")
    await create_admin()
    
    print("\n🤔 Создать тестовых пользователей? (y/n): ", end="")
    answer = input().strip().lower()
    
    if answer == "y":
        print("\n🚀 Создание тестовых пользователей...\n")
        await create_test_users()
        print("\n✅ Готово!\n")
    else:
        print("\n✅ Готово!\n")


if __name__ == "__main__":
    asyncio.run(main())
