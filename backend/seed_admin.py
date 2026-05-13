"""
Initialize database tables and create a superadmin account.
Run with: python seed_admin.py
"""
import asyncio
import uuid
from datetime import datetime, timezone

async def main():
    from app.core.database import engine, Base, AsyncSessionLocal
    # Import models so they register with Base
    from app.models import models  # noqa: F401
    from app.core.security import hash_password

    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created OK.")

    # Create superadmin
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # Check if superadmin already exists
        result = await session.execute(
            select(models.User).where(models.User.email == "admin@rombiz.ro")
        )
        existing = result.scalar_one_or_none()
        if existing:
            print("Superadmin already exists (admin@rombiz.ro)")
            return

        # Create organization
        org = models.Organization(
            id=uuid.uuid4(),
            name="RomBiz Admin",
            email="admin@rombiz.ro",
            subscription_plan="ENTERPRISE",
        )
        session.add(org)
        await session.flush()

        # Create superadmin user
        user = models.User(
            id=uuid.uuid4(),
            org_id=org.id,
            email="admin@rombiz.ro",
            password_hash=hash_password("Admin123!"),
            first_name="Super",
            last_name="Admin",
            role="admin",
            is_active=True,
            email_verified=True,
        )
        session.add(user)
        await session.commit()

        print("=" * 50)
        print("SUPERADMIN CREATED:")
        print(f"  Email:    admin@rombiz.ro")
        print(f"  Password: Admin123!")
        print(f"  Role:     admin")
        print(f"  Org:      RomBiz Admin")
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
