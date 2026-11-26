import pyotp 

def generate_otp(otp_secret: str) -> str:
    """
    Generate a time-based OTP for the given OTP secret.
    """
    # Create a TOTP object using the email as the secret key
    totp = pyotp.TOTP(otp_secret, interval=300)  # 5 minutes validity
    # Generate the OTP
    otp = totp.now()
    return otp