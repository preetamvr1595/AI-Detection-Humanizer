"""
Auth router — registration, login, and real TOTP-based MFA (FR-01, FR-02, FR-03).

MFA here is genuine RFC 6238 TOTP (via pyotp) — the same algorithm Google
Authenticator / Authy / Keycloak's own OTP credential type use. A user
enrolls by scanning the returned QR code into any standard authenticator
app, then must supply a live 6-digit code on every subsequent login.
"""
import io
import base64
import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.security.audit_log import AuditLog
from app import models, schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.Token)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    is_first_user = db.query(models.User).count() == 0
    user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        institution=payload.institution or "GM University",
        role="Admin" if is_first_user else "Student",
        mfa_enabled=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    AuditLog(db).record(user.user_id, "REGISTER", user.email)

    token = create_access_token(user, mfa_verified=False)
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        AuditLog(db).record(None, "LOGIN_FAILED", payload.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.mfa_enabled:
        if not payload.totp_code:
            raise HTTPException(status_code=401, detail="MFA_REQUIRED")
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(payload.totp_code, valid_window=1):
            AuditLog(db).record(user.user_id, "MFA_FAILED", user.email)
            raise HTTPException(status_code=401, detail="Invalid MFA code")

    AuditLog(db).record(user.user_id, "LOGIN", user.email)
    token = create_access_token(user, mfa_verified=user.mfa_enabled)
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/mfa/setup")
def mfa_setup(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generates a real TOTP secret + QR code for the user to scan into an authenticator app."""
    secret = pyotp.random_base32()
    current_user.mfa_secret = secret
    db.commit()

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name="ScholarShield")

    qr = qrcode.make(uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    AuditLog(db).record(current_user.user_id, "MFA_SETUP_STARTED", current_user.email)
    return {"secret": secret, "provisioning_uri": uri, "qr_code_png_base64": qr_b64}


@router.post("/mfa/enable")
def mfa_enable(code: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verifies one live TOTP code before turning MFA on, proving the user's authenticator app is correctly enrolled."""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="Call /auth/mfa/setup first")
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code — MFA not enabled")
    current_user.mfa_enabled = True
    db.commit()
    AuditLog(db).record(current_user.user_id, "MFA_ENABLED", current_user.email)
    return {"mfa_enabled": True}


@router.post("/mfa/disable")
def mfa_disable(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    db.commit()
    AuditLog(db).record(current_user.user_id, "MFA_DISABLED", current_user.email)
    return {"mfa_enabled": False}
