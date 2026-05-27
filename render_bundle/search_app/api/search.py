from fastapi import APIRouter, Query
from typing import List, Optional, Dict, Any
import structlog

logger = structlog.get_logger()
router = APIRouter()

# Mock workspace database for demo
MOCK_WORKSPACES = [
    {
        "id": "ws-001",
        "name": "WeWork Galaxy",
        "provider": "wework",
        "city": "Bangalore",
        "area": "Koramangala",
        "address": "Galaxy Mall, 7th Block, Koramangala",
        "workspace_type": "coworking",
        "seating_capacity": 500,
        "available_seats": 120,
        "price_per_seat_inr": 12000,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation", "24_7"],
        "meeting_rooms": 8,
        "cabins": 15,
        "parking_capacity": 80,
        "is_24_7": True,
        "latitude": 12.9352,
        "longitude": 77.6245,
        "trust_score": 4.3,
    },
    {
        "id": "ws-002",
        "name": "IndiQube Park",
        "provider": "indiqube",
        "city": "Bangalore",
        "area": "Whitefield",
        "address": "IndiQube Park, EPIP Zone, Whitefield",
        "workspace_type": "managed_office",
        "seating_capacity": 350,
        "available_seats": 80,
        "price_per_seat_inr": 9500,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "server_room", "24_7"],
        "meeting_rooms": 6,
        "cabins": 12,
        "parking_capacity": 60,
        "is_24_7": True,
        "latitude": 12.9716,
        "longitude": 77.7500,
        "trust_score": 4.5,
    },
    {
        "id": "ws-003",
        "name": "Awfis MG Road",
        "provider": "awfis",
        "city": "Bangalore",
        "area": "MG Road",
        "address": "UB City, MG Road",
        "workspace_type": "coworking",
        "seating_capacity": 200,
        "available_seats": 45,
        "price_per_seat_inr": 15000,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation"],
        "meeting_rooms": 5,
        "cabins": 8,
        "parking_capacity": 40,
        "is_24_7": False,
        "latitude": 12.9756,
        "longitude": 77.6058,
        "trust_score": 4.1,
    },
    {
        "id": "ws-004",
        "name": "Smartworks ORR",
        "provider": "smartworks",
        "city": "Bangalore",
        "area": "Outer Ring Road",
        "address": "Smartworks Tower, ORR, Bellandur",
        "workspace_type": "enterprise_suite",
        "seating_capacity": 800,
        "available_seats": 200,
        "price_per_seat_inr": 11000,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation", "server_room", "24_7", "branding"],
        "meeting_rooms": 12,
        "cabins": 25,
        "parking_capacity": 150,
        "is_24_7": True,
        "latitude": 12.9279,
        "longitude": 77.6785,
        "trust_score": 4.4,
    },
    {
        "id": "ws-005",
        "name": "BHIVE HSR",
        "provider": "bhive",
        "city": "Bangalore",
        "area": "HSR Layout",
        "address": "BHIVE Workspace, HSR Layout Sector 7",
        "workspace_type": "coworking",
        "seating_capacity": 150,
        "available_seats": 30,
        "price_per_seat_inr": 8500,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking"],
        "meeting_rooms": 4,
        "cabins": 6,
        "parking_capacity": 25,
        "is_24_7": False,
        "latitude": 12.9121,
        "longitude": 77.6446,
        "trust_score": 4.2,
    },
    {
        "id": "ws-006",
        "name": "CoWrks Embassy",
        "provider": "cowrks",
        "city": "Bangalore",
        "area": "Manyata Tech Park",
        "address": "Embassy Manyata, Nagavara",
        "workspace_type": "managed_office",
        "seating_capacity": 600,
        "available_seats": 150,
        "price_per_seat_inr": 10500,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation", "server_room", "24_7", "branding"],
        "meeting_rooms": 10,
        "cabins": 20,
        "parking_capacity": 120,
        "is_24_7": True,
        "latitude": 13.0458,
        "longitude": 77.6207,
        "trust_score": 4.5,
    },
    {
        "id": "ws-007",
        "name": "Simpliwork BKC",
        "provider": "simpliwork",
        "city": "Mumbai",
        "area": "BKC",
        "address": "Simpliwork Tower, BKC, Mumbai",
        "workspace_type": "enterprise_suite",
        "seating_capacity": 400,
        "available_seats": 100,
        "price_per_seat_inr": 18000,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation", "server_room", "24_7", "branding"],
        "meeting_rooms": 8,
        "cabins": 16,
        "parking_capacity": 100,
        "is_24_7": True,
        "latitude": 19.0600,
        "longitude": 72.8656,
        "trust_score": 4.3,
    },
    {
        "id": "ws-008",
        "name": "Regus Connaught Place",
        "provider": "regus",
        "city": "Delhi",
        "area": "Connaught Place",
        "address": "Regus, Connaught Place, New Delhi",
        "workspace_type": "coworking",
        "seating_capacity": 300,
        "available_seats": 75,
        "price_per_seat_inr": 14000,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "24_7"],
        "meeting_rooms": 7,
        "cabins": 10,
        "parking_capacity": 50,
        "is_24_7": True,
        "latitude": 28.6315,
        "longitude": 77.2167,
        "trust_score": 4.1,
    },
    {
        "id": "ws-009",
        "name": "91Springboard Hyderabad",
        "provider": "91springboard",
        "city": "Hyderabad",
        "area": "Hitech City",
        "address": "91Springboard, Hitech City, Hyderabad",
        "workspace_type": "coworking",
        "seating_capacity": 250,
        "available_seats": 60,
        "price_per_seat_inr": 9000,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation"],
        "meeting_rooms": 6,
        "cabins": 8,
        "parking_capacity": 40,
        "is_24_7": False,
        "latitude": 17.4430,
        "longitude": 78.3772,
        "trust_score": 4.0,
    },
    {
        "id": "ws-010",
        "name": "TableSpace Pune",
        "provider": "tablespace",
        "city": "Pune",
        "area": "Kharadi",
        "address": "TableSpace, Kharadi, Pune",
        "workspace_type": "managed_office",
        "seating_capacity": 450,
        "available_seats": 110,
        "price_per_seat_inr": 10000,
        "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "server_room", "24_7"],
        "meeting_rooms": 9,
        "cabins": 15,
        "parking_capacity": 90,
        "is_24_7": True,
        "latitude": 18.5500,
        "longitude": 73.9500,
        "trust_score": 4.2,
    },
]

