# Translation AI Model Information

## Base Model

**Model Name:** `facebook/nllb-200-distilled-1.3B`

**Full Name:** NLLB-200 (No Language Left Behind) Distilled 1.3B

**Model Type:** Sequence-to-Sequence (Seq2Seq) Language Model

**Architecture:** Transformer-based encoder-decoder

**Parameters:** 1.3 Billion

**Source:** Meta AI (Facebook)

**Hugging Face Hub:** https://huggingface.co/facebook/nllb-200-distilled-1.3B

---

## Fine-Tuning Method

**Method:** LoRA (Low-Rank Adaptation)

**PEFT Library:** PEFT (Parameter-Efficient Fine-Tuning) v0.17.1

**LoRA Configuration:**
- **Rank (r):** 8
- **LoRA Alpha:** 16
- **LoRA Dropout:** 0.05
- **Target Modules:** 
  - `q_proj` (Query projection)
  - `k_proj` (Key projection)
  - `v_proj` (Value projection)
  - `out_proj` (Output projection)
- **Task Type:** SEQ_2_SEQ_LM (Sequence-to-Sequence Language Modeling)
- **Bias:** None

**Fine-Tuned Model Path:** `outputs/nllb_finetuned_v1/`

---

## Technology Stack

### Core ML Libraries

1. **Transformers** (v4.57.1)
   - Library: Hugging Face Transformers
   - Purpose: Model loading, tokenization, and inference
   - Used for: AutoTokenizer, AutoModelForSeq2SeqLM

2. **PyTorch** (v2.9.1)
   - Library: PyTorch
   - Purpose: Deep learning framework
   - Used for: Model computation, tensor operations

3. **PEFT** (v0.17.1)
   - Library: Parameter-Efficient Fine-Tuning
   - Purpose: LoRA adapters for efficient fine-tuning
   - Used for: PeftModel, LoraConfig, get_peft_model

4. **Datasets** (≥2.14.0)
   - Library: Hugging Face Datasets
   - Purpose: Data loading and preprocessing

5. **Accelerate** (≥0.24.0)
   - Library: Hugging Face Accelerate
   - Purpose: Training acceleration and optimization

### Tokenization

- **Tokenizer:** NllbTokenizer (NLLB Tokenizer)
- **Source Language Code:** `eng_Latn` (English Latin script)
- **Target Language Code:** `azj_Latn` (Azerbaijani Latin script)
- **Vocabulary Size:** 256,204 tokens
- **SentencePiece Model:** Used for subword tokenization

### Additional Libraries

- **sacrebleu** (≥2.3.1): BLEU score calculation
- **sentence-transformers** (≥2.2.2): Sentence embeddings for style similarity
- **sentencepiece** (≥0.1.99): Subword tokenization
- **nltk** (≥3.8.1): Natural language processing utilities

---

## Model Details

### Language Support

- **Source:** English (eng_Latn)
- **Target:** Azerbaijani (azj_Latn)
- **Note:** NLLB-200 supports 200+ languages

### Model Architecture

- **Type:** Encoder-Decoder Transformer
- **Base Model:** Distilled version of larger NLLB-200 model
- **Distillation:** Knowledge distillation from larger model (3.3B or 54.5B)

### Fine-Tuning Process

1. **Base Model:** Load `facebook/nllb-200-distilled-1.3B`
2. **LoRA Setup:** Add LoRA adapters to attention layers
3. **Training:** Fine-tune on English→Azerbaijani parallel corpus
4. **Output:** LoRA adapters saved in `outputs/nllb_finetuned_v1/`

### Inference Configuration

- **Device:** CUDA (if available) or CPU
- **Data Type:** float16 (CUDA) or float32 (CPU)
- **Generation Parameters:**
  - `max_length`: 256
  - `num_beams`: 4
  - `early_stopping`: True
  - `forced_bos_token_id`: 256020 (azj_Latn token ID)

---

## File Structure

```
outputs/nllb_finetuned_v1/
├── adapter_config.json      # LoRA configuration
├── adapter_model.bin        # LoRA adapter weights
├── tokenizer_config.json     # Tokenizer configuration
├── sentencepiece.bpe.model   # SentencePiece model
└── README.md                 # Model card
```

---

## Usage

The model is used in `backend/services/translation.py`:

```python
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel

# Load base model
base_model = AutoModelForSeq2SeqLM.from_pretrained(
    "facebook/nllb-200-distilled-1.3B"
)

# Load LoRA adapters
model = PeftModel.from_pretrained(
    base_model, 
    "outputs/nllb_finetuned_v1"
)
```

---

## References

- **NLLB Paper:** "No Language Left Behind: Scaling Human-Centered Machine Translation"
- **LoRA Paper:** "LoRA: Low-Rank Adaptation of Large Language Models"
- **Hugging Face Model Card:** https://huggingface.co/facebook/nllb-200-distilled-1.3B

