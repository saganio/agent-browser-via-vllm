"""
Tests for authentication module
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.auth.models import User, Organization, Role


class TestPasswordHashing:
    """Tests for password hashing functions"""
    
    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a valid hash"""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password"""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestJWTTokens:
    """Tests for JWT token functions"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "123"}
        token = create_access_token(data)
        
        assert token is not None
        assert len(token) > 0
    
    def test_decode_access_token(self):
        """Test access token decoding"""
        data = {"sub": "123"}
        token = create_access_token(data)
        
        decoded = decode_token(token)
        
        assert decoded is not None
        assert decoded["sub"] == "123"
        assert decoded["type"] == "access"
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "123"}
        token = create_refresh_token(data)
        
        assert token is not None
        assert len(token) > 0
    
    def test_decode_refresh_token(self):
        """Test refresh token decoding"""
        data = {"sub": "123"}
        token = create_refresh_token(data)
        
        decoded = decode_token(token)
        
        assert decoded is not None
        assert decoded["sub"] == "123"
        assert decoded["type"] == "refresh"
        assert "jti" in decoded  # Unique token ID
    
    def test_decode_invalid_token(self):
        """Test that invalid token returns None"""
        invalid_token = "invalid.token.here"
        
        decoded = decode_token(invalid_token)
        
        assert decoded is None


class TestUserModel:
    """Tests for User model"""
    
    def test_user_is_admin(self):
        """Test is_admin property"""
        admin_user = User(
            id=1,
            email="admin@test.com",
            organization_id=1,
            role=Role.ADMIN
        )
        developer_user = User(
            id=2,
            email="dev@test.com",
            organization_id=1,
            role=Role.DEVELOPER
        )
        
        assert admin_user.is_admin is True
        assert developer_user.is_admin is False
    
    def test_user_can_create_projects(self):
        """Test can_create_projects property"""
        admin_user = User(
            id=1,
            email="admin@test.com",
            organization_id=1,
            role=Role.ADMIN
        )
        developer_user = User(
            id=2,
            email="dev@test.com",
            organization_id=1,
            role=Role.DEVELOPER
        )
        viewer_user = User(
            id=3,
            email="viewer@test.com",
            organization_id=1,
            role=Role.VIEWER
        )
        
        assert admin_user.can_create_projects is True
        assert developer_user.can_create_projects is True
        assert viewer_user.can_create_projects is False
    
    def test_user_can_run_tests(self):
        """Test can_run_tests property"""
        admin_user = User(
            id=1,
            email="admin@test.com",
            organization_id=1,
            role=Role.ADMIN
        )
        developer_user = User(
            id=2,
            email="dev@test.com",
            organization_id=1,
            role=Role.DEVELOPER
        )
        viewer_user = User(
            id=3,
            email="viewer@test.com",
            organization_id=1,
            role=Role.VIEWER
        )
        
        assert admin_user.can_run_tests is True
        assert developer_user.can_run_tests is True
        assert viewer_user.can_run_tests is False


class TestOrganizationModel:
    """Tests for Organization model"""
    
    def test_organization_repr(self):
        """Test Organization string representation"""
        org = Organization(id=1, name="Test Org", slug="test-org")
        
        assert "Test Org" in repr(org)
        assert "1" in repr(org)
