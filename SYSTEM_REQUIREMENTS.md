# System Requirements for Translation AI System

## Overview

This document outlines the hardware and software requirements for running the Translation AI system, including both **inference (translation)** and **training** operations.

---

## 🖥️ Minimum Requirements (Inference Only)

### For Translation/Inference (CPU-based)

**Use Case:** Running the translation service for production use without GPU.

#### Hardware:
- **CPU:** 4+ cores (Intel/AMD x64 or Apple Silicon M1/M2/M3)
- **RAM:** 8 GB minimum, 16 GB recommended
- **Storage:** 10 GB free space (for model files and data)
- **Network:** Stable internet connection (for API calls to OpenAI/Gemini)

#### Software:
- **OS:** Linux, macOS, or Windows
- **Python:** 3.10 or higher
- **PostgreSQL:** 15+ with pgvector extension
- **Node.js:** 18+ (for frontend)

#### Performance:
- **Translation Speed:** ~1-2 sentences/second on CPU
- **Model Size:** ~2.5 GB (base model + LoRA adapters)
- **Memory Usage:** ~4-6 GB during inference

---

## 🚀 Recommended Requirements (Training)

### For Model Training (GPU Recommended)

**Use Case:** Fine-tuning the model with LoRA on your bilingual corpus.

#### Hardware (GPU Training):
- **GPU:** NVIDIA GPU with CUDA support
  - **Minimum:** 8 GB VRAM (e.g., RTX 3060, RTX 3070)
  - **Recommended:** 16+ GB VRAM (e.g., RTX 3090, RTX 4090, A100)
  - **CUDA Compute Capability:** 7.0+ (Volta architecture or newer)
- **CPU:** 8+ cores (Intel/AMD)
- **RAM:** 32 GB minimum, 64 GB recommended
- **Storage:** 50+ GB free space (for models, datasets, checkpoints)
- **Network:** High-speed internet (for downloading models)

#### Hardware (CPU Training - Not Recommended):
- **CPU:** 16+ cores (Intel/AMD x64)
- **RAM:** 64 GB
- **Storage:** 50+ GB
- **Training Time:** 10-50x slower than GPU (days instead of hours)

#### Hardware (Apple Silicon M1/M2/M3):
- **Chip:** M1 Pro/Max/Ultra, M2 Pro/Max/Ultra, or M3 Pro/Max/Ultra
- **Unified Memory:** 32+ GB recommended
- **Storage:** 50+ GB
- **Note:** Uses Metal Performance Shaders (MPS), slower than CUDA but faster than CPU

#### Software:
- **OS:** Linux (recommended), macOS, or Windows with WSL2
- **Python:** 3.10+
- **CUDA:** 11.8+ (for NVIDIA GPUs)
- **cuDNN:** 8.6+ (for NVIDIA GPUs)
- **PyTorch:** 2.1+ with CUDA support

#### Performance (Training):
- **Training Time (GPU):**
  - Small dataset (1K examples): ~30 minutes - 1 hour
  - Medium dataset (10K examples): ~2-4 hours
  - Large dataset (100K examples): ~8-16 hours
- **Training Time (CPU):**
  - Small dataset: ~5-10 hours
  - Medium dataset: ~2-3 days
  - Large dataset: ~1-2 weeks
- **Training Time (Apple Silicon):**
  - Small dataset: ~1-2 hours
  - Medium dataset: ~4-8 hours
  - Large dataset: ~1-2 days

---

## 📊 Detailed Specifications

### Model Specifications

| Component | Size | Memory Usage |
|-----------|------|--------------|
| Base Model (NLLB-200 1.3B) | ~2.5 GB | ~5 GB (inference) |
| LoRA Adapters | ~50-100 MB | ~100 MB |
| Tokenizer | ~10 MB | ~20 MB |
| **Total (Inference)** | **~2.6 GB** | **~5-6 GB** |
| **Total (Training)** | **~2.6 GB** | **~12-16 GB (GPU)** |

### Dataset Size Impact

| Dataset Size | Training Examples | Training Time (RTX 3090) | Storage Needed |
|-------------|-------------------|-------------------------|----------------|
| Small | 1K - 5K | 30 min - 2 hours | 5 GB |
| Medium | 10K - 50K | 2 - 8 hours | 10 GB |
| Large | 100K+ | 8 - 24 hours | 20+ GB |

---

## 🖥️ Server Recommendations

### Production Server (Inference Only)

**For serving translations to multiple users:**

- **CPU:** 8+ cores (Intel Xeon or AMD EPYC)
- **RAM:** 32 GB
- **Storage:** 100 GB SSD
- **GPU:** Optional (NVIDIA T4 or A10 for faster inference)
- **Network:** 1 Gbps
- **OS:** Ubuntu 22.04 LTS or similar

### Training Server

**For periodic model retraining:**

- **GPU:** NVIDIA A100 (40GB) or RTX 4090 (24GB)
- **CPU:** 16+ cores
- **RAM:** 64+ GB
- **Storage:** 500 GB+ NVMe SSD
- **Network:** 10 Gbps (for data transfer)
- **OS:** Ubuntu 22.04 LTS with CUDA 11.8+

---

## ☁️ Cloud Options

