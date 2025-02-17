from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated
from src.core.dependencies import get_screenplay_store, get_templates
from src.storage.screenplay_store import ScreenplayStore

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def gallery(
    request: Request,
    screenplay_store: Annotated[ScreenplayStore, Depends(get_screenplay_store)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    page_starts_at: str = None,
):
    """Show paginated gallery of screenplays"""
    page_size = 12
    screenplays, next_page_start = await screenplay_store.get_paginated_screenplays(
        page_size=page_size, page_starts_at=page_starts_at, public_only=True
    )

    # If page_starts_at is provided, return only the gallery items
    if page_starts_at:
        return templates.TemplateResponse(
            "gallery_items.html",
            {
                "request": request,
                "screenplays": screenplays,
                "next_page_start": next_page_start,
            },
        )

    # Otherwise return the full gallery page
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "screenplays": screenplays,
            "next_page_start": next_page_start,
        },
    )
