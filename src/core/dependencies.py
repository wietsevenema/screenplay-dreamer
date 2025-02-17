from fastapi import Request, HTTPException
from urllib.parse import quote
from google.cloud import firestore, storage
from google import genai
from src.storage.user_store import UserStore
from src.storage.screenplay_store import ScreenplayStore
from src.storage.image_store import ImageStore
from fastapi.templating import Jinja2Templates
from src.core.settings import settings

# Initialize clients
firestore_client = firestore.Client()
storage_client = storage.Client()
genai_client = genai.Client(
    vertexai=True, project=settings.PROJECT_ID, location=settings.GEMINI_REGION
)

# Initialize stores
user_store = UserStore(firestore_client)
screenplay_store = ScreenplayStore(firestore_client)
image_store = ImageStore(storage_client)

# Templates (should be a global dependency)
templates = Jinja2Templates(directory="templates")
templates.env.globals["is_logged_in"] = lambda request: bool(
    request.cookies.get("session_token")
)


async def require_user(request: Request):
    user = await request.state.get_current_user()
    if not user:
        # Get the current path to redirect back to after login
        # Get just the path and query parts of the URL for relative redirect
        return_url = quote(
            str(request.url.path)
            + ("?" + str(request.url.query) if request.url.query else "")
        )
        raise HTTPException(
            status_code=303, headers={"Location": f"/login?next={return_url}"}
        )
    return user


def get_genai_client():
    return genai_client


def get_user_store():
    return user_store


def get_screenplay_store():
    return screenplay_store


def get_image_store():
    return image_store


def get_templates():
    return templates
