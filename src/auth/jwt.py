import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from src.core.settings import settings


def create_jwt_token(user_data: Dict[str, Any]) -> str:
    """Create a JWT token containing user data"""
    expiration = datetime.now(timezone.utc) + timedelta(days=settings.TOKEN_EXPIRE_DAYS)

    token_data = {**user_data, "exp": expiration}

    return jwt.encode(token_data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token"""
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
