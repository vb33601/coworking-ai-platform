from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()
router = APIRouter()

class PricingRequest(BaseModel):
    workspace_id: str
    team_size: int
    duration_months: int
    amenities: List[str] = []
    parking_count: int = 0
    cabins: int = 0
    meeting_rooms: int = 0
    require_24_7: bool = False
    provider: Optional[str] = None
    price_per_seat_inr: Optional[float] = None

class PricingBreakdown(BaseModel):
    base_seat_cost_inr: float
    seat_count: int
    subtotal_inr: float
    gst_inr: float
    maintenance_inr: float
    parking_inr: float
    internet_inr: float
    security_deposit_inr: float
    setup_fee_inr: float
    total_month_1_inr: float
    total_monthly_inr: float
    tco_6_month_inr: float
    tco_12_month_inr: float
    per_seat_effective_inr: float

# Pricing rules by provider
PROVIDER_PRICING_RULES = {
    "wework": {"base_per_seat": 12000, "maintenance_pct": 0.08, "parking_per_vehicle": 2500, "setup_per_seat": 1000, "security_months": 2},
    "indiqube": {"base_per_seat": 9500, "maintenance_pct": 0.06, "parking_per_vehicle": 2000, "setup_per_seat": 500, "security_months": 2},
    "awfis": {"base_per_seat": 15000, "maintenance_pct": 0.10, "parking_per_vehicle": 3000, "setup_per_seat": 1500, "security_months": 3},
    "smartworks": {"base_per_seat": 11000, "maintenance_pct": 0.07, "parking_per_vehicle": 2200, "setup_per_seat": 800, "security_months": 2},
    "bhive": {"base_per_seat": 8500, "maintenance_pct": 0.05, "parking_per_vehicle": 1500, "setup_per_seat": 0, "security_months": 1},
    "cowrks": {"base_per_seat": 10500, "maintenance_pct": 0.07, "parking_per_vehicle": 2200, "setup_per_seat": 750, "security_months": 2},
    "simpliwork": {"base_per_seat": 10000, "maintenance_pct": 0.07, "parking_per_vehicle": 2500, "setup_per_seat": 500, "security_months": 2},
    "regus": {"base_per_seat": 14000, "maintenance_pct": 0.09, "parking_per_vehicle": 2800, "setup_per_seat": 1200, "security_months": 2},
    "91springboard": {"base_per_seat": 9000, "maintenance_pct": 0.05, "parking_per_vehicle": 1800, "setup_per_seat": 0, "security_months": 1},
    "tablespace": {"base_per_seat": 10000, "maintenance_pct": 0.07, "parking_per_vehicle": 2000, "setup_per_seat": 500, "security_months": 2},
}

@router.post("/calculate")
async def calculate_pricing(request: PricingRequest) -> Dict[str, Any]:
    """Calculate detailed pricing breakdown for a workspace configuration."""
    # Use provided provider or extract from workspace_id prefix
    provider = request.provider or (request.workspace_id.split("-")[0] if "-" in request.workspace_id else "wework")
    rules = PROVIDER_PRICING_RULES.get(provider, PROVIDER_PRICING_RULES["wework"])
    
    # Use provided price_per_seat_inr if available, otherwise use rules default
    base = request.price_per_seat_inr or rules["base_per_seat"]
    seats = request.team_size
    months = request.duration_months
    
    # Base seat cost
    base_cost = base * seats
    
    # Premiums
    premium_24_7 = 0.15 if request.require_24_7 else 0.0
    premium_cabin = request.cabins * 15000
    premium_meeting = request.meeting_rooms * 8000
    
    subtotal = base_cost * (1 + premium_24_7) + premium_cabin + premium_meeting
    
    # Additional costs
    maintenance = subtotal * rules["maintenance_pct"]
    parking = request.parking_count * rules["parking_per_vehicle"]
    internet = seats * 500  # Redundant internet per seat
    
    # One-time costs
    setup_fee = seats * rules["setup_per_seat"]
    security_deposit = subtotal * rules["security_months"]
    
    # GST (18% in India)
    gst = (subtotal + maintenance + parking + internet) * 0.18
    
    monthly_total = subtotal + maintenance + parking + internet + gst
    month_1_total = monthly_total + setup_fee + security_deposit
    
    tco_6 = monthly_total * min(6, months) + setup_fee + security_deposit
    tco_12 = monthly_total * min(12, months) + setup_fee + security_deposit
    
    per_seat_effective = monthly_total / seats if seats > 0 else 0
    
    logger.info("pricing.calculated", workspace=request.workspace_id, seats=seats, monthly=monthly_total)
    
    return {
        "workspace_id": request.workspace_id,
        "provider": provider,
        "breakdown": {
            "base_seat_cost_inr": base,
            "seat_count": seats,
            "base_subtotal_inr": round(base_cost, 2),
            "premium_24_7_inr": round(base_cost * premium_24_7, 2),
            "premium_cabins_inr": round(premium_cabin, 2),
            "premium_meeting_rooms_inr": round(premium_meeting, 2),
            "subtotal_inr": round(subtotal, 2),
            "maintenance_inr": round(maintenance, 2),
            "parking_inr": round(parking, 2),
            "internet_inr": round(internet, 2),
            "gst_18_pct_inr": round(gst, 2),
            "setup_fee_inr": round(setup_fee, 2),
            "security_deposit_inr": round(security_deposit, 2),
            "total_month_1_inr": round(month_1_total, 2),
            "total_monthly_inr": round(monthly_total, 2),
            "tco_6_month_inr": round(tco_6, 2),
            "tco_12_month_inr": round(tco_12, 2),
            "per_seat_effective_inr": round(per_seat_effective, 2),
        },
        "negotiation_leverage": [
            f"Bulk seat discount potential: {(seats > 20) * 5 + (seats > 50) * 5}%",
            f"Long-term commitment ({months}+ months) discount: {(months >= 12) * 5 + (months >= 18) * 5}%",
            f"Quick move-in (within 30 days) discount: 3-5%",
            f"Referral from existing tenant: 2-3%",
        ],
    }

@router.post("/compare")
async def compare_pricing(requests: List[PricingRequest]) -> Dict[str, Any]:
    """Compare pricing across multiple workspace configurations."""
    results = []
    for req in requests:
        result = await calculate_pricing(req)
        results.append(result)
    
    # Rank by monthly cost
    ranked = sorted(results, key=lambda x: x["breakdown"]["total_monthly_inr"])
    
    return {
        "comparisons": results,
        "ranked": ranked,
        "best_value": ranked[0] if ranked else None,
        "cost_savings": round(ranked[-1]["breakdown"]["total_monthly_inr"] - ranked[0]["breakdown"]["total_monthly_inr"], 2) if len(ranked) > 1 else 0,
    }