### AWS
- **Inference:** EC2 `g4dn.xlarge` (NVIDIA T4, 16 GB RAM) - ~$0.50/hour
- **Training:** EC2 `p3.2xlarge` (NVIDIA V100, 61 GB RAM) - ~$3.00/hour
- **Training:** EC2 `g5.2xlarge` (NVIDIA A10G, 32 GB RAM) - ~$1.00/hour

### Google Cloud
- **Inference:** `n1-standard-4` with T4 GPU - ~$0.35/hour
- **Training:** `n1-standard-8` with V100 GPU - ~$2.50/hour

### Azure
- **Inference:** `Standard_NC6s_v3` (NVIDIA V100) - ~$3.00/hour
- **Training:** `Standard_NC12s_v3` (2x NVIDIA V100) - ~$6.00/hour

### Paperspace / Lambda Labs
- **Training:** RTX 3090 (24GB) - ~$0.50-1.00/hour
- **Training:** A100 (40GB) - ~$1.50-2.00/hour

---

## 🔧 Configuration Parameters

### Training Parameters (Adjustable)

```python
# Batch size (adjust based on GPU memory)
batch_size = 2-8  # Smaller for less VRAM, larger for more VRAM

# Learning rate
learning_rate = 2e-4  # Standard for LoRA

# LoRA parameters
lora_r = 8  # Rank (lower = less memory, less capacity)
lora_alpha = 16  # Scaling factor

# Training epochs
num_epochs = 3  # Usually 3-5 epochs is enough
```

### Memory Optimization Tips

1. **Reduce Batch Size:** If you get OOM (Out of Memory) errors, reduce `batch_size` to 1 or 2
2. **Use Gradient Accumulation:** Simulate larger batch sizes without more memory
3. **Use Mixed Precision:** `fp16=True` (already enabled for CUDA)
4. **Clear Cache:** Use `torch.cuda.empty_cache()` between batches

---

## 📝 Platform-Specific Notes

### Apple Silicon (M1/M2/M3)

- ✅ **Works for inference and training**
- ⚠️ **Slower than NVIDIA GPUs** but faster than CPU
- ⚠️ **pin_memory warning:** Automatically disabled (no action needed)
- **Memory:** Uses unified memory (RAM + VRAM combined)
- **PyTorch:** Install with MPS support: `pip install torch torchvision torchaudio`

### NVIDIA GPUs

- ✅ **Best performance for training**
- **CUDA:** Required version 11.8+
- **Driver:** Latest NVIDIA drivers
- **Memory:** Check VRAM with `nvidia-smi`

### CPU-Only

- ⚠️ **Very slow for training** (not recommended)
- ✅ **Fine for inference** (acceptable speed)
- **Use:** Only if GPU is not available

---

## 🚀 Quick Start Commands

### Check Your System

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Check GPU (NVIDIA)
nvidia-smi

# Check GPU (Apple Silicon)
system_profiler SPDisplaysDataType

# Check PyTorch CUDA
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python3 -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

### Test Training Speed

```bash
# Small test training
python3 ml/training/train_lora.py \
  --train-data data/processed/retrain_combined_train.jsonl \
  --val-data data/processed/retrain_combined_val.jsonl \
  --output-dir outputs/test_training \
  --epochs 1 \
  --batch-size 2
```

---

## 📈 Performance Benchmarks

### Inference Speed (sentences/second)

| Hardware | Speed |
|----------|-------|
| CPU (Intel i7-12700K) | 1-2 sentences/sec |
| CPU (Apple M2) | 2-3 sentences/sec |
| GPU (RTX 3060) | 10-15 sentences/sec |
| GPU (RTX 4090) | 30-50 sentences/sec |
| GPU (A100) | 50-100 sentences/sec |

### Training Speed (examples/second)

| Hardware | Speed |
|----------|-------|
| CPU (16 cores) | 0.5-1 examples/sec |
| Apple M2 Max | 2-3 examples/sec |
| RTX 3060 (12GB) | 5-8 examples/sec |
| RTX 3090 (24GB) | 10-15 examples/sec |
| A100 (40GB) | 20-30 examples/sec |

---

## 💡 Recommendations

### For Development/Testing
- **Use:** Your local machine (CPU or Apple Silicon)
- **Training:** Use cloud GPU (Paperspace, Lambda Labs) for training
- **Inference:** Local CPU is fine

### For Production
- **Inference Server:** Dedicated server with optional GPU
- **Training:** Separate GPU server or cloud instance
- **Database:** Dedicated PostgreSQL server with pgvector

### For Large-Scale Deployment
- **Load Balancer:** Multiple inference servers
- **Training:** Dedicated GPU cluster
- **Database:** PostgreSQL cluster with replication

---

## ❓ FAQ

**Q: Can I train on CPU?**  
A: Yes, but it's 10-50x slower. Only recommended for very small datasets (< 1K examples).

**Q: Do I need a GPU for inference?**  
A: No, CPU works fine. GPU speeds up inference 5-10x but is optional.

**Q: How much VRAM do I need?**  
A: Minimum 8GB for training, 16GB+ recommended. For inference, CPU RAM is sufficient.

**Q: Can I use Apple Silicon for training?**  
A: Yes, but it's slower than NVIDIA GPUs. Good for small-medium datasets.

**Q: How long does training take?**  
A: Depends on dataset size and hardware. See "Performance" section above.

---

## 📚 Additional Resources

- [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)
- [CUDA Installation](https://developer.nvidia.com/cuda-downloads)
- [PostgreSQL with pgvector](https://github.com/pgvector/pgvector)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)

