"""Style memory service for storing and retrieving approved translations."""
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Optional
import logging
import numpy as np
from config.settings import settings

logger = logging.getLogger(__name__)


class StyleMemoryService:
    """Service for managing style memory with vector embeddings."""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db
            )
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def add_memory(
        self,
        source_en: str,
        preferred_az: str,
        segment_id: Optional[int] = None,
        approved_by: Optional[int] = None,
        engine: Optional[str] = None,
        similarity_score: Optional[float] = None
    ) -> int:
        """Add a new entry to style memory."""
        try:
            # Generate embedding
            embedding = self.embedding_model.encode([source_en])[0]
            embedding_list = embedding.tolist()
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO style_memory 
                (segment_id, source_en, preferred_az, embedding, approved_by, engine, similarity_score)
                VALUES (%s, %s, %s, %s::vector, %s, %s, %s)
                RETURNING id
            """, (segment_id, source_en, preferred_az, str(embedding_list), approved_by, engine, similarity_score))
            
            memory_id = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()
            
            logger.info(f"Added style memory entry {memory_id}")
            return memory_id
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error adding style memory: {e}")
            raise
    
    def find_nearest(
        self,
        source_en: str,
        k: int = 5,
        threshold: float = 0.7
    ) -> List[Tuple[dict, float]]:
        """
        Find nearest style memory entries.
        
        Returns:
            List of (entry_dict, similarity_score) tuples
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_model.encode([source_en])[0]
            query_embedding_list = query_embedding.tolist()
            
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    id, segment_id, source_en, preferred_az, 
                    approved_by, engine, similarity_score, approved_at,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM style_memory
                WHERE 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (str(query_embedding_list), str(query_embedding_list), threshold, str(query_embedding_list), k))
            
            results = []
            for row in cursor.fetchall():
                entry = {
                    "id": row[0],
                    "segment_id": row[1],
                    "source_en": row[2],
                    "preferred_az": row[3],
                    "approved_by": row[4],
                    "engine": row[5],
                    "similarity_score": row[6],
                    "approved_at": row[7].isoformat() if row[7] else None
                }
                similarity = float(row[8])
                results.append((entry, similarity))
            
            cursor.close()
            return results
        
        except Exception as e:
            logger.error(f"Error finding nearest style memory: {e}")
            return []
    
    def get_override_count(self) -> int:
        """Get count of approved overrides for retraining trigger."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM style_memory
                WHERE approved_at >= NOW() - INTERVAL '%s days'
            """, (settings.retrain_interval_days,))
            
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        
        except Exception as e:
            logger.error(f"Error getting override count: {e}")
            return 0
    
    def get_recent_overrides(self, limit: int = 500) -> List[dict]:
        """Get recent overrides for retraining."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT source_en, preferred_az
                FROM style_memory
                ORDER BY approved_at DESC
                LIMIT %s
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "source": row[0],
                    "target": row[1]
                })
            
            cursor.close()
            return results
        
        except Exception as e:
            logger.error(f"Error getting recent overrides: {e}")
            return []
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Global instance
_style_memory_service: Optional[StyleMemoryService] = None


def get_style_memory_service() -> StyleMemoryService:
    """Get or create style memory service instance."""
    global _style_memory_service
    if _style_memory_service is None:
        _style_memory_service = StyleMemoryService()
    return _style_memory_service

