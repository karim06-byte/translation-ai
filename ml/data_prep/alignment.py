"""Sentence alignment utilities."""
import logging
from typing import List, Tuple, Optional
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)


def simple_length_based_alignment(
    source_sentences: List[str],
    target_sentences: List[str],
    max_ratio: float = 3.0
) -> List[Tuple[int, int]]:
    """
    Simple length-based sentence alignment.
    Returns list of (source_idx, target_idx) pairs.
    """
    alignments = []
    source_idx = 0
    target_idx = 0
    
    while source_idx < len(source_sentences) and target_idx < len(target_sentences):
        source_len = len(source_sentences[source_idx])
        target_len = len(target_sentences[target_idx])
        
        # Calculate length ratio
        if source_len > 0:
            ratio = target_len / source_len
        else:
            ratio = 1.0
        
        # If ratio is reasonable, align
        if 0.3 <= ratio <= max_ratio:
            alignments.append((source_idx, target_idx))
            source_idx += 1
            target_idx += 1
        elif ratio < 0.3:
            # Target is too short, skip it
            target_idx += 1
        else:
            # Target is too long, try to match with next source
            source_idx += 1
    
    return alignments


def bleualign_alignment(
    source_file: str,
    target_file: str,
    output_file: Optional[str] = None
) -> List[Tuple[str, str]]:
    """
    Use bleualign for sentence alignment.
    Requires bleualign to be installed from GitHub:
    pip install git+https://github.com/rsennrich/Bleualign.git
    """
    try:
        # Try to import bleualign
        try:
            import bleualign
        except ImportError:
            logger.warning("bleualign not installed. Install with: pip install git+https://github.com/rsennrich/Bleualign.git")
            return []
    except Exception as e:
        logger.error(f"Error importing bleualign: {e}")
        return []
    
    try:
        if output_file is None:
            output_file = tempfile.mktemp(suffix='.txt')
        
        # Run bleualign
        cmd = [
            'python', '-m', 'bleualign.align',
            source_file,
            target_file,
            '-o', output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Read aligned pairs
        pairs = []
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    pairs.append((parts[0], parts[1]))
        
        return pairs
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Bleualign failed: {e.stderr}")
        return []
    except Exception as e:
        logger.error(f"Error in bleualign alignment: {e}")
        return []


def align_sentences(
    source_sentences: List[str],
    target_sentences: List[str],
    method: str = 'simple'
) -> List[Tuple[str, str]]:
    """
    Align source and target sentences.
    
    Args:
        source_sentences: List of source language sentences
        target_sentences: List of target language sentences
        method: 'simple' or 'bleualign'
    
    Returns:
        List of (source, target) aligned pairs
    """
    if method == 'simple':
        alignments = simple_length_based_alignment(source_sentences, target_sentences)
        pairs = [(source_sentences[i], target_sentences[j]) for i, j in alignments]
        return pairs
    
    elif method == 'bleualign':
        # Check if bleualign is available
        try:
            import bleualign
        except ImportError:
            logger.warning("bleualign not installed. Falling back to simple alignment method.")
            logger.info("To install bleualign: pip install git+https://github.com/rsennrich/Bleualign.git")
            # Fall back to simple method
            alignments = simple_length_based_alignment(source_sentences, target_sentences)
            pairs = [(source_sentences[i], target_sentences[j]) for i, j in alignments]
            return pairs
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as src_file:
            src_file.write('\n'.join(source_sentences))
            src_path = src_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tgt_file:
            tgt_file.write('\n'.join(target_sentences))
            tgt_path = tgt_file.name
        
        try:
            pairs = bleualign_alignment(src_path, tgt_path)
            if not pairs:  # If bleualign failed, fall back to simple
                logger.warning("bleualign returned no results, falling back to simple alignment")
                alignments = simple_length_based_alignment(source_sentences, target_sentences)
                pairs = [(source_sentences[i], target_sentences[j]) for i, j in alignments]
            return pairs
        finally:
            # Cleanup
            if os.path.exists(src_path):
                os.unlink(src_path)
            if os.path.exists(tgt_path):
                os.unlink(tgt_path)
    
    else:
        raise ValueError(f"Unknown alignment method: {method}")

