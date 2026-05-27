from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import uuid

class RequirementSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    team_size: Optional[int] = None
    budget_per_month_inr: Optional[float] = None
    duration_months: Optional[int] = None
    city: Optional[str] = None
    area_preferences: List[str] = Field(default_factory=list)
    workspace_type: Optional[Literal["coworking","managed_office","hot_desk","enterprise_suite"]] = None
    seating_capacity: Optional[int] = None
    cabins_required: Optional[int] = None
    meeting_rooms_required: Optional[int] = None
    conference_rooms_required: Optional[int] = None
    parking_needed: Optional[bool] = None
    parking_capacity: Optional[int] = None
    cafeteria_needed: Optional[bool] = None
    recreation_needed: Optional[bool] = None
    server_room_needed: Optional[bool] = None
    internet_redundancy_needed: Optional[bool] = None
    is_24_7_needed: Optional[bool] = None
    is_furnished: Optional[bool] = True
    branding_needed: Optional[bool] = None
    accessibility_needed: Optional[bool] = None
    sustainability_needed: Optional[bool] = None
    compliance_requirements: List[str] = Field(default_factory=list)
    nearby_metro: Optional[str] = None
    nearby_residential: Optional[bool] = None
    client_facing: Optional[bool] = None
    preferred_providers: List[str] = Field(default_factory=list)
    floor_preference: Optional[str] = None
    move_in_date: Optional[str] = None
    expansion_plan: Optional[str] = None
    hybrid_ratio: Optional[str] = None
    raw_nlp_input: Optional[str] = None

class AmbiguityFlag(BaseModel):
    field: str
    question: str
    severity: Literal["low","medium","high"]

class RequirementExtractionResult(BaseModel):
    requirements: RequirementSchema
    ambiguity_flags: List[AmbiguityFlag] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    confidence: float = Field(ge=0, le=1)
    reasoning: Optional[str] = None

class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None
    latency_ms: int = 0

class AgentState(BaseModel):
    conversation_id: str
    current_agent: Optional[str] = None
    requirements: Optional[RequirementSchema] = None
    extracted_requirements: Optional[RequirementExtractionResult] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    report: Optional[Dict[str, Any]] = None
    iteration: int = 0
    status: Literal["idle","requirements","discovery","pricing","optimization","reporting","done","error"] = "idle"
    memory_context: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class ConversationCreate(BaseModel):
    tenant_id: str
    user_id: str
    title: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

class MessageRequest(BaseModel):
    role: Literal["user","assistant","system","tool"]
    content: str
    agent_name: Optional[str] = None
    tool_calls: Optional[List[Dict[str,Any]]] = None
    tool_results: Optional[List[Dict[str,Any]]] = None

class RecommendationResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    workspace_id: str
    workspace_name: Optional[str] = None
    provider: Optional[str] = None
    rank: int
    overall_score: float
    scores: Dict[str, float]
    reasoning: str
    pros: List[str]
    cons: List[str]
    cost_breakdown: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    commute_analysis: Optional[Dict[str, Any]] = None
    risk_analysis: Optional[List[str]] = None
    negotiation_points: Optional[List[str]] = None
    nearby_facilities: Optional[Dict[str, str]] = None
    commute_insights: Optional[Dict[str, Any]] = None
    expansion_possibilities: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    conversation_id: str
    raw_input: str
    tenant_id: str
    user_id: str

class SearchResponse(BaseModel):
    search_job_id: str
    status: str
    recommendations: List[RecommendationResult]
    summary: str
    total_cost_estimate: Optional[float] = None
    ambiguity_flags: List[AmbiguityFlag] = Field(default_factory=list)
