"""Specialized agent implementations for the coworking AI platform.

Discovery and Pricing agents call real microservice APIs.
Optimization, Negotiation, and Report agents use LLM for analysis.
"""

import os
import structlog
import httpx
from typing import Dict, Any, List
from app.agents.base import BaseAgent
from app.agents.prompts import (
    REQUIREMENT_AGENT_PROMPT,
    OPTIMIZATION_AGENT_PROMPT,
    NEGOTIATION_AGENT_PROMPT,
    REPORT_AGENT_PROMPT,
    LOCATION_AGENT_PROMPT,
)
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

SEARCH_URL = settings.SEARCH_URL
PRICING_URL = settings.PRICING_URL

class RequirementUnderstandingAgent(BaseAgent):
    def __init__(self):
        super().__init__("requirement_analyst", REQUIREMENT_AGENT_PROMPT)
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raw_input = state.get("raw_input", "")
        result = await self.run({"raw_input": raw_input})
        data = result.data
        
        # Normalize LLM response structure (Fireworks models are inconsistent with keys)
        # Try multiple possible keys in order of preference
        parsed = (
            data.get("explicit_requirements") or
            data.get("parsed_requirements") or
            data.get("extracted_requirements") or
            data.get("requirements") or
            {}
        )
        
        # Build normalized requirements dict
        # Fireworks models return flat keys: city, micromarket, team_size, space_type, etc.
        # But sometimes they nest them under "requirements" or "explicit_requirements".
        # We search recursively for critical fields.
        requirements = {}
        
        def _deep_get(d, *keys, default=None):
            """Recursively search for any of the keys in nested dicts."""
            if not isinstance(d, dict):
                return default
            for k in keys:
                if k in d:
                    return d[k]
            # Search one level deeper in all child dicts
            for v in d.values():
                if isinstance(v, dict):
                    found = _deep_get(v, *keys, default=default)
                    if found is not None:
                        return found
            return default
        
        if isinstance(parsed, dict):
            # Location (flat or nested)
            city = parsed.get("city") or _deep_get(parsed, "city")
            if city:
                requirements["city"] = city
            
            area = parsed.get("micromarket") or parsed.get("area") or _deep_get(parsed, "micromarket", "area", "micro_market")
            if area:
                requirements["area_preferences"] = [area]
            
            # Team size — THE CRITICAL FIX
            team_size = parsed.get("team_size") or _deep_get(parsed, "team_size", "current_employees", "required_seats", "employees")
            if isinstance(team_size, int):
                requirements["team_size"] = team_size
            elif isinstance(team_size, str) and team_size.isdigit():
                requirements["team_size"] = int(team_size)
            elif isinstance(team_size, dict):
                requirements["team_size"] = team_size.get("current_employees") or team_size.get("required_seats") or team_size.get("employees")
            
            # Fallback: regex extract team_size from raw_input if LLM missed it
            if not requirements.get("team_size"):
                import re
                match = re.search(r'(\d+)\s*(?:employees?|people|seats?|team)', raw_input.lower())
                if match:
                    requirements["team_size"] = int(match.group(1))
            
            # Property type
            space_type = parsed.get("space_type") or parsed.get("workspace_type") or _deep_get(parsed, "space_type", "workspace_type")
            if space_type and isinstance(space_type, str):
                requirements["workspace_type"] = space_type.lower().replace(" ", "_")
            
            # Industry
            industry = parsed.get("industry_vertical") or parsed.get("industry_sector") or parsed.get("industry") or _deep_get(parsed, "industry_vertical", "industry_sector", "industry")
            if industry and isinstance(industry, str):
                requirements["industry_sector"] = industry
            
            # Amenities
            amenities = parsed.get("explicit_amenities") or parsed.get("amenities") or _deep_get(parsed, "explicit_amenities", "amenities")
            if isinstance(amenities, list):
                requirements["amenities"] = amenities
            
            # Budget
            budget = parsed.get("budget_inr_monthly") or parsed.get("budget") or _deep_get(parsed, "budget_inr_monthly", "budget")
            if budget and not isinstance(budget, dict):
                requirements["budget_per_month_inr"] = budget
            elif isinstance(budget, dict) and budget.get("value"):
                requirements["budget_per_month_inr"] = budget["value"]
            
            # Timeline
            move_in = parsed.get("move_in_date") or _deep_get(parsed, "move_in_date")
            if move_in:
                requirements["move_in_date"] = move_in
            
            # Preferred providers
            providers = parsed.get("likely_providers") or parsed.get("preferred_providers") or _deep_get(parsed, "likely_providers", "preferred_providers")
            if isinstance(providers, list):
                requirements["preferred_providers"] = providers
        
        # Normalize ambiguity flags
        ambiguities = data.get("ambiguities", data.get("ambiguity_flags", []))
        ambiguity_flags = []
        for a in ambiguities:
            if isinstance(a, dict):
                sev = a.get("severity", "medium")
                if isinstance(sev, str):
                    sev = sev.lower()
                ambiguity_flags.append({
                    "field": a.get("field", ""),
                    "question": a.get("description", a.get("question", "")),
                    "severity": sev if sev in ("low", "medium", "high") else "medium",
                })
        
        # Normalize follow-up questions
        follow_ups = data.get("follow_up_questions", data.get("follow_up_questions", []))
        
        # Confidence
        confidence = data.get("confidence_score", data.get("confidence", 0.5))
        
        return {
            "extracted_requirements": {
                "requirements": requirements,
                "raw_analysis": data,
            },
            "ambiguity_flags": ambiguity_flags,
            "follow_up_questions": follow_ups,
            "confidence": confidence,
        }

class LocationIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__("location_intelligence", LOCATION_AGENT_PROMPT)
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        reqs = state.get("requirements", {})
        city = reqs.get("city")
        areas = reqs.get("area_preferences", [])
        result = await self.run({"city": city, "areas": areas, "requirements": reqs})
        return {"location_analysis": result.data}

class DiscoveryAgent(BaseAgent):
    """Calls the real Search microservice API instead of hallucinating workspaces."""
    
    def __init__(self):
        super().__init__("discovery", "You are a workspace discovery coordinator.")
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        reqs = state.get("requirements", {})
        raw_input = state.get("raw_input", "")
        
        # Fallback city extraction from raw_input if LLM didn't extract it
        city = reqs.get("city")
        if not city:
            raw_lower = raw_input.lower()
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
        
        # Build search params
        params = {"limit": 20}
        if city:
            params["city"] = city
        if reqs.get("area_preferences"):
            params["area"] = reqs["area_preferences"][0]
        if reqs.get("workspace_type"):
            params["workspace_type"] = reqs["workspace_type"]
        
        # Min seats: only pass if reasonable (avoid filtering out everything)
        team_size = reqs.get("team_size")
        if isinstance(team_size, int) and 1 <= team_size <= 500:
            params["min_seats"] = team_size
        
        # Call search service
        discovered = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(f"{SEARCH_URL}/api/v1/search/workspaces", params=params)
                if r.status_code == 200:
                    discovered = r.json().get("results", [])
                    logger.info("discovery.api_success", count=len(discovered), params=params)
        except Exception as e:
            logger.warning("discovery.api_failed", error=str(e), params=params)
        
        # If strict filters return nothing, try relaxed (city only)
        if not discovered and city:
            logger.warning("discovery.empty_with_strict", params=params)
            relaxed = {"limit": 20, "city": city}
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r = await client.get(f"{SEARCH_URL}/api/v1/search/workspaces", params=relaxed)
                    if r.status_code == 200:
                        discovered = r.json().get("results", [])
                        logger.info("discovery.api_success_relaxed", count=len(discovered), params=relaxed)
            except Exception as e:
                logger.warning("discovery.api_failed_relaxed", error=str(e))
        
        # Ultimate fallback to mock data
        if not discovered:
            logger.warning("discovery.using_mock_fallback")
            discovered = _mock_workspaces(city, team_size or 10)
        
        return {"discovered_workspaces": discovered}

