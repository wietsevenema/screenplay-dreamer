import sys
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated
from src.core.dependencies import get_user_store, UserStore, get_templates, require_user
from src.auth.jwt import create_jwt_token
from src.core.settings import settings

router = APIRouter()


@router.get("/logout", response_class=HTMLResponse)
async def logout_page(
    request: Request,
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    user: Annotated[dict, Depends(require_user)],
):
    return templates.TemplateResponse("logout.html", {"request": request, "user": user})


@router.post("/logout")
async def logout(request: Request):
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("session_token")
    return response


@router.post("/token")
async def verify_token(
    request: Request, user_store: Annotated[UserStore, Depends(get_user_store)]
):
    try:
        body = await request.json()
        token = body.get("credential")

        # Verify token and store user
        user_id = await user_store.create_or_update_user(token)

        # Create JWT token
        jwt_token = create_jwt_token({"user_id": user_id})

        # Calculate max_age in seconds to match JWT expiry
        max_age = settings.TOKEN_EXPIRE_DAYS * 24 * 60 * 60 - 60

        # Create response with secure cookie
        response = JSONResponse(content={"status": "success"})
        response.set_cookie(
            key="session_token",
            value=jwt_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=max_age,
        )

        return response

    except ValueError as e:
        print(f"Token validation error: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    next: str = None,
):
    return templates.TemplateResponse(
        "login.html", {"request": request, "next": next, "settings": settings}
    )


@router.get("/about", response_class=HTMLResponse)
async def about(
    request: Request, templates: Annotated[Jinja2Templates, Depends(get_templates)]
):
    return templates.TemplateResponse("about.html", {"request": request})
