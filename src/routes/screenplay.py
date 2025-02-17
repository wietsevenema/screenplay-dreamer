from fastapi import APIRouter, Request, Form, HTTPException, Response, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated
from src.core.dependencies import (
    get_screenplay_store,
    get_templates,
    get_image_store,
    get_genai_client,
    get_user_store,
    require_user,
)
from src.storage.screenplay_store import ScreenplayStore
from src.storage.user_store import UserStore
from src.storage.image_store import ImageStore
from fastapi import UploadFile, File
from src.writing.template_loader import TemplateLoader
from google import genai
from src.writing.screenplay_graph import ScreenplayGenerator

router = APIRouter()
prompt_templates = TemplateLoader()


@router.get("/new", response_class=HTMLResponse)
async def new_screenplay(
    request: Request,
    user: Annotated[dict, Depends(require_user)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
):
    return templates.TemplateResponse("new.html", {"request": request, "user": user})


@router.get("/{screenplay_id}", response_class=HTMLResponse)
async def view_screenplay(
    request: Request,
    screenplay_id: str,
    screenplay_store: Annotated[ScreenplayStore, Depends(get_screenplay_store)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
):
    """Serve a stored screenplay by its ID"""
    screenplay = await screenplay_store.get_screenplay(screenplay_id)
    screenplay_user = await user_store.get_user_by_id(screenplay["user_id"])
    if not screenplay:
        raise HTTPException(status_code=404, detail="Screenplay not found")

    # Get current user if logged in
    user = await request.state.get_current_user()

    return templates.TemplateResponse(
        "screenplay_view.html",
        {
            "request": request,
            "screenplay_id": screenplay_id,
            "screenplay": screenplay,
            "screenplay_user": screenplay_user,
            "user": user,
        },
    )


@router.post("/generate")
async def generate_screenplay(
    request: Request,
    user: Annotated[dict, Depends(require_user)],
    image_store: Annotated[ImageStore, Depends(get_image_store)],
    screenplay_store: Annotated[ScreenplayStore, Depends(get_screenplay_store)],
    genai_client: Annotated[genai.Client, Depends(get_genai_client)],
    file: UploadFile = File(...),
):
    # Validate file type
    if file.content_type not in [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/heic",
        "image/heif",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG, GIF and HEIC/HEIF images are allowed",
        )

    # Read and store the image first
    image_contents = await file.read()
    image_id, resized_image = await image_store.process_and_store_image(
        image_contents, file.content_type
    )

    # Generate the screenplay
    generator = ScreenplayGenerator(genai_client)
    final_state = await generator.generate_from_image(resized_image)

    # Store the screenplay
    screenplay_data = {
        "user_id": user["id"],
        "raw_scene": final_state["scene"],
        "structured_scene": final_state["structured_scene"].model_dump(),
        "genre": final_state["genre"],
        "models": final_state["models"],
        "analysis": final_state.get("analysis"),
    }

    # Store the screenplay with reference to the image
    screenplay_id = await screenplay_store.store_screenplay(screenplay_data, image_id)

    # Return a response with HX-Redirect header
    response = Response()
    response.headers["HX-Redirect"] = f"/screenplay/{screenplay_id}"
    return response


@router.patch("/{screenplay_id}/settings")
async def update_screenplay_settings(
    screenplay_id: str,
    user: Annotated[dict, Depends(require_user)],
    screenplay_store: Annotated[ScreenplayStore, Depends(get_screenplay_store)],
    public: Annotated[bool, Form()] = False,
):
    """Update screenplay settings from form data if user owns it"""
    settings = {"public": public}
    success = await screenplay_store.update_screenplay_settings(
        screenplay_id=screenplay_id, user_id=user["id"], settings=settings
    )

    if not success:
        raise HTTPException(
            status_code=404, detail="Screenplay not found or not authorized"
        )

    return {"status": "success"}


@router.get("/", response_class=HTMLResponse)
async def user_screenplays(
    request: Request,
    user: Annotated[dict, Depends(require_user)],
    screenplay_store: Annotated[ScreenplayStore, Depends(get_screenplay_store)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    page_starts_at: str = None,
):
    """Show all screenplays for the logged in user"""
    page_size = 12
    screenplays, next_page_start = await screenplay_store.get_paginated_screenplays(
        page_size=page_size,
        page_starts_at=page_starts_at,
        public_only=False,
        user_id=user["id"],
    )

    return templates.TemplateResponse(
        "user_screenplays.html",
        {
            "request": request,
            "screenplays": screenplays,
            "next_page_start": next_page_start,
        },
    )
