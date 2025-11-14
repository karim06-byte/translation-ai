"""Metrics calculation service."""
import sacrebleu
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for calculating translation metrics."""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    def calculate_bleu(self, predictions: List[str], references: List[str]) -> float:
        """Calculate BLEU score."""
        try:
            bleu = sacrebleu.corpus_bleu(predictions, [references])
            return bleu.score
        except Exception as e:
            logger.error(f"Error calculating BLEU: {e}")
            return 0.0
    
    def calculate_chrf(self, predictions: List[str], references: List[str]) -> float:
        """Calculate ChrF score."""
        try:
            chrf = sacrebleu.corpus_chrf(predictions, [references])
            return chrf.score
        except Exception as e:
            logger.error(f"Error calculating ChrF: {e}")
            return 0.0
    
    def calculate_style_similarity(
        self,
        predictions: List[str],
        references: List[str]
    ) -> float:
        """Calculate Style Similarity Score (SSS) using cosine similarity."""
        try:
            if not predictions or not references:
                return 0.0
            
            pred_embeddings = self.embedding_model.encode(predictions)
            ref_embeddings = self.embedding_model.encode(references)
            
            similarities = []
            for pred_emb, ref_emb in zip(pred_embeddings, ref_embeddings):
                similarity = cosine_similarity([pred_emb], [ref_emb])[0][0]
                similarities.append(similarity)
            
            return float(np.mean(similarities))
        
        except Exception as e:
            logger.error(f"Error calculating style similarity: {e}")
            return 0.0
    
    def calculate_single_style_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """Calculate style similarity between two single texts."""
        try:
            if not text1 or not text2:
                return 0.0
            
            emb1 = self.embedding_model.encode([text1])
            emb2 = self.embedding_model.encode([text2])
            
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
        
        except Exception as e:
            logger.error(f"Error calculating single style similarity: {e}")
            return 0.0
    
    def calculate_manual_override_rate(
        self,
        total_segments: int,
        overridden_segments: int
    ) -> float:
        """Calculate Manual Override Rate (MOR)."""
        if total_segments == 0:
            return 0.0
        return (overridden_segments / total_segments) * 100.0
    
    def calculate_attribution_ratio(
        self,
        model_outputs: List[str],
        style_memory_embeddings: List[np.ndarray],
        external_corpus_embeddings: Optional[List[np.ndarray]] = None
    ) -> float:
        """
        Calculate Attribution Ratio (AR) - how much of the style comes from publisher's data.
        
        Simplified version: compares similarity to style memory vs external corpus.
        """
        try:
            if not model_outputs or not style_memory_embeddings:
                return 0.0
            
            model_embeddings = self.embedding_model.encode(model_outputs)
            
            style_similarities = []
            for model_emb in model_embeddings:
                # Find max similarity to style memory
                max_sim = 0.0
                for style_emb in style_memory_embeddings:
                    sim = cosine_similarity([model_emb], [style_emb])[0][0]
                    max_sim = max(max_sim, sim)
                style_similarities.append(max_sim)
            
            avg_style_sim = np.mean(style_similarities)
            
            # If no external corpus, use a baseline
            if external_corpus_embeddings is None or len(external_corpus_embeddings) == 0:
                # Assume external similarity is lower (e.g., 0.5 baseline)
                external_sim = 0.5
            else:
                external_similarities = []
                for model_emb in model_embeddings:
                    max_sim = 0.0
                    for ext_emb in external_corpus_embeddings:
                        sim = cosine_similarity([model_emb], [ext_emb])[0][0]
                        max_sim = max(max_sim, sim)
                    external_similarities.append(max_sim)
                external_sim = np.mean(external_similarities)
            
            # Attribution ratio
            total_sim = avg_style_sim + external_sim
            if total_sim == 0:
                return 0.0
            
            ar = (avg_style_sim / total_sim) * 100.0
            return float(ar)
        
        except Exception as e:
            logger.error(f"Error calculating attribution ratio: {e}")
            return 0.0
    
    def calculate_all_metrics(
        self,
        predictions: List[str],
        references: List[str],
        total_segments: int = 0,
        overridden_segments: int = 0
    ) -> Dict[str, float]:
        """Calculate all metrics."""
        return {
            "bleu": self.calculate_bleu(predictions, references),
            "chrf": self.calculate_chrf(predictions, references),
            "style_similarity_score": self.calculate_style_similarity(predictions, references),
            "manual_override_rate": self.calculate_manual_override_rate(
                total_segments, overridden_segments
            )
        }


# Global instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get or create metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service

