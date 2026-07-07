from pydantic import BaseModel


class LoginRequest(BaseModel):
    phone: str

class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
