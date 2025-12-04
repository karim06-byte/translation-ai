"""Translation service using fine-tuned model."""
import re
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel
from typing import Optional
import logging
from pathlib import Path
from config.settings import settings

logger = logging.getLogger(__name__)


class TranslationService:
    """Service for translation using fine-tuned NLLB model."""
    
    def __init__(self, model_path: Optional[str] = None):
        # Use the trained model path if available, otherwise use base model
        if model_path:
            self.model_path = model_path
        else:
            # Try to find the latest trained model
            import os
            output_dir = Path(settings.output_dir)
            if output_dir.exists():
                # Look for latest model directory
                model_dirs = [d for d in output_dir.iterdir() if d.is_dir() and (d / "adapter_config.json").exists()]
                if model_dirs:
                    # Sort by modification time, get latest
                    model_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    self.model_path = str(model_dirs[0])
                    logger.info(f"Using trained model from: {self.model_path}")
                else:
                    self.model_path = None
            else:
                self.model_path = None
        
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """Load model and tokenizer."""
        try:
            base_model_name = settings.model_name
            logger.info(f"Loading base model: {base_model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                base_model_name,
                cache_dir=settings.model_cache_dir,
                src_lang="eng_Latn",
                tgt_lang="aze_Latn"
            )
            
            base_model = AutoModelForSeq2SeqLM.from_pretrained(
                base_model_name,
                cache_dir=settings.model_cache_dir,
                dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
            # Load LoRA adapters if they exist
            import os
            if self.model_path and os.path.exists(self.model_path) and os.path.exists(
                os.path.join(self.model_path, "adapter_config.json")
            ):
                logger.info(f"Loading LoRA adapters from {self.model_path}")
                self.model = PeftModel.from_pretrained(base_model, self.model_path)
            else:
                logger.warning("No LoRA adapters found, using base model")
                self.model = base_model
            
            self.model.to(self.device)
            self.model.eval()
            logger.info("Model loaded successfully")
        
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def translate(self, text: str, max_length: int = 256, use_style_memory: bool = True) -> str:
        """Translate English text to Azerbaijani with optional style memory integration."""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded")
        
        # Check style memory first if enabled
        if use_style_memory:
            try:
                from backend.services.style_memory import get_style_memory_service
                style_memory_service = get_style_memory_service()
                
                # Find nearest style memory entry
                nearest = style_memory_service.find_nearest(text, k=1, threshold=0.85)
                if nearest:
                    entry, similarity = nearest[0]
                    # If similarity is very high, use style memory translation directly
                    if similarity >= 0.95:
                        logger.info(f"Using style memory translation (similarity: {similarity:.3f})")
                        return entry["preferred_az"]
                    # If similarity is high but not perfect, we can still use it as a hint
                    # For now, we'll use the model translation but could enhance this later
            except Exception as e:
                logger.warning(f"Error checking style memory: {e}, falling back to model translation")
        
        try:
            # Set source and target languages for NLLB tokenizer
            # Note: NLLB uses 'azj_Latn' for Azerbaijani, not 'aze_Latn'
            self.tokenizer.src_lang = "eng_Latn"
            self.tokenizer.tgt_lang = "azj_Latn"  # Correct Azerbaijani language code
            
            # Tokenize with source language
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=max_length,
                truncation=True,
                padding=True
            ).to(self.device)
            
            # Generate translation
            with torch.no_grad():
                # For NLLB, we need to get the correct language token ID
                # The issue is that convert_tokens_to_ids("aze_Latn") returns UNK (3)
                # We need to find the actual Azerbaijani language token ID
                # NLLB uses token IDs in the range 256000+ for language codes
                
                forced_bos_token_id = None
                
                # Method 1: Try to get from tokenizer's internal language mapping
                # NLLB tokenizer should have language codes as special tokens
                try:
                    # Check if tokenizer has a way to get language token IDs
                    # Some NLLB versions store this differently
                    vocab = self.tokenizer.get_vocab()
                    
                    # Azerbaijani language code - NLLB uses 'azj_Latn' (token ID 256020)
                    # Try the correct code first
                    if 'azj_Latn' in vocab:
                        forced_bos_token_id = vocab['azj_Latn']
                        logger.info(f"Found Azerbaijani token: azj_Latn -> {forced_bos_token_id}")
                    else:
                        # Fallback to other variations
                        aze_variants = ['azj_Latn', 'aze_Latn', 'azb_Latn', 'az_Latn']
                        for variant in aze_variants:
                            if variant in vocab:
                                forced_bos_token_id = vocab[variant]
                                logger.info(f"Found Azerbaijani token: {variant} -> {forced_bos_token_id}")
                                break
                    
                    # If not found, try to find by pattern
                    # NLLB language tokens are typically in the 256000+ range
                    if forced_bos_token_id is None:
                        # Look for tokens that might be Azerbaijani
                        # This is a heuristic - we'll try common Azerbaijani token IDs
                        # Based on NLLB-200 structure, Azerbaijani should be around 256000-257000
                        # Let's try a few known patterns
                        potential_ids = [256000 + i for i in range(200)]  # Check first 200 language slots
                        for token_id in potential_ids:
                            try:
                                token = self.tokenizer.convert_ids_to_tokens([token_id])[0]
                                if 'aze' in token.lower() or token == 'aze_Latn':
                                    forced_bos_token_id = token_id
                                    logger.info(f"Found Azerbaijani token by pattern: {token_id} -> {token}")
                                    break
                            except:
                                continue
                
                except Exception as e:
                    logger.warning(f"Error finding Azerbaijani token: {e}")
                
                # Method 2: If still not found, try using the tokenizer's tgt_lang setting
                # and let the model generate without forced_bos_token_id
                # The model should still work, though quality may vary
                if forced_bos_token_id is None or forced_bos_token_id == self.tokenizer.unk_token_id:
                    logger.warning("Could not find valid Azerbaijani language token, will generate without forced_bos_token_id")
                    forced_bos_token_id = None
                
                generate_kwargs = {
                    **inputs,
                    "max_length": max_length,
                    "num_beams": 4,
                    "early_stopping": True,
                }
                
                # Only use forced_bos_token_id if it's valid (not UNK)
                if forced_bos_token_id is not None and forced_bos_token_id != self.tokenizer.unk_token_id:
                    generate_kwargs["forced_bos_token_id"] = forced_bos_token_id
                    logger.debug(f"Using forced_bos_token_id: {forced_bos_token_id} for aze_Latn")
                else:
                    # Don't use forced_bos_token_id if it's UNK - the model will still translate
                    # but might not be perfectly targeted to Azerbaijani
                    logger.warning("No valid forced_bos_token_id (got UNK), generating without it - translation may not be perfect")
                
                outputs = self.model.generate(**generate_kwargs)
            
            # Decode with target language context
            self.tokenizer.tgt_lang = "azj_Latn"  # Correct Azerbaijani language code
            translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Clean up translation - remove language codes and prefixes
            translation = translation.replace("azj_Latn", "").replace("aze_Latn", "").replace("eng_Latn", "").strip()
            # Remove "azj" or "aze" prefixes if they appear at the start
            translation = re.sub(r'^(azj|aze)\s*,?\s*', '', translation, flags=re.IGNORECASE).strip()
            if translation.lower().startswith("azj "):
                translation = translation[4:].strip()
            if translation.lower().startswith("azj,"):
                translation = translation[4:].strip()
            if translation.lower().startswith("azee"):
                # Sometimes produces "azee" or "azees" - remove it
                translation = re.sub(r'^azee?s?\s*,?\s*', '', translation, flags=re.IGNORECASE).strip()
            
            # Verify translation is different from input
            if translation.strip().lower() == text.strip().lower() or not translation:
                logger.error(f"Translation failed - output same as input or empty: {text[:50]}... -> {translation[:50]}")
                # Try one more time with a simpler approach
                return self._translate_simple(text, max_length)
            
            return translation
        
        except Exception as e:
            logger.error(f"Error during translation: {e}", exc_info=True)
            # Try simple translation as fallback
            try:
                return self._translate_simple(text, max_length)
            except:
                logger.warning(f"Translation failed for: {text[:50]}..., returning original text")
                return f"[Translation Error] {text}"
    
    def _translate_simple(self, text: str, max_length: int = 256) -> str:
        """Simple translation fallback method."""
        self.tokenizer.src_lang = "eng_Latn"
        self.tokenizer.tgt_lang = "azj_Latn"
        inputs = self.tokenizer(text, return_tensors="pt", max_length=max_length, truncation=True).to(self.device)
        
        # Get correct Azerbaijani token ID
        azj_token_id = self.tokenizer.convert_tokens_to_ids("azj_Latn")
        
        with torch.no_grad():
            generate_kwargs = {
                **inputs,
                "max_length": max_length,
                "num_beams": 4,
            }
            if azj_token_id is not None and azj_token_id != self.tokenizer.unk_token_id:
                generate_kwargs["forced_bos_token_id"] = azj_token_id
            
            outputs = self.model.generate(**generate_kwargs)
        
        self.tokenizer.tgt_lang = "azj_Latn"
        translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        translation = translation.replace("azj_Latn", "").replace("aze_Latn", "").replace("eng_Latn", "").strip()
        return translation if translation else f"[Translation Error] {text}"
    
    def translate_batch(self, texts: list, max_length: int = 256) -> list:
        """Translate a batch of texts."""
        translations = []
        for text in texts:
            translations.append(self.translate(text, max_length))
        return translations


# Global instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get or create translation service instance."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service

