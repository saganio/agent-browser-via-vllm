"""
Authentication API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone
import secrets

from app.database import get_db
from app.auth.models import User, Organization, Role, RefreshToken
from app.auth.jwt import (
    create_access_token, 
    create_refresh_token, 
    decode_token,
    hash_password,
    verify_password,
    get_token_expiry
)
from app.auth.oidc import oidc_client
from app.auth.dependencies import get_current_user, get_current_active_user
from app.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    organization_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    role: str
    organization_id: int
    organization_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class RefreshRequest(BaseModel):
    refresh_token: str


# Helper to create slug from name
def create_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")[:100]


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user and organization"""
    
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization if name provided, otherwise use email domain
    org_name = request.organization_name or request.email.split("@")[1]
    org_slug = create_slug(org_name) + "-" + secrets.token_hex(4)
    
    organization = Organization(
        name=org_name,
        slug=org_slug,
    )
    db.add(organization)
    await db.flush()  # Get organization ID
    
    # Create user as admin of their organization
    user = User(
        email=request.email,
        name=request.name,
        hashed_password=hash_password(request.password),
        organization_id=organization.id,
        role=Role.ADMIN,
        is_active=True,
        is_verified=True,  # Auto-verify for now
    )
    db.add(user)
    await db.flush()
    
    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Store refresh token
    token_record = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=get_token_expiry(refresh_token),
    )
    db.add(token_record)
    
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password"""
    
    # Find user
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    
    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Store refresh token
    token_record = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=get_token_expiry(refresh_token),
    )
    db.add(token_record)
    
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    
    payload = decode_token(request.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Check if token is in database and not revoked
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == request.refresh_token,
            RefreshToken.revoked == False
        )
    )
    token_record = result.scalar_one_or_none()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked"
        )
    
    # Check expiry
    if token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    
    user_id = payload.get("sub")
    
    # Revoke old refresh token
    token_record.revoked = True
    
    # Create new tokens
    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})
    
    # Store new refresh token
    new_token_record = RefreshToken(
        user_id=int(user_id),
        token=refresh_token,
        expires_at=get_token_expiry(refresh_token),
    )
    db.add(new_token_record)
    
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout - revoke all refresh tokens for user"""
    
    # Revoke all refresh tokens for this user
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False
        )
    )
    tokens = result.scalars().all()
    
    for token in tokens:
        token.revoked = True
    
    await db.commit()
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user info"""
    
    # Fetch organization name
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        organization_id=current_user.organization_id,
        organization_name=org.name if org else None,
        avatar_url=current_user.avatar_url,
    )


# OIDC Routes
@router.get("/oidc/login")
async def oidc_login(request: Request):
    """Initiate OIDC login flow"""
    
    if not oidc_client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC is not configured"
        )
    
    state = secrets.token_urlsafe(32)
    # In production, store state in session/cache for validation
    
    auth_url = await oidc_client.get_authorization_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/oidc/callback")
async def oidc_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle OIDC callback"""
    
    if not oidc_client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC is not configured"
        )
    
    # Exchange code for tokens
    tokens = await oidc_client.exchange_code(code)
    access_token = tokens.get("access_token")
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get access token from OIDC provider"
        )
    
    # Get user info
    userinfo = await oidc_client.get_userinfo(access_token)
    
    oidc_sub = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name") or userinfo.get("preferred_username")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by OIDC provider"
        )
    
    # Find or create user
    result = await db.execute(
        select(User).where(User.oidc_sub == oidc_sub)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Check if user exists by email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Link OIDC to existing user
            user.oidc_sub = oidc_sub
            user.oidc_provider = "oidc"
        else:
            # Create new organization and user
            org_name = email.split("@")[1]
            org_slug = create_slug(org_name) + "-" + secrets.token_hex(4)
            
            organization = Organization(
                name=org_name,
                slug=org_slug,
            )
            db.add(organization)
            await db.flush()
            
            user = User(
                email=email,
                name=name,
                oidc_sub=oidc_sub,
                oidc_provider="oidc",
                organization_id=organization.id,
                role=Role.ADMIN,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    
    # Create our own tokens
    our_access_token = create_access_token({"sub": str(user.id)})
    our_refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Store refresh token
    token_record = RefreshToken(
        user_id=user.id,
        token=our_refresh_token,
        expires_at=get_token_expiry(our_refresh_token),
    )
    db.add(token_record)
    
    await db.commit()
    
    # Redirect to frontend with tokens
    frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
    redirect_url = f"{frontend_url}/auth/callback?access_token={our_access_token}&refresh_token={our_refresh_token}"
    
    return RedirectResponse(url=redirect_url)


@router.get("/oidc/config")
async def get_oidc_config():
    """Get OIDC configuration status"""
    return {
        "configured": oidc_client.is_configured,
        "provider": "custom" if oidc_client.is_configured else None,
    }
