"""
LangGraph-inspired state machine for multi-agent orchestration.
Implements the Observe -> Plan -> Execute -> Evaluate -> Retry -> Optimize -> Finalize loop.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import structlog
from orch_app.agents.specialized import (
    RequirementUnderstandingAgent,
    LocationIntelligenceAgent,
    DiscoveryAgent,
    PricingAgent,
    OptimizationAgent,
    NegotiationAgent,
    ReportAgent,
)
from orch_app.memory.vector_store import MemoryManager
from orch_app.tools.registry import ToolRegistry, get_registry

logger = structlog.get_logger()

class OrchestratorState(Enum):
    IDLE = "idle"
    REQUIREMENTS = "requirements"
    PLANNING = "planning"
    LOCATION_INTEL = "location_intel"
    DISCOVERY = "discovery"
    PRICING = "pricing"
    OPTIMIZATION = "optimization"
    NEGOTIATION = "negotiation"
    REPORTING = "reporting"
    DONE = "done"
    ERROR = "error"

@dataclass
class ExecutionPlan:
    steps: List[Dict[str, Any]] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    max_iterations: int = 10

@dataclass
class GraphState:
    conversation_id: str
    tenant_id: str
    user_id: str
    raw_input: str = ""
    current_state: OrchestratorState = OrchestratorState.IDLE
    requirements: Optional[Dict[str, Any]] = None
    extracted_requirements: Optional[Dict[str, Any]] = None
    ambiguity_flags: List[Dict[str, Any]] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    location_analysis: Optional[Dict[str, Any]] = None
    discovered_workspaces: List[Dict[str, Any]] = field(default_factory=list)
    pricing_analysis: Optional[Dict[str, Any]] = None
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    negotiation_strategy: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    iteration: int = 0
    errors: List[str] = field(default_factory=list)
    execution_trace: List[Dict[str, Any]] = field(default_factory=list)

class AgentOrchestrator:
    """Orchestrates multiple AI agents in a stateful execution graph."""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.tool_registry = get_registry()
        self.agents = {
            "requirement": RequirementUnderstandingAgent(),
            "location": LocationIntelligenceAgent(),
            "discovery": DiscoveryAgent(),
            "pricing": PricingAgent(),
            "optimization": OptimizationAgent(),
            "negotiation": NegotiationAgent(),
            "report": ReportAgent(),
        }
        self._transitions: Dict[OrchestratorState, Callable[[GraphState], Awaitable[GraphState]]] = {
            OrchestratorState.IDLE: self._handle_idle,
            OrchestratorState.REQUIREMENTS: self._handle_requirements,
            OrchestratorState.PLANNING: self._handle_planning,
            OrchestratorState.LOCATION_INTEL: self._handle_location,
            OrchestratorState.DISCOVERY: self._handle_discovery,
            OrchestratorState.PRICING: self._handle_pricing,
            OrchestratorState.OPTIMIZATION: self._handle_optimization,
            OrchestratorState.NEGOTIATION: self._handle_negotiation,
            OrchestratorState.REPORTING: self._handle_reporting,
        }
    
    async def run(self, conversation_id: str, tenant_id: str, user_id: str, raw_input: str) -> Dict[str, Any]:
        state = GraphState(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
            raw_input=raw_input,
            current_state=OrchestratorState.IDLE,
        )
        
        logger.info("orchestrator.run.start", conversation=conversation_id)
        
        while state.current_state not in (OrchestratorState.DONE, OrchestratorState.ERROR):
            if state.iteration >= 10:
                state.errors.append("Max iterations reached")
                state.current_state = OrchestratorState.ERROR
                break
            
            handler = self._transitions.get(state.current_state)
            if not handler:
                state.errors.append(f"No handler for state {state.current_state}")
                state.current_state = OrchestratorState.ERROR
                break
            
            try:
                state = await handler(state)
                state.iteration += 1
            except Exception as e:
                logger.error("orchestrator.state_error", state=state.current_state.value, error=str(e))
                state.errors.append(str(e))
                state.current_state = OrchestratorState.ERROR
        
        logger.info("orchestrator.run.complete", conversation=conversation_id, iterations=state.iteration, final_state=state.current_state.value)
        return self._format_output(state)
    
    async def _handle_idle(self, state: GraphState) -> GraphState:
        state.current_state = OrchestratorState.REQUIREMENTS
        return state
    
    async def _handle_requirements(self, state: GraphState) -> GraphState:
        agent = self.agents["requirement"]
        result = await agent.execute({"raw_input": state.raw_input})
        state.extracted_requirements = result
        # The agent returns {"extracted_requirements": {...}, "ambiguity_flags": [...], ...}
        # The actual structured requirements are nested inside extracted_requirements
        extracted = result.get("extracted_requirements", {})
        state.requirements = extracted.get("requirements", extracted)
        state.ambiguity_flags = result.get("ambiguity_flags", [])
        state.follow_up_questions = result.get("follow_up_questions", [])
        
        # If high ambiguity, we might pause here for user clarification
        # For now, continue to planning
        state.current_state = OrchestratorState.PLANNING
        state.execution_trace.append({"step": "requirements", "result": result})
        return state
    
    async def _handle_planning(self, state: GraphState) -> GraphState:
        # Create execution plan based on requirements
        reqs = state.requirements or {}
        plan = ExecutionPlan()
        
        # Always do location intel if city specified
        if reqs.get("city"):
            plan.steps.append({"agent": "location", "parallel": False})
        
        # Discovery is always needed
        plan.steps.append({"agent": "discovery", "parallel": False})
        
        # Pricing after discovery
        plan.steps.append({"agent": "pricing", "parallel": False})
        
        # Optimization after pricing
        plan.steps.append({"agent": "optimization", "parallel": False})
        
        # Negotiation and report are optional final steps
        plan.steps.append({"agent": "negotiation", "parallel": True})
        plan.steps.append({"agent": "report", "parallel": True})
        
        state.execution_trace.append({"step": "planning", "plan": [s["agent"] for s in plan.steps]})
        
        # Move to first execution step
        if reqs.get("city"):
            state.current_state = OrchestratorState.LOCATION_INTEL
        else:
            state.current_state = OrchestratorState.DISCOVERY
        return state
    
    async def _handle_location(self, state: GraphState) -> GraphState:
        agent = self.agents["location"]
        result = await agent.execute({"requirements": state.requirements})
        state.location_analysis = result.get("location_analysis", {})
        state.execution_trace.append({"step": "location", "result": result})
        state.current_state = OrchestratorState.DISCOVERY
        return state
    
    async def _handle_discovery(self, state: GraphState) -> GraphState:
        agent = self.agents["discovery"]
        result = await agent.execute({
            "requirements": state.requirements,
            "raw_input": state.raw_input,
            "provider_filters": state.requirements.get("preferred_providers", []) if state.requirements else [],
        })
        state.discovered_workspaces = result.get("discovered_workspaces", [])
        state.execution_trace.append({"step": "discovery", "count": len(state.discovered_workspaces)})
        state.current_state = OrchestratorState.PRICING
        return state
    
    async def _handle_pricing(self, state: GraphState) -> GraphState:
        agent = self.agents["pricing"]
        result = await agent.execute({
            "requirements": state.requirements,
            "discovered_workspaces": state.discovered_workspaces,
        })
        state.pricing_analysis = result.get("pricing_analysis", {})
        state.execution_trace.append({"step": "pricing", "result": result})
        state.current_state = OrchestratorState.OPTIMIZATION
        return state
    
    async def _handle_optimization(self, state: GraphState) -> GraphState:
        agent = self.agents["optimization"]
        result = await agent.execute({
            "requirements": state.requirements,
            "discovered_workspaces": state.discovered_workspaces,
            "pricing_analysis": state.pricing_analysis,
            "location_analysis": state.location_analysis,
            "raw_input": state.raw_input,
        })
        recs = result.get("recommendations", [])
        
        # Fallback: build recommendations from discovered workspaces if agent returns empty
        if not recs and state.discovered_workspaces:
            logger.warning("optimization.fallback_to_rule_based", workspaces=len(state.discovered_workspaces))
            recs = _deterministic_recommendations(
                state.discovered_workspaces, state.requirements, state.pricing_analysis, state.raw_input
            )
        
        state.recommendations = recs
        state.execution_trace.append({"step": "optimization", "recommendations": len(recs)})
        state.current_state = OrchestratorState.NEGOTIATION
        return state
    
    async def _handle_negotiation(self, state: GraphState) -> GraphState:
        agent = self.agents["negotiation"]
        if not state.recommendations:
            logger.warning("negotiation.no_recommendations")
            state.negotiation_strategy = {"note": "No recommendations available for negotiation"}
            state.current_state = OrchestratorState.REPORTING
            return state
        result = await agent.execute({"recommendations": state.recommendations})
        state.negotiation_strategy = result.get("negotiation_strategy", {})
        state.execution_trace.append({"step": "negotiation"})
        state.current_state = OrchestratorState.REPORTING
        return state
    
    async def _handle_reporting(self, state: GraphState) -> GraphState:
        agent = self.agents["report"]
        result = await agent.execute({
            "recommendations": state.recommendations,
            "requirements": state.requirements,
            "negotiation_strategy": state.negotiation_strategy,
        })
        state.report = result.get("report", {})
        state.execution_trace.append({"step": "report"})
        state.current_state = OrchestratorState.DONE
        return state
    
    def _format_output(self, state: GraphState) -> Dict[str, Any]:
        return {
            "conversation_id": state.conversation_id,
            "status": state.current_state.value,
            "requirements": state.extracted_requirements,
            "ambiguity_flags": state.ambiguity_flags,
            "follow_up_questions": state.follow_up_questions,
            "recommendations": state.recommendations[:10],
            "report": state.report,
            "negotiation": state.negotiation_strategy,
            "execution_trace": state.execution_trace,
            "errors": state.errors,
            "iterations": state.iteration,
        }
