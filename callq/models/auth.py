from dataclasses import dataclass
from typing import Optional


@dataclass
class AuthResponse:
    userId: str
    accessToken: str
    refreshToken: str
    userLogin: Optional[str]
    accessTokenExpiredDate: Optional[str]
    
    @staticmethod
    def from_dict(data: dict) -> "AuthResponse":
        return AuthResponse(
            userId=data.get("userId", ""),
            accessToken=data.get("accessToken", ""),
            refreshToken=data.get("refreshToken", ""),
            userLogin=data.get("userLogin", ""),
            accessTokenExpiredDate=data.get("accessTokenExpiredDate", "")
        )
