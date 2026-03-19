
```
┌─────────────────────────────────────────────────────────────────────┐
│  ROLE:  Input Layer & OCR Engineer                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Modules to Build

```
src/input/
├── input_handler.py
└── image_loader.py

src/ingestion/
├── document_processor.py
└── page_image_store.py

src/ocr/
└── ocr_engine.py

notebooks/
└── 01_input_routing_demo.ipynb
```

### Step-by-Step Tasks

```
STEP 1 │ Build Input Handler
       │
       │  • Implement InputHandler class in input_handler.py
       │
       │  • detect_input_type(path) method:
       │    .pdf                    → InputType.PDF
       │    .jpg/.jpeg/.png/
       │    .tiff/.tif/.bmp/.webp  → InputType.IMAGE
       │    anything else           → raise ValueError with
       │                              clear supported formats message
       │
       │  • load(input_path) method:
       │    - Calls detect_input_type()
       │    - Routes to _load_pdf() or _load_image()
       │    - Returns LoadedInput (from shared_types.py)
       │      always same structure regardless of source type
       │
       │  • File existence check before processing:
       │    raise FileNotFoundError if path does not exist
       │
       │  Output: src/input/input_handler.py
       │
─────────────────────────────────────────────────────────────────────
STEP 2 │ Build Page Image Store (PDF Loading)
       │
       │  • Implement PageImageStore class
       │
       │  • load_pdf(pdf_path) method:
       │    - Use PyMuPDF (fitz) to open PDF
       │    - Render each page at 150 DPI (configurable)
       │    - Convert to PIL Image (RGB)
       │    - Base64 encode each page for MLLM API compatibility
       │    - Store as Dict[page_number → PageImage]
       │    - Return total page count
       │
       │  • get_pages(page_numbers: List[int]) method:
       │    - Called AFTER RAG returns target page numbers
       │    - Returns only the requested PageImage objects
       │    - This is the key cost optimization:
       │      only requested pages reach the MLLM
       │
       │  • get_all_pages() method:
       │    - Returns all pages (used in fallback mode)
       │
       │  Output: src/ingestion/page_image_store.py
       │
─────────────────────────────────────────────────────────────────────
STEP 3 │ Build Image Loader (Direct Image Path)
       │
       │  • Implement ImageLoader class in image_loader.py
       │
       │  • load_image(image_path) method:
       │    - Open image using PIL
       │    - Convert to RGB (handles RGBA, grayscale, etc.)
       │    - Resize if image exceeds 4096×4096 (MLLM size limits)
       │    - Base64 encode to PNG format
       │    - Wrap in PageImage with page_number=1
       │    - Return LoadedInput with total_pages=1
       │
       │  • Support all formats:
       │    JPEG, PNG, TIFF, BMP, WebP
       │
       │  • This is the EASY PATH — no OCR, no RAG, no indexing
       │    Image goes directly to MLLM in pipeline
       │
       │  Output: src/input/image_loader.py
       │
─────────────────────────────────────────────────────────────────────
STEP 4 │ Build OCR Engine
       │
       │  • Implement OCREngine class in ocr_engine.py
       │
       │  • Support two backends via engine parameter:
       │    "surya"  → best layout understanding (recommended)
       │    "paddle" → faster, lighter weight (alternative)
       │
       │  • process_pdf(pdf_path) method:
       │    Returns List[StructuredPage] — one per page
       │
       │  • Each StructuredPage must contain:
       │    - page_number (1-indexed)
       │    - raw_text    (full OCR text, NO summarization)
       │    - section_headers (detected by heuristic:
       │                       short + uppercase/title case lines)
       │    - key_value_pairs (detected by "Label: Value" pattern)
       │    - index_text (structured text for RAG indexing:
       │                  "SECTIONS: ... KEY_VALUES: ... raw_text")
       │
       │  IMPORTANT: index_text must preserve ALL numeric values.
       │  Do NOT summarize. Karthik's retriever depends on
       │  exact terms and numbers being present in index_text.
       │
       │  • _build_index_text() private method:
       │    Combine section headers + key-value pairs + raw_text
       │    in structured format for maximum retrieval signal
       │
       │  Output: src/ocr/ocr_engine.py
       │
─────────────────────────────────────────────────────────────────────
STEP 5 │ Write Tests
       │
       │  • tests/test_input_handler.py:
       │    - PDF file → InputType.PDF returned
       │    - PNG file → InputType.IMAGE returned
       │    - Unknown extension → ValueError raised
       │    - Missing file → FileNotFoundError raised
       │    - LoadedInput.total_pages correct for PDF
       │    - LoadedInput.total_pages == 1 for image
       │
       │  • tests/test_ocr_engine.py:
       │    - StructuredPage has all required fields
       │    - index_text contains raw numeric values
       │    - section_headers detected for SBC documents
       │    - key_value_pairs extracted for "Label: Value" patterns
       │
       │  Output: tests/test_input_handler.py
       │          tests/test_ocr_engine.py
       │
─────────────────────────────────────────────────────────────────────
STEP 6 │ Build Demo Notebook
       │
       │  notebooks/01_input_routing_demo.ipynb
       │
       │  Cell 1: Load a PDF → show page count, show page 1 image
       │  Cell 2: Load an image → show it loads as 1 page directly
       │  Cell 3: Run OCR on PDF → show StructuredPage output
       │          with section_headers and key_value_pairs visible
       │  Cell 4: Show index_text for a page containing
       │          deductible amounts — confirm numbers preserved
       │
       │  Output: notebooks/01_input_routing_demo.ipynb
```

### Deliverable Checklist

```
  □  InputHandler correctly routes PDF and all image formats
  □  PageImageStore loads multi-page PDF, get_pages() works
  □  ImageLoader loads all supported image formats cleanly
  □  OCR returns StructuredPage with all required fields
  □  index_text preserves numeric values (no summarization)
  □  All input handler and OCR unit tests passing
  □  Demo notebook runs without errors, output visible
```
