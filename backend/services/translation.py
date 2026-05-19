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
    
    def _purge_broken_cache(self, cache_dir: str, model_name: str):
        """Delete model cache if config.json is missing or not valid JSON."""
        import json
        import shutil
        model_cache_name = "models--" + model_name.replace("/", "--")
        model_cache_path = Path(cache_dir) / model_cache_name
        if not model_cache_path.exists():
            return
        snapshots_dir = model_cache_path / "snapshots"
        if not snapshots_dir.exists():
            return
        for snapshot_dir in snapshots_dir.iterdir():
            if not snapshot_dir.is_dir():
                continue
            config_file = snapshot_dir / "config.json"
            if not config_file.exists():
                continue
            try:
                json.loads(config_file.read_text(encoding="utf-8"))
                return  # cache is healthy
            except Exception:
                logger.warning(f"Broken model cache at {model_cache_path} — deleting so it can re-download")
                shutil.rmtree(str(model_cache_path), ignore_errors=True)
                return

    def _load_model(self):
        """Load model and tokenizer."""
        try:
            base_model_name = settings.model_name
            self._purge_broken_cache(settings.model_cache_dir, base_model_name)
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
    
    def translate(self, text: str, max_length: int = 256, use_style_memory: bool = True, direction: str = "en_to_az") -> str:
        """Translate text between English and Azerbaijani."""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded")

        src_lang = "eng_Latn" if direction == "en_to_az" else "azj_Latn"
        tgt_lang = "azj_Latn" if direction == "en_to_az" else "eng_Latn"

        # Check style memory first if enabled (only for en_to_az, memory is indexed on EN)
        if use_style_memory and direction == "en_to_az":
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
            self.tokenizer.src_lang = src_lang
            self.tokenizer.tgt_lang = tgt_lang
            
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

                try:
                    vocab = self.tokenizer.get_vocab()

                    if tgt_lang == "azj_Latn":
                        candidates = ['azj_Latn', 'aze_Latn', 'azb_Latn', 'az_Latn']
                    else:
                        candidates = ['eng_Latn']

                    for candidate in candidates:
                        if candidate in vocab:
                            forced_bos_token_id = vocab[candidate]
                            logger.info(f"Found target language token: {candidate} -> {forced_bos_token_id}")
                            break

                    # Fallback: scan language token range for Azerbaijani
                    if forced_bos_token_id is None and tgt_lang == "azj_Latn":
                        for token_id in [256000 + i for i in range(200)]:
                            try:
                                token = self.tokenizer.convert_ids_to_tokens([token_id])[0]
                                if 'aze' in token.lower():
                                    forced_bos_token_id = token_id
                                    logger.info(f"Found Azerbaijani token by pattern: {token_id} -> {token}")
                                    break
                            except:
                                continue

                except Exception as e:
                    logger.warning(f"Error finding target language token: {e}")

                if forced_bos_token_id is None or forced_bos_token_id == self.tokenizer.unk_token_id:
                    logger.warning("Could not find valid target language token, generating without forced_bos_token_id")
                    forced_bos_token_id = None

                generate_kwargs = {
                    **inputs,
                    "max_length": max_length,
                    "num_beams": 4,
                    "early_stopping": True,
                }

                if forced_bos_token_id is not None and forced_bos_token_id != self.tokenizer.unk_token_id:
                    generate_kwargs["forced_bos_token_id"] = forced_bos_token_id

                outputs = self.model.generate(**generate_kwargs)

            translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Strip language code artifacts
            translation = translation.replace("azj_Latn", "").replace("aze_Latn", "").replace("eng_Latn", "").strip()
            translation = re.sub(r'^(azj|aze)\s*,?\s*', '', translation, flags=re.IGNORECASE).strip()
            if translation.lower().startswith("azj "):
                translation = translation[4:].strip()
            if translation.lower().startswith("azj,"):
                translation = translation[4:].strip()
            if translation.lower().startswith("azee"):
                translation = re.sub(r'^azee?s?\s*,?\s*', '', translation, flags=re.IGNORECASE).strip()

            if translation.strip().lower() == text.strip().lower() or not translation:
                logger.error(f"Translation failed - output same as input or empty: {text[:50]}...")
                return self._translate_simple(text, max_length, direction=direction)

            return translation

        except Exception as e:
            logger.error(f"Error during translation: {e}", exc_info=True)
            try:
                return self._translate_simple(text, max_length, direction=direction)
            except:
                logger.warning(f"Translation failed for: {text[:50]}..., returning original text")
                return f"[Translation Error] {text}"
    
    def _translate_simple(self, text: str, max_length: int = 256, direction: str = "en_to_az") -> str:
        """Simple translation fallback method."""
        src_lang = "eng_Latn" if direction == "en_to_az" else "azj_Latn"
        tgt_lang = "azj_Latn" if direction == "en_to_az" else "eng_Latn"
        self.tokenizer.src_lang = src_lang
        self.tokenizer.tgt_lang = tgt_lang
        inputs = self.tokenizer(text, return_tensors="pt", max_length=max_length, truncation=True).to(self.device)

        tgt_token_id = self.tokenizer.convert_tokens_to_ids(tgt_lang)

        with torch.no_grad():
            generate_kwargs = {
                **inputs,
                "max_length": max_length,
                "num_beams": 4,
            }
            if tgt_token_id is not None and tgt_token_id != self.tokenizer.unk_token_id:
                generate_kwargs["forced_bos_token_id"] = tgt_token_id

            outputs = self.model.generate(**generate_kwargs)

        translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        translation = translation.replace("azj_Latn", "").replace("aze_Latn", "").replace("eng_Latn", "").strip()
        return translation if translation else f"[Translation Error] {text}"
    
    def translate_batch(self, texts: list, max_length: int = 256, direction: str = "en_to_az") -> list:
        """Translate a batch of texts."""
        translations = []
        for text in texts:
            translations.append(self.translate(text, max_length, direction=direction))
        return translations


# Global instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get or create translation service instance."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service

