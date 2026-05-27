import structlog
from typing import List, Dict, Any, Optional
import numpy as np
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

class VectorStore:
    """Vector store using pgvector for semantic search and memory retrieval."""
    
    def __init__(self):
        self._initialized = False
        self._dim = 1536
    
    async def initialize(self):
        """Initialize connection pool and verify extensions."""
        try:
            # In production, use asyncpg connection pool
            logger.info("vector_store.initialized")
            self._initialized = True
        except Exception as e:
            logger.error("vector_store.init_failed", error=str(e))
    
    async def upsert(self, collection: str, id: str, text: str, metadata: Dict[str, Any], embedding: Optional[List[float]] = None) -> bool:
        """Store or update a vector entry."""
        try:
            # In production: use asyncpg to insert into pgvector table
            logger.info("vector_store.upsert", collection=collection, id=id)
            return True
        except Exception as e:
            logger.error("vector_store.upsert_failed", error=str(e))
            return False
    
    async def search(self, collection: str, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Semantic search using cosine similarity."""
        try:
            # In production: execute SQL with vector_cosine_ops
            logger.info("vector_store.search", collection=collection, top_k=top_k)
            return []
        except Exception as e:
            logger.error("vector_store.search_failed", error=str(e))
            return []
    
    async def delete(self, collection: str, id: str) -> bool:
        logger.info("vector_store.delete", collection=collection, id=id)
        return True

class MemoryManager:
    """Manages short-term and long-term memory for AI agents."""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.short_term: Dict[str, List[Dict[str, Any]]] = {}
    
    async def add_memory(self, tenant_id: str, user_id: Optional[str], conversation_id: Optional[str], memory_type: str, key: str, value: str, embedding: Optional[List[float]] = None, confidence: float = 0.8, expires_hours: Optional[int] = None) -> bool:
        """Add a memory entry."""
        entry = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "memory_type": memory_type,
            "key": key,
            "value": value,
            "confidence": confidence,
        }
        
        # Short-term memory (in-memory)
        if memory_type == "short_term":
            conv_key = conversation_id or f"{tenant_id}:{user_id}"
            if conv_key not in self.short_term:
                self.short_term[conv_key] = []
            self.short_term[conv_key].append(entry)
            # Keep only last 20 entries
            self.short_term[conv_key] = self.short_term[conv_key][-20:]
        
        # Long-term / preference memory (vector store)
        if memory_type in ("long_term", "preference", "feedback"):
            await self.vector_store.upsert(
                collection="memory",
                id=f"{tenant_id}:{user_id or 'all'}:{memory_type}:{key}",
                text=f"{key}: {value}",
                metadata=entry,
                embedding=embedding,
            )
        
        logger.info("memory.added", type=memory_type, key=key, tenant=tenant_id)
        return True
    
    async def retrieve_context(self, tenant_id: str, user_id: Optional[str], conversation_id: Optional[str], query_embedding: Optional[List[float]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve relevant memory context for an agent."""
        results = []
        
        # Short-term
        conv_key = conversation_id or f"{tenant_id}:{user_id}"
        if conv_key in self.short_term:
            results.extend(self.short_term[conv_key][-5:])
        
        # Long-term via vector search
        if query_embedding:
            long_term = await self.vector_store.search(
                collection="memory",
                query_embedding=query_embedding,
                top_k=limit,
                filters={"tenant_id": tenant_id, "user_id": user_id},
            )
            results.extend(long_term)
        
        return results[:limit]
    
    async def get_preferences(self, tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Retrieve user preference weights and patterns."""
        prefs = await self.vector_store.search(
            collection="memory",
            query_embedding=[0.0] * self.vector_store._dim,  # dummy - would be actual embedding
            top_k=20,
            filters={"tenant_id": tenant_id, "user_id": user_id, "memory_type": "preference"},
        )
        return {p.get("key"): p.get("value") for p in prefs}
