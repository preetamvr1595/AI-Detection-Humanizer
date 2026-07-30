"""
Enforces TLS 1.3 on the FastAPI gateway (NFR-01), per PRD Section 6.4.

Uses a locally-generated self-signed certificate under .certs/ (see
generate below) for local/demo HTTPS testing. A production deployment
replaces fullchain.pem/privkey.pem with certificates from a real CA
(e.g. Let's Encrypt) — no other code changes needed.

Run with:  python3 run_tls.py
Then test: curl -k --tlsv1.3 https://127.0.0.1:8443/api/health
"""
import os
import ssl
import uvicorn

CERT_DIR = os.path.join(os.path.dirname(__file__), ".certs")
CERTFILE = os.path.join(CERT_DIR, "fullchain.pem")
KEYFILE = os.path.join(CERT_DIR, "privkey.pem")

if __name__ == "__main__":
    if not (os.path.exists(CERTFILE) and os.path.exists(KEYFILE)):
        raise SystemExit(
            "TLS certificate not found. Generate one first:\n"
            "  mkdir -p .certs && cd .certs && "
            "openssl req -x509 -newkey rsa:2048 -keyout privkey.pem -out fullchain.pem "
            "-days 365 -nodes -subj '/CN=localhost'"
        )

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8443,
        ssl_certfile=CERTFILE,
        ssl_keyfile=KEYFILE,
        ssl_version=ssl.PROTOCOL_TLS_SERVER,  # negotiates the highest mutually supported version (TLS 1.3 on modern OpenSSL/clients)
    )
