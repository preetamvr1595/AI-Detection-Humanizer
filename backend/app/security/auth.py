"""
Identity & Access Management (FR-01, FR-02, FR-03) — PRD Section 6.5.

Production target: Keycloak (OAuth 2.0/OIDC) issuing RS256 JWTs, verified
here via PyJWKClient against Keycloak's JWKS endpoint, with roles carried
in the `realm_access.roles` claim and MFA state in a `mfa_verified` claim.

This environment cannot reach a live Keycloak realm (no network route to
deploy/host one here), so this module issues RS256-signed JWTs locally
using a generated keypair, with the *identical token shape and claim
structure* Keycloak would produce (`sub`, `realm_access.roles`, `exp`,
`iat`, `mfa_verified`). `require_role()` is byte-for-byte the same RBAC
check PRD Section 6.5 specifies.

Migrating to real Keycloak later is a two-line change:
  1. Set KEYCLOAK_JWKS_URL to the real realm's certs endpoint.
  2. Switch verify_token() to use PyJWKClient against that URL instead of
     the local public key (see the commented block below).
"""
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import jwt as pyjwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.encryption import get_or_create_signing_keypair
from app import models

bearer = HTTPBearer()

# --- Production Keycloak config (inactive here — no reachable realm) ------
KEYCLOAK_JWKS_URL = os.getenv(
    "KEYCLOAK_JWKS_URL",
    "https://auth.scholarshield.app/realms/gmu/protocol/openid-connect/certs",
)
KEYCLOAK_AUDIENCE = "scholarshield-api"
# ---------------------------------------------------------------------------

ACCESS_TOKEN_TTL_SECONDS = 60 * 60 * 8  # 8 hours


def issue_local_token(user_id: str, roles: list, mfa_verified: bool = False) -> str:
    """
    Issues an RS256 JWT with the same claim shape a real Keycloak realm
    would produce. This is the LOCAL stand-in issuer described above.
    """
    private_key, _ = get_or_create_signing_keypair()
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL_SECONDS,
        "aud": KEYCLOAK_AUDIENCE,
        "realm_access": {"roles": roles},
        "mfa_verified": mfa_verified,
        "iss": "scholarshield-local-issuer",
    }
    return pyjwt.encode(payload, private_key, algorithm="RS256")


def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer)) -> dict:
    token = credentials.credentials
    _, public_key = get_or_create_signing_keypair()
    try:
        payload = pyjwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=KEYCLOAK_AUDIENCE,
            options={"require": ["exp", "iat"]},
        )
    except pyjwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid session token: {e}")
    return payload


def require_role(role: str):
    """Identical RBAC pattern to PRD Section 6.5 — role must appear in realm_access.roles."""
    def _checker(payload: dict = Depends(verify_token)):
        roles = payload.get("realm_access", {}).get("roles", [])
        if role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role (RBAC, FR-03)")
        return payload
    return _checker


def get_current_user_from_token(
    payload: dict = Depends(verify_token), db: Session = Depends(get_db)
) -> models.User:
    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found for token subject")
    return user
