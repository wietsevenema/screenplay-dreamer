from fastapi import FastAPI
from src.auth.middleware import AuthMiddleware
from fastapi.staticfiles import StaticFiles
from src.core.dependencies import get_user_store
from src.routes import auth, gallery, images, screenplay

app = FastAPI(docs_url=None, redoc_url=None)

# Add authentication middleware
app.middleware("http")(AuthMiddleware(get_user_store()))

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(gallery.router)
app.include_router(images.router, prefix="/images")
app.include_router(screenplay.router, prefix="/screenplay")
