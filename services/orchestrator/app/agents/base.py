from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import structlog
import json
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

@dataclass
class AgentRunResult:
    success: bool
    data: Dict[str, Any]
    reasoning: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: int = 0
    tokens_used: int = 0

class BaseAgent(ABC):
    def __init__(self, name: str, system_prompt: str, model: str = None):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model or settings.FIREWORKS_MODEL
        
        # Initialize Fireworks AI client (OpenAI-compatible)
        if settings.FIREWORKS_API_KEY:
            self.llm_client = AsyncOpenAI(
                api_key=settings.FIREWORKS_API_KEY,
                base_url=settings.FIREWORKS_BASE_URL,
            )
        elif settings.OPENAI_API_KEY:
            self.llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.llm_client = None
    
    async def run(self, context: Dict[str, Any], memory: List[Dict[str, Any]] = None) -> AgentRunResult:
        import time
        start = time.time()
        try:
            messages = self._build_messages(context, memory)
            response = await self._call_llm(messages)
            parsed = self._parse_response(response)
            latency = int((time.time() - start) * 1000)
            
            logger.info(
                "agent.run.complete",
                agent=self.name,
                success=True,
                latency_ms=latency,
            )
            
            return AgentRunResult(
                success=True,
                data=parsed.get("data") if "data" in parsed else parsed,
                reasoning=parsed.get("reasoning"),
                tool_calls=parsed.get("tool_calls", []),
                tokens_used=parsed.get("tokens_used", 0),
                latency_ms=latency,
            )
        except Exception as e:
            logger.error("agent.run.failed", agent=self.name, error=str(e))
            return AgentRunResult(
                success=False,
                data={},
                error=str(e),
                latency_ms=int((time.time() - start) * 1000),
            )
    
    def _build_messages(self, context: Dict[str, Any], memory: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        if memory:
            for m in memory[:5]:
                messages.append({"role": "system", "content": f"[Memory] {m.get('key')}: {m.get('value')}"})
        messages.append({"role": "user", "content": json.dumps(context, default=str)})
        return messages
    
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        if self.llm_client:
            resp = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
            )
            return resp.choices[0].message.content
        else:
            # Fallback mock response for demo
            return json.dumps({
                "data": {"mock": True, "agent": self.name},
                "reasoning": "LLM not configured - returning mock data",
                "tool_calls": [],
                "tokens_used": 0,
            })
    
    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """Parse LLM response, stripping markdown code blocks if present."""
        # Strip markdown code fences (```json, ```, etc.)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remove first line (e.g., ```json)
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
            # Remove trailing ```
            cleaned = cleaned.rsplit("```", 1)[0].strip() if "```" in cleaned else cleaned
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"data": {"raw_response": raw}, "reasoning": "Failed to parse JSON", "tool_calls": []}
    
    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic. Override in subclasses."""
        pass
