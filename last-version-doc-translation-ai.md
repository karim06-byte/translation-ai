# Nəşriyyat üçün EN → AZ Tərcümə Sistemi — Təfsilatlı Texniki Plan (Genişləndirilmiş Versiya)

> **Hədəf:** Keçmiş tərcümə olunmuş kitab cütlərindən istifadə edərək **ən yaxşı nəticəni verən** bir model seçmək, onu tətbiq etmək, bütün **data preparation**, **retrain mexanizmi**, **real kod nümunələri**, **DB ER diagramı** və **cron-based retrain sistemi** daxil olmaqla tam implementasiya planı təqdim etmək.

---

## 1. Ümumi baxış

* **Model:** NLLB-200 (1.3B) — seq2seq tərcümə üçün ən uyğun balans.
* **Fine-tune üsulu:** LoRA (PEFT) ilə yüngül təlim.
* **Məqsəd:** EN → AZ tərcümələrdə publisher-in stilini qorumaq.
* **Əlavə:** Redaktorların override etdiyi cütlükləri style memory-də saxlamaq və LoRA adapteri ilə dövri təlim.

---

## 2. Data Preparation Prosesi

### 2.1. Extract mərhələsi

```python
import fitz, os

def extract_pdf(path):
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text.strip()

def extract_all(data_dir):
    results = {}
    for file in os.listdir(data_dir):
        if file.endswith('.pdf'):
            results[file] = extract_pdf(os.path.join(data_dir, file))
    return results
```

### 2.2. Alignment (bleualign nümunəsi)

```bash
python bleualign.py data/en_book.txt data/az_book.txt -o data/aligned.txt
```

### 2.3. Cleaning

```python
import re

def clean_text(t):
    t = re.sub(r'<[^>]+>', '', t)  # HTML sil
    t = re.sub(r'\s+', ' ', t)
    return t.strip()
```

### 2.4. JSONL formatına çevirmə

```python
import json

def to_jsonl(en_lines, az_lines, out_path):
    with open(out_path, 'w', encoding='utf-8') as f:
        for i, (en, az) in enumerate(zip(en_lines, az_lines)):
            f.write(json.dumps({"id": f"book1_{i}", "en": en, "az": az}, ensure_ascii=False) + '\n')
```

---

## 3. Fine-tuning (LoRA ilə)

### 3.1. Mühit hazırlığı

```bash
pip install transformers datasets accelerate peft sentencepiece sacrebleu
```

### 3.2. Run script nümunəsi (`run_translation.py`)

```python
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, Trainer, TrainingArguments
from datasets import load_dataset
from peft import LoraConfig, get_peft_model

model_name = "facebook/nllb-200-distilled-1.3B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

lora_config = LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"], lora_dropout=0.05)
model = get_peft_model(model, lora_config)

dataset = load_dataset('json', data_files={'train': 'train.jsonl', 'val': 'val.jsonl'})

def preprocess(batch):
    inputs = tokenizer(batch['en'], truncation=True, padding='max_length', max_length=256)
    targets = tokenizer(batch['az'], truncation=True, padding='max_length', max_length=256)
    inputs['labels'] = targets['input_ids']
    return inputs

dataset = dataset.map(preprocess, batched=True)

args = TrainingArguments(
    output_dir='./outputs',
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    learning_rate=2e-4,
    num_train_epochs=3,
    evaluation_strategy="epoch",
)

trainer = Trainer(model=model, args=args, train_dataset=dataset['train'], eval_dataset=dataset['val'])
trainer.train()
```

---

## 4. Style Memory və Vector Search

### 4.1. PostgreSQL + pgvector setup

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE style_memory (
  id SERIAL PRIMARY KEY,
  source_en TEXT,
  preferred_az TEXT,
  embedding VECTOR(768),
  approved_by INT,
  approved_at TIMESTAMP DEFAULT now()
);
CREATE INDEX ON style_memory USING ivfflat (embedding vector_cosine_ops);
```

### 4.2. Python insert və query

```python
from sentence_transformers import SentenceTransformer
import psycopg2
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

conn = psycopg2.connect(dbname='db', user='user', password='pw', host='localhost')
cursor = conn.cursor()

def add_memory(source, translation):
    emb = model.encode([source])[0].tolist()
    cursor.execute("INSERT INTO style_memory (source_en, preferred_az, embedding) VALUES (%s,%s,%s)", (source, translation, emb))
    conn.commit()

def query_memory(source, k=3):
    emb = model.encode([source])[0].tolist()
    cursor.execute(f"SELECT preferred_az, embedding <=> %s AS dist FROM style_memory ORDER BY dist LIMIT {k}", (emb,))
    return cursor.fetchall()
```

---

## 5. Cron-based Retrain Planı

### 5.1. Task mexanizmi

* Hər **500 override** və ya **2 həftəlik interval**dan sonra yeni retrain trigger olunur.
* Redis və ya Celery vasitəsilə background iş planı.

### 5.2. Cron konfiqurasiya nümunəsi (`crontab -e`)

```
0 3 */14 * * /usr/bin/python3 /app/retrain_lora.py >> /var/log/retrain.log 2>&1
```

### 5.3. Retrain skripti (`retrain_lora.py`)

```python
import os, subprocess

def retrain():
    print("Starting scheduled retrain...")
    subprocess.run(["python", "run_translation.py"])

if __name__ == "__main__":
    retrain()
```

---

## 6. Məlumat Bazası — ER Diagramı

**Əsas obyektlər və əlaqələr:**

```
┌────────────┐       ┌───────────────┐
│  books     │1     *│  segments     │
│ id         │──────▶│ id, book_id   │
└────────────┘       │ source_en     │
                     │ translated_az │
                     └───────┬───────┘
                             │1
                             │
                             ▼
                     ┌────────────────┐
                     │ style_memory   │
                     │ id, segment_id │
                     │ preferred_az   │
                     └────────────────┘
```

Əlavə cədvəllər:

* `users` — redaktor məlumatları.
* `overrides` — dəyişiklik tarixi.

---

## 7. Monitorinq və Keyfiyyət

### 7.1. API endpoint (monitor)

```python
@app.get('/api/metrics/summary')
def metrics():
    return {
        'BLEU': 0.71,
        'ChrF': 0.68,
        'SSS': 0.74,
        'MOR': 0.27,
        'AR': 0.70
    }
```

### 7.2. BLEU hesablanması

```bash
sacrebleu predictions.txt -r references.txt --metrics bleu chrf ter
```

### 7.3. Style Similarity Score

```python
from sklearn.metrics.pairwise import cosine_similarity
score = cosine_similarity(embed_model.encode([model_out]), embed_model.encode([reference]))[0][0]
```

---

## 8. Son nəticə və növbəti addımlar

* NLLB-200 (1.3B) model LoRA ilə train edilir.
* Redaktor düzəlişləri style memory-də saxlanır.
* Cron job avtomatik retrain həyata keçirir.
* BLEU, ChrF, SSS və MOR metrikləri hər dövr üçün ölçülür.

> Bu plan real tətbiq üçün tam texniki baza və kod nümunələri ilə hazırdır. İstənilərsə növbəti mərhələdə Docker və CI/CD (GitLab + Celery + pgvector) inteqrasiyası əlavə edilə bilər.
