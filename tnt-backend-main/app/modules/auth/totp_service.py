"""TOTP-based 2FA for admin accounts."""
import pyotp
import qrcode
import io
import base64

ADMIN_ROLES = {"admin", "super_admin"}
ISSUER = "TNT Tap N Take"


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username, issuer_name=ISSUER
    )


def generate_qr_code_b64(secret: str, username: str) -> str:
    """Return base64-encoded PNG QR code for the TOTP setup screen."""
    uri = get_totp_uri(secret, username)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code. Accepts current ± 1 window (30s drift tolerance)."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def is_admin_role(role: str) -> bool:
    return role.lower() in ADMIN_ROLES