@router.get("/workspaces")
async def search_workspaces(
    city: Optional[str] = None,
    area: Optional[str] = None,
    workspace_type: Optional[str] = None,
    min_seats: Optional[int] = None,
    max_budget_inr: Optional[int] = None,
    providers: Optional[List[str]] = Query(default=None),
    amenities: Optional[List[str]] = Query(default=None),
    is_24_7: Optional[bool] = None,
    meeting_rooms_min: Optional[int] = None,
    parking_min: Optional[int] = None,
    q: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """Search and filter workspaces across providers."""
    results = MOCK_WORKSPACES.copy()
    
    if city:
        results = [w for w in results if w["city"].lower() == city.lower()]
    if area:
        results = [w for w in results if area.lower() in w["area"].lower()]
    if workspace_type:
        results = [w for w in results if w["workspace_type"] == workspace_type]
    if min_seats:
        results = [w for w in results if w["available_seats"] >= min_seats]
    if max_budget_inr:
        results = [w for w in results if w["price_per_seat_inr"] <= max_budget_inr]
    if providers:
        results = [w for w in results if w["provider"] in providers]
    if amenities:
        results = [w for w in results if all(a in w["amenities"] for a in amenities)]
    if is_24_7 is not None:
        results = [w for w in results if w["is_24_7"] == is_24_7]
    if meeting_rooms_min:
        results = [w for w in results if w["meeting_rooms"] >= meeting_rooms_min]
    if parking_min:
        results = [w for w in results if w["parking_capacity"] >= parking_min]
    if q:
        q_lower = q.lower()
        results = [w for w in results if q_lower in w["name"].lower() or q_lower in w["area"].lower() or q_lower in w["city"].lower()]
    
    total = len(results)
    paginated = results[offset:offset + limit]
    
    logger.info("search.workspaces", city=city, results=total, filters={"providers": providers, "amenities": amenities})
    
    return {
        "results": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters_applied": {
            "city": city,
            "area": area,
            "workspace_type": workspace_type,
            "min_seats": min_seats,
            "max_budget_inr": max_budget_inr,
            "providers": providers,
            "amenities": amenities,
        },
    }

@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get detailed information about a specific workspace."""
    ws = next((w for w in MOCK_WORKSPACES if w["id"] == workspace_id), None)
    if not ws:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws

@router.get("/providers")
async def list_providers():
    """List all supported workspace providers."""
    providers = {}
    for w in MOCK_WORKSPACES:
        p = w["provider"]
        if p not in providers:
            providers[p] = {"name": p.title(), "cities": set(), "workspace_count": 0}
        providers[p]["cities"].add(w["city"])
        providers[p]["workspace_count"] += 1
    
    return [
        {"slug": k, "name": v["name"], "cities": list(v["cities"]), "workspace_count": v["workspace_count"]}
        for k, v in providers.items()
    ]
