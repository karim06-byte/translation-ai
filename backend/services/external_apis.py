"""External API integrations for Gemini and ChatGPT."""
import openai
import google.generativeai as genai
from typing import Optional
import logging
from config.settings import settings

logger = logging.getLogger(__name__)


class ExternalAPIService:
    """Service for calling external translation APIs."""
    
    def __init__(self):
        # Initialize OpenAI
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
        
        # Initialize Gemini
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
        else:
            self.gemini_model = None
    
    def translate_with_chatgpt(self, text: str, context: Optional[str] = None) -> str:
        """Translate using ChatGPT API."""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        try:
            prompt = f"Translate the following English text to Azerbaijani. Maintain a professional publishing house style.\n\nText: {text}"
            if context:
                prompt += f"\n\nContext: {context}"
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional translator specializing in English to Azerbaijani translation for publishing houses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            translation = response.choices[0].message.content.strip()
            return translation
        
        except Exception as e:
            logger.error(f"Error with ChatGPT translation: {e}")
            raise
    
    def translate_with_gemini(self, text: str, context: Optional[str] = None) -> str:
        """Translate using Gemini API."""
        if not settings.gemini_api_key or not self.gemini_model:
            raise ValueError("Gemini API key not configured")
        
        try:
            prompt = f"Translate the following English text to Azerbaijani. Maintain a professional publishing house style.\n\nText: {text}"
            if context:
                prompt += f"\n\nContext: {context}"
            
            response = self.gemini_model.generate_content(prompt)
            translation = response.text.strip()
            return translation
        
        except Exception as e:
            logger.error(f"Error with Gemini translation: {e}")
            raise
    
    def retranslate(self, text: str, engine: str, context: Optional[str] = None) -> str:
        """Retranslate text using specified engine."""
        if engine.lower() == "chatgpt" or engine.lower() == "gpt":
            return self.translate_with_chatgpt(text, context)
        elif engine.lower() == "gemini":
            return self.translate_with_gemini(text, context)
        else:
            raise ValueError(f"Unknown engine: {engine}")


# Global instance
_external_api_service: Optional[ExternalAPIService] = None


def get_external_api_service() -> ExternalAPIService:
    """Get or create external API service instance."""
    global _external_api_service
    if _external_api_service is None:
        _external_api_service = ExternalAPIService()
    return _external_api_service

