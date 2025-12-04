"""Text cleaning and normalization utilities."""
import re
import unicodedata
from typing import List


def clean_text(text: str) -> str:
    """Clean text by removing HTML tags, extra whitespace, etc."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def normalize_azerbaijani(text: str) -> str:
    """Normalize Azerbaijani characters."""
    # Unicode normalization (NFKC)
    text = unicodedata.normalize('NFKC', text)
    
    # Ensure proper Azerbaijani characters
    # This is a basic normalization - can be extended
    return text


def sentence_tokenize(text: str, language: str = 'en') -> List[str]:
    """Tokenize text into sentences with improved splitting."""
    import nltk
    import ssl
    
    # Handle SSL certificate issues for NLTK downloads
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    
    # Download required NLTK data
    try:
        nltk.data.find(f'tokenizers/punkt_tab/{language}/')
    except LookupError:
        try:
            nltk.download('punkt_tab', quiet=True)
        except:
            # Fallback to old punkt
            try:
                nltk.download('punkt', quiet=True)
            except:
                pass
    
    from nltk.tokenize import sent_tokenize
    
    try:
        # Use NLTK sentence tokenizer
        sentences = sent_tokenize(text, language=language)
    except:
        # Fallback: improved regex-based sentence splitting
        import re
        # Split on sentence endings (. ! ?) followed by whitespace or newline
        # Handle abbreviations and decimal numbers
        pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(pattern, text)
    
    # Clean and filter sentences
    cleaned_sentences = []
    for sent in sentences:
        sent = sent.strip()
        # Remove extra whitespace
        sent = re.sub(r'\s+', ' ', sent)
        
        # Only include sentences that are:
        # - At least 10 characters
        # - Not just whitespace/punctuation
        # - Have at least one letter
        if len(sent) >= 10 and not sent.isspace():
            if any(c.isalpha() for c in sent):
                # Remove leading/trailing punctuation-only parts
                sent = sent.strip('.,;:!?')
                if len(sent) >= 10:
                    cleaned_sentences.append(sent)
    
    return cleaned_sentences


def filter_pair(source: str, target: str, min_length: int = 10, max_length: int = 512) -> bool:
    """Filter translation pairs based on length and quality."""
    # Check length constraints
    if len(source) < min_length or len(target) < min_length:
        return False
    if len(source) > max_length or len(target) > max_length:
        return False
    
    # Check for empty or whitespace-only
    if not source.strip() or not target.strip():
        return False
    
    # Basic quality checks
    # Remove pairs with too many special characters (likely corrupted)
    special_char_ratio_source = len(re.findall(r'[^\w\s]', source)) / len(source) if source else 0
    special_char_ratio_target = len(re.findall(r'[^\w\s]', target)) / len(target) if target else 0
    
    if special_char_ratio_source > 0.5 or special_char_ratio_target > 0.5:
        return False
    
    return True

