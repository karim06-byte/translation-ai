"""Inference utilities for translation with style memory integration."""
from typing import Optional, List
import logging

from backend.services.translation import get_translation_service
from backend.services.style_memory import get_style_memory_service

logger = logging.getLogger(__name__)


class TranslationInference:
    """Combined inference with model and style memory."""
    
    def __init__(self):
        self.translation_service = get_translation_service()
        self.style_memory_service = get_style_memory_service()
        self.style_threshold = 0.8
    
    def translate_with_style(
        self,
        source_text: str,
        use_style_memory: bool = True
    ) -> dict:
        """
        Translate with style memory integration.
        
        Returns:
            dict with 'translation', 'style_hint', 'from_style_memory'
        """
        # Get base translation
        translation = self.translation_service.translate(source_text)
        
        result = {
            "translation": translation,
            "style_hint": None,
            "from_style_memory": False
        }
        
        if use_style_memory:
            # Check style memory
            nearest = self.style_memory_service.find_nearest(
                source_text,
                k=1,
                threshold=self.style_threshold
            )
            
            if nearest:
                entry, similarity = nearest[0]
                result["style_hint"] = {
                    "similar_source": entry["source_en"],
                    "preferred_translation": entry["preferred_az"],
                    "similarity": similarity
                }
                
                # If similarity is very high, use style memory translation
                if similarity >= 0.95:
                    result["translation"] = entry["preferred_az"]
                    result["from_style_memory"] = True
        
        return result
    
    def translate_batch_with_style(
        self,
        source_texts: List[str],
        use_style_memory: bool = True
    ) -> List[dict]:
        """Translate a batch of texts with style memory."""
        results = []
        for text in source_texts:
            results.append(self.translate_with_style(text, use_style_memory))
        return results


def get_inference_service() -> TranslationInference:
    """Get inference service instance."""
    return TranslationInference()

