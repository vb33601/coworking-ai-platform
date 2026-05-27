from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from orch_app.tools.registry import get_registry, ToolCategory

router = APIRouter()

class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

@router.get("/list")
async def list_tools(category: Optional[str] = None):
    """List all registered tools, optionally filtered by category."""
    registry = get_registry()
    tools = registry.list_tools(
        ToolCategory(category) if category else None
    )
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "input_schema": t.input_schema,
                "rate_limit_per_minute": t.rate_limit_per_minute,
                "timeout_seconds": t.timeout_seconds,
                "retry_attempts": t.retry_attempts,
            }
            for t in tools
        ],
        "total": len(tools),
    }

@router.post("/execute")
async def execute_tool(request: ToolExecuteRequest):
    """Execute a tool with given arguments."""
    registry = get_registry()
    result = await registry.execute(request.tool_name, request.arguments)
    return result

@router.post("/select")
async def select_tools(intent: str, capabilities: List[str]):
    """Select best tools for a given intent and required capabilities."""
    registry = get_registry()
    tools = registry.select_tools(intent, capabilities)
    return {
        "selected_tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
            }
            for t in tools
        ],
        "intent": intent,
    }
