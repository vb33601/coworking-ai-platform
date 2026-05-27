from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
import httpx
import structlog
from gateway_app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()
router = APIRouter()

SERVICE_MAP = {
    "orchestrator": settings.ORCHESTRATOR_URL,
    "search": settings.SEARCH_URL,
    "pricing": settings.PRICING_URL,
    "analytics": settings.ANALYTICS_URL,
    "notification": settings.NOTIFICATION_URL,
}

async def get_current_user(request: Request):
    # In production: validate JWT and extract tenant/user
    return {"tenant_id": "demo", "user_id": "demo", "role": "admin"}

@router.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(service: str, path: str, request: Request, user: dict = Depends(get_current_user)):
    """Route requests to upstream microservices."""
    if service not in SERVICE_MAP:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    target = f"{SERVICE_MAP[service]}/api/v1/{service}/{path}"
    method = request.method
    headers = dict(request.headers)
    headers["X-Tenant-ID"] = user.get("tenant_id", "")
    headers["X-User-ID"] = user.get("user_id", "")
    
    body = await request.body()
    
    try:
        # Orchestrator can take 90-120s for full multi-agent LLM pipeline
        timeout = 180.0 if service == "orchestrator" else 60.0
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, target, headers=headers, content=body, params=request.query_params)
            return resp.json()
    except httpx.TimeoutException:
        logger.error("gateway.timeout", service=service, path=path, timeout=timeout)
        raise HTTPException(status_code=504, detail="Upstream service timeout")
    except Exception as e:
        logger.error("gateway.error", service=service, path=path, error=str(e))
        raise HTTPException(status_code=502, detail=str(e))
