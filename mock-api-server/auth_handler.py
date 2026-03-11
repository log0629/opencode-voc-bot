"""
JWT Handler for Mock Server
"""
import jwt
from datetime import datetime, timedelta

JWT_SECRET = "mock-secret-key-for-testing"
JWT_ALGORITHM = "HS256"


def create_jwt(user_id: str, user_name: str) -> str:
    """Create a JWT token with user info"""
    payload = {
        "user_id": user_id,
        "user_name": user_name,
        "ep_id": "EP001",
        "division": "Engineering",
        "department": "Platform",
        "upr_department": "Tech",
        "lwr_department": "Backend",
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and verify JWT token"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
