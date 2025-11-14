# Nəşriyyat üçün EN → AZ Tərcümə Sistemi — Təfsilatlı Texniki Plan

> **Hədəf:** Keçmiş tərcümə olunmuş kitab cütlərindən istifadə edərək **ən yaxşı nəticəni verən** bir model seçmək, onu tətbiq etmək, bütün **data preparation** prosesini göstərmək və sistem üçün lazımi metrikləri təmin edən tam implementasiya planı hazırlamaq.

---

## 1. Qısa xülasə (TL;DR)

* **Seçilmiş model:** **NLLB-200 (1.3B)** — ən yaxşı balans: yüksək keyfiyyət, çoxdilli dəstək və fine-tune üçün uyğundur.
* **Əsas yanaşma:** Seq2seq fine-tuning (EN→AZ) üzərində işləmək; redaktor düzəlişlərini saxlamaq üçün **style-memory** + embedding re-ranking; yüngül, resurs qənaətli yenilənmələr üçün **PEFT (LoRA / Adapters)** istifadə etmək.
* **Metriklər:** BLEU, ChrF, TER, Cosine similarity (sentence embeddings), Style Similarity Score, Manual Override Rate, Attribution Ratio.
* **Data pipeline:** PDF/DOCX → text extraction → sentence alignment (bleualign/hunalign) → cleaning → normalization → tokenization (sentencepiece) → JSONL (en/az) → split train/val/test.

---

## 2. Niyə **NLLB-200 (1.3B)**?

* **Keyfiyyət:** NLLB çoxdilli tərcümə üçün state-of-the-art nəticələr göstərib; xüsusən azərbaycan dili kimi resursu nisbətən az dillər üçün yaxşı ümumi performans.
* **Çeviklik:** Hugging Face mühiti ilə asan fine-tune etmək mümkündür.
* **Resurs/Performans balansı:** 1.3B modeli praktik olaraq daha yüksək modelə nisbətən daha az resurs tələb edir, eyni zamanda 600M-dən daha yaxşı nəticə verir.
* **Uyğunluq:** seq2seq task üçün ideal (EN→AZ) — həm direkt tərcümə, həm də style-conditioning üçün istifadə etmək mümkündür.

> Qeyd: Əgər komanda çox böyük GPU-lara malikdirsə, 3.3B variantı da nəzərdən keçirilə bilər. Lakin sən dediyin kimi sürət prioritet deyil, keyfiyyət və metriklər daha vacibdir — 1.3B yaxşı kompromisdir.

---

## 3. Data Preparation — Tam addım-addım

### 3.1. Mənbələr

* Nəşriyyatın bütün **ingilis** və **azərbaycan** versiyalı kitabları (PDF/DOCX/EPUB). Hər kitab üçün mümkün qədər meta (müəllif, nəşr ili, bölüm) saxlanılmalıdır.
* Kiçik ölçüdə “xarici” tərcümə seti (məsələn OPUS) müqayisə üçün.

### 3.2. Fayl → Mətn çıxarılması

* **Alətlər:** `pdfminer.six`, `pymupdf` (fitz), `textract` (DOCX), `ebooklib` (EPUB)
* **Addım:** hər kitab üçün səhifə və bölmə səviyyəsində xam mətn çıxart.

**Pseudocode:**

```
for file in uploads:
    if file.endswith('.pdf'):
        text = extract_pdf(file)  # pymupdf yoki pdfminer
    elif file.endswith('.docx'):
        text = extract_docx(file)
    save_raw_text(book_id, text)
```

### 3.3. Bölmə və Cümlə səviyyəsində align (alignment)

* **Məqsəd:** eyni məna daşıyan cümlələri ingilis-azərbaycanca cütləmək.
* **Alətlər:** `bleualign`, `hunalign`, `eflomal` (word alignment), `fast_align`.

**Workflow:**

1. Kitab bölümlərini və paragrafları approx. uyğunlaşdır.
2. Paragraf → cümlə bölmə (sentence segmentation) (NLP toolkits `nltk`/`spacy` for EN, AZ üçün custom rule-based).
3. `bleualign` və ya `hunalign` ilə cümlə-cümlə align.

**Praktik nümunə:**

```bash
# example with bleualign
python bleualign.py az_sentences.txt en_sentences.txt > aligned_pairs.txt
```

### 3.4. Cleaning & Normalization

* HTML tag-ları, çoxlu boşluqlar, qeyri-utf8 simvollar, koda düşən başlıqlar təmizlənməlidir.
* Azərbaycan dili üçün Unicode normalizasiyası (NFKC).
* Mümkün səhv transliteration və ya OCR səhvlərini filterlə.

**Qaydalar:**

* Min / max token say limitləri (məsələn, < 512 token).
* Qeyri-məntiqi cütlüklər (ən az 70% lexic overlap yoxdursa) manual review.

### 3.5. Tokenization

