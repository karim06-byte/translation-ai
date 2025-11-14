"""Main data preparation pipeline."""
import json
import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ml.data_prep.extractors import extract_text
from ml.data_prep.cleaning import clean_text, normalize_azerbaijani, sentence_tokenize, filter_pair
from ml.data_prep.alignment import align_sentences

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_book_pair(
    source_file: str,
    target_file: str,
    book_id: str,
    alignment_method: str = 'simple'
) -> List[dict]:
    """
    Process a pair of source and target books.
    
    Returns:
        List of dictionaries with 'id', 'en', 'az' keys
    """
    logger.info(f"Processing book pair: {source_file} -> {target_file}")
    
    # Extract text
    source_text = extract_text(source_file)
    target_text = extract_text(target_file)
    
    if not source_text or not target_text:
        logger.error(f"Failed to extract text from files")
        return []
    
    # Clean text
    source_text = clean_text(source_text)
    target_text = clean_text(target_text)
    
    # Normalize Azerbaijani
    target_text = normalize_azerbaijani(target_text)
    
    # Tokenize into sentences
    source_sentences = sentence_tokenize(source_text, language='en')
    target_sentences = sentence_tokenize(target_text, language='az')
    
    logger.info(f"Extracted {len(source_sentences)} source and {len(target_sentences)} target sentences")
    
    # Align sentences
    aligned_pairs = align_sentences(source_sentences, target_sentences, method=alignment_method)
    
    logger.info(f"Aligned {len(aligned_pairs)} sentence pairs")
    
    # Create JSONL entries
    entries = []
    for idx, (source, target) in enumerate(aligned_pairs):
        # Filter pairs
        if not filter_pair(source, target):
            continue
        
        entry = {
            "id": f"{book_id}_{idx:06d}",
            "en": source,
            "az": target
        }
        entries.append(entry)
    
    logger.info(f"Created {len(entries)} valid translation pairs")
    return entries


def save_jsonl(entries: List[dict], output_path: str):
    """Save entries to JSONL file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    logger.info(f"Saved {len(entries)} entries to {output_path}")


def split_dataset(
    jsonl_path: str,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1
):
    """Split JSONL dataset into train/val/test."""
    # Read all entries
    entries = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            entries.append(json.loads(line.strip()))
    
    # Shuffle
    import random
    random.seed(42)
    random.shuffle(entries)
    
    # Calculate splits
    total = len(entries)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)
    
    train_entries = entries[:train_end]
    val_entries = entries[train_end:val_end]
    test_entries = entries[val_end:]
    
    # Save splits
    base_path = os.path.splitext(jsonl_path)[0]
    save_jsonl(train_entries, f"{base_path}_train.jsonl")
    save_jsonl(val_entries, f"{base_path}_val.jsonl")
    save_jsonl(test_entries, f"{base_path}_test.jsonl")
    
    logger.info(f"Split dataset: train={len(train_entries)}, val={len(val_entries)}, test={len(test_entries)}")


def process_directory(
    input_dir: str,
    output_dir: str,
    alignment_method: str = 'simple'
):
    """
    Process all book pairs in a directory.
    
    Expected structure:
    input_dir/
        book1_en.pdf
        book1_az.pdf
        book2_en.docx
        book2_az.docx
        ...
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all source files
    source_files = {}
    for file in input_path.iterdir():
        if file.is_file():
            name_lower = file.stem.lower()
            if name_lower.endswith('_en') or name_lower.endswith('_ing'):
                book_id = name_lower.rsplit('_', 1)[0]
                if book_id not in source_files:
                    source_files[book_id] = {}
                source_files[book_id]['source'] = str(file)
            elif name_lower.endswith('_az') or name_lower.endswith('_aze'):
                book_id = name_lower.rsplit('_', 1)[0]
                if book_id not in source_files:
                    source_files[book_id] = {}
                source_files[book_id]['target'] = str(file)
    
    # Process each book pair
    all_entries = []
    for book_id, files in source_files.items():
        if 'source' in files and 'target' in files:
            entries = process_book_pair(
                files['source'],
                files['target'],
                book_id,
                alignment_method
            )
            all_entries.extend(entries)
        else:
            logger.warning(f"Incomplete pair for book {book_id}")
    
    # Save combined JSONL
    combined_path = output_path / "combined.jsonl"
    save_jsonl(all_entries, str(combined_path))
    
    # Split dataset
    split_dataset(str(combined_path))
    
    logger.info(f"Processing complete. Total entries: {len(all_entries)}")


def main():
    parser = argparse.ArgumentParser(description="Data preparation pipeline")
    parser.add_argument("--input-dir", required=True, help="Input directory with book pairs")
    parser.add_argument("--output-dir", required=True, help="Output directory for processed data")
    parser.add_argument("--alignment", default="simple", choices=["simple", "bleualign"],
                       help="Alignment method")
    
    args = parser.parse_args()
    
    process_directory(args.input_dir, args.output_dir, args.alignment)


if __name__ == "__main__":
    main()

