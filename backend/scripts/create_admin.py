#!/usr/bin/env python3
"""
Script to create an admin user for the Browser Test Platform.
Run from the backend directory: python scripts/create_admin.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session_maker, init_db
from app.auth.models import User, Organization, Role
from app.auth.jwt import hash_password

# Import all models to ensure relationships are resolved
from app.projects.models import Project
from app.tests.models import TestRun, TestResult, Schedule
from app.notifications.models import NotificationChannel


async def create_admin_user():
    """Create default organization and admin user"""
    
    # Initialize database tables
    await init_db()
    
    async with async_session_maker() as db:
        # Check if default organization exists
        result = await db.execute(
            select(Organization).where(Organization.slug == "default")
        )
        org = result.scalar_one_or_none()
        
        if not org:
            print("Creating default organization...")
            org = Organization(
                name="Default Organization",
                slug="default",
                is_active=True
            )
            db.add(org)
            await db.commit()
            await db.refresh(org)
            print(f"✓ Created organization: {org.name} (ID: {org.id})")
        else:
            print(f"✓ Organization already exists: {org.name} (ID: {org.id})")
        
        # Check if admin user exists
        admin_email = "admin@example.com"
        result = await db.execute(
            select(User).where(User.email == admin_email)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("Creating admin user...")
            admin = User(
                email=admin_email,
                hashed_password=hash_password("admin123"),
                name="Admin User",
                organization_id=org.id,
                role=Role.ADMIN,
                is_active=True
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            print(f"✓ Created admin user: {admin.email} (ID: {admin.id})")
        else:
            print(f"✓ Admin user already exists: {admin.email} (ID: {admin.id})")
        
        # Create a test developer user
        dev_email = "developer@example.com"
        result = await db.execute(
            select(User).where(User.email == dev_email)
        )
        dev = result.scalar_one_or_none()
        
        if not dev:
            print("Creating developer user...")
            dev = User(
                email=dev_email,
                hashed_password=hash_password("dev123"),
                name="Developer User",
                organization_id=org.id,
                role=Role.DEVELOPER,
                is_active=True
            )
            db.add(dev)
            await db.commit()
            await db.refresh(dev)
            print(f"✓ Created developer user: {dev.email} (ID: {dev.id})")
        else:
            print(f"✓ Developer user already exists: {dev.email} (ID: {dev.id})")
        
        # Create a test viewer user
        viewer_email = "viewer@example.com"
        result = await db.execute(
            select(User).where(User.email == viewer_email)
        )
        viewer = result.scalar_one_or_none()
        
        if not viewer:
            print("Creating viewer user...")
            viewer = User(
                email=viewer_email,
                hashed_password=hash_password("viewer123"),
                name="Viewer User",
                organization_id=org.id,
                role=Role.VIEWER,
                is_active=True
            )
            db.add(viewer)
            await db.commit()
            await db.refresh(viewer)
            print(f"✓ Created viewer user: {viewer.email} (ID: {viewer.id})")
        else:
            print(f"✓ Viewer user already exists: {viewer.email} (ID: {viewer.id})")
    
    print("\n" + "="*50)
    print("TEST ACCOUNTS CREATED:")
    print("="*50)
    print("\n📧 Admin Account:")
    print("   Email:    admin@example.com")
    print("   Password: admin123")
    print("   Role:     ADMIN (full access)")
    print("\n📧 Developer Account:")
    print("   Email:    developer@example.com")
    print("   Password: dev123")
    print("   Role:     DEVELOPER (can create projects & run tests)")
    print("\n📧 Viewer Account:")
    print("   Email:    viewer@example.com")
    print("   Password: viewer123")
    print("   Role:     VIEWER (read-only access)")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(create_admin_user())
