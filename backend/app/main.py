import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.limiter import limiter
from app.core.settings import settings
from app.db.database import Base, SessionLocal, engine
from app.routers.auth import router as auth_router
from app.routers.public_review import router as public_review_router
from app.routers.reviews import router as reviews_router
from app.routers.smart_reply import router as smart_reply_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    os.makedirs("static", exist_ok=True)
    if settings.debug:
        # Dev-only shortcut — run `alembic upgrade head` in production
        Base.metadata.create_all(bind=engine)
        logger.warning("dev mode: created tables via create_all — use Alembic in production")
    logger.info("Application started (debug=%s)", settings.debug)
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_title,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router,         prefix="/auth",        tags=["Auth"])
app.include_router(reviews_router,      prefix="/reviews",     tags=["Reviews"])
app.include_router(smart_reply_router,  prefix="/smart-reply", tags=["Smart Reply"])
app.include_router(public_review_router, prefix="/r",          tags=["Public Review"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "active"}


@app.get("/health", tags=["Health"])
def health():
    """Liveness + readiness check for load balancers and container orchestrators."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        db.close()

    overall = "ok" if db_ok else "degraded"
    return {"status": overall, "db": "ok" if db_ok else "error"}
