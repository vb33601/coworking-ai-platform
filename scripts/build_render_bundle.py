#!/usr/bin/env python3
"""Build a monolithic Render deployment bundle from microservices."""

import shutil
import sys
import re
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE_DIR = os.path.join(PROJECT_ROOT, "render_bundle")

def clean_and_create_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def copy_service(service_name, src_rel, dest_name):
    src = os.path.join(PROJECT_ROOT, src_rel)
    dst = os.path.join(BUNDLE_DIR, dest_name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst

def rename_imports_in_file(filepath, old_prefix, new_prefix):
    """Replace 'from app.' and 'import app.' with service-specific names."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Only replace imports, not general 'app.' usage
    # Pattern: from app.XXX -> from {new_prefix}.XXX
    content = re.sub(r'\bfrom\s+app\.', f'from {new_prefix}.', content)
    # Pattern: import app.XXX -> import {new_prefix}.XXX
    content = re.sub(r'\bimport\s+app\.', f'import {new_prefix}.', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def process_service(service_name, src_rel, pkg_name):
    dst = copy_service(service_name, src_rel, pkg_name)
    for root, dirs, files in os.walk(dst):
        for fname in files:
            if fname.endswith('.py'):
                fpath = os.path.join(root, fname)
                rename_imports_in_file(fpath, 'app', pkg_name)
    print(f"  Copied {service_name} -> {pkg_name}")

def build():
    print("Building Render bundle...")
    clean_and_create_dir(BUNDLE_DIR)

    # 1. Copy and rename each service
    services = [
        ("gateway", "services/gateway/app", "gateway_app"),
        ("orchestrator", "services/orchestrator/app", "orch_app"),
        ("search", "services/search/app", "search_app"),
        ("pricing", "services/pricing/app", "pricing_app"),
    ]
    for name, src, pkg in services:
        process_service(name, src, pkg)

    # 2. Copy shared if it exists and has content
    shared_src = os.path.join(PROJECT_ROOT, "shared")
    if os.path.exists(shared_src):
        shared_dst = os.path.join(BUNDLE_DIR, "shared")
        shutil.copytree(shared_src, shared_dst)
        print("  Copied shared/")

    # 3. Create unified requirements.txt
    req_lines = set()
    for svc_root in ["services/gateway", "services/orchestrator", "services/search", "services/pricing"]:
        req_path = os.path.join(PROJECT_ROOT, svc_root, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        req_lines.add(line)

    # Add missing common deps
    extra = ['python-dotenv', 'email-validator', 'jinja2']
    for e in extra:
        req_lines.add(e)

    with open(os.path.join(BUNDLE_DIR, "requirements.txt"), 'w') as f:
        for line in sorted(req_lines):
            f.write(line + '\n')
    print("  Created requirements.txt")

    # 4. Create combined main.py
    main_py = '''import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog

logger = structlog.get_logger()

# Ensure bundle dir is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gateway_app.api import health as gw_health
from gateway_app.api import proxy as gw_proxy
from orch_app.api import health as orch_health
from orch_app.api import orchestrator as orch_router
from orch_app.api import memory as orch_memory
from orch_app.api import tools as orch_tools
from search_app.api import health as search_health
from search_app.api import search as search_router
from pricing_app.api import health as pricing_health
from pricing_app.api import pricing as pricing_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("platform.startup")
    # Initialize orchestrator vector store if available
    try:
        from orch_app.memory.vector_store import VectorStore
        app.state.vector_store = VectorStore()
        await app.state.vector_store.initialize()
    except Exception as e:
        logger.warning("vector_store.init_failed", error=str(e))
        app.state.vector_store = None
    yield
    logger.info("platform.shutdown")

app = FastAPI(
    title="Coworking AI Platform",
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

# API Routes
app.include_router(gw_health.router, tags=["Health"])
app.include_router(orch_health.router, tags=["Health"])
app.include_router(search_health.router, tags=["Health"])
app.include_router(pricing_health.router, tags=["Health"])

app.include_router(orch_router.router, prefix="/api/v1/orchestrator", tags=["Orchestrator"])
app.include_router(orch_memory.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(orch_tools.router, prefix="/api/v1/tools", tags=["Tools"])
app.include_router(search_router.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(pricing_router.router, prefix="/api/v1/pricing", tags=["Pricing"])

# Static files (frontend build output)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# Fallback for SPA routing — serve index.html for non-API, non-file requests
@app.api_route("/{path:path}", methods=["GET"])
async def spa_fallback(path: str):
    if path.startswith("api/") or path.startswith("docs") or path.startswith("redoc") or path.startswith("openapi.json"):
        return None
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Not Found"}

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
'''

    with open(os.path.join(BUNDLE_DIR, "main.py"), 'w') as f:
        f.write(main_py)
    print("  Created main.py")

    # 5. Copy frontend build output if it exists
    frontend_dist = os.path.join(PROJECT_ROOT, "frontend", "dist")
    if os.path.exists(frontend_dist):
        static_dst = os.path.join(BUNDLE_DIR, "static")
        shutil.copytree(frontend_dist, static_dst)
        print("  Copied frontend/dist -> static/")
    else:
        print("  WARNING: frontend/dist not found. Run 'cd frontend && npm run build' first.")

    print(f"\\nBundle ready at: {BUNDLE_DIR}")

if __name__ == "__main__":
    build()