* **Approach:** `sentencepiece` (BPE) və ya Hugging Face `transformers` tokenizer (NLLB tokenizers uyğunlaşdırmaq lazımdır).
* Əgər öz tokenizer qurulursa, bütün dataset-ə `sentencepiece` tətbiq et (vocab 32k–50k).

### 3.6. Format & Split

* Hər sətri JSONL:

```json
{"id":"book1_000123","en":"The sun rises in the east.","az":"Günəş şərqdən doğur."}
```

* Split: `train: 85%`, `validation: 10%`, `test: 5%` (və ya 80/10/10).

---

## 4. Model Fine-tuning (NLLB-200 1.3B) — Praktik addımlar

> **Nəzərə al:** Tam fine-tuning böyük resurs tələb edir. Biz **PEFT (LoRA / adapters)** tövsiyə edirik ki, style adaptation və incremental updates CPU/az GPU ilə də idarə olunsun.

### 4.1. Mühit və asılılıqlar

* Python 3.10+, `transformers`, `datasets`, `accelerate`, `peft`, `sentencepiece`, `sacrebleu`, `sentence-transformers`, `faiss`/`pgvector`.

```bash
pip install transformers datasets accelerate peft sentencepiece sacrebleu sentence-transformers faiss-cpu
```

### 4.2. DataLoader və Dataset

* Hugging Face `datasets`-ə JSONL yüklə və `map()` ilə tokenizasiya et.

### 4.3. LoRA ilə fine-tuning (PEFT)

* LoRA ilə yalnız müəyyən qatları adaptasiya edərək yaddaş və compute qənaəti əldə et.

**Pseudo-command:**

```bash
# bu bir high-level nümunədir
python run_translation.py \
  --model facebook/nllb-200-distilled-1.3B \
  --dataset-path ./data/jsonl \
  --output-dir ./outputs/nllb_finetuned \
  --peft lora \
  --batch-size 16 \
  --epochs 3 \
  --fp16 False
```

### 4.4. Checkpoints və versiyalar

* Hər retrain mərhələsində versiya yarat (v1, v1.1, v2).
* Redaktor düzəlişləri toplandıqca LoRA adapterini retrain et.

---

## 5. Style Memory və Runtime İnferens — Implementation detalları

### 5.1. Style Memory nədir?

* Redaktorların override etdiyi cütlüklərin (source + approved_translation) embedding-ləri saxlanılır. Bu baza `pgvector` (Postgres + vector extension) və ya `Faiss` ola bilər.
* Hər yeni source üçün infer zamanı:

  1. source embedding hesabla,
  2. memory-də nearest neighbor axtar (cosine),
  3. əgər similarity > `T_style` (məs. 0.80) → həmin preferred translation prioritetlə re-rank et və nəticəni o istiqamətdə transformasiya et.

### 5.2. Embedding modeli

* `sentence-transformers` (məs. `paraphrase-multilingual-MiniLM-L12-v2` və ya `LaBSE`).

### 5.3. Re-ranking nümunəsi (pseudo):

```python
# infer pipeline (high level)
src = "The sun rises in the east."
# 1. model_trans = translate_with_nllb(src)
# 2. src_emb = embed(src)
# 3. top_k = query_style_memory(src_emb, k=5)
# 4. if top_k[0].score > 0.80:
#      use top_k[0].preferred_translation as bias / template
#    else:
#      use model_trans
```

### 5.4. Override flow

* Redaktor override-edən zaman backend: yeni cütlüyü `approved` flag ilə `style_memory`-yə yazır.
* Async worker: bu yeni cütlüyü LoRA fine-tuning bufferına əlavə edir. Hər N (məs. 500) yeni approved dəyişiklikdə retrain triggerlənir.

---

## 6. Evaluation Metrikləri — Tam siyahı və necə hesablamaq

### 6.1. Core translation metrics

* **BLEU** (`sacrebleu`) — ən çox istifadə olunan metric.
* **ChrF** — morfoloji dillər üçün daha etibarlı.
* **TER** — nə qədər edit tələb olunur.

**Hesablama:**

```bash
sacrebleu -t "path/to/hypotheses.txt" -r "path/to/references.txt" --metrics bleu chrf ter
```

### 6.2. Style & Attribution metrics

* **Cosine similarity (sentence embeddings)** — model çıxışı ilə publisher-approved translations arasındakı oxşarlıq.

  * Hesablama: `cosine(encode(hyp), encode(approved_reference))`.
* **Style Similarity Score (SSS)** — ortalama cosine similarity across test set with nearest style memory neighbor.

  * `SSS = mean(cosine(hyp_i, best_style_ref_i))`.
* **Manual Override Rate (MOR)** — redaktorların neçə % hallarda nəticəni override etdiyini göstərir: `MOR = overrides / total_segments`.
* **Attribution Ratio (AR)** — hər çıxış üçün memory vs model-origin score. Sadə yanaşma:

  * `AR = (sim_to_style_memory) / (sim_to_external_corpus + sim_to_style_memory)` → normalize edib % şəklində ver.

