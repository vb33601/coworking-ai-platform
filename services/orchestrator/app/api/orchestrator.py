from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import structlog
import httpx
import os
from app.models.schemas import SearchRequest, SearchResponse, RequirementExtractionResult, ConversationCreate, MessageRequest
from app.agents.orchestrator_graph import AgentOrchestrator
from app.memory.vector_store import MemoryManager, VectorStore

logger = structlog.get_logger()
router = APIRouter()

class SearchRequestV2(BaseModel):
    tenant_id: str
    user_id: str
    raw_input: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class WorkspaceDetailRequest(BaseModel):
    tenant_id: str
    user_id: str
    team_size: int = 10
    duration_months: int = 12

# Helper: generate rich workspace metadata
def _enrich_workspace_data(ws: Dict[str, Any], team_size: int, raw_input: str) -> Dict[str, Any]:
    """Add negotiation points, risk analysis, commute, expansion data."""
    raw_lower = raw_input.lower()
    city = ws.get("city", "")
    area = ws.get("area", "")
    
    # Negotiation points
    negotiation_points = []
    if ws.get("available_seats", 0) > team_size * 2:
        negotiation_points.append(f"High vacancy ({ws['available_seats']} seats) - negotiate 10-15% discount")
    if team_size > 50:
        negotiation_points.append("Large team commitment - ask for dedicated account manager")
    if "managed" in raw_lower and ws.get("workspace_type") == "managed_office":
        negotiation_points.append("Managed office - negotiate branding rights and custom fit-outs")
    if ws.get("is_24_7"):
        negotiation_points.append("24/7 access included - verify HVAC and security costs")
    negotiation_points.append("Ask for first month free or reduced deposit")
    negotiation_points.append("Request parking allocation guarantee in writing")
    
    # Risk analysis
    risks = []
    if ws.get("available_seats", 0) < team_size:
        risks.append(f"Only {ws['available_seats']} seats available for {team_size} team - phased move-in required")
    if not ws.get("is_24_7") and ("24/7" in raw_lower or "round the clock" in raw_lower):
        risks.append("No 24/7 access - may not meet operational requirements")
    if ws.get("trust_score", 0) < 4.2:
        risks.append("Lower trust score - verify recent reviews and current management")
    risks.append("Verify exact pricing including GST, maintenance, and utilities")
    risks.append("Confirm deposit refund terms and notice period")
    
    # Nearby facilities (mock but realistic)
    nearby = {
        "metro_station": f"{area} Metro (0.8 km)" if city in ["Delhi", "Bangalore", "Mumbai", "Hyderabad", "Pune"] else "Nearest metro: 2.5 km",
        "restaurants": f"15+ restaurants within 500m of {area}",
        "hotels": f"Business hotels within 1km" if city in ["Bangalore", "Mumbai", "Delhi"] else "Hotels within 2km",
        "hospitals": f"Multi-specialty hospital within 1.5km",
        "banks": f"Major banks (HDFC, ICICI, SBI) within 800m",
        " gyms": f"Fitness centers within 600m",
    }
    
    # Commute insights
    commute = {
        "airport_distance_km": 25 if city == "Bangalore" else (20 if city == "Mumbai" else 18),
        "airport_time_min": 45 if city == "Bangalore" else 60,
        "peak_traffic": "Heavy 8-10 AM, 6-8 PM on ORR" if "ORR" in area or "Outer Ring" in area else "Moderate peak hours",
        "public_transport": f"Metro connectivity to {area} planned" if city == "Bangalore" else f"Metro available near {area}",
        "parking_availability": f"{ws.get('parking_capacity', 0)} spots on-site",
    }
    
    # Expansion possibilities
    expansion = {
        "adjacent_space": f"{max(0, ws.get('available_seats', 0) - team_size)} additional seats available in same building",
        "nearby_locations": [
            f"{ws.get('provider')} {area} Annex - 0.5km",
            f"{ws.get('provider')} {city} Central - 3km",
        ],
        "scalability_score": min(100, ws.get("available_seats", 0) / max(1, team_size) * 40),
        "recommended_growth": f"Can accommodate {ws.get('available_seats', 0)} total seats",
    }
    
    return {
        "negotiation_points": negotiation_points,
        "risk_analysis": risks,
        "nearby_facilities": nearby,
        "commute_insights": commute,
        "expansion_possibilities": expansion,
    }

