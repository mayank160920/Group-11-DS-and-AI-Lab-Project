"""
CMSVS Workflow App — End-to-End Document Validation
Combines RAG Input Routing (app.py) + CMSVS Validation (validation_app.py)
into a single guided workflow.

Install deps:
    pip install streamlit pymupdf pillow anthropic

Optional OCR:
    pip install pytesseract        # + install Tesseract binary
    pip install paddlepaddle paddleocr  # heavier, more accurate

Run:
    streamlit run workflow_app.py
"""

import base64
import io
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# ════════════════════════════════════════════════════════
#  Domain types
# ════════════════════════════════════════════════════════

class InputType(Enum):
    PDF   = "pdf"
    IMAGE = "image"

class ValidationStatus(Enum):
    MATCH          = "MATCH"
    MISMATCH       = "MISMATCH"
    PARTIAL_MATCH  = "PARTIAL_MATCH"
    INELIGIBLE     = "INELIGIBLE"

class DiscrepancyType(Enum):
    NUMERIC_DIFFERENCE        = "NUMERIC_DIFFERENCE"
    TERMINOLOGY_VARIANT       = "TERMINOLOGY_VARIANT"
    COVERAGE_RECLASSIFICATION = "COVERAGE_RECLASSIFICATION"
    FORMAT_DIFFERENCE         = "FORMAT_DIFFERENCE"

@dataclass
class PageImage:
    page_number: int
    image: Image.Image
    base64_data: str = ""

@dataclass
class LoadedInput:
    input_type: InputType
    source_path: str
    total_pages: int
    page_images: Dict[int, PageImage] = field(default_factory=dict)

@dataclass
class StructuredPage:
    page_number: int
    raw_text: str
    section_headers: List[str] = field(default_factory=list)
    key_value_pairs: Dict[str, str] = field(default_factory=dict)
    index_text: str = ""

@dataclass
class FinalEntityValue:
    entity_name: str
    value: str
    confidence: float = 1.0
    status: str = "OK"

@dataclass
class ValidationResult:
    entity_name: str
    value_a: str
    value_b: str
    validation_status: ValidationStatus
    discrepancy_type: Optional[str] = None
    reasoning: str = ""
    confidence: float = 1.0
    requires_human_review: bool = False
    normalized_a: str = ""
    normalized_b: str = ""
    fast_path_used: bool = False

