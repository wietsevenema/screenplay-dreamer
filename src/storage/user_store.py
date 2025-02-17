from google.cloud import firestore
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from google.oauth2 import id_token
from google.auth.transport import requests
from src.core.settings import settings


class UserStore:
    def __init__(self, db: firestore.Client):
        self.db = db
        self.users = self.db.collection("users")

    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Look up a user by email"""
        query = self.users.where(field_path="email", op_string="==", value=email).limit(
            1
        )
        docs = list(query.stream())
        if docs:
            return {"id": docs[0].id, **docs[0].to_dict()}
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Look up a user by their ID"""
        doc_ref = self.users.document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None

    async def validate_token(self, token: str) -> dict:
        """Validate Google OAuth token and return user info"""
        try:
            return id_token.verify_oauth2_token(
                token, requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError as e:
            raise ValueError("Invalid token") from e

    async def create_or_update_user(self, token: str) -> str:
        """Verify token and create or update user record"""
        try:
            # Verify the token
            id_info = await self.validate_token(token)

            # Extract user data
            user_data = {
                "email": id_info["email"],
                "name": id_info.get("name"),
                "picture": id_info.get("picture"),
                "hd": id_info.get("hd"),  # Hosted domain for Google Workspace users
                "last_login": datetime.now(timezone.utc),
            }

            # Find existing user
            existing_user = await self.find_user_by_email(user_data["email"])

            if existing_user:
                # Update existing user
                user_ref = self.users.document(existing_user["id"])
                user_ref.update(user_data)
                return existing_user["id"]
            else:
                # Create new user
                doc_ref = self.users.document()
                doc_ref.set(user_data)
                return doc_ref.id

        except ValueError as e:
            raise ValueError("Invalid token") from e
