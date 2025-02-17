from fastapi import APIRouter, Response, Depends, HTTPException
from typing import Annotated
from src.core.dependencies import get_image_store
from src.storage.image_store import ImageStore

router = APIRouter()


@router.get("/{image_id}")
async def get_image(
    image_id: str,
    image_store: Annotated[ImageStore, Depends(get_image_store)],
):
    """Serve images directly from Cloud Storage"""
    try:
        blob = image_store.get_image_blob(image_id)
        image_bytes = blob.download_as_bytes()
        return Response(content=image_bytes, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=404, detail="Image not found")
