"""
Authentication endpoints — JWT RS256 (hard constraint #14).
"""

import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
    TokenPayload,
)
from pydantic import BaseModel, Field
from app.models.models import Organization, User
from app.schemas.schemas import LoginRequest, RegisterRequest, TokenResponse, MessageResponse

logger = get_logger(__name__)

# In-memory store for password reset tokens (use Redis in production)
_password_reset_tokens: dict[str, dict] = {}

router = APIRouter()


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(request: Request, req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new organization + admin user."""
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create organization
    org = Organization(
        name=req.organization_name or f"{req.first_name or ''} {req.last_name or ''}".strip() or "Default",
        email=req.email,
        subscription_plan="FREE",
    )
    db.add(org)
    await db.flush()

    # Create admin user
    user = User(
        org_id=org.id,
        email=req.email,
        password_hash=hash_password(req.password),
        first_name=req.first_name,
        last_name=req.last_name,
        role="admin",
    )
    db.add(user)
    return MessageResponse(message="Registration successful. Please verify your email.")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and return JWT tokens."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    access = create_access_token(str(user.id), str(user.org_id), user.role)
    refresh = create_refresh_token(str(user.id), str(user.org_id), user.role)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=1800,
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh an access token using a valid refresh token."""
    payload = decode_token(body.refresh_token)

    # Verify user still exists and is active
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(payload.sub)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access = create_access_token(str(user.id), str(user.org_id), user.role)
    refresh = create_refresh_token(str(user.id), str(user.org_id), user.role)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=1800,
    )


@router.get("/me")
async def get_me(
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current user info with full profile."""
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(current_user.sub)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get org name
    org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = org_result.scalar_one_or_none()

    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "role": user.role,
        "org_id": str(user.org_id),
        "org_name": org.name if org else "",
        "org_cui": org.cui if org else "",
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "credits_left": user.credits_left,
        "avatar_url": user.avatar_url,
    }


# ═══════════════════════════════════════════════════════════════════
# UPDATE PROFILE — edit current user info
# ═══════════════════════════════════════════════════════════════════

class UpdateProfileRequest(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)


@router.patch("/me", response_model=MessageResponse)
@limiter.limit("10/minute")
async def update_profile(
    request: Request,
    body: UpdateProfileRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(current_user.sub)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizator negăsit")

    if body.first_name is not None:
        user.first_name = body.first_name.strip()
    if body.last_name is not None:
        user.last_name = body.last_name.strip()

    logger.info("profile_updated", user_id=str(user.id))
    return MessageResponse(message="Profil actualizat cu succes.")


# ═══════════════════════════════════════════════════════════════════
# FORGOT PASSWORD — request reset link via email
# ═══════════════════════════════════════════════════════════════════

class ForgotPasswordRequest(BaseModel):
    email: str = Field(max_length=254)


def _send_reset_email(to_email: str, reset_token: str) -> None:
    """Send password reset email via SMTP."""
    reset_url = f"{settings.BASE_URL.rstrip('/')}/reset-password?token={reset_token}"
    # Use frontend URL if available; fallback to BASE_URL
    frontend_url = reset_url.replace("/api/v1", "").replace("api.", "app.")

    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_FROM or "noreply@rombiz.ro"
    msg["To"] = to_email
    msg["Subject"] = "ATH Rating — Resetare parolă"

    body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px; background: #f8fafc; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #1e293b; font-size: 22px; margin: 0;">ATH | RATING</h1>
            <p style="color: #64748b; font-size: 13px; margin-top: 4px;">Resetare parolă</p>
        </div>
        <div style="background: white; border-radius: 10px; padding: 28px; border: 1px solid #e2e8f0;">
            <p style="color: #334155; font-size: 14px; line-height: 1.6;">
                Ai solicitat resetarea parolei. Folosește link-ul de mai jos pentru a seta o parolă nouă:
            </p>
            <div style="text-align: center; margin: 24px 0;">
                <a href="{frontend_url}"
                   style="display: inline-block; padding: 12px 32px; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px;">
                    Resetează Parola
                </a>
            </div>
            <p style="color: #94a3b8; font-size: 12px; line-height: 1.5;">
                Link-ul expiră în 30 de minute. Dacă nu ai solicitat resetarea, ignoră acest email.
            </p>
        </div>
    </div>
    """
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT or 587) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("password_reset_email_sent", to=to_email)
    except Exception as e:
        logger.error("password_reset_email_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Nu s-a putut trimite email-ul de resetare")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a password reset link to the user's email."""
    result = await db.execute(select(User).where(User.email == body.email.strip().lower()))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user or not user.is_active:
        return MessageResponse(message="Dacă adresa există, vei primi un email cu instrucțiuni.")

    # Generate secure token
    reset_token = secrets.token_urlsafe(48)
    _password_reset_tokens[reset_token] = {
        "user_id": str(user.id),
        "email": user.email,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
    }

    _send_reset_email(user.email, reset_token)

    return MessageResponse(message="Dacă adresa există, vei primi un email cu instrucțiuni.")