class PricingAgent(BaseAgent):
    """Calls the real Pricing microservice API for each workspace."""
    
    def __init__(self):
        super().__init__("pricing_intelligence", "You are a pricing coordinator.")
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        workspaces = state.get("discovered_workspaces", [])
        reqs = state.get("requirements", {})
        team_size = reqs.get("team_size") or 10
        duration = reqs.get("lease_duration_months") or 12
        
        pricing_results = {}
        for ws in workspaces:
            payload = {
                "workspace_id": ws.get("id", "unknown"),
                "provider": ws.get("provider", ""),
                "price_per_seat_inr": ws.get("price_per_seat_inr"),
                "team_size": team_size,
                "duration_months": 12,
                "amenities": ws.get("amenities", []),
                "parking_count": max(5, (team_size or 10) // 10),
                "cabins": max(1, (team_size or 10) // 30),
                "meeting_rooms": max(2, (team_size or 10) // 20),
                "require_24_7": ws.get("is_24_7", False),
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.post(f"{PRICING_URL}/api/v1/pricing/calculate", json=payload)
                    if r.status_code == 200:
                        pricing_results[ws["id"]] = r.json()
            except Exception as e:
                logger.warning("pricing.api_failed", workspace=ws.get("id"), error=str(e))
        
        return {"pricing_analysis": {"per_workspace": pricing_results}}

class OptimizationAgent(BaseAgent):
    """Deterministic scoring on real workspace + pricing data. No LLM hallucination."""
    
    def __init__(self):
        super().__init__("optimization", "You are a workspace optimization coordinator.")
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        workspaces = state.get("discovered_workspaces", [])
        pricing = state.get("pricing_analysis", {})
        reqs = state.get("requirements", {})
        raw_input = state.get("raw_input", "")
        team_size = reqs.get("team_size") or 10
        
        if not workspaces:
            logger.warning("optimization.no_workspaces")
            return {"recommendations": [], "scoring_weights": {}}
        
        # Enrich workspaces with pricing data
        enriched = []
        for ws in workspaces:
            ws_id = ws.get("id", "unknown")
            ws_copy = dict(ws)
            ws_copy["pricing"] = pricing.get("per_workspace", {}).get(ws_id, {})
            enriched.append(ws_copy)
        
        # Deterministic multi-dimensional scoring
        recommendations = []
        for ws in enriched[:10]:
            seat_price = ws.get("price_per_seat_inr", 10000)
            available = ws.get("available_seats", 0)
            trust = ws.get("trust_score", 4.0)
            amenities = ws.get("amenities", [])
            
            scores = {
                "cost_efficiency": max(0, 100 - (seat_price / 200)),
                "accessibility": min(100, 75 + trust * 5),
                "amenities": min(100, len(amenities) * 12),
                "scalability": min(100, available / max(1, team_size) * 30),
                "employee_comfort": min(100, 70 + trust * 5),
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
            
            # Use the enrichment helper from orchestrator.py
            from app.api.orchestrator import _enrich_workspace_data
            enrichment = _enrich_workspace_data(ws, team_size, raw_input)
            
            pricing_data = ws.get("pricing", {})
            cost_breakdown = pricing_data.get("breakdown", {}) if pricing_data else {}
            
            recommendations.append({
                "workspace_id": ws.get("id", "unknown"),
                "workspace_name": ws.get("name", "Unknown"),
                "provider": ws.get("provider", ""),
                "city": ws.get("city", ""),
                "area": ws.get("area", ""),
                "address": ws.get("address", ""),
                "workspace_type": ws.get("workspace_type", ""),
                "seating_capacity": ws.get("seating_capacity"),
                "available_seats": ws.get("available_seats"),
                "price_per_seat_inr": seat_price,
                "amenities": amenities,
                "meeting_rooms": ws.get("meeting_rooms"),
                "cabins": ws.get("cabins"),
                "parking_capacity": ws.get("parking_capacity"),
                "is_24_7": ws.get("is_24_7"),
                "trust_score": trust,
                "overall_score": overall,
                "scores": {k: round(v, 1) for k, v in scores.items()},
                "reasoning": f"{ws.get('name')} scores {overall}/100 with strong {max(scores, key=scores.get).replace('_', ' ')}.",
                "pros": list(set(["Well-rated workspace", "Good location"] + (["24/7 access"] if ws.get("is_24_7") else []))),
                "cons": ["Verify exact availability"],
                "cost_breakdown": cost_breakdown,
                "negotiation_points": enrichment["negotiation_points"],
                "risk_analysis": enrichment["risk_analysis"],
                "nearby_facilities": enrichment["nearby_facilities"],
                "commute_insights": enrichment["commute_insights"],
                "expansion_possibilities": enrichment["expansion_possibilities"],
            })
        
        recommendations.sort(key=lambda x: x["overall_score"], reverse=True)
        for i, r in enumerate(recommendations):
            r["rank"] = i + 1
        
        logger.info("optimization.complete", recommendations=len(recommendations))
        return {
            "recommendations": recommendations,
            "scoring_weights": {
                "cost_efficiency": 0.25,
                "accessibility": 0.15,
                "amenities": 0.15,
                "scalability": 0.15,
                "employee_comfort": 0.15,
                "infrastructure": 0.15,
            },
        }

class NegotiationAgent(BaseAgent):
    def __init__(self):
        super().__init__("negotiation", NEGOTIATION_AGENT_PROMPT)
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        recs = state.get("recommendations", [])
        if not recs:
            logger.warning("negotiation.no_recommendations")
            return {"negotiation_strategy": {"note": "No recommendations available"}}
        top_pick = recs[0]
        result = await self.run({"recommendation": top_pick})
        return {"negotiation_strategy": result.data}

class ReportAgent(BaseAgent):
    def __init__(self):
        super().__init__("report_generation", REPORT_AGENT_PROMPT)
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        recs = state.get("recommendations", [])
        reqs = state.get("requirements", {})
        result = await self.run({"recommendations": recs, "requirements": reqs})
        return {"report": result.data}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_workspaces(city: str, min_seats: int) -> List[Dict[str, Any]]:
    """Ultimate fallback mock data when search service is unreachable."""
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

def _deterministic_recommendations(workspaces, reqs, pricing, raw_input):
    """Build recommendations from real workspace data when LLM fails."""
    from app.api.orchestrator import _enrich_workspace_data
    import re
    
    team_size = (reqs.get("team_size") or 10) if reqs else 10
    raw_lower = raw_input.lower()
    
    recommendations = []
    for ws in workspaces:
        scores = {
            "cost_efficiency": max(0, 100 - (ws.get("price_per_seat_inr", 10000) / 200)),
            "accessibility": 75 + (ws.get("trust_score", 4.0) * 5),
            "amenities": min(100, len(ws.get("amenities", [])) * 12),
            "scalability": min(100, ws.get("available_seats", 0) / max(1, team_size) * 30),
            "employee_comfort": 70 + ws.get("trust_score", 4.0) * 5,
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
        
        enrichment = _enrich_workspace_data(ws, team_size, raw_input)
        rec = {
            "workspace_id": ws.get("id", "unknown"),
            "workspace_name": ws.get("name", "Unknown"),
            "provider": ws.get("provider", ""),
            "city": ws.get("city", ""),
            "area": ws.get("area", ""),
            "address": ws.get("address", ""),
            "workspace_type": ws.get("workspace_type", ""),
            "seating_capacity": ws.get("seating_capacity"),
            "available_seats": ws.get("available_seats"),
            "price_per_seat_inr": ws.get("price_per_seat_inr"),
            "amenities": ws.get("amenities", []),
            "meeting_rooms": ws.get("meeting_rooms"),
            "cabins": ws.get("cabins"),
            "parking_capacity": ws.get("parking_capacity"),
            "is_24_7": ws.get("is_24_7"),
            "trust_score": ws.get("trust_score"),
            "overall_score": overall,
            "scores": {k: round(v, 1) for k, v in scores.items()},
            "reasoning": f"{ws.get('name')} matches requirements with strong {max(scores, key=scores.get).replace('_', ' ')}.",
            "pros": ["Well-rated workspace", "Good location"] + (["24/7 access"] if ws.get("is_24_7") else []),
            "cons": ["Verify exact availability"],
            "cost_breakdown": ws.get("pricing", {}).get("breakdown", {}) if ws.get("pricing") else {},
            "negotiation_points": enrichment["negotiation_points"],
            "risk_analysis": enrichment["risk_analysis"],
            "nearby_facilities": enrichment["nearby_facilities"],
            "commute_insights": enrichment["commute_insights"],
            "expansion_possibilities": enrichment["expansion_possibilities"],
        }
        recommendations.append(rec)
    
    recommendations.sort(key=lambda x: x["overall_score"], reverse=True)
    for i, r in enumerate(recommendations):
        r["rank"] = i + 1
    
    return recommendations
