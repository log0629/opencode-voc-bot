"""
JWT Bearer Authentication
"""
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth_handler import decode_jwt


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.user_id = ""
        self.user_name = ""
        self.ep_id = ""
        self.division = ""
        self.department = ""
        self.upr_department = ""
        self.lwr_department = ""
        self.credentials = ""

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if not credentials:
            raise HTTPException(status_code=401, detail="Invalid authorization code.")
        if not credentials.scheme == "Bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme.")
        if not self.verify_jwt(credentials.credentials):
            raise HTTPException(status_code=401, detail="Invalid token or expired token.")
        return self.user_id, self.user_name, self.ep_id, self.division, self.department, self.upr_department, self.lwr_department, self.credentials

    def verify_jwt(self, jwtoken: str) -> bool:
        try:
            payload = decode_jwt(jwtoken)
            self.user_id = payload['user_id']
            self.user_name = payload['user_name']
            self.ep_id = payload.get('ep_id', "")
            self.division = payload['division']
            self.department = payload['department']
            self.upr_department = payload.get('upr_department', "")
            self.lwr_department = payload.get('lwr_department', "")
            self.credentials = jwtoken
            return True
        except Exception as e:
            print(f"JWT verification failed: {e}")
            return False
