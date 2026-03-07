"""
Development Seed Data

Creates minimal data for local development:
- 1 admin user
- 1 workspace
- User is owner of workspace
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.dependencies import AsyncSessionLocal
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import hash_password


DEV_USER_EMAIL = "admin@botforge.dev"
DEV_USER_PASSWORD = "admin123"
DEV_WORKSPACE_NAME = "Development Workspace"


async def seed_dev_data():
    """Seed development database with minimal test data."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if dev user already exists
            result = await session.execute(
                select(User).where(User.email == DEV_USER_EMAIL)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"✓ Dev user already exists: {DEV_USER_EMAIL}")
                return

            # Create dev user
            dev_user = User(
                email=DEV_USER_EMAIL,
                password_hash=hash_password(DEV_USER_PASSWORD),
                name="Dev Admin"
            )
            session.add(dev_user)
            await session.flush()

            # Create dev workspace
            dev_workspace = Workspace(
                owner_id=dev_user.id,
                name=DEV_WORKSPACE_NAME,
                features={
                    "rag_enabled": True,
                    "voice_enabled": False,
                    "channels_enabled": False,
                },
                settings={
                    "bot_name": "DevBot",
                    "personality": "professional",
                    "greeting": "Hello! I'm DevBot, your development assistant.",
                }
            )
            session.add(dev_workspace)
            await session.flush()

            # Add user as owner of workspace
            workspace_member = WorkspaceMember(
                workspace_id=dev_workspace.id,
                user_id=dev_user.id,
                role="owner"
            )
            session.add(workspace_member)

            await session.commit()

            print("✓ Dev data seeded successfully!")
            print(f"  Email: {DEV_USER_EMAIL}")
            print(f"  Password: {DEV_USER_PASSWORD}")
            print(f"  Workspace: {DEV_WORKSPACE_NAME}")

        except Exception as e:
            await session.rollback()
            print(f"✗ Error seeding dev data: {e}")
            raise


if __name__ == "__main__":
    print("Seeding development data...")
    asyncio.run(seed_dev_data())
