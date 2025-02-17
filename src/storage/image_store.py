from google.cloud import storage
from google.cloud import firestore
from src.core.settings import settings
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import hashlib
from PIL import Image
import io
from pillow_heif import register_heif_opener

register_heif_opener()


class ImageStore:
    def __init__(self, storage_client: storage.Client):
        self.storage_client = storage_client
        self.bucket = self.storage_client.bucket(settings.BUCKET_NAME)
        self.db = firestore.Client()
        self.images = self.db.collection("images")
        self.MAX_WIDTH = 1024
        self.MAX_HEIGHT = 768

    async def find_image_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Look up an image by its hash"""
        query = self.images.where(
            field_path="hash", op_string="==", value=file_hash
        ).limit(1)
        docs = query.stream()
        for doc in docs:
            return {"id": doc.id, **doc.to_dict()}
        return None

    async def store_image_metadata(self, content_type: str, file_hash: str) -> str:
        """Store image metadata in Firestore and return its ID"""
        # Check for existing image
        existing = await self.find_image_by_hash(file_hash)
        if existing:
            return existing["id"]

        # Store new image metadata
        doc_ref = self.images.document()
        doc_ref.set(
            {
                "content_type": content_type,
                "hash": file_hash,
                "created_at": datetime.now(timezone.utc),
            }
        )
        return doc_ref.id

    async def process_and_store_image(
        self, contents: bytes, content_type: str
    ) -> tuple[str, bytes]:
        """
        Process an image by checking for duplicates and storing if new.
        Returns tuple of (image_id, resized_image_data).
        """
        # Compute hash of original image
        file_hash = self.compute_hash(contents)

        # Check for existing image
        existing_image = await self.find_image_by_hash(file_hash)

        if existing_image:
            # For existing images, download the resized version
            blob = self.get_image_blob(existing_image["id"])
            return existing_image["id"], blob.download_as_bytes()

        # For new images, resize once
        resized_image = self.resize_image(contents)

        # Store new image metadata first to get an ID
        image_id = await self.store_image_metadata(content_type, file_hash)

        # Store the resized image
        await self.store_image(resized_image, content_type, image_id)

        return image_id, resized_image

    def get_image_blob(self, image_id: str):
        """Get a blob reference for an image"""
        return self.bucket.blob(f"images/{image_id}")

    def resize_image(self, image_data: bytes) -> bytes:
        """Resize image, preserving aspect ratio, to max dimensions and convert to JPEG"""
        image = Image.open(io.BytesIO(image_data))

        # Apply EXIF rotation if present
        try:
            exif = image.getexif()
            if exif is not None:
                orientation = exif.get(274)  # 274 is the orientation tag
                if orientation is not None:
                    # Rotation values
                    if orientation == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation == 8:
                        image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            # Handle images without EXIF data
            pass

        # Convert to RGB if needed
        if image.mode in ("RGBA", "P", "CMYK"):
            image = image.convert("RGB")

        # Only convert to JPEG if it's not already JPEG
        if image.format != "JPEG":
            jpeg_buffer = io.BytesIO()
            image.save(jpeg_buffer, format="JPEG", quality=85)
            image = Image.open(jpeg_buffer)

        # Calculate aspect ratio
        width_ratio = self.MAX_WIDTH / image.width
        height_ratio = self.MAX_HEIGHT / image.height
        ratio = min(width_ratio, height_ratio)

        # Only resize if image is larger than max dimensions
        if ratio < 1:
            new_width = int(image.width * ratio)
            new_height = int(image.height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert to JPEG bytes
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85)
        return output.getvalue()

    def compute_hash(self, image_data: bytes) -> str:
        """Compute SHA256 hash of image data"""
        return hashlib.sha256(image_data).hexdigest()

    async def store_image(
        self, image_data: bytes, content_type: str, image_id: str
    ) -> str:
        """Store a resized JPEG image in Cloud Storage"""
        resized_image = self.resize_image(image_data)
        blob = self.get_image_blob(image_id)
        blob.upload_from_string(resized_image, content_type="image/jpeg")
