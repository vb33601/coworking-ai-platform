from fastapi import FastAPI
from app.api import pricing, health

app = FastAPI(title="Pricing Service", version="1.0.0")
app.include_router(health.router, tags=["Health"])
app.include_router(pricing.router, prefix="/api/v1/pricing", tags=["Pricing"])