### 6.3. Nutuq səviyyəli metriklər (linguistic consistency)

* **Terminology Preservation Rate** — quraşdırılmış terminology glossary-dən xüsusi terminlərin düzgün istifadə nisbəti.
* **Sentence Length Distribution Similarity** — Kullback-Leibler divergence ilə model və publisher distributions müqayisəsi.

---

## 7. Məlumat Bazası Dizaynı (ER xülasəsi)

**Əsas cədvəllər:**

1. `books` — kitab metadata (id, title_en, title_az, author, year)
2. `segments` — hər cümlə/paragraf (id, book_id, segment_index, source_en, translated_az, status, created_at)
3. `style_memory` — approved overrides (id, segment_id, source_en, preferred_az, embedding_vector, approved_by, approved_at)
4. `users` — redaktorlar
5. `overrides` — tarixçələr (id, segment_id, old_translation, new_translation, user_id, engine, created_at)

**Vektor sahəsi:** `style_memory.embedding_vector` → `pgvector` column (float[]) və index ilə.

---

## 8. API Endpoints — Minimal spec

### Auth

* `POST /api/login` → token

### Upload & Processing

* `POST /api/books` → upload file
* `GET /api/books/{book_id}/segments` → get paginated segments

### Translation

* `POST /api/translate` `{source_en, segment_id?}` → returns translated_az + style_hint
* `POST /api/translate/retranslate` `{segment_id, engine: [gpt|gemini]}` → calls LLM API and returns new translation

### Override & Style Memory

* `POST /api/segments/{id}/override` `{new_translation, user_id, engine}` → saves override to `overrides` and inserts into `style_memory` (embedding async)
* `GET /api/style_memory/nearest` `{source_en, k}` → returns top-k style matches

### Metrics

* `GET /api/metrics/summary` → returns BLEU, ChrF, SSS, MOR, AR for requested period

---

## 9. Retraining Strategy & Schedule

* **Buffering:** hər `N=500` approved overrides → schedule small LoRA retrain.
* **Validation:** retrain-da validation set-i saxla (keçmiş human-reviewed segments).
* **Canary testing:** yeni model deploy etməzdən əvvəl `shadow` rejimində 2 həftə test et; MOR və BLEU monitor et.
* **Rollback:** əgər MOR artarsa və ya BLEU düşərsə → rollback.

---

## 10. Monitoring və QA

* **Dashboard:** BLEU, ChrF, SSS, MOR, AR hər gün/ay üzrə trend.
* **Alert:** BLEU düşdükdə 10%+ və ya MOR 5% artış.
* **Manual spot-check:** 100 random segments weekly human review.

---

## 11. Praktik nümunələr (komanda və kod parçaları)

**a) JSONL data nümunəsi**

```json
{"id":"book1_000123","en":"The sun rises in the east.","az":"Günəş şərqdən doğur."}
```

**b) sacrebleu çağırışı**

```
sacrebleu predictions.txt -r references.txt --metrics bleu chrf ter
```

**c) embedding-based nearest neighbor pseudocode**

```python
src_emb = embed(src_text)
neighbors = pgvector_query(src_emb, top_k=5)
if neighbors[0].score > 0.80:
    use neighbors[0].preferred_translation
else:
    use model_translation
```

---

## 12. Risklər və Mitigasiya

* **Risk:** Alignment səhvləri → *Mitigasiya:* manual sample check + threshold filtering.
* **Risk:** Overfitting to small dataset → *Mitigasiya:* regularization, validation, early stopping.
* **Risk:** Redaktorların inconsistent overrides (fərqli stillər) → *Mitigasiya:* style guidelines + editor training + voting (majority).

---

## 13. Növbəti addımlar (Action items)

1. Raw kitab fayllarını topla və indexlə.
2. Text extraction skriptini işə sal və 1 kitabı tam pipeline ilə keç.
3. Alignment və cleaning sonrası `1000` keyfiyyətli cüt yarat və toy training et (smaller subset).
4. İlk LoRA fine-tune və test.
5. UI + override prototipi və style memory test.
6. Ölç və nəticələri Rasim müəllimə təqdim et.

---

## 14. Əlavə qeydlər

* Əgər sən GPU resursu təmin edə bilsən, retrain sürəti və model ölçüsü daha yaxşı nəticə verə bilər.
* Əgər tam offline/kapalı sistem istəyirsinizsə, API-lərlə GPT/Gemini çağırışları yerinə, yoxsa redaktor üçün LLM-based assistans offline Open-Source modellərlə də təmin edilə bilər (məsələn LLaMA / Mistral + LoRA).

---

**Hazır sənəd**: Bu document Rasim müəllimə təqdim etmək üçün kifayət qədər texniki və icraedici detal ehtiva edir. İstəsən, bu sənədi PDF-ə çevirim və ya sənə təqdimat (PowerPoint) slaydlarına çevirim — hansı format istərsən bildir.