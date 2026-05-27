from fastapi import FastAPI
from search_app.api import search, health

app = FastAPI(title="Search Service", version="1.0.0")
app.include_router(health.router, tags=["Health"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
