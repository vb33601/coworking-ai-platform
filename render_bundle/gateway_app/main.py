from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
import structlog
import httpx
from gateway_app.api import proxy, health
from gateway_app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("gateway.startup", app=settings.APP_NAME)
    yield
    logger.info("gateway.shutdown")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    # In production: check Redis for rate limit by tenant/API key
    response = await call_next(request)
    return response

app.include_router(health.router, tags=["Health"])
app.include_router(proxy.router, prefix="/api/v1", tags=["Gateway"])

# Catch-all: proxy everything else to Next.js frontend on port 3000
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def frontend_proxy(request: Request, path: str):
    """Proxy non-API requests to the Next.js frontend server."""
    frontend_url = "http://localhost:3000"
    target = f"{frontend_url}/{path}"
    if request.query_params:
        target += f"?{request.query_params}"

    method = request.method
    headers = dict(request.headers)
    headers.pop("host", None)

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.request(method, target, headers=headers, content=body)

        # Stream large responses (e.g. JS chunks) without loading fully into memory
        async def stream_response():
            async for chunk in resp.aiter_bytes():
                yield chunk

        return StreamingResponse(
            content=stream_response(),
            status_code=resp.status_code,
            headers=dict(resp.headers),
        )
    except Exception as e:
        logger.error("frontend_proxy.error", path=path, error=str(e))
        return Response(content=f"Frontend unavailable: {e}", status_code=502)