# ═══════════════════════════════════════════════════════════════════
# RESET PASSWORD — use the token from email to set new password
# ═══════════════════════════════════════════════════════════════════

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using the token received via email."""
    token_data = _password_reset_tokens.get(body.token)

    if not token_data:
        raise HTTPException(status_code=400, detail="Token invalid sau expirat")

    if datetime.now(timezone.utc) > token_data["expires_at"]:
        _password_reset_tokens.pop(body.token, None)
        raise HTTPException(status_code=400, detail="Token expirat. Solicită un link nou.")

    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(token_data["user_id"])))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Utilizator negăsit")

    user.password_hash = hash_password(body.new_password)

    # Invalidate the used token
    _password_reset_tokens.pop(body.token, None)

    logger.info("password_reset_success", user_id=str(user.id))
    return MessageResponse(message="Parola a fost resetată cu succes. Te poți autentifica.")


# ═══════════════════════════════════════════════════════════════════
# CHANGE PASSWORD — for authenticated users
# ═══════════════════════════════════════════════════════════════════

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/change-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the currently authenticated user."""
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(current_user.sub)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Utilizator negăsit")

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Parola curentă este incorectă")

    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="Parola nouă trebuie să fie diferită de cea curentă")

    user.password_hash = hash_password(body.new_password)

    logger.info("password_changed", user_id=str(user.id))
    return MessageResponse(message="Parola a fost schimbată cu succes.")


# ═══════════════════════════════════════════════════════════════════
# AVATAR UPLOAD — profile picture
# ═══════════════════════════════════════════════════════════════════

AVATAR_DIR = Path("/home/aether/public_html/rating.nineinternational.ro/avatars")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB


@router.post("/avatar", response_model=MessageResponse)
@limiter.limit("10/minute")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload or replace user avatar image."""
    import uuid as uuid_mod

    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Format invalid. Acceptăm: JPG, PNG, WEBP")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="Imaginea depășește 2 MB")

    # Validate it's actually an image by checking magic bytes
    if not (
        content[:3] == b"\xff\xd8\xff"  # JPEG
        or content[:8] == b"\x89PNG\r\n\x1a\n"  # PNG
        or content[:4] == b"RIFF" and content[8:12] == b"WEBP"  # WEBP
    ):
        raise HTTPException(status_code=400, detail="Fișierul nu este o imagine validă")

    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(current_user.sub)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizator negăsit")

    # Create avatars directory
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)

    # Delete old avatar if exists
    if user.avatar_url:
        old_file = AVATAR_DIR / Path(user.avatar_url).name
        if old_file.exists():
            old_file.unlink()

    # Save with unique name
    filename = f"{user.id}{ext}"
    filepath = AVATAR_DIR / filename
    filepath.write_bytes(content)

    # Update user
    user.avatar_url = f"/avatars/{filename}"
    await db.commit()

    logger.info("avatar_uploaded", user_id=str(user.id), filename=filename)
    return MessageResponse(message="Avatar actualizat cu succes.")
