import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.limiter import limiter
from app.core.settings import settings
from app.db.database import Base, engine
from app.routers.auth import router as auth_router
from app.routers.public_review import router as public_review_router
from app.routers.reviews import router as reviews_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    os.makedirs("static", exist_ok=True)
    if settings.debug:
        # Dev-only shortcut — run `alembic upgrade head` in production
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_title, lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(reviews_router, prefix="/reviews", tags=["Reviews"])
app.include_router(public_review_router, prefix="/r", tags=["Public Review"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "active"}
