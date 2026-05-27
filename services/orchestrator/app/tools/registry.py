"""
Dynamic Tool Registry for autonomous tool orchestration.
Implements tool discovery, selection, validation, and retry mechanisms.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
import structlog
import asyncio
import time

logger = structlog.get_logger()

class ToolCategory(str, Enum):
    MAPS = "maps"
    SEARCH = "search"
    PRICING = "pricing"
    TRANSPORT = "transport"
    WEATHER = "weather"
    CALENDAR = "calendar"
    EMAIL = "email"
    CRM = "crm"
    SCRAPER = "scraper"
    INTERNAL = "internal"

@dataclass
class ToolDefinition:
    name: str
    description: str
    category: ToolCategory
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    handler: Optional[Callable[..., Awaitable[Any]]] = None
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    retry_attempts: int = 3
    fallback_tools: List[str] = None
    auth_required: bool = False

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._usage_counters: Dict[str, int] = {}
        self._last_reset: float = time.time()
    
    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool
        self._usage_counters[tool.name] = 0
        logger.info("tool.registered", name=tool.name, category=tool.category)
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolDefinition]:
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools
    
    def select_tools(self, intent: str, required_capabilities: List[str]) -> List[ToolDefinition]:
        """Select tools based on intent and required capabilities."""
        scored = []
        for tool in self._tools.values():
            score = 0.0
            # Semantic matching on description
            desc_lower = tool.description.lower()
            for cap in required_capabilities:
                if cap.lower() in desc_lower or cap.lower() in tool.name.lower():
                    score += 0.5
            # Intent keyword matching
            intent_lower = intent.lower()
            if any(kw in intent_lower for kw in tool.description.lower().split()[:10]):
                score += 0.3
            # Check rate limit availability
            if self._check_rate_limit(tool.name):
                score += 0.2
            if score > 0.3:
                scored.append((score, tool))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:5]]
    
    def _check_rate_limit(self, tool_name: str) -> bool:
        if time.time() - self._last_reset > 60:
            self._usage_counters = {k: 0 for k in self._usage_counters}
            self._last_reset = time.time()
        tool = self._tools.get(tool_name)
        if not tool:
            return False
        return self._usage_counters[tool_name] < tool.rate_limit_per_minute
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}
        
        if not self._check_rate_limit(tool_name):
            # Try fallback
            if tool.fallback_tools:
                for fallback in tool.fallback_tools:
                    result = await self.execute(fallback, arguments)
                    if result.get("success"):
                        return result
            return {"success": False, "error": f"Rate limit exceeded for '{tool_name}'"}
        
        if not tool.handler:
            return {"success": False, "error": f"Tool '{tool_name}' has no handler"}
        
        self._usage_counters[tool_name] += 1
        
        for attempt in range(tool.retry_attempts):
            try:
                result = await asyncio.wait_for(
                    tool.handler(**arguments),
                    timeout=tool.timeout_seconds,
                )
                return {"success": True, "data": result, "tool": tool_name, "attempt": attempt + 1}
            except asyncio.TimeoutError:
                logger.warning("tool.timeout", tool=tool_name, attempt=attempt + 1)
                if attempt == tool.retry_attempts - 1:
                    return {"success": False, "error": f"Timeout after {tool.retry_attempts} attempts", "tool": tool_name}
            except Exception as e:
                logger.error("tool.error", tool=tool_name, error=str(e), attempt=attempt + 1)
                if attempt == tool.retry_attempts - 1:
                    return {"success": False, "error": str(e), "tool": tool_name}
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return {"success": False, "error": "All retry attempts failed", "tool": tool_name}

# Global registry instance
_registry = ToolRegistry()

def get_registry() -> ToolRegistry:
    return _registry
