"""
Password hashing + JWT session handling.

JWT issuance/verification now delegates to app.security.auth, which issues
RS256 tokens with the same claim shape (realm_access.roles, mfa_verified)
that a real Keycloak realm would produce — see app/security/auth.py for the
full explanation and the production Keycloak migration path.
"""
import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.auth import issue_local_token, verify_token
from app import models

bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_access_token(user: models.User, mfa_verified: bool = False) -> str:
    """Issues a Keycloak-shaped RS256 JWT for the given user (see security/auth.py)."""
    roles = [user.role]
    return issue_local_token(user_id=user.user_id, roles=roles, mfa_verified=mfa_verified)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    payload = verify_token(credentials)
    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin privileges required (RBAC, FR-03)")
    return user