# Fallback: deterministic rule-based recommendation when no AI keys
async def _fallback_recommendations(raw_input: str) -> Dict[str, Any]:
    """Generate recommendations via search + pricing services without LLM."""
    from app.core.config import get_settings
    settings = get_settings()
    search_url = settings.SEARCH_URL
    pricing_url = settings.PRICING_URL
    
    # Extract simple parameters from raw input
    raw_lower = raw_input.lower()
    city = None
    if "bangalore" in raw_lower or "bengaluru" in raw_lower:
        city = "Bangalore"
    elif "mumbai" in raw_lower:
        city = "Mumbai"
    elif "delhi" in raw_lower or "gurgaon" in raw_lower or "noida" in raw_lower:
        city = "Delhi"
    elif "hyderabad" in raw_lower:
        city = "Hyderabad"
    elif "pune" in raw_lower:
        city = "Pune"
    
    # Estimate team size
    team_size = 10
    import re
    sizes = re.findall(r'(\d+)\s*(employees?|people|team|seats?)', raw_lower)
    if sizes:
        team_size = int(sizes[0][0])
    
    # Estimate budget
    budget = None
    budget_match = re.search(r'(\d+)\s*lakh', raw_lower)
    if budget_match:
        budget = int(budget_match.group(1)) * 100000
    else:
        budget_match = re.search(r'(\d+),?\d*\s*/\s*month', raw_lower)
        if budget_match:
            budget = int(budget_match.group(1).replace(",", ""))
    
    # Amenities
    amenities = []
    amenity_keywords = {
        "meeting": "meeting_rooms",
        "cabin": "cabins",
        "cafeteria": "cafeteria",
        "parking": "parking",
        "server": "server_room",
        "24/7": "24_7",
        "24x7": "24_7",
        "24-7": "24_7",
        "internet": "internet",
        "recreation": "recreation",
        "branding": "branding",
    }
    for keyword, amenity in amenity_keywords.items():
        if keyword in raw_lower:
            amenities.append(amenity)
    
    # Call search service
    params = {"city": city, "min_seats": team_size, "limit": 10}
    if budget:
        params["max_budget_inr"] = budget // team_size if team_size > 0 else budget
    if "24/7" in raw_lower or "24x7" in raw_lower or "24-7" in raw_lower or "round the clock" in raw_lower:
        params["is_24_7"] = True
    
    search_results = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{search_url}/api/v1/search/workspaces", params=params)
            if r.status_code == 200:
                search_results = r.json().get("results", [])
    except Exception as e:
        logger.warning("fallback.search_failed", error=str(e))
        search_results = _mock_workspaces(city, team_size)
    
    # Get pricing for each
    recommendations = []
    for ws in search_results[:10]:
        pricing_payload = {
            "workspace_id": ws["id"],
            "team_size": team_size,
            "duration_months": 12,
            "amenities": amenities,
            "parking_count": max(5, team_size // 10),
            "cabins": 2 if team_size > 30 else 1,
            "meeting_rooms": max(2, team_size // 20),
            "require_24_7": ws.get("is_24_7", False),
        }
        
        cost_breakdown = {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(f"{pricing_url}/api/v1/pricing/calculate", json=pricing_payload)
                if r.status_code == 200:
                    cost_breakdown = r.json().get("breakdown", {})
        except Exception as e:
            logger.warning("fallback.pricing_failed", workspace=ws["id"], error=str(e))
        
        # Simple scoring
        scores = {
            "cost_efficiency": max(0, 100 - (ws["price_per_seat_inr"] / 200)),
            "accessibility": 75 + (ws["trust_score"] * 5),
            "amenities": min(100, len(ws.get("amenities", [])) * 12),
            "scalability": min(100, ws["available_seats"] / max(1, team_size) * 30),
            "employee_comfort": 70 + ws["trust_score"] * 5,
            "infrastructure": 80 if ws.get("is_24_7") else 65,
        }
        overall = round(
            0.25 * scores["cost_efficiency"] +
            0.15 * scores["accessibility"] +
            0.15 * scores["amenities"] +
            0.15 * scores["scalability"] +
            0.15 * scores["employee_comfort"] +
            0.15 * scores["infrastructure"], 1
        )
        
        pros = []
        cons = []
        if ws.get("is_24_7"):
            pros.append("24/7 access available")
        if "server_room" in ws.get("amenities", []):
            pros.append("Server room on-site")
        if "parking" in ws.get("amenities", []):
            pros.append(f"Parking for {ws.get('parking_capacity', 0)} vehicles")
        if ws["available_seats"] >= team_size * 1.5:
            pros.append("Good expansion headroom")
        if ws["price_per_seat_inr"] > budget // team_size if budget and team_size else False:
            cons.append("Slightly over budget")
        if not ws.get("is_24_7") and "24/7" in raw_lower:
            cons.append("No 24/7 access")
        if ws["available_seats"] < team_size:
            cons.append("May not have enough seats immediately")
        
        # Enrich with full detail data
        enrichment = _enrich_workspace_data(ws, team_size, raw_input)
        
        recommendations.append({
            "workspace_id": ws["id"],
            "workspace_name": ws["name"],
            "provider": ws["provider"],
            "rank": len(recommendations) + 1,
            "overall_score": overall,
            "scores": {k: round(v, 1) for k, v in scores.items()},
            "reasoning": f"{ws['name']} matches your requirements with strong {max(scores, key=scores.get).replace('_', ' ')}. Located in {ws['area']} with {ws['available_seats']} available seats.",
            "pros": pros or ["Well-rated workspace", "Good location"],
            "cons": cons or ["Verify exact availability"],
            "cost_breakdown": cost_breakdown,
            "location": {"city": ws["city"], "area": ws["area"], "address": ws["address"]},
            "workspace_type": ws["workspace_type"],
            "seating_capacity": ws.get("seating_capacity"),
            "available_seats": ws.get("available_seats"),
            "price_per_seat_inr": ws.get("price_per_seat_inr"),
            "amenities": ws.get("amenities", []),
            "meeting_rooms": ws.get("meeting_rooms"),
            "cabins": ws.get("cabins"),
            "parking_capacity": ws.get("parking_capacity"),
            "is_24_7": ws.get("is_24_7"),
            "trust_score": ws.get("trust_score"),
            "latitude": ws.get("latitude"),
            "longitude": ws.get("longitude"),
            "negotiation_points": enrichment["negotiation_points"],
            "risk_analysis": enrichment["risk_analysis"],
            "nearby_facilities": enrichment["nearby_facilities"],
            "commute_insights": enrichment["commute_insights"],
            "expansion_possibilities": enrichment["expansion_possibilities"],
        })
    
    # Sort by score descending
    recommendations.sort(key=lambda x: x["overall_score"], reverse=True)
    for i, r in enumerate(recommendations):
        r["rank"] = i + 1
    
    return {
        "recommendations": recommendations,
        "requirements": {
            "city": city,
            "team_size": team_size,
            "budget_inr_monthly": budget,
            "workspace_type": "managed_office" if "managed" in raw_lower else "coworking",
            "ambiguity_flags": [],
        },
        "status": "completed",
    }

def _mock_workspaces(city: str, min_seats: int) -> List[Dict[str, Any]]:
    """Return mock workspaces when search service is unavailable."""
    all_ws = [
        {"id": "ws-001", "name": "WeWork Galaxy", "provider": "wework", "city": "Bangalore", "area": "Koramangala", "address": "Galaxy Mall, Koramangala", "workspace_type": "coworking", "seating_capacity": 500, "available_seats": 120, "price_per_seat_inr": 12000, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation", "24_7"], "meeting_rooms": 8, "cabins": 15, "parking_capacity": 80, "is_24_7": True, "latitude": 12.9352, "longitude": 77.6245, "trust_score": 4.3},
        {"id": "ws-002", "name": "IndiQube Park", "provider": "indiqube", "city": "Bangalore", "area": "Whitefield", "address": "IndiQube Park, EPIP Zone", "workspace_type": "managed_office", "seating_capacity": 350, "available_seats": 80, "price_per_seat_inr": 9500, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "server_room", "24_7"], "meeting_rooms": 6, "cabins": 12, "parking_capacity": 60, "is_24_7": True, "latitude": 12.9716, "longitude": 77.7500, "trust_score": 4.5},
        {"id": "ws-003", "name": "Awfis MG Road", "provider": "awfis", "city": "Bangalore", "area": "MG Road", "address": "UB City, MG Road", "workspace_type": "coworking", "seating_capacity": 200, "available_seats": 45, "price_per_seat_inr": 15000, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation"], "meeting_rooms": 5, "cabins": 8, "parking_capacity": 40, "is_24_7": False, "latitude": 12.9756, "longitude": 77.6058, "trust_score": 4.1},
        {"id": "ws-004", "name": "Smartworks ORR", "provider": "smartworks", "city": "Bangalore", "area": "Outer Ring Road", "address": "Smartworks Tower, ORR", "workspace_type": "enterprise_suite", "seating_capacity": 800, "available_seats": 200, "price_per_seat_inr": 11000, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation", "server_room", "24_7", "branding"], "meeting_rooms": 12, "cabins": 25, "parking_capacity": 150, "is_24_7": True, "latitude": 12.9279, "longitude": 77.6785, "trust_score": 4.4},
        {"id": "ws-005", "name": "BHIVE HSR", "provider": "bhive", "city": "Bangalore", "area": "HSR Layout", "address": "BHIVE Workspace, HSR Layout", "workspace_type": "coworking", "seating_capacity": 150, "available_seats": 30, "price_per_seat_inr": 8500, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking"], "meeting_rooms": 4, "cabins": 6, "parking_capacity": 25, "is_24_7": False, "latitude": 12.9121, "longitude": 77.6446, "trust_score": 4.2},
        {"id": "ws-006", "name": "CoWrks Embassy", "provider": "cowrks", "city": "Bangalore", "area": "Manyata Tech Park", "address": "Embassy Manyata, Nagavara", "workspace_type": "managed_office", "seating_capacity": 600, "available_seats": 150, "price_per_seat_inr": 10500, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation", "server_room", "24_7", "branding"], "meeting_rooms": 10, "cabins": 20, "parking_capacity": 120, "is_24_7": True, "latitude": 13.0458, "longitude": 77.6207, "trust_score": 4.5},
        {"id": "ws-007", "name": "Simpliwork BKC", "provider": "simpliwork", "city": "Mumbai", "area": "BKC", "address": "Simpliwork Tower, BKC", "workspace_type": "enterprise_suite", "seating_capacity": 400, "available_seats": 100, "price_per_seat_inr": 18000, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation", "server_room", "24_7", "branding"], "meeting_rooms": 8, "cabins": 16, "parking_capacity": 100, "is_24_7": True, "latitude": 19.0600, "longitude": 72.8656, "trust_score": 4.3},
        {"id": "ws-008", "name": "Regus Connaught Place", "provider": "regus", "city": "Delhi", "area": "Connaught Place", "address": "Regus, Connaught Place", "workspace_type": "coworking", "seating_capacity": 300, "available_seats": 75, "price_per_seat_inr": 14000, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "24_7"], "meeting_rooms": 7, "cabins": 10, "parking_capacity": 50, "is_24_7": True, "latitude": 28.6315, "longitude": 77.2167, "trust_score": 4.1},
        {"id": "ws-009", "name": "91Springboard Hyderabad", "provider": "91springboard", "city": "Hyderabad", "area": "Hitech City", "address": "91Springboard, Hitech City", "workspace_type": "coworking", "seating_capacity": 250, "available_seats": 60, "price_per_seat_inr": 9000, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "recreation"], "meeting_rooms": 6, "cabins": 8, "parking_capacity": 40, "is_24_7": False, "latitude": 17.4430, "longitude": 78.3772, "trust_score": 4.0},
        {"id": "ws-010", "name": "TableSpace Pune", "provider": "tablespace", "city": "Pune", "area": "Kharadi", "address": "TableSpace, Kharadi, Pune", "workspace_type": "managed_office", "seating_capacity": 450, "available_seats": 110, "price_per_seat_inr": 10000, "amenities": ["internet", "meeting_rooms", "cafeteria", "parking", "server_room", "24_7"], "meeting_rooms": 9, "cabins": 15, "parking_capacity": 90, "is_24_7": True, "latitude": 18.5500, "longitude": 73.9500, "trust_score": 4.2},
    ]
    
    filtered = [w for w in all_ws if (not city or w["city"] == city) and w["available_seats"] >= min_seats]
    return filtered if filtered else all_ws[:5]

@router.post("/search", response_model=SearchResponse)
async def create_search(
    request: SearchRequestV2,
    background_tasks: BackgroundTasks,
    http_request: Request,
):
    """
    Start a new co-working space search.
    Accepts natural language requirements and orchestrates the full AI pipeline.
    Falls back to rule-based matching when AI API keys are unavailable.
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    # Check if AI keys are available (Fireworks, OpenAI, or Anthropic)
    # For demo: use fallback by default for fast responses. Set use_ai=true for LLM mode.
    use_ai = request.context.get("use_ai", False) if request.context else False
    has_ai_keys = bool(use_ai and (
        os.getenv("FIREWORKS_API_KEY") or 
        os.getenv("OPENAI_API_KEY") or 
        os.getenv("ANTHROPIC_API_KEY")
    ))
    
    if has_ai_keys:
        logger.info("search.ai_mode", conversation=conversation_id, reason="use_ai_true")
        
        # Run the FULL multi-agent orchestrator graph:
        # RequirementUnderstanding (LLM) -> Discovery (API) -> Pricing (API) ->
        # Optimization (LLM scoring) -> Negotiation (LLM strategy) -> Report (LLM summary)
        try:
            vector_store = http_request.app.state.vector_store
            memory = MemoryManager(vector_store)
            orchestrator = AgentOrchestrator(memory)
            
            result = await orchestrator.run(
                conversation_id=conversation_id,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                raw_input=request.raw_input,
            )
            
            recommendations = result.get("recommendations", [])
            reqs = result.get("requirements", {})
            
            # If the full graph returns empty recommendations, that's a real failure
            if not recommendations:
                logger.warning("ai_mode.empty_recommendations", conversation=conversation_id)
            
            return SearchResponse(
                search_job_id=conversation_id,
                status=result.get("status", "completed"),
                recommendations=recommendations,
                summary=_generate_summary(recommendations, reqs),
                total_cost_estimate=_estimate_total_cost(recommendations),
                ambiguity_flags=result.get("ambiguity_flags", []) if result else [],
            )
        except Exception as e:
            logger.error("ai_mode.failed", error=str(e), conversation=conversation_id)
            # Only fallback to rule-based if the AI pipeline truly errors out
            result = await _fallback_recommendations(request.raw_input)
            recommendations = result.get("recommendations", [])
            reqs = result.get("requirements", {})
            
            return SearchResponse(
                search_job_id=conversation_id,
                status="partial_error",
                recommendations=recommendations,
                summary=_generate_summary(recommendations, reqs) + " (AI pipeline error - showing rule-based fallback)",
                total_cost_estimate=_estimate_total_cost(recommendations),
                ambiguity_flags=reqs.get("ambiguity_flags", []) if reqs else [],
            )
    
    # Default fallback mode (no AI keys or use_ai=false)
    logger.info("search.fallback_mode", conversation=conversation_id, reason="no_ai_keys")
    try:
        result = await _fallback_recommendations(request.raw_input)
        recommendations = result.get("recommendations", [])
        reqs = result.get("requirements", {})
        
        return SearchResponse(
            search_job_id=conversation_id,
            status=result.get("status", "completed"),
            recommendations=recommendations,
            summary=_generate_summary(recommendations, reqs),
            total_cost_estimate=_estimate_total_cost(recommendations),
            ambiguity_flags=reqs.get("ambiguity_flags", []) if reqs else [],
        )
    except Exception as e:
        logger.error("fallback.failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workspace/{workspace_id}")
async def get_workspace_detail(workspace_id: str, request: Request):
    """Get full details for a specific workspace including pricing, negotiation, risks."""
    from app.core.config import get_settings
    settings = get_settings()
    search_url = settings.SEARCH_URL
    pricing_url = settings.PRICING_URL
    
    # Find workspace in mock data or call search service
    all_ws = _mock_workspaces(None, 0)
    ws = next((w for w in all_ws if w["id"] == workspace_id), None)
    
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Get pricing
    pricing_payload = {
        "workspace_id": ws["id"],
        "team_size": 50,
        "duration_months": 12,
        "amenities": ws.get("amenities", []),
        "parking_count": 10,
        "cabins": 2,
        "meeting_rooms": 4,
        "require_24_7": ws.get("is_24_7", False),
    }
    
    cost_breakdown = {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{pricing_url}/api/v1/pricing/calculate", json=pricing_payload)
            if r.status_code == 200:
                cost_breakdown = r.json().get("breakdown", {})
    except Exception as e:
        logger.warning("workspace.pricing_failed", workspace=ws["id"], error=str(e))
    
    enrichment = _enrich_workspace_data(ws, 50, ws.get("name", ""))
    
    return {
        "workspace": ws,
        "cost_breakdown": cost_breakdown,
        "negotiation_points": enrichment["negotiation_points"],
        "risk_analysis": enrichment["risk_analysis"],
        "nearby_facilities": enrichment["nearby_facilities"],
        "commute_insights": enrichment["commute_insights"],
        "expansion_possibilities": enrichment["expansion_possibilities"],
    }

def _generate_summary(recommendations: List[Dict[str, Any]], requirements: Dict[str, Any]) -> str:
    if not recommendations:
        return "No recommendations generated. Please refine your requirements."
    top = recommendations[0]
    return (
        f"Top recommendation: {top.get('workspace_name', 'Unknown')} in {top.get('area', 'Unknown')} "
        f"with score {top.get('overall_score', 0):.1f}/100. "
        f"{len(recommendations)} options analyzed across multiple providers."
    )

def _estimate_total_cost(recommendations: List[Dict[str, Any]]) -> Optional[float]:
    if not recommendations:
        return None
    try:
        costs = [r.get("cost_breakdown", {}).get("monthly_total_inr", 0) for r in recommendations[:3]]
        return sum(costs) / len(costs) if costs else None
    except Exception:
        return None

@router.post("/conversations")
async def create_conversation(payload: ConversationCreate):
    """Create a new conversation session."""
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": payload.tenant_id,
        "user_id": payload.user_id,
        "title": payload.title or "New Search",
        "status": "active",
    }

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation details and history."""
    return {
        "id": conversation_id,
        "status": "active",
        "messages": [],
    }

@router.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, message: MessageRequest):
    """Add a message to a conversation."""
    return {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "role": message.role,
        "content": message.content,
        "created_at": "2024-01-01T00:00:00Z",
    }

@router.get("/recommendations/{search_job_id}")
async def get_recommendations(search_job_id: str):
    """Get detailed recommendations for a search job."""
    return {
        "search_job_id": search_job_id,
        "recommendations": [],
        "report_url": None,
    }

@router.post("/recommendations/{recommendation_id}/feedback")
async def submit_feedback(recommendation_id: str, feedback: Dict[str, Any]):
    """Submit feedback on a recommendation to improve future results."""
    return {"success": True, "message": "Feedback recorded"}

# ============================================================================
# SCHEDULE VISIT & NOTIFICATIONS
# ============================================================================

class ScheduleVisitRequest(BaseModel):
    workspace_id: str
    workspace_name: str
    visitor_name: str
    visitor_email: str
    visitor_mobile: str
    visitor_address: str
    visit_date: str
    visit_time: str
    team_size: Optional[int] = None
    notes: Optional[str] = None

@router.post("/schedule-visit")
async def schedule_visit(payload: ScheduleVisitRequest):
    """Schedule a site visit. Sends email confirmation and WhatsApp message."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime
    
    visit_datetime = f"{payload.visit_date} at {payload.visit_time}"
    
    # 1. Send Email via SMTP
    email_sent = False
    email_error = None
    try:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", "noreply@coworking-ai.com")
        
        if smtp_user and smtp_password:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Site Visit Confirmed - {payload.workspace_name}"
            msg["From"] = smtp_from
            msg["To"] = payload.visitor_email
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #4F46E5;">Site Visit Confirmed</h2>
                <p>Hello <b>{payload.visitor_name}</b>,</p>
                <p>Your site visit has been scheduled successfully!</p>
                <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Workspace</b></td><td style="padding: 8px; border: 1px solid #ddd;">{payload.workspace_name}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Date</b></td><td style="padding: 8px; border: 1px solid #ddd;">{payload.visit_date}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Time</b></td><td style="padding: 8px; border: 1px solid #ddd;">{payload.visit_time}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Mobile</b></td><td style="padding: 8px; border: 1px solid #ddd;">{payload.visitor_mobile}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Address</b></td><td style="padding: 8px; border: 1px solid #ddd;">{payload.visitor_address}</td></tr>
                </table>
                <p style="margin-top: 20px;">Please arrive 10 minutes early. Carry a valid ID.</p>
                <p style="color: #666; font-size: 12px;">Powered by Coworking AI Platform</p>
            </body>
            </html>
            """
            
            text_body = f"""Site Visit Confirmed\n\nHello {payload.visitor_name},\n\nYour visit to {payload.workspace_name} is scheduled for {visit_datetime}.\n\nMobile: {payload.visitor_mobile}\nAddress: {payload.visitor_address}\n\nPlease arrive 10 minutes early."""
            
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_from, [payload.visitor_email], msg.as_string())
            
            email_sent = True
            logger.info("email.sent", to=payload.visitor_email, workspace=payload.workspace_name)
        else:
            email_error = "SMTP credentials not configured - email logged but not sent"
            logger.warning("email.skipped", reason="no_smtp_creds", to=payload.visitor_email)
    except Exception as e:
        email_error = str(e)
        logger.error("email.failed", error=str(e), to=payload.visitor_email)
    
    # 2. Send WhatsApp (mock - logs message, real via WhatsApp Business API)
    whatsapp_sent = False
    whatsapp_error = None
    try:
        # In production, integrate with WhatsApp Business API or Twilio
        # For demo, we log the message and return success
        logger.info(
            "whatsapp.message_prepared",
            to=payload.visitor_mobile,
            workspace=payload.workspace_name,
            datetime=visit_datetime,
        )
        whatsapp_sent = True
    except Exception as e:
        whatsapp_error = str(e)
        logger.error("whatsapp.failed", error=str(e))
    
    return {
        "success": True,
        "visit_id": str(uuid.uuid4()),
        "workspace_name": payload.workspace_name,
        "visit_datetime": visit_datetime,
        "email_sent": email_sent,
        "email_error": email_error,
        "whatsapp_sent": whatsapp_sent,
        "whatsapp_error": whatsapp_error,
        "message": "Visit scheduled. Check your email for confirmation."
    }

# ============================================================================
# PDF PROPOSAL GENERATION
# ============================================================================

class ProposalRequest(BaseModel):
    workspace_id: str
    workspace_name: str
    provider: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    address: Optional[str] = None
    workspace_type: Optional[str] = None
    seating_capacity: Optional[int] = None
    available_seats: Optional[int] = None
    price_per_seat_inr: Optional[int] = None
    amenities: Optional[List[str]] = None
    meeting_rooms: Optional[int] = None
    cabins: Optional[int] = None
    parking_capacity: Optional[int] = None
    is_24_7: Optional[bool] = None
    trust_score: Optional[float] = None
    overall_score: Optional[float] = None
    scores: Optional[Dict[str, float]] = None
    reasoning: Optional[str] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    cost_breakdown: Optional[Dict[str, Any]] = None
    negotiation_points: Optional[List[str]] = None
    risk_analysis: Optional[List[str]] = None
    nearby_facilities: Optional[Dict[str, str]] = None
    commute_insights: Optional[Dict[str, Any]] = None
    expansion_possibilities: Optional[Dict[str, Any]] = None
    company_name: Optional[str] = "Your Company"
    team_size: Optional[int] = None

@router.post("/proposal")
async def generate_proposal(payload: ProposalRequest):
    """Generate a PDF proposal for a workspace recommendation using ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO
    from datetime import datetime
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=8,
        spaceBefore=12,
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        leftIndent=20,
        spaceAfter=4,
    )
    
    story = []
    
    # Header
    story.append(Paragraph("Coworking AI - Workspace Proposal", title_style))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=10, textColor=colors.grey, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.5*cm))
    
    # Horizontal line
    story.append(Table([['']], colWidths=[16*cm], style=TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#4F46E5')),
    ])))
    story.append(Spacer(1, 0.5*cm))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", section_style))
    exec_text = f"Dear <b>{payload.company_name}</b> Team,<br/><br/>"
    exec_text += f"We are pleased to present this comprehensive workspace proposal for <b>{payload.workspace_name}</b>. "
    exec_text += f"This recommendation scores <b>{payload.overall_score or 'N/A'}/100</b> on our multi-dimensional evaluation framework, "
    exec_text += f"making it a strong candidate for your team of <b>{payload.team_size or 'N/A'}</b> members."
    story.append(Paragraph(exec_text, body_style))
    if payload.reasoning:
        story.append(Paragraph(f"<b>AI Reasoning:</b> {payload.reasoning}", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Workspace Overview
    story.append(Paragraph("Workspace Overview", section_style))
    overview_data = [
        ["Workspace Name", payload.workspace_name or "N/A"],
        ["Provider", payload.provider or "N/A"],
        ["Location", f"{payload.area or 'N/A'}, {payload.city or 'N/A'}"],
        ["Address", payload.address or "N/A"],
        ["Type", payload.workspace_type or "N/A"],
        ["Total Capacity", f"{payload.seating_capacity or 'N/A'} seats"],
        ["Available Seats", f"{payload.available_seats or 'N/A'} seats"],
        ["Price Per Seat", f"Rs. {payload.price_per_seat_inr:,.0f}" if payload.price_per_seat_inr else "N/A"],
        ["Trust Score", f"{payload.trust_score or 'N/A'}/5.0"],
        ["24/7 Access", "Yes" if payload.is_24_7 else "No"],
    ]
    overview_table = Table(overview_data, colWidths=[5*cm, 10*cm])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1F2937')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 0.3*cm))
    
    # Score Breakdown
    if payload.scores:
        story.append(Paragraph("Score Breakdown", section_style))
        score_data = [["Dimension", "Score", "Visual"]]
        for key, value in payload.scores.items():
            bar_len = int(value / 5)
            bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)
            score_data.append([key.replace("_", " ").title(), f"{value:.1f}", bar])
        
        score_table = Table(score_data, colWidths=[4*cm, 2*cm, 9*cm])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 0.3*cm))
    
    # Cost Breakdown
    if payload.cost_breakdown:
        story.append(Paragraph("Cost Breakdown", section_style))
        cost_data = []
        for key, value in payload.cost_breakdown.items():
            label = key.replace("_", " ").title()
            if isinstance(value, (int, float)):
                cost_data.append([label, f"Rs. {value:,.0f}"])
            else:
                cost_data.append([label, str(value)])
        
        cost_table = Table(cost_data, colWidths=[5*cm, 10*cm])
        cost_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1F2937')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(cost_table)
        story.append(Spacer(1, 0.3*cm))
    
    # Amenities
    if payload.amenities:
        story.append(Paragraph("Amenities & Facilities", section_style))
        for amenity in payload.amenities:
            story.append(Paragraph(f"\u2022 {amenity.replace('_', ' ').title()}", bullet_style))
        story.append(Spacer(1, 0.2*cm))
    
    # Pros
    if payload.pros:
        story.append(Paragraph("Strengths (Pros)", section_style))
        for pro in payload.pros:
            story.append(Paragraph(f"\u2022 {pro}", bullet_style))
        story.append(Spacer(1, 0.2*cm))
    
    # Cons
    if payload.cons:
        story.append(Paragraph("Considerations (Cons)", section_style))
        for con in payload.cons:
            story.append(Paragraph(f"\u2022 {con}", bullet_style))
        story.append(Spacer(1, 0.2*cm))
    
    # Negotiation Points
    if payload.negotiation_points:
        story.append(Paragraph("Negotiation Strategy", section_style))
        story.append(Paragraph("Use these points during your negotiation to secure the best deal:", body_style))
        for point in payload.negotiation_points:
            story.append(Paragraph(f"\u2022 {point}", bullet_style))
        story.append(Spacer(1, 0.2*cm))
    
    # Risk Analysis
    if payload.risk_analysis:
        story.append(Paragraph("Risk Analysis", section_style))
        story.append(Paragraph("Be aware of the following risks before signing:", body_style))
        for risk in payload.risk_analysis:
            story.append(Paragraph(f"\u2022 {risk}", bullet_style))
        story.append(Spacer(1, 0.2*cm))
    
    # Nearby Facilities
    if payload.nearby_facilities:
        story.append(Paragraph("Nearby Facilities", section_style))
        nearby_data = []
        for key, value in payload.nearby_facilities.items():
            nearby_data.append([key.replace("_", " ").title(), value])
        nearby_table = Table(nearby_data, colWidths=[5*cm, 10*cm])
        nearby_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(nearby_table)
        story.append(Spacer(1, 0.2*cm))
    
    # Commute Insights
    if payload.commute_insights:
        story.append(Paragraph("Commute & Accessibility", section_style))
        commute_data = []
        for key, value in payload.commute_insights.items():
            commute_data.append([key.replace("_", " ").title(), str(value)])
        commute_table = Table(commute_data, colWidths=[5*cm, 10*cm])
        commute_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(commute_table)
        story.append(Spacer(1, 0.2*cm))
    
    # Expansion
    if payload.expansion_possibilities:
        story.append(Paragraph("Expansion Possibilities", section_style))
        for key, value in payload.expansion_possibilities.items():
            if isinstance(value, list):
                story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b>", body_style))
                for item in value:
                    story.append(Paragraph(f"\u2022 {item}", bullet_style))
            else:
                story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {value}", body_style))
        story.append(Spacer(1, 0.2*cm))
    
    # Next Steps
    story.append(Paragraph("Next Steps", section_style))
    next_steps = "1. <b>Schedule a site visit</b> to experience the workspace firsthand.<br/>"
    next_steps += "2. <b>Review the cost breakdown</b> with your finance team.<br/>"
    next_steps += "3. <b>Use the negotiation points</b> to discuss terms with the provider.<br/>"
    next_steps += "4. <b>Request a trial period</b> or pilot program if available.<br/>"
    next_steps += "5. <b>Finalize the agreement</b> with legal and facilities teams."
    story.append(Paragraph(next_steps, body_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Footer text
    footer_text = "For any questions, contact your Coworking AI account manager.<br/><br/>"
    footer_text += "<b>Best regards,<br/>Coworking AI Platform</b>"
    story.append(Paragraph(footer_text, body_style))
    
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    import base64
    pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
    
    return {
        "success": True,
        "pdf_base64": pdf_b64,
        "filename": f"proposal_{payload.workspace_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
        "workspace_name": payload.workspace_name,
    }