@dataclass
class ValidationReport:
    pair_id: str
    doc_a: str
    doc_b: str
    results: List[ValidationResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


# ════════════════════════════════════════════════════════
#  Input Handling
# ════════════════════════════════════════════════════════

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
PDF_EXTS   = {".pdf"}

def detect_input_type(path: Path) -> InputType:
    ext = path.suffix.lower()
    if ext in PDF_EXTS:   return InputType.PDF
    if ext in IMAGE_EXTS: return InputType.IMAGE
    raise ValueError(f"Unsupported format '{ext}'.")

def _img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def load_pdf(pdf_path: Path, dpi: int = 150) -> LoadedInput:
    try:
        import fitz
    except ImportError:
        st.error("PyMuPDF not installed. Run: pip install pymupdf")
        st.stop()
    doc = fitz.open(str(pdf_path))
    page_images: Dict[int, PageImage] = {}
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_images[i] = PageImage(page_number=i, image=img, base64_data=_img_to_b64(img))
    doc.close()
    return LoadedInput(InputType.PDF, str(pdf_path), len(page_images), page_images)

def load_image(image_path: Path) -> LoadedInput:
    img = Image.open(image_path).convert("RGB")
    if max(img.size) > 4096:
        img.thumbnail((4096, 4096), Image.LANCZOS)
    pg = PageImage(1, img, _img_to_b64(img))
    return LoadedInput(InputType.IMAGE, str(image_path), 1, {1: pg})

def load(path: Path) -> LoadedInput:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    t = detect_input_type(path)
    return load_pdf(path) if t == InputType.PDF else load_image(path)


# ════════════════════════════════════════════════════════
#  OCR
# ════════════════════════════════════════════════════════

def _detect_section_headers(lines: List[str]) -> List[str]:
    return [l.strip() for l in lines if l.strip() and len(l.strip()) <= 60
            and (l.strip().isupper() or l.strip().istitle())]

def _detect_key_value_pairs(text: str) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for m in re.finditer(r"([A-Za-z][^\n:]{0,50}):\s*(.+)", text):
        kv[m.group(1).strip()] = m.group(2).strip()
    return kv

def _build_index_text(headers: List[str], kv: Dict[str, str], raw: str) -> str:
    return (f"SECTIONS: {', '.join(headers) or 'NONE'}\n"
            f"KEY_VALUES: {' | '.join(f'{k}: {v}' for k,v in kv.items()) or 'NONE'}\n"
            f"RAW_TEXT:\n{raw}")

def ocr_page_text_only(page_img: PageImage) -> StructuredPage:
    raw_text = ""
    try:
        import pytesseract
        raw_text = pytesseract.image_to_string(page_img.image).strip()
    except Exception:
        raw_text = (
            "CLAIM SUMMARY\nMember Information\n"
            "Deductible: 500\nCopay: 25\nCoinsurance: 20%\nPlan Type: PPO"
        )
    lines   = raw_text.splitlines()
    headers = _detect_section_headers(lines)
    kv      = _detect_key_value_pairs(raw_text)
    idx     = _build_index_text(headers, kv, raw_text)
    return StructuredPage(page_img.page_number, raw_text, headers, kv, idx)

def ocr_paddle(pdf_path: Path) -> List[StructuredPage]:
    loaded = load_pdf(pdf_path)
    try:
        from paddleocr import PaddleOCR
        ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        pages: List[StructuredPage] = []
        for pg in loaded.page_images.values():
            buf = io.BytesIO()
            pg.image.save(buf, format="PNG")
            result  = ocr_engine.ocr(buf.getvalue(), cls=True)
            raw_text = " ".join(
                line[1][0] for block in (result or [])
                for line in (block or []) if line and line[1]
            )
            lines   = raw_text.splitlines()
            headers = _detect_section_headers(lines)
            kv      = _detect_key_value_pairs(raw_text)
            idx     = _build_index_text(headers, kv, raw_text)
            pages.append(StructuredPage(pg.page_number, raw_text, headers, kv, idx))
        return pages
    except ImportError:
        return [ocr_page_text_only(pg) for pg in loaded.page_images.values()]


# ════════════════════════════════════════════════════════
#  Value Normalizer
# ════════════════════════════════════════════════════════

COVERAGE_EQUIVALENTS = {
    "no charge":        "0.00 USD",
    "covered in full":  "0.00 USD",
    "fully covered":    "0.00 USD",
    "not covered":      "MEMBER_PAYS_100",
    "member pays 100%": "MEMBER_PAYS_100",
    "member pays 100":  "MEMBER_PAYS_100",
}

class ValueNormalizer:
    def normalize(self, value: str, data_type: str = "auto") -> str:
        v = value.strip().lower()
        if v in COVERAGE_EQUIVALENTS:
            return COVERAGE_EQUIVALENTS[v]
        if data_type in ("percentage", "auto") and v.endswith("%"):
            try: return f"{float(v.rstrip('%').replace(',', '')):.1f}%"
            except ValueError: pass
        try:
            fv = float(v.replace(",", ""))
            if 0 < fv <= 1.0 and data_type == "percentage":
                return f"{fv * 100:.1f}%"
        except ValueError: pass
        clean = re.sub(r"[^\d.]", "", re.sub(r"\$|,", "", v.split()[0]))
        if clean:
            try:
                if data_type in ("monetary", "auto"):
                    return f"{float(clean):.2f} USD"
            except ValueError: pass
        return value.strip()

    def fast_path(self, val_a: str, val_b: str, data_type: str = "auto") -> Optional[bool]:
        return True if self.normalize(val_a, data_type) == self.normalize(val_b, data_type) else None


# ════════════════════════════════════════════════════════
#  Prompt Builder
# ════════════════════════════════════════════════════════

class ValidationPromptBuilder:
    def build_cot_prompt(self, entity_name: str, value_a: str, value_b: str,
                          data_type: str = "auto", expression_ctx: Optional[Dict] = None) -> str:
        expr_block = ""
        if expression_ctx:
            expr_block = f"\nEXPRESSION CONTEXT:\n  Template : {expression_ctx.get('template','N/A')}\n  Variables: {json.dumps(expression_ctx.get('variables',{}), indent=2)}\n"
        return f"""You are a healthcare benefits document validator.
Compare the two extracted values for entity "{entity_name}" and reason step-by-step.

VALUE A: {value_a}
VALUE B: {value_b}
DATA TYPE: {data_type}
{expr_block}
Steps: Normalize → Compare → Classify discrepancy → Assign status → Rate confidence.

Respond ONLY with valid JSON, no markdown fences:
{{
  "entity_name": "{entity_name}",
  "normalized_value_a": "<canonical form>",
  "normalized_value_b": "<canonical form>",
  "validation_status": "MATCH|MISMATCH|PARTIAL_MATCH|INELIGIBLE",
  "discrepancy_type": null,
  "reasoning": "<step-by-step chain>",
  "confidence": 0.0,
  "requires_human_review": false
}}"""


# ════════════════════════════════════════════════════════
#  Semantic Validator
# ════════════════════════════════════════════════════════

class SemanticValidator:
    def __init__(self, api_key: Optional[str] = None):
        self.normalizer     = ValueNormalizer()
        self.prompt_builder = ValidationPromptBuilder()
        self.api_key        = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def _call_mllm(self, prompt: str) -> Dict:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            raw = re.sub(r"^```json\s*|```$", "", raw, flags=re.MULTILINE).strip()
            return json.loads(raw)
        except Exception as e:
            return {
                "entity_name": "unknown", "normalized_value_a": "",
                "normalized_value_b": "", "validation_status": "MISMATCH",
                "discrepancy_type": "FORMAT_DIFFERENCE",
                "reasoning": f"API error: {e}", "confidence": 0.5,
                "requires_human_review": True,
            }

    def validate_entity_pair(self, entity_name: str,
                              val_a: FinalEntityValue, val_b: FinalEntityValue,
                              data_type: str = "auto") -> Tuple[ValidationResult, bool]:
        if val_a.status in ("INELIGIBLE", "ERROR") or val_b.status in ("INELIGIBLE", "ERROR"):
            return ValidationResult(
                entity_name=entity_name, value_a=val_a.value, value_b=val_b.value,
                validation_status=ValidationStatus.INELIGIBLE,
                reasoning="One or both values are INELIGIBLE/ERROR.", confidence=1.0,
                fast_path_used=True,
            ), False
        na = self.normalizer.normalize(val_a.value, data_type)
        nb = self.normalizer.normalize(val_b.value, data_type)
        if na == nb:
            return ValidationResult(
                entity_name=entity_name, value_a=val_a.value, value_b=val_b.value,
                validation_status=ValidationStatus.MATCH,
                reasoning="Exact match after normalization — fast path.",
                confidence=0.99, normalized_a=na, normalized_b=nb, fast_path_used=True,
            ), False
        prompt = self.prompt_builder.build_cot_prompt(entity_name, val_a.value, val_b.value, data_type)
        resp   = self._call_mllm(prompt)
        status_map = {s.value: s for s in ValidationStatus}
        return ValidationResult(
            entity_name=entity_name, value_a=val_a.value, value_b=val_b.value,
            validation_status=status_map.get(resp.get("validation_status","MISMATCH"), ValidationStatus.MISMATCH),
            discrepancy_type=resp.get("discrepancy_type"),
            reasoning=resp.get("reasoning",""),
            confidence=float(resp.get("confidence", 0.5)),
            requires_human_review=bool(resp.get("requires_human_review", False)),
            normalized_a=resp.get("normalized_value_a", na),
            normalized_b=resp.get("normalized_value_b", nb),
            fast_path_used=False,
        ), True

    def validate(self, extractions_a, extractions_b, pair_id, entity_configs):
        results = []
        for cfg in entity_configs:
            name  = cfg["name"]
            dtype = cfg.get("data_type", "auto")
            ev_a  = extractions_a.get(name, FinalEntityValue(name, "N/A", status="INELIGIBLE"))
            ev_b  = extractions_b.get(name, FinalEntityValue(name, "N/A", status="INELIGIBLE"))
            r, _  = self.validate_entity_pair(name, ev_a, ev_b, dtype)
            results.append(r)
        counts = {s.value: sum(1 for r in results if r.validation_status == s) for s in ValidationStatus}
        fast   = sum(1 for r in results if r.fast_path_used)
        return ValidationReport(
            pair_id=pair_id, doc_a="Doc A", doc_b="Doc B", results=results,
            summary={"total": len(results), **counts, "fast_path_hits": fast, "mllm_calls": len(results)-fast},
        )


# ════════════════════════════════════════════════════════
#  Demo helpers
# ════════════════════════════════════════════════════════

DEMO_ENTITY_CONFIGS = [
    {"name": "Deductible (Individual)",   "data_type": "monetary"},
    {"name": "Deductible (Family)",       "data_type": "monetary"},
    {"name": "Out-of-Pocket Max",         "data_type": "monetary"},
    {"name": "Emergency Room Copay",      "data_type": "monetary"},
    {"name": "Coinsurance",               "data_type": "percentage"},
    {"name": "Urgent Care",               "data_type": "monetary"},
    {"name": "Preventive Care",           "data_type": "auto"},
    {"name": "Mental Health (Inpatient)", "data_type": "auto"},
]

DEMO_PRESETS = {
    "Mostly Matching (SBC #1)": {
        "Deductible (Individual)":   ("$1,500",    "1500"),
        "Deductible (Family)":       ("$3,000",    "$3,000 Family"),
        "Out-of-Pocket Max":         ("$6,550",    "6550.00"),
        "Emergency Room Copay":      ("$250 copay","$400 copay"),
        "Coinsurance":               ("20%",        "0.20"),
        "Urgent Care":               ("$50",        "50"),
        "Preventive Care":           ("No charge",  "Covered in Full"),
        "Mental Health (Inpatient)": ("Not covered","member pays 100%"),
    },
    "Many Mismatches (stress test)": {
        "Deductible (Individual)":   ("$500",   "$1,000"),
        "Deductible (Family)":       ("$1,500", "$2,500"),
        "Out-of-Pocket Max":         ("$5,000", "$8,150"),
        "Emergency Room Copay":      ("$150",   "$350"),
        "Coinsurance":               ("10%",    "30%"),
        "Urgent Care":               ("$25",    "$75"),
        "Preventive Care":           ("$0",     "Not covered"),
        "Mental Health (Inpatient)": ("$200/day","$350/day"),
    },
    "Custom (edit below)": {},
}

def status_color(s: ValidationStatus) -> str:
    return {
        ValidationStatus.MATCH:         "#6ee7b7",
        ValidationStatus.MISMATCH:      "#f87171",
        ValidationStatus.PARTIAL_MATCH: "#fbbf77",
        ValidationStatus.INELIGIBLE:    "#94a3b8",
    }.get(s, "#e8eaf0")

def status_icon(s: ValidationStatus) -> str:
    return {ValidationStatus.MATCH:"✓",ValidationStatus.MISMATCH:"✗",
            ValidationStatus.PARTIAL_MATCH:"~",ValidationStatus.INELIGIBLE:"—"}.get(s,"?")

def make_demo_pdf(path: Path):
    try:
        import fitz
    except ImportError:
        st.error("PyMuPDF not installed. Run: pip install pymupdf"); st.stop()
    doc = fitz.open()
    p1  = doc.new_page()
    p1.insert_text((72,72), "CLAIM SUMMARY\nMember Information\nDeductible: 500\nCopay: 25\nCoinsurance: 20%\nPlan Type: PPO")
    p2  = doc.new_page()
    p2.insert_text((72,72), "BENEFITS\nEmergency Room: 250\nUrgent Care: 50")
    doc.save(str(path)); doc.close()

def make_demo_image(path: Path):
    img  = Image.new("RGBA", (320,180), (244,248,255,255))
    draw = ImageDraw.Draw(img)
    draw.rectangle((20,20,300,160), outline=(40,70,120), width=3)
    draw.text((40,70), "Sample image input", fill=(40,70,120))
    img.save(str(path), format="PNG")

def highlight_numbers(text: str) -> str:
    return re.sub(r"(\b\d[\d,.$%]+\b)", r'<span class="highlight">\1</span>', text)


# ════════════════════════════════════════════════════════
#  Page Config & CSS
# ════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CMSVS Workflow",
    page_icon="⚡",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Outfit:wght@300;400;600;800&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
code, pre, .mono { font-family: 'Space Mono', monospace !important; }
.stApp { background: #ffffff; color: #0b1220; }
[data-testid="stSidebar"] { background: #f7f8fa !important; border-right: 1px solid #e6e6e9; }

h1 { color: #0b3b66 !important; font-weight: 800; letter-spacing: -1.5px; font-size:2rem !important; }
h2 { color: #0b6a4a !important; font-weight: 600; }
h3 { color: #334155 !important; font-weight: 600; }

/* ── Step progress bar ── */
.workflow-steps {
    display: flex;
    gap: 0;
    margin: 1.2rem 0 1.8rem 0;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #e6e9ef;
    background: #fbfdff;
}
.wf-step {
    flex: 1;
    padding: 0.7rem 0.5rem;
    text-align: center;
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    background: #f3f5f9;
    color: #334155;
    border-right: 1px solid #e6e9ef;
    transition: all 0.2s;
}
.wf-step:last-child { border-right: none; }
.wf-step.active  { background: #eaf6f0; color: #0b6a4a; }
.wf-step.done    { background: #eef6ff; color: #0b3b66; }
.wf-step .step-num { font-size: 1.1rem; display: block; margin-bottom: 2px; }

/* ── Cards ── */
.card {
    background: #ffffff;
    border: 1px solid #e6e9ef;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.card-green  { border-color: #d1efe0; }
.card-blue   { border-color: #d9e8f6; }
.card-purple { border-color: #efe3f8; }

/* ── Badges ── */
.badge {
    display: inline-block;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-family: 'Space Mono', monospace;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-right: 6px;
}
.badge-pdf    { background:#eef6ff; color:#0b3b66; border:1px solid #d6e9ff; }
.badge-image  { background:#faf0ff; color:#3a1a66; border:1px solid #f0d9ff; }
.badge-ocr    { background:#fff8e6; color:#7a5600; border:1px solid #ffedc2; }
.badge-MATCH         { background:#eaf8f0; color:#0b7a45; border:1px solid #d1efe0; }
.badge-MISMATCH      { background:#fff2f2; color:#a12a2a; border:1px solid #ffd6d6; }
.badge-PARTIAL_MATCH { background:#fff8f0; color:#8a5a1a; border:1px solid #ffefd6; }
.badge-INELIGIBLE    { background:#f4f6f9; color:#6b7280; border:1px solid #e6e9ef; }

/* ── KV table ── */
.kv-table { width:100%; border-collapse:collapse; font-size:0.84rem; }
.kv-table th { background:#f1f5f9; color:#0b3b66; font-family:'Space Mono',monospace;
               padding:6px 12px; text-align:left; border-bottom:1px solid #e6e9ef; }
.kv-table td { padding:5px 12px; border-bottom:1px solid #f1f3f6;
               color:#0b1220; font-family:'Space Mono',monospace; font-size:0.8rem; }
.kv-table tr:hover td { background:#fbfdff; }

/* ── Index box ── */
.index-box {
    background: #ffffff;
    border: 1px solid #e6e9ef;
    border-left: 3px solid #cfeee0;
    border-radius: 6px;
    padding: 0.9rem 1.1rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem; line-height: 1.7; white-space: pre-wrap;
    color: #0b1220;
}
.highlight { color: #fbbf77; font-weight: 600; }

/* ── Result rows ── */
.result-row {
    display: flex; align-items: center; gap: 0.8rem;
    padding: 0.55rem 0.8rem; border-radius: 8px; margin-bottom: 0.35rem;
    background: #ffffff; border: 1px solid #e6e9ef; font-size: 0.88rem;
}
.result-row:hover { background: #fbfdff; }
.entity-name { flex: 2; color: #0b3b66; font-weight: 500; }
.val-a { flex:2; color:#0b66a3; font-family:'Space Mono',monospace; font-size:0.8rem; }
.val-b { flex:2; color:#d97706; font-family:'Space Mono',monospace; font-size:0.8rem; }
.status-badge {
    flex: 1.2; text-align: center; padding: 3px 10px; border-radius: 4px;
    font-family: 'Space Mono', monospace; font-size: 0.72rem; font-weight: 700;
}
.fp-tag   { font-family:'Space Mono',monospace; font-size:0.68rem; color:#065f46;
            background:#ecfdf3; border:1px solid #d1efe0; border-radius:3px; padding:1px 6px; flex-shrink:0; }
.mllm-tag { font-family:'Space Mono',monospace; font-size:0.68rem; color:#7a3f00;
            background:#fff7ed; border:1px solid #ffecd1; border-radius:3px; padding:1px 6px; flex-shrink:0; }

/* ── Summary grid ── */
.summary-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:0.6rem; margin:1rem 0; }
.summary-card { background:#ffffff; border:1px solid #e6e9ef; border-radius:8px; padding:0.8rem; text-align:center; }
.summary-num  { font-size:1.6rem; font-weight:800; line-height:1; }
.summary-label{ font-size:0.7rem; color:#64748b; margin-top:3px; font-family:'Space Mono',monospace; }

/* ── CoT box ── */
.cot-box {
    background: #ffffff; border:1px solid #e6e9ef; border-left:3px solid #e6e1fb;
    border-radius:6px; padding:0.9rem 1.1rem; font-family:'Space Mono',monospace;
    font-size:0.78rem; line-height:1.7; color:#0b1220; white-space:pre-wrap;
    max-height:240px; overflow-y:auto;
}
.norm-pill {
    display:inline-block; background:#eef6ff; color:#0b3b66; border:1px solid #d6e9ff;
    border-radius:4px; padding:1px 8px; font-family:'Space Mono',monospace; font-size:0.76rem; margin:2px;
}

/* ── Buttons ── */
[data-testid="stToolbar"] + div .stButton > button, .stButton > button {
    background: #0a6a4a !important; color: #ffffff !important;
    border: 1px solid #0a6a4a !important; border-radius: 6px !important;
    font-family: 'Space Mono', monospace !important; font-weight: 700 !important;
}
.stButton > button:hover { background: #0f7a59 !important; }
.stTextInput > div > input, .stSelectbox > div {
    background: #ffffff !important; color: #0b1220 !important;
    border: 1px solid #e6e9ef !important; font-family: 'Space Mono', monospace !important;
}
[data-testid="stFileUploader"] { border: 1px dashed #d6e9ff !important;
    border-radius: 8px !important; background: #ffffff !important; }
hr { border-color: #e6e9ef !important; }
div[data-baseweb="tab"] { font-family: 'Space Mono', monospace !important; }
</style>
""", unsafe_allow_html=True)

# Sidebar visibility state (persist in session)
if "sidebar_collapsed" not in st.session_state:
    st.session_state["sidebar_collapsed"] = False

# If the sidebar is marked collapsed, inject CSS to hide it.
if st.session_state.get("sidebar_collapsed", False):
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        /* ensure main content uses full width when sidebar hidden */
        .css-1y4p8pa { margin-left: 0px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════
#  Sidebar
# ════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ⚡ CMSVS Workflow")
    st.markdown("---")
    st.markdown("""
**End-to-end pipeline**
```
STEP 1 — Upload docs
   ↓
STEP 2 — Load & OCR
   ↓
STEP 3 — Review OCR
   ↓
STEP 4 — Enter values
   ↓
STEP 5 — Validate
   ↓
STEP 6 — Export report
```
    """)
    st.markdown("---")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-…",
        help="Required for MLLM CoT (non-fast-path comparisons).",
    )
    st.markdown("---")
    ocr_backend = st.radio(
        "OCR Backend",
        ["Auto (pytesseract / mock)", "PaddleOCR"],
        index=0,
    )
    st.markdown("---")
    st.markdown("""
<small style='color:#64748b'>
<b>Fast path</b>: no API call<br>
<b>MLLM CoT</b>: 1 call per entity<br>
<b>INELIGIBLE</b>: no API call
</small>
""", unsafe_allow_html=True)

    # Button to hide (close) the sidebar — toggles session state and reruns
    if st.button("Close sidebar"):  # small UX affordance
        st.session_state["sidebar_collapsed"] = True
        st.experimental_rerun()


# ════════════════════════════════════════════════════════
#  Header & progress
# ════════════════════════════════════════════════════════

# If sidebar is collapsed show a small 'Open sidebar' button in the main area
if st.session_state.get("sidebar_collapsed", False):
    if st.button("☰ Open sidebar"):
        st.session_state["sidebar_collapsed"] = False
        st.experimental_rerun()

st.markdown("# ⚡ CMSVS Workflow")
st.markdown('<p style="color:#64748b;font-size:0.9rem;margin-top:-10px'>
            'End-to-end document validation — upload → OCR → validate → export</p>',
            unsafe_allow_html=True)

# Determine current workflow step from session state
def _step_class(step_num: int, current: int) -> str:
    if step_num < current: return "done"
    if step_num == current: return "active"
    return ""

def _step_label(num: int, label: str, current: int) -> str:
    cls = _step_class(num, current)
    prefix = "✓ " if num < current else f"{num}. "
    return (f'<div class="wf-step {cls}">'
            f'<span class="step-num">{prefix}</span>{label}</div>')

# Infer step
def current_step() -> int:
    if "validation_report" in st.session_state: return 6
    if "entity_inputs"     in st.session_state: return 5
    if "ocr_pages_a"       in st.session_state or "ocr_pages_b" in st.session_state: return 4
    if "loaded_a"          in st.session_state or "loaded_b"    in st.session_state: return 3
    if "uploaded_a"        in st.session_state or "uploaded_b"  in st.session_state: return 2
    return 1

step = current_step()

st.markdown(
    '<div class="workflow-steps">'
    + _step_label(1, "Upload", step)
    + _step_label(2, "Load", step)
    + _step_label(3, "OCR Review", step)
    + _step_label(4, "Values", step)
    + _step_label(5, "Validate", step)
    + _step_label(6, "Export", step)
    + '</div>',
    unsafe_allow_html=True,
)


# ════════════════════════════════════════════════════════
#  STEP 1 — Upload documents
# ════════════════════════════════════════════════════════

with st.expander("📁 Step 1 — Upload Documents", expanded=(step == 1)):
    st.markdown("Upload **Doc A** and **Doc B** (PDF or image). Or generate demo assets below.")

    demo_c1, demo_c2 = st.columns(2)
    with demo_c1:
        if st.button("📄 Generate Demo PDF"):
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            make_demo_pdf(Path(tmp.name))
            with open(tmp.name,"rb") as f:
                st.session_state["demo_pdf_bytes"] = f.read()
            st.success("Demo PDF ready — download and re-upload above ✓")
        if "demo_pdf_bytes" in st.session_state:
            st.download_button("⬇ Download Demo PDF", st.session_state["demo_pdf_bytes"],
                               file_name="demo_policy.pdf", mime="application/pdf")
    with demo_c2:
        if st.button("🖼️ Generate Demo Image"):
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            make_demo_image(Path(tmp.name))
            with open(tmp.name,"rb") as f:
                st.session_state["demo_img_bytes"] = f.read()
            st.success("Demo image ready — download and re-upload above ✓")
        if "demo_img_bytes" in st.session_state:
            st.download_button("⬇ Download Demo Image", st.session_state["demo_img_bytes"],
                               file_name="demo_card.png", mime="image/png")

    st.markdown("---")
    uc1, uc2 = st.columns(2)
    with uc1:
        st.markdown("**Doc A**")
        file_a = st.file_uploader("Upload Doc A", type=["pdf","jpg","jpeg","png","tiff","tif","bmp","webp"],
                                   key="fu_a", label_visibility="collapsed")
        if file_a:
            st.session_state["uploaded_a"] = file_a
            st.success(f"✓ {file_a.name}")
    with uc2:
        st.markdown("**Doc B**")
        file_b = st.file_uploader("Upload Doc B", type=["pdf","jpg","jpeg","png","tiff","tif","bmp","webp"],
                                   key="fu_b", label_visibility="collapsed")
        if file_b:
            st.session_state["uploaded_b"] = file_b
            st.success(f"✓ {file_b.name}")

    if "uploaded_a" in st.session_state and "uploaded_b" in st.session_state:
        st.info("Both documents uploaded. Proceed to **Step 2 — Load & OCR** below.")


# ════════════════════════════════════════════════════════
#  STEP 2 — Load & OCR
# ════════════════════════════════════════════════════════

with st.expander("🔬 Step 2 — Load & OCR", expanded=(step == 2)):
    if "uploaded_a" not in st.session_state or "uploaded_b" not in st.session_state:
        st.info("Complete Step 1 first — upload both documents.")
    else:
        st.markdown("Click **Run Load & OCR** to detect file types, render pages, and extract text.")
        if st.button("▶ Run Load & OCR", use_container_width=True):
            def _process(uploaded_file, label: str):
                suffix = Path(uploaded_file.name).suffix
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = Path(tmp.name)
                input_type = detect_input_type(tmp_path)
                with st.spinner(f"Loading {label}…"):
                    loaded = load(tmp_path)
                if input_type == InputType.PDF:
                    with st.spinner(f"Running OCR on {label}…"):
                        if "PaddleOCR" in ocr_backend:
                            pages = ocr_paddle(tmp_path)
                        else:
                            pages = [ocr_page_text_only(loaded.page_images[i])
                                     for i in sorted(loaded.page_images)]
                else:
                    pages = []
                try: os.unlink(tmp_path)
                except Exception: pass
                return input_type, loaded, pages

            fa = st.session_state["uploaded_a"]
            fb = st.session_state["uploaded_b"]
            fa.seek(0); fb.seek(0)

            type_a, loaded_a, pages_a = _process(fa, "Doc A")
            type_b, loaded_b, pages_b = _process(fb, "Doc B")

            st.session_state["type_a"]       = type_a
            st.session_state["loaded_a"]     = loaded_a
            st.session_state["ocr_pages_a"]  = pages_a
            st.session_state["type_b"]       = type_b
            st.session_state["loaded_b"]     = loaded_b
            st.session_state["ocr_pages_b"]  = pages_b
            st.success("Load & OCR complete ✓ Continue to Step 3.")

        if "loaded_a" in st.session_state:
            rc1, rc2 = st.columns(2)
            for col, lbl, t, ld in [
                (rc1,"Doc A", st.session_state["type_a"], st.session_state["loaded_a"]),
                (rc2,"Doc B", st.session_state["type_b"], st.session_state["loaded_b"]),
            ]:
                with col:
                    badge_cls  = "badge-pdf" if t == InputType.PDF else "badge-image"
                    badge_text = t.value.upper()
                    st.markdown(
                        f'<div class="card">'
                        f'<span class="badge {badge_cls}">{badge_text}</span> '
                        f'<b>{lbl}</b> — {ld.total_pages} page(s)'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    pg = ld.page_images[1]
                    st.image(pg.image, caption=f"{lbl} — Page 1", use_container_width=True)


# ════════════════════════════════════════════════════════
#  STEP 3 — OCR Review
# ════════════════════════════════════════════════════════

with st.expander("📑 Step 3 — OCR Review & Index Text", expanded=(step == 3)):
    if "ocr_pages_a" not in st.session_state:
        st.info("Complete Step 2 first.")
    else:
        tabs3 = st.tabs(["Doc A — OCR", "Doc B — OCR"])
        for tab, lbl, pages in [
            (tabs3[0], "Doc A", st.session_state["ocr_pages_a"]),
            (tabs3[1], "Doc B", st.session_state["ocr_pages_b"]),
        ]:
            with tab:
                if not pages:
                    t = st.session_state.get("type_a" if lbl == "Doc A" else "type_b")
                    ld = st.session_state.get("loaded_a" if lbl == "Doc A" else "loaded_b")
                    st.markdown(
                        f'<div class="card card-blue">'
                        f'<span class="badge badge-image">IMAGE</span> '
                        f'Image inputs bypass OCR and go directly to the MLLM. '
                        f'Size: {ld.page_images[1].image.size[0]}×{ld.page_images[1].image.size[1]}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    for sp in pages:
                        with st.expander(f"Page {sp.page_number}", expanded=(sp.page_number == 1)):
                            oc1, oc2 = st.columns(2)
                            with oc1:
                                st.markdown('<span class="badge badge-ocr">Headers</span>', unsafe_allow_html=True)
                                if sp.section_headers:
                                    for h in sp.section_headers: st.markdown(f"- `{h}`")
                                else:
                                    st.markdown('<span style="color:#64748b;font-size:0.82rem">None detected</span>', unsafe_allow_html=True)
                            with oc2:
                                st.markdown('<span class="badge badge-ocr">Key-Value Pairs</span>', unsafe_allow_html=True)
                                if sp.key_value_pairs:
                                    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k,v in sp.key_value_pairs.items())
                                    st.markdown(f'<table class="kv-table"><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>{rows}</tbody></table>',
                                                unsafe_allow_html=True)
                                else:
                                    st.markdown('<span style="color:#64748b;font-size:0.82rem">None detected</span>', unsafe_allow_html=True)
                            st.markdown("**Index text** (RAG payload):")
                            hi = highlight_numbers(sp.index_text)
                            st.markdown(f'<div class="index-box">{hi}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  STEP 4 — Enter Entity Values
# ════════════════════════════════════════════════════════

with st.expander("📝 Step 4 — Enter Entity Values", expanded=(step == 4)):
    if "loaded_a" not in st.session_state:
        st.info("Complete Steps 1–2 first.")
    else:
        st.markdown("Edit extracted values for Doc A and Doc B. Use a preset to populate quickly.")
        preset_name = st.selectbox("Load preset", list(DEMO_PRESETS.keys()), key="preset_sel4")
        preset = DEMO_PRESETS[preset_name]

        entity_inputs: Dict[str, Tuple[str,str]] = {}
        st.markdown(
            '<div class="result-row" style="background:#ffffff;font-family:Space Mono,monospace;font-size:0.7rem;color:#64748b;">'
            '<span style="flex:2">ENTITY</span><span style="flex:3">DOC A VALUE</span><span style="flex:3">DOC B VALUE</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        for cfg in DEMO_ENTITY_CONFIGS:
            name     = cfg["name"]
            defaults = preset.get(name, ("",""))
            ec1, ec2, ec3 = st.columns([2,3,3])
            with ec1:
                st.markdown(f'<div style="padding:0.4rem 0;color:#0b3b66;font-size:0.88rem">{name}</div>', unsafe_allow_html=True)
            with ec2:
                va = st.text_input(f"A·{name}", value=defaults[0], key=f"w4a_{name}", label_visibility="collapsed")
            with ec3:
                vb = st.text_input(f"B·{name}", value=defaults[1], key=f"w4b_{name}", label_visibility="collapsed")
            entity_inputs[name] = (va, vb)

        if st.button("💾 Save Entity Values", use_container_width=True):
            st.session_state["entity_inputs"] = entity_inputs
            st.success("Values saved ✓ Continue to Step 5 — Validate.")


# ════════════════════════════════════════════════════════
#  STEP 5 — Run Validation
# ════════════════════════════════════════════════════════

with st.expander("⚖️ Step 5 — Run Validation", expanded=(step == 5)):
    if "entity_inputs" not in st.session_state:
        st.info("Complete Step 4 first — save entity values.")
    else:
        st.markdown("Run the semantic validator. Fast-path pairs skip the MLLM; mismatches use Claude CoT.")
        if st.button("▶ Run Full Validation", use_container_width=True):
            entity_inputs = st.session_state["entity_inputs"]
            validator = SemanticValidator(api_key=api_key)
            extractions_a: Dict[str, FinalEntityValue] = {}
            extractions_b: Dict[str, FinalEntityValue] = {}
            for cfg in DEMO_ENTITY_CONFIGS:
                name  = cfg["name"]
                va, vb = entity_inputs.get(name, ("",""))
                extractions_a[name] = FinalEntityValue(name, va, status="INELIGIBLE" if not va.strip() else "OK")
                extractions_b[name] = FinalEntityValue(name, vb, status="INELIGIBLE" if not vb.strip() else "OK")
            with st.spinner("Validating — MLLM calls may take a moment…"):
                report = validator.validate(extractions_a, extractions_b, "workflow_pair_001", DEMO_ENTITY_CONFIGS)
            st.session_state["validation_report"] = report
            st.success("Validation complete ✓ See results below and export in Step 6.")

        if "validation_report" in st.session_state:
            report: ValidationReport = st.session_state["validation_report"]
            s = report.summary
            st.markdown(
                f'<div class="summary-grid">'
                f'<div class="summary-card"><div class="summary-num" style="color:#0b6a4a">{s.get("MATCH",0)}</div><div class="summary-label">MATCH</div></div>'
                f'<div class="summary-card"><div class="summary-num" style="color:#b91c1c">{s.get("MISMATCH",0)}</div><div class="summary-label">MISMATCH</div></div>'
                f'<div class="summary-card"><div class="summary-num" style="color:#b45309">{s.get("PARTIAL_MATCH",0)}</div><div class="summary-label">PARTIAL</div></div>'
                f'<div class="summary-card"><div class="summary-num" style="color:#64748b">{s.get("INELIGIBLE",0)}</div><div class="summary-label">INELIGIBLE</div></div>'
                f'<div class="summary-card"><div class="summary-num" style="color:#0b6a4a">{s.get("fast_path_hits",0)}</div><div class="summary-label">FAST PATH</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="result-row" style="background:#ffffff;font-family:Space Mono,monospace;font-size:0.7rem;color:#64748b;">'
                '<span class="entity-name">ENTITY</span>'
                '<span class="val-a">DOC A</span>'
                '<span class="val-b">DOC B</span>'
                '<span class="status-badge">STATUS</span>'
                '<span style="flex:0.8;font-size:0.7rem">PATH</span>'
                '</div>',
                unsafe_allow_html=True,
            )
            for r in report.results:
                sc       = r.validation_status.value
                path_tag = '<span class="fp-tag">FAST</span>' if r.fast_path_used else '<span class="mllm-tag">MLLM</span>'
                st.markdown(
                    f'<div class="result-row">'
                    f'<span class="entity-name">{r.entity_name}</span>'
                    f'<span class="val-a">{r.value_a or "—"}</span>'
                    f'<span class="val-b">{r.value_b or "—"}</span>'
                    f'<span class="status-badge badge-{sc}">{status_icon(r.validation_status)} {sc}</span>'
                    f'{path_tag}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("---")
            st.markdown("### Entity Detail")
            sel = st.selectbox("Inspect entity", [r.entity_name for r in report.results])
            sr  = next(r for r in report.results if r.entity_name == sel)
            dc1, dc2 = st.columns(2)
            with dc1:
                st.markdown("**Normalized A:**")
                st.markdown(f'<span class="norm-pill">{sr.normalized_a or sr.value_a}</span>', unsafe_allow_html=True)
            with dc2:
                st.markdown("**Normalized B:**")
                st.markdown(f'<span class="norm-pill">{sr.normalized_b or sr.value_b}</span>', unsafe_allow_html=True)
            if sr.discrepancy_type:
                st.markdown(f"**Discrepancy type:** `{sr.discrepancy_type}`")
            st.markdown(f"**Confidence:** `{sr.confidence:.2f}`")
            if sr.requires_human_review:
                st.warning("⚠️ Flagged for human review")
            if sr.reasoning:
                st.markdown("**CoT Reasoning:**")
                st.markdown(f'<div class="cot-box">{sr.reasoning}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  STEP 6 — Export
# ════════════════════════════════════════════════════════

with st.expander("📦 Step 6 — Export Report", expanded=(step == 6)):
    if "validation_report" not in st.session_state:
        st.info("Complete Step 5 first — run validation.")
    else:
        report: ValidationReport = st.session_state["validation_report"]
        st.markdown("Download the full validation report as JSON, or reset to start over.")
        report_json = json.dumps({
            "pair_id": report.pair_id,
            "summary": report.summary,
            "results": [
                {
                    "entity_name":        r.entity_name,
                    "value_a":            r.value_a,
                    "value_b":            r.value_b,
                    "normalized_a":       r.normalized_a,
                    "normalized_b":       r.normalized_b,
                    "validation_status":  r.validation_status.value,
                    "discrepancy_type":   r.discrepancy_type,
                    "reasoning":          r.reasoning,
                    "confidence":         r.confidence,
                    "requires_human_review": r.requires_human_review,
                    "fast_path_used":     r.fast_path_used,
                }
                for r in report.results
            ],
        }, indent=2)

        st.download_button(
            "⬇ Download JSON Report",
            data=report_json,
            file_name=f"{report.pair_id}_report.json",
            mime="application/json",
            use_container_width=True,
        )
        st.markdown("---")
        st.markdown("**Preview:**")
        st.code(report_json[:1200] + ("\n  … (truncated)" if len(report_json) > 1200 else ""),
                language="json")

        st.markdown("---")
        if st.button("🔄 Reset Workflow", use_container_width=True):
            for k in ["uploaded_a","uploaded_b","type_a","type_b","loaded_a","loaded_b",
                      "ocr_pages_a","ocr_pages_b","entity_inputs","validation_report",
                      "demo_pdf_bytes","demo_img_bytes","last_report"]:
                st.session_state.pop(k, None)
            st.rerun()