"""Text extraction from various file formats."""
import fitz  # PyMuPDF
from docx import Document
import ebooklib
from ebooklib import epub
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def extract_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting PDF {file_path}: {e}")
        raise


def extract_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting DOCX {file_path}: {e}")
        raise


def extract_epub(file_path: str) -> str:
    """Extract text from EPUB file."""
    try:
        book = epub.read_epub(file_path)
        text = ""
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Simple HTML stripping - can be improved
                content = item.get_content().decode('utf-8')
                # Basic HTML tag removal
                import re
                content = re.sub(r'<[^>]+>', '', content)
                text += content + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting EPUB {file_path}: {e}")
        raise


def extract_text(file_path: str) -> Optional[str]:
    """Extract text from file based on extension."""
    file_path_lower = file_path.lower()
    
    if file_path_lower.endswith('.pdf'):
        return extract_pdf(file_path)
    elif file_path_lower.endswith('.docx'):
        return extract_docx(file_path)
    elif file_path_lower.endswith('.epub'):
        return extract_epub(file_path)
    elif file_path_lower.endswith('.txt'):
        # Plain text file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return None
    else:
        logger.warning(f"Unsupported file type: {file_path}")
        return None

