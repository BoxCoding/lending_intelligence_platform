"""LendIQ — Retail Lending Intelligence Platform API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import logger
from app.ml_registry import registry
from app.routers import aa, dashboard, insights, predict


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.load_all()
    logger.info("LendIQ API started. Models: %s", registry.status())
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "AI-powered retail lending intelligence: AA data ingestion, income "
        "estimation, borrowing intent, repayment capacity, risk, lead scoring, "
        "explainable loan recommendations and a Gemini financial advisor."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(aa.router)
app.include_router(predict.router)
app.include_router(insights.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Health"])
def health():
    return {"service": settings.app_name, "version": settings.version, "models": registry.status()}
