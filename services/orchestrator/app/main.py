import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger = structlog.get_logger()
    logger.info("env.loaded", path=env_path)

from app.core.config import get_settings
from app.api import orchestrator, health, memory, tools

logger = structlog.get_logger()
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("orchestrator.startup", app=settings.APP_NAME)
    try:
        from app.memory.vector_store import VectorStore
        app.state.vector_store = VectorStore()
        await app.state.vector_store.initialize()
    except Exception as e:
        logger.warning("vector_store.init_failed", error=str(e))
        app.state.vector_store = None
    yield
    logger.info("orchestrator.shutdown")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["Orchestrator"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["Tools"])

@app.middleware("http")
async def log_requests(request: Request, call_next):
    from time import time
    start = time()
    response = await call_next(request)
    latency = (time() - start) * 1000
    logger.info(
        "http.request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=round(latency, 2),
    )
    return response
