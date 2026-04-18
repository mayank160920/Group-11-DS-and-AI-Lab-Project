# CMSVS — Developer Guide

**Configurable Multimodal Semantic Validation System**
*Group 11 DSAI Lab Project — IIT Madras*

---

## 1. Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.12 or lower |
| pip | Latest |
| NVIDIA NIM API Key | Free tier — [build.nvidia.com](https://build.nvidia.com) |

---

## 2. Local Setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd Group-11-DS-and-AI-Lab-Project/code

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# 4. Set API key
export NVIDIA_API_KEY="nvapi-..."
```

---

## 3. Running the Application

### Terminal 1 — FastAPI Backend

```bash
source .venv/bin/activate
export NVIDIA_API_KEY="nvapi-..."
python3 -m api.main
# → http://localhost:8000  (docs at /docs)
```

### Terminal 2 — Streamlit Frontend

```bash
source .venv/bin/activate
python3 -m streamlit run streamlit_app/app.py
# → http://localhost:8501
```

### Verify Health

```bash
curl http://localhost:8000/health
# nvidia_key_set: true, configs_available: [funsd_ner_config, healthcare_sbc_config]
```

---

## 4. CLI Pipeline Usage

```bash
# Healthcare SBC validation
python scripts/run_pipeline.py \
    --doc_a  path/to/sbc.pdf \
    --doc_b  path/to/benefit_grid.pdf \
    --config configs/healthcare_sbc_config.yaml \
    --output output/report.json

# FUNSD form validation (ground truth format)
python scripts/run_pipeline.py \
    --doc_a  path/to/form_a.png \
    --doc_b  path/to/form_b.png \
    --config configs/funsd_ner_config.yaml \
    --output output/funsd_report.json \
    --groundtruth_format
```

### CLI Parameters

| Parameter | Default | Description |
|---|---|---|
| `--doc_a` | required | Path to Document A (PDF or image) |
| `--doc_b` | required | Path to Document B (PDF or image) |
| `--config` | required | YAML configuration file path |
| `--output` | `output/report.json` | Output JSON report path |
| `--confidence_threshold` | 0.75 | Min confidence before review flag |
| `--top_k` | 2 | RAG pages retrieved per section |
| `--fallback_top_k` | 4 | Expanded pages for fallback |
| `--groundtruth_format` | false | Output in M2 GT format |

---

## 5. Dependencies (requirements.txt)

| Package | Purpose |
|---|---|
| `fastapi` | REST API backend |
| `uvicorn` | ASGI server |
| `streamlit` | Web frontend |
| `openai` | NVIDIA NIM API client (OpenAI-compatible) |
| `chromadb` | In-memory vector store for RAG |
| `PyMuPDF` (fitz) | PDF page rendering to images |
| `Pillow` | Image processing |
| `paddleocr` | OCR text extraction for indexing |
| `pydantic` | Data validation and API models |
| `PyYAML` | Configuration file parsing |
| `simpleeval` | Safe expression evaluation |
| `python-dotenv` | Environment variable loading |
| `python-multipart` | File upload handling |
| `requests` | HTTP client |
| `pandas` | Data handling in frontend |
| `numpy` | Evaluation metrics |

---

## 6. Repository Structure

```
Group-11-DS-and-AI-Lab-Project/
├── README.md                    # Root README
├── Problem-Statement.pdf
├── datasets/
│   ├── FUNSD/
│   │   ├── doc_a/              # Original form images
│   │   ├── doc_b/              # Augmented form images
│   │   ├── ground_truth/       # 33 GT JSON files
│   │   └── entities_superset.json
│   └── SBC/
│       ├── sbc (1).pdf ... sbc (34).pdf   # 34 SBC PDFs
│       ├── SBCbenefitgrid/     # Benefit grid PDFs
│       ├── SBCbeneftroriginal/ # Original benefit grids
│       ├── json/               # 8 GT JSON files (sbc_001–008)
│       └── SBC_benefit_grid template.xlsx
├── docs/
│   ├── milestone-1/ through milestone-6/
│   ├── Technical_Report.md
│   └── Developer_Guide.md
└── code/                        # ← Main application
    ├── README.md
    ├── requirements.txt
    ├── .python-version          # 3.12
    ├── api/                     # FastAPI backend
    │   ├── main.py              # App entry point
    │   ├── routes.py            # API endpoints
    │   ├── services.py          # Business logic
    │   ├── models.py            # Pydantic schemas
    │   ├── config_generator.py  # Config builder
    │   └── api.json             # OpenAPI spec
    ├── src/                     # Core pipeline modules
    │   ├── shared_types.py      # Central type contracts
    │   ├── input/
    │   │   ├── input_handler.py # PDF/image routing
    │   │   └── image_loader.py  # Image loading + base64
    │   ├── ingestion/
    │   │   ├── document_processor.py  # PDF → page images
    │   │   └── page_image_store.py    # In-memory image store
    │   ├── ocr/
    │   │   └── ocr_engine.py    # PaddleOCR integration
    │   ├── retrieval/
    │   │   ├── index_builder.py # ChromaDB index creation
    │   │   └── dense_retriever.py  # Semantic page retrieval
    │   ├── config/
    │   │   └── config_parser.py # YAML config loader
    │   ├── prompts/
    │   │   ├── ner_prompt_builder.py       # Extraction prompts
    │   │   └── validation_prompt_builder.py # Validation prompts
    │   ├── models/
    │   │   ├── nvidia_client.py  # NVIDIA NIM LLM + Embedding
    │   │   └── groq_client.py    # Legacy Groq client
    │   ├── extraction/
    │   │   ├── mllm_extractor.py         # Visual entity extraction
    │   │   ├── expression_evaluator.py   # SimpleEval math
    │   │   └── expression_orchestrator.py # Expression wiring
    │   ├── validation/
    │   │   ├── semantic_validator.py  # CoT validation engine
    │   │   └── utils/
    │   │       └── value_normalizer.py  # Rule-based normalizer
    │   ├── output/
    │   │   └── report_generator.py  # JSON report builder
    │   └── pipeline/
    │       ├── cmsvs_pipeline.py  # Master orchestrator
    │       ├── pdf_pipeline.py    # Full RAG pipeline
    │       └── image_pipeline.py  # Direct MLLM pipeline
    ├── configs/
    │   ├── healthcare_sbc_config.yaml  # 18 entities, 5 sections
    │   ├── funsd_ner_config.yaml       # 20 entities, 6 sections
    │   └── schema/
    │       ├── config_schema.json
    │       └── output_schema.json
    ├── scripts/
    │   ├── run_pipeline.py       # CLI entry point
    │   └── start_with_ngrok.py   # Ngrok tunnel helper
    ├── streamlit_app/
    │   └── app.py                # Streamlit frontend (106KB)
    ├── notebooks/
    │   └── rag_pipeline.ipynb    # RAG pipeline demo
    └── tests/
        ├── test_end_to_end.py
        ├── test_config_parser.py
        ├── test_dense_retriever.py
        ├── test_expression_evaluator.py
        ├── test_index_builder.py
        ├── test_input_handler.py
        ├── test_mllm_extractor.py
        ├── test_ocr_engine.py
        └── test_semantic_validator.py
```

---

## 7. Architecture & Pipeline Details

### 7.1 Pipeline Flow

```
Document (PDF/Image)
        │
        ▼
┌── Input Routing (input_handler.py) ──┐
│   Detects .pdf vs .jpg/.png etc.     │
└──────────┬───────────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
 PDF Path     Image Path
    │             │
    ▼             │
 OCR Engine       │  (PaddleOCR → StructuredPage)
    │             │
    ▼             │
 Index Builder    │  (NemoRetriever embeddings → ChromaDB)
    │             │
    ▼             │
 Dense Retriever  │  (cosine similarity → top-K pages)
    │             │
    ▼             ▼
 MLLM Extractor (nvidia_client.py → llama-4-maverick)
        │
        ▼
 Expression Engine (SimpleEval for EXPRESSION entities)
        │
        ▼
 Semantic Validator (rule-based normalizer + CoT MLLM)
        │
        ▼
 Report Generator → JSON output
```

### 7.2 Key Type Contracts (shared_types.py)

| Type | Layer | Purpose |
|---|---|---|
| `InputType` | Input | PDF or IMAGE enum |
| `PageImage` | Input | Rendered page with base64 |
| `LoadedInput` | Input | Complete loaded document |
| `StructuredPage` | OCR | Page text + headers + KV pairs |
| `RawExtraction` | Extraction | Single entity MLLM result |
| `EntityResult` | Extraction | Post-fallback entity result |
| `FinalEntityValue` | Extraction | Canonical entity output |
| `EntityValidationResult` | Validation | Per-entity comparison result |
| `SectionValidationResult` | Validation | Section-level results |
| `ValidationReport` | Output | Complete document pair report |
| `ValidationStatus` | Validation | MATCH/MISMATCH/PARTIAL_MATCH/INELIGIBLE |
| `DiscrepancyType` | Validation | NUMERIC_DIFFERENCE/TERMINOLOGY_VARIANT/etc. |
| `ExtractionStatus` | Extraction | FOUND/NOT_FOUND/AMBIGUOUS/ERROR |

### 7.3 Module Responsibilities

| Module | File(s) | Responsibility |
|---|---|---|
| **Input** | `input_handler.py`, `image_loader.py` | Detect file type, load document, base64 encode |
| **Ingestion** | `document_processor.py`, `page_image_store.py` | Render PDF pages at 150 DPI, store in memory |
| **OCR** | `ocr_engine.py` | PaddleOCR Mobile text extraction for indexing only |
| **Retrieval** | `index_builder.py`, `dense_retriever.py` | Build ChromaDB index, retrieve top-K pages per section |
| **Config** | `config_parser.py` | Parse YAML → `CMSVSConfig` with sections and entities |
| **Prompts** | `ner_prompt_builder.py`, `validation_prompt_builder.py` | Build structured extraction and CoT validation prompts |
| **Models** | `nvidia_client.py` | NVIDIA NIM API wrapper for embeddings + LLM |
| **Extraction** | `mllm_extractor.py`, `expression_evaluator.py`, `expression_orchestrator.py` | Visual extraction, math computation, wiring |
| **Validation** | `semantic_validator.py`, `value_normalizer.py` | Rule-based fast path + MLLM CoT comparison |
| **Output** | `report_generator.py` | Structured JSON report generation |
| **Pipeline** | `cmsvs_pipeline.py`, `pdf_pipeline.py`, `image_pipeline.py` | Orchestration |

---

## 8. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check + config status |
| `GET` | `/configs` | List available configs |
| `GET` | `/configs/{name}` | Config details (sections + entities) |
| `POST` | `/configs/create` | Create config from field definitions |
| `DELETE` | `/configs/{name}` | Delete config files |
| `POST` | `/extract` | Extract entities from single document |
| `POST` | `/validate` | Full document pair validation |
| `POST` | `/validate/gt` | Validation in GT format |
| `GET` | `/configs/{name}/sections` | List config sections |
| `GET` | `/configs/{name}/sections/{s}/entities` | List section entities |
| `POST` | `/configs/{name}/sections/{s}/preview` | Preview extraction with overrides |
| `PATCH` | `/configs/{name}/sections/{s}/entities` | Patch entity definitions |

Full OpenAPI spec: `code/api/api.json`

---

## 9. Configuration File Format

### YAML Schema

```yaml
config_name: healthcare_sbc_config
version: "1.0"
domain: healthcare_insurance

sections:
  - section_name: Deductibles
    section_description: >
      Annual amounts a member must pay before insurance begins.
    section_keywords: [deductible, annual, individual, family]
    entities:
      - entity_name: individual_deductible_in_network
        entity_description: >
          Per-person annual deductible for in-network providers.
        entity_extraction_logic: DIRECT      # or EXPRESSION
        entity_example_value: "$1,500"
        data_type: monetary                   # monetary|percentage|coverage_classification|text

      - entity_name: combined_family_deductible
        entity_extraction_logic: EXPRESSION
        entity_example_value: "$7,500"
        data_type: monetary
        expression_template: "var_a + var_b"
        expression_variables:
          var_a:
            description: "In-network deductible"
            example_value: "$1,500"
          var_b:
            description: "Out-of-network deductible"
            example_value: "$4,500"

validation_settings:
  confidence_threshold: 0.75
  high_stakes_entities: [individual_deductible_in_network]
  human_review_escalation: true
```

### Bundled Configs

| Config | Domain | Entities | Sections |
|---|---|---|---|
| `healthcare_sbc_config.yaml` | Healthcare Insurance | 18 (2 EXPRESSION) | 5 |
| `funsd_ner_config.yaml` | Form Understanding | 20 (all DIRECT) | 6 |

---

## 10. Configurable Parameters

| Parameter | Location | Default | Range Tested |
|---|---|---|---|
| `confidence_threshold` | Pipeline init / CLI | 0.75 | 0.60–0.80 |
| `default_top_k` | Pipeline init / CLI | 2 | 2–5 |
| `fallback_top_k` | Pipeline init / CLI | 4 | 4–6 |
| LLM model | `nvidia_client.py` | llama-4-maverick-17b-128e-instruct | — |
| Embedding model | `nvidia_client.py` | llama-3.2-nemoretriever-300m-embed-v1 | — |
| Max JSON retries | `mllm_extractor.py` | 3 | — |
| Page DPI | `document_processor.py` | 150 | — |

**Recommended production values:** `top_k=4`, `confidence_threshold=0.75` (or 0.70 for recall-first).

---

## 11. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `NVIDIA_API_KEY` | Yes | NVIDIA NIM API key (for embeddings + LLM) |
| `CMSVS_API_URL` | No | Backend URL for Streamlit (default: `http://localhost:8000`) |

---

## 12. Testing

```bash
cd code/
source .venv/bin/activate
export NVIDIA_API_KEY="nvapi-..."

# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_end_to_end.py -v
python -m pytest tests/test_config_parser.py -v
python -m pytest tests/test_expression_evaluator.py -v
```

### Test Files

| Test | Covers |
|---|---|
| `test_end_to_end.py` | Full pipeline E2E with evaluation metrics |
| `test_config_parser.py` | YAML parsing and validation |
| `test_input_handler.py` | PDF/image detection and routing |
| `test_ocr_engine.py` | PaddleOCR text extraction |
| `test_index_builder.py` | ChromaDB index creation |
| `test_dense_retriever.py` | Semantic page retrieval |
| `test_mllm_extractor.py` | MLLM extraction with JSON parsing |
| `test_expression_evaluator.py` | SimpleEval math computation |
| `test_semantic_validator.py` | Validation logic and normalizer |

---

## 13. Notebooks

| Notebook | Purpose |
|---|---|
| `notebooks/rag_pipeline.ipynb` | Full RAG pipeline walkthrough — OCR, indexing, retrieval, extraction, validation |

---

## 14. Hugging Face Deployment

> **Do NOT deploy `main` branch** — it includes large dataset folders.

Use the `deploy/hf` orphan branch:

```bash
git fetch origin
git switch --track deploy/hf origin/deploy/hf
```

### Branch Layout

`deploy/hf` moves `code/` contents to repo root and adds:
- `Dockerfile` (SDK: docker, port: 7860)
- `scripts/start_space.sh` (starts FastAPI on 8000 + Streamlit on 7860)

### Required Secret

In HF Space settings: `NVIDIA_API_KEY=nvapi-...`

---

## 15. Reproducing Evaluation Results

### SBC Dataset Evaluation

```bash
cd code/
export NVIDIA_API_KEY="nvapi-..."

# Run pipeline on all 8 GT pairs
for i in $(seq 1 8); do
    python scripts/run_pipeline.py \
        --doc_a "../datasets/SBC/sbc ($i).pdf" \
        --doc_b "../datasets/SBC/SBCbenefitgrid/grid_$i.pdf" \
        --config configs/healthcare_sbc_config.yaml \
        --output "output/sbc_00${i}_result.json" \
        --groundtruth_format \
        --top_k 3
done

# Compare against ground truth
# GT files: datasets/SBC/json/sbc_001_ground_truth.json through sbc_008
```

### FUNSD Dataset Evaluation

```bash
# Run on all 33 FUNSD pairs
# Doc pairs are in datasets/FUNSD/doc_a/ and datasets/FUNSD/doc_b/
# GT files: datasets/FUNSD/ground_truth/*.json
python scripts/run_pipeline.py \
    --doc_a "../datasets/FUNSD/doc_a/00040534.png" \
    --doc_b "../datasets/FUNSD/doc_b/00040534.png" \
    --config configs/funsd_ner_config.yaml \
    --output output/funsd_result.json \
    --groundtruth_format
```

### Expected Results (Baseline: top_k=3, threshold=0.75)

| Dataset | F1 | Precision | Recall | Accuracy |
|---|---|---|---|---|
| SBC (8 pairs) | 0.789 | 0.820 | 0.760 | 0.894 |
| FUNSD 2-class (33 pairs) | 0.89 | 0.91 | 0.89 | 0.885 |
| FUNSD 3-class (33 pairs) | 0.71 | 0.75 | 0.72 | 0.717 |

---

## 16. Adding a New Domain

1. **Create YAML config** in `code/configs/`:
   - Define sections with keywords
   - Define entities with names, descriptions, extraction logic, examples, data types
   - Set validation thresholds

2. **No code changes needed** — the pipeline reads config at runtime

3. **Test with CLI:**
```bash
python scripts/run_pipeline.py \
    --doc_a path/to/doc_a.pdf \
    --doc_b path/to/doc_b.pdf \
    --config configs/your_new_config.yaml \
    --output output/test.json
```

4. **Or via Streamlit:** Upload config through the UI, then upload documents

---

## 17. Troubleshooting

| Issue | Fix |
|---|---|
| `NVIDIA_API_KEY is not configured` | Export the key: `export NVIDIA_API_KEY="nvapi-..."` |
| Streamlit shows API offline | Ensure `python3 -m api.main` is running on port 8000 |
| No configs in sidebar | Confirm `configs/` has YAML files; backend started from `code/` |
| OCR install fails | Recreate venv; use Python 3.12; install from requirements.txt |
| Rate limit errors | Add inter-call delays; NVIDIA NIM free tier has daily quotas |
| JSON parse errors from LLM | System retries up to 3 times automatically |

---

*Document Version: 1.0 | April 2026*
