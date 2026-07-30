"""
At-Rest Encryption & Report Signing (FR-13, NFR-01) — real AES-256-GCM
authenticated encryption, per PRD Section 6.4. Used to encrypt generated
PDF reports at rest and to produce a tamper-evident signature alongside
the SHA-256 hash already computed in report_gen.py.
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

MASTER_KEY_PATH = os.getenv("SCHOLARSHIELD_AES_KEY_PATH", "/home/claude/scholarshield_app/backend/.keys/aes_master.key")
RSA_KEY_DIR = os.getenv("SCHOLARSHIELD_RSA_KEY_DIR", "/home/claude/scholarshield_app/backend/.keys")


def _ensure_key_dir():
    os.makedirs(os.path.dirname(MASTER_KEY_PATH), exist_ok=True)


def get_or_create_master_key() -> bytes:
    """Loads (or generates once) a persistent AES-256 master key for report-at-rest encryption."""
    _ensure_key_dir()
    if os.path.exists(MASTER_KEY_PATH):
        with open(MASTER_KEY_PATH, "rb") as f:
            return f.read()
    key = AESGCM.generate_key(bit_length=256)
    with open(MASTER_KEY_PATH, "wb") as f:
        f.write(key)
    os.chmod(MASTER_KEY_PATH, 0o600)
    return key


def encrypt_report(plaintext: bytes, key: bytes = None) -> dict:
    """AES-256-GCM authenticated encryption for report payloads at rest (FR-13/NFR-01)."""
    key = key or get_or_create_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=b"scholarshield-report")
    return {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }


def decrypt_report(nonce_b64: str, ciphertext_b64: str, key: bytes = None) -> bytes:
    key = key or get_or_create_master_key()
    aesgcm = AESGCM(key)
    nonce = base64.b64decode(nonce_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    return aesgcm.decrypt(nonce, ciphertext, associated_data=b"scholarshield-report")


# ---------------------------------------------------------------------------
# Digital signature (RSA-PSS) for tamper-evident report authenticity.
# ---------------------------------------------------------------------------
def _rsa_key_paths():
    return (
        os.path.join(RSA_KEY_DIR, "report_signing_private.pem"),
        os.path.join(RSA_KEY_DIR, "report_signing_public.pem"),
    )


def get_or_create_signing_keypair():
    os.makedirs(RSA_KEY_DIR, exist_ok=True)
    priv_path, pub_path = _rsa_key_paths()
    if os.path.exists(priv_path):
        with open(priv_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
    else:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open(priv_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        os.chmod(priv_path, 0o600)
        with open(pub_path, "wb") as f:
            f.write(private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ))
    return private_key, private_key.public_key()


def sign_report(digest: bytes) -> str:
    """Signs a SHA-256 report digest with RSA-PSS, returns base64 signature."""
    private_key, _ = get_or_create_signing_keypair()
    signature = private_key.sign(
        digest,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode()


def verify_report_signature(digest: bytes, signature_b64: str) -> bool:
    _, public_key = get_or_create_signing_keypair()
    try:
        public_key.verify(
            base64.b64decode(signature_b64),
            digest,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
