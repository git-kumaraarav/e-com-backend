import base64
import hashlib
import hmac

import pyotp
from django.conf import settings


def get_email_totp(email: str) -> pyotp.TOTP:
    normalized_email = email.strip().lower().encode("utf-8")
    digest = hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=normalized_email,
        digestmod=hashlib.sha256,
    ).digest()

    # pyotp requires a valid Base32 secret (first 20 bytes -> 32 Base32 chars)
    base32_secret = base64.b32encode(digest[:20]).decode("utf-8")
    return pyotp.TOTP(base32_secret, interval=120)