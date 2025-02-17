from fastapi import Request
from typing import Optional
from src.storage.user_store import UserStore
from src.auth.jwt import decode_jwt_token


class AuthMiddleware:
    def __init__(self, user_store: UserStore):
        self.user_store = user_store

    async def get_current_user(self, request: Request) -> Optional[dict]:
        """Get the current user from the session token"""
        token = request.cookies.get("session_token")
        if not token:
            return None

        try:
            # Verify and decode the JWT token
            user_data = decode_jwt_token(token)
            user = await self.user_store.get_user_by_id(user_data["user_id"])
            return user
        except:
            return None

    async def __call__(self, request: Request, call_next):
        # Attach the get_current_user method to the request state
        request.state.get_current_user = lambda: self.get_current_user(request)

        response = await call_next(request)
        return response
