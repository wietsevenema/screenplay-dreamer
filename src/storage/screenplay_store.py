from google.cloud import firestore
from datetime import datetime, timezone
from typing import Dict, Any


class ScreenplayStore:
    def __init__(self, db: firestore.Client):
        self.db = db
        self.screenplays = self.db.collection("screenplays")

    async def store_screenplay(
        self, screenplay_data: Dict[str, Any], image_id: str
    ) -> str:
        """Store a screenplay in Firestore and return its ID"""
        doc_ref = self.screenplays.document()

        # Add metadata
        screenplay_data["created_at"] = datetime.now(timezone.utc)
        screenplay_data["image_id"] = image_id

        # Store the document
        doc_ref.set(screenplay_data)

        return doc_ref.id

    async def get_screenplay(self, screenplay_id: str) -> Dict[str, Any] | None:
        """Retrieve a screenplay from Firestore by ID"""
        doc_ref = self.screenplays.document(screenplay_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None

    async def update_screenplay_settings(
        self, screenplay_id: str, user_id: str, settings: Dict[str, Any]
    ) -> bool:
        """
        Update screenplay settings if the user owns it
        Returns True if successful, False if not found or not authorized
        """
        doc_ref = self.screenplays.document(screenplay_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        screenplay = doc.to_dict()
        if screenplay.get("user_id") != user_id:
            return False

        # Only allow updating specific fields
        allowed_settings = {k: v for k, v in settings.items() if k in ["public"]}

        if allowed_settings:
            doc_ref.update(allowed_settings)
            return True

        return False

    async def get_paginated_screenplays(
        self,
        page_size: int = 12,
        page_starts_at: str = None,
        public_only: bool = True,
        user_id: str = None,
    ) -> tuple[list[Dict[str, Any]], str | None]:
        """
        Retrieve paginated screenplays, ordered by creation date
        Returns tuple of (screenplays list, next_page_start_id)

        Args:
            page_size: Number of items per page
            page_starts_at: ID of document to start at for pagination
            public_only: If True, only return public screenplays
            user_id: If provided, only return screenplays for this user
        """
        # Start with base query
        query = self.screenplays.order_by(
            "created_at", direction=firestore.Query.DESCENDING
        )

        # Add filters
        if public_only:
            query = query.where("public", "==", True)
        if user_id:
            query = query.where("user_id", "==", user_id)

        # Add pagination limit
        query = query.limit(page_size + 1)

        if page_starts_at:
            start_doc = self.screenplays.document(page_starts_at).get()
            if start_doc.exists:
                query = query.start_at(start_doc)

        docs = list(query.stream())

        # If we got an extra item, use it as the next page start
        next_page_start = docs[page_size].id if len(docs) > page_size else None

        # Convert visible items to list of dicts
        result = []
        for doc in docs[:page_size]:  # Only take requested page size
            screenplay = doc.to_dict()
            screenplay["id"] = doc.id
            result.append(screenplay)

        return result, next_page_start
