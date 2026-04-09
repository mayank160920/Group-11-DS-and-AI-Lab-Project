"""
streamlit_app/app.py
---------------------
Streamlit frontend for the CMSVS API.

Run with:
    streamlit run streamlit_app/app.py

Expects the FastAPI backend running at:
    http://localhost:8000
"""
from __future__ import annotations

import io, os
import json
import time
from typing import Any

import pandas as pd
import requests
import streamlit as st

# ── Config ─────────────────────────────────────────────────────────────────────

# API_BASE = "http://localhost:8000"
API_BASE = os.environ.get("CMSVS_API_URL", "http://localhost:8000").rstrip("/")
PAGE_TITLE = "CMSVS — Document Validation System"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ══════════════════════════════════════════════════════════════════════════════
# API helpers
# ══════════════════════════════════════════════════════════════════════════════

def api_get(path: str) -> dict | None:
    """GET request to the API. Returns None on failure."""
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None


def api_post_json(path: str, payload: dict, timeout: int = 30) -> dict | None:
    """POST JSON to the API. Returns None on failure."""
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        st.error(f"API error {exc.response.status_code}: {detail}")
        return None
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return None


def api_delete(path: str) -> dict | None:
    """DELETE request to the API. Returns None on failure."""
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        st.error(f"API error {exc.response.status_code}: {detail}")
        return None
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return None


def api_post_files(
    path: str,
    files: dict,
    data: dict,
    timeout: int = 300,
) -> dict | None:
    """POST multipart/form-data to the API. Returns None on failure."""
    try:
        r = requests.post(
            f"{API_BASE}{path}",
            files=files,
            data=data,
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        st.error(f"API error {exc.response.status_code}: {detail}")
        return None
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return None


@st.cache_data(ttl=5, show_spinner=False)
def _cached_api_get(path: str) -> dict | None:
    """Fast GET helper for high-rerun UI paths (e.g. sidebar)."""
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar() -> dict:
    """Render sidebar and return user settings."""
    with st.sidebar:
        st.title("⚙️ Settings")

        # API health check
        health = _cached_api_get("/health")
        if health:
            if health.get("nvidia_key_set"):
                st.success("🟢 API Online | NVIDIA Key: Set")
            else:
                st.warning("🟡 API Online | NVIDIA Key: Missing")
        else:
            st.error("🔴 API Offline — start the FastAPI server")

        st.divider()

        # Config selection
        configs = []
        config_data = _cached_api_get("/configs")
        if config_data:
            configs = config_data.get("configs", [])

        selected_config = st.selectbox(
            "Configuration",
            options=configs,
            help="Select the entity extraction + validation configuration",
        )

        confidence = st.slider(
            "Confidence Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.75,
            step=0.05,
            help="Entities below this threshold are flagged for human review",
        )

        st.divider()

        # Show config details
        if selected_config:
            with st.expander("📋 Config Details", expanded=False):
                detail = _cached_api_get(f"/configs/{selected_config}")
                if detail:
                    st.markdown(f"**Domain:** {detail.get('domain', '')}")
                    st.markdown(
                        f"**Sections:** {detail.get('total_sections', 0)} | "
                        f"**Entities:** {detail.get('total_entities', 0)}"
                    )
                    for section in detail.get("sections", []):
                        st.markdown(f"**{section['section_name']}**")
                        for e in section["entities"]:
                            badge = (
                                "🧮" if e["entity_extraction_logic"] == "EXPRESSION"
                                else "🔍"
                            )
                            st.markdown(
                                f"&nbsp;&nbsp;{badge} `{e['entity_name']}`",
                                unsafe_allow_html=True,
                            )

        st.divider()
        st.caption("CMSVS v1.0 | NVIDIA NIM Free Tier")

    return {
        "config_name": selected_config,
        "confidence": confidence,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Tab 1: Single Document Extraction
# ══════════════════════════════════════════════════════════════════════════════

def render_extraction_tab(settings: dict) -> None:
    """Render the single-document extraction tab."""
    st.header("🔍 Extract Entities")
    st.caption(
        "Upload a single document (PDF or image) to extract all configured entities."
    )

    uploaded = st.file_uploader(
        "Upload Document",
        type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"],
        help="PDF files use the full RAG pipeline. Images use direct MLLM extraction.",
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        doc_label = st.text_input(
            "Document Label",
            value="My Document",
            help="Human-readable name for this document",
        )
    with col2:
        extract_btn = st.button(
            "Extract Entities",
            type="primary",
            disabled=not (uploaded and settings.get("config_name")),
            use_container_width=True,
        )

    if not settings.get("config_name"):
        st.info("Select a configuration in the sidebar to continue.")
        return

    if extract_btn and uploaded:
        with st.spinner("Extracting entities… this may take 30-90 seconds"):
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            data = {
                "config_name": settings["config_name"],
                "confidence_threshold": settings["confidence"],
            }
            result = api_post_files("/extract", files=files, data=data)

        if result:
            _render_extraction_result(result)


def _render_extraction_result(result: dict) -> None:
    """Display extraction results."""
    st.success(
        f"✅ Extraction complete in {result.get('processing_time_s', 0):.1f}s "
        f"| Job: {result.get('job_id', '')}"
    )

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Entities", result.get("total_entities", 0))
    col2.metric("Found", result.get("found_count", 0))
    col3.metric(
        "Not Found",
        result.get("total_entities", 0) - result.get("found_count", 0),
    )
    col4.metric(
        "Review Required",
        result.get("review_count", 0),
        delta=None,
        delta_color="inverse",
    )

    st.divider()

    # Entity table
    entities = result.get("entities", {})
    if not entities:
        st.warning("No entities extracted.")
        return

    rows = []
    for name, ent in entities.items():
        rows.append({
            "Entity": name,
            "Value": ent.get("extracted_value") or "—",
            "Status": ent.get("extraction_status", ""),
            "Type": ent.get("entity_type", ""),
            "Confidence": f"{ent.get('confidence', 0.0):.0%}",
            "Source Page": ent.get("source_page"),
            "Review": "⚠️" if ent.get("review_required") else "✅",
        })

    df = pd.DataFrame(rows)

    def _highlight(row):
        if row["Review"] == "⚠️":
            return ["background-color: #fff3cd"] * len(row)
        if row["Status"] == "NOT_FOUND":
            return ["background-color: #fce8e8"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(_highlight, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    # Detailed view
    with st.expander("🔎 Entity Details", expanded=False):
        for name, ent in entities.items():
            with st.container():
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"**{name}**")
                    st.markdown(f"Status: `{ent.get('extraction_status')}`")
                    st.markdown(f"Confidence: `{ent.get('confidence', 0):.0%}`")
                with c2:
                    st.markdown(f"**Value:** {ent.get('extracted_value') or '—'}")
                    if ent.get("source_region"):
                        st.markdown(f"**Region:** {ent.get('source_region')}")
                    if ent.get("expression_audit"):
                        st.json(ent["expression_audit"])
                st.divider()

    # JSON download
    st.download_button(
        "⬇️ Download JSON",
        data=json.dumps(result, indent=2),
        file_name=f"extraction_{result.get('job_id', 'result')}.json",
        mime="application/json",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tab 2: Document Pair Validation
# ══════════════════════════════════════════════════════════════════════════════

def render_validation_tab(settings: dict) -> None:
    """Render the document pair validation tab."""
    st.header("⚖️ Validate Document Pair")
    st.caption(
        "Upload two documents to extract entities and run semantic validation."
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Document A")
        doc_a_file = st.file_uploader(
            "Upload Document A",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"],
            key="doc_a_upload",
        )
        doc_a_name = st.text_input(
            "Label for Document A",
            value="Document A (Source)",
            key="doc_a_name",
        )

    with col_b:
        st.subheader("Document B")
        doc_b_file = st.file_uploader(
            "Upload Document B",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"],
            key="doc_b_upload",
        )
        doc_b_name = st.text_input(
            "Label for Document B",
            value="Document B (Comparison)",
            key="doc_b_name",
        )

    if not settings.get("config_name"):
        st.info("Select a configuration in the sidebar to continue.")
        return

    output_format = st.radio(
        "Output Format",
        options=["Full Validation Report", "M2 Ground Truth Format"],
        horizontal=True,
    )

    validate_btn = st.button(
        "Run Validation",
        type="primary",
        disabled=not (doc_a_file and doc_b_file and settings.get("config_name")),
        use_container_width=False,
    )

    if validate_btn and doc_a_file and doc_b_file:
        endpoint = (
            "/validate/gt"
            if output_format == "M2 Ground Truth Format"
            else "/validate"
        )

        with st.spinner(
            "Validating document pair… this may take 60-180 seconds"
        ):
            files = {
                "doc_a": (doc_a_file.name, doc_a_file.getvalue(), doc_a_file.type),
                "doc_b": (doc_b_file.name, doc_b_file.getvalue(), doc_b_file.type),
            }
            data = {
                "config_name": settings["config_name"],
                "doc_a_name": doc_a_name,
                "doc_b_name": doc_b_name,
                "confidence_threshold": settings["confidence"],
            }
            result = api_post_files(endpoint, files=files, data=data, timeout=600)

        if result:
            if output_format == "M2 Ground Truth Format":
                _render_groundtruth_result(result)
            else:
                _render_validation_result(result)


def _render_validation_result(result: dict) -> None:
    """Display full validation report."""
    summary = result.get("summary", {})

    st.success(
        f"✅ Validation complete in {result.get('processing_time_s', 0):.1f}s "
        f"| Job: {result.get('job_id', '')}"
    )

    # Summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    total = summary.get("total_entities", 0)
    matches = summary.get("total_matches", 0)
    mismatches = summary.get("total_mismatches", 0)
    match_rate = summary.get("match_rate", 0.0)

    col1.metric("Total Entities", total)
    col2.metric("✅ Matches", matches)
    col3.metric("❌ Mismatches", mismatches)
    col4.metric("Match Rate", f"{match_rate:.0%}")
    col5.metric("Review Required", summary.get("review_required", 0))

    # Match rate gauge
    st.progress(match_rate, text=f"Overall Match Rate: {match_rate:.1%}")

    st.divider()

    # Per-section results
    sections = result.get("sections", [])
    for section in sections:
        sec_name = section.get("section_name", "")
        sec_match = section.get("match_count", 0)
        sec_mismatch = section.get("mismatch_count", 0)
        sec_total = len(section.get("entities", []))

        with st.expander(
            f"📂 {sec_name}  "
            f"({sec_match}/{sec_total} match)",
            expanded=sec_mismatch > 0,
        ):
            rows = []
            for ent in section.get("entities", []):
                status = ent.get("validation_status", "")
                icon = {
                    "MATCH": "✅",
                    "MISMATCH": "❌",
                    "PARTIAL_MATCH": "⚠️",
                    "INELIGIBLE": "➖",
                }.get(status, "?")

                rows.append({
                    "Entity": ent.get("entity_name", ""),
                    "Doc A Value": ent.get("doc_a_value") or "—",
                    "Doc B Value": ent.get("doc_b_value") or "—",
                    "Status": f"{icon} {status}",
                    "Discrepancy": ent.get("discrepancy_type", ""),
                    "Confidence": f"{ent.get('confidence', 0):.0%}",
                    "Fast Path": "⚡" if ent.get("fast_path_match") else "",
                })

            df = pd.DataFrame(rows)

            def _style(row):
                s = row["Status"]
                if "MISMATCH" in s:
                    return ["background-color: #fce8e8"] * len(row)
                if "MATCH" in s and "PARTIAL" not in s:
                    return ["background-color: #e8f5e9"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df.style.apply(_style, axis=1),
                use_container_width=True,
                hide_index=True,
            )

            # Reasoning details
            for ent in section.get("entities", []):
                if ent.get("validation_status") in ("MISMATCH", "PARTIAL_MATCH"):
                    st.warning(
                        f"**{ent['entity_name']}**: {ent.get('reasoning', '')}"
                    )

    st.divider()

    # Extraction details
    with st.expander("📊 Raw Extraction Results", expanded=False):
        col_a, col_b = st.columns(2)

        def _entity_df(entities_dict: dict) -> pd.DataFrame:
            return pd.DataFrame([
                {
                    "Entity": name,
                    "Value": e.get("extracted_value") or "—",
                    "Status": e.get("extraction_status", ""),
                    "Confidence": f"{e.get('confidence', 0):.0%}",
                    "Page": e.get("source_page"),
                }
                for name, e in entities_dict.items()
            ])

        with col_a:
            st.markdown(f"**{result.get('doc_a_name', 'Doc A')}**")
            st.dataframe(
                _entity_df(result.get("doc_a_entities", {})),
                hide_index=True,
                use_container_width=True,
            )
        with col_b:
            st.markdown(f"**{result.get('doc_b_name', 'Doc B')}**")
            st.dataframe(
                _entity_df(result.get("doc_b_entities", {})),
                hide_index=True,
                use_container_width=True,
            )

    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Download Full Report (JSON)",
            data=json.dumps(result, indent=2),
            file_name=f"validation_{result.get('job_id', 'result')}.json",
            mime="application/json",
        )
    with col2:
        # Build GT format from the full result for convenience
        gt_entities = []
        for section in result.get("sections", []):
            for ent in section.get("entities", []):
                gt_entities.append({
                    "entity_name": ent["entity_name"],
                    "doc_a_value": ent.get("doc_a_value"),
                    "doc_b_value": ent.get("doc_b_value"),
                    "normalized_value": ent.get("doc_a_normalized"),
                    "validation_type": "exact_match" if ent.get("fast_path_match") else "semantic_match",
                    "validation_result": ent.get("validation_status", "").lower(),
                })
        gt_payload = {"entities": gt_entities}
        st.download_button(
            "⬇️ Download GT Format (JSON)",
            data=json.dumps(gt_payload, indent=2),
            file_name=f"gt_{result.get('job_id', 'result')}.json",
            mime="application/json",
        )


def _render_groundtruth_result(result: dict) -> None:
    """Display M2 ground truth format result."""
    st.success(
        f"✅ Validation complete in {result.get('processing_time_s', 0):.1f}s "
        f"| Job: {result.get('job_id', '')}"
    )

    entities = result.get("entities", [])
    matches = sum(1 for e in entities if e.get("validation_result") == "match")
    mismatches = len(entities) - matches

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Entities", len(entities))
    col2.metric("Matches", matches)
    col3.metric("Mismatches", mismatches)

    st.divider()

    rows = []
    for ent in entities:
        icon = "✅" if ent.get("validation_result") == "match" else "❌"
        rows.append({
            "Entity": ent.get("entity_name", ""),
            "Doc A Value": ent.get("doc_a_value") or "—",
            "Doc B Value": ent.get("doc_b_value") or "—",
            "Normalized": ent.get("normalized_value") or "—",
            "Type": ent.get("validation_type", ""),
            "Result": f"{icon} {ent.get('validation_result', '')}",
        })

    df = pd.DataFrame(rows)

    def _style(row):
        if "❌" in row["Result"]:
            return ["background-color: #fce8e8"] * len(row)
        return ["background-color: #e8f5e9"] * len(row)

    st.dataframe(
        df.style.apply(_style, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download Ground Truth JSON",
        data=json.dumps({"entities": entities}, indent=2),
        file_name=f"gt_{result.get('job_id', 'result')}.json",
        mime="application/json",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tab 3: API Explorer
# ══════════════════════════════════════════════════════════════════════════════

def render_api_tab() -> None:
    """Render API explorer tab."""
    st.header("🔌 API Explorer")
    st.caption(
        f"FastAPI backend running at `{API_BASE}` | "
        f"[OpenAPI Docs]({API_BASE}/docs) | [ReDoc]({API_BASE}/redoc)"
    )

    # Health check
    st.subheader("Health Check")
    if st.button("GET /health"):
        health = api_get("/health")
        if health:
            st.json(health)

    st.divider()

    # Config list
    st.subheader("List Configs")
    if st.button("GET /configs"):
        configs = api_get("/configs")
        if configs:
            st.json(configs)

    st.divider()

    # Config detail
    st.subheader("Config Detail")
    config_name_input = st.text_input(
        "Config name",
        value="funsd_ner_config",
        key="api_explorer_config",
    )
    if st.button("GET /configs/{name}"):
        detail = api_get(f"/configs/{config_name_input}")
        if detail:
            st.json(detail)

    st.divider()

    # Endpoint reference
    st.subheader("📚 Endpoint Reference")
    endpoints = [
        ("GET",  "/health",       "API health + available configs"),
        ("GET",  "/configs",      "List all configuration names"),
        ("GET",  "/configs/{name}", "Get config sections and entities"),
        ("POST", "/extract",      "Extract entities from one document"),
        ("POST", "/validate",     "Validate a document pair (full report)"),
        ("POST", "/validate/gt",  "Validate a document pair (GT format)"),
        ("POST", "/configs/create", "Create config from field definitions"),
        ("GET",  "/configs/markdowns", "List saved Markdown configs"),
        ("GET",  "/configs/{name}/markdown", "Get Markdown extraction file"),
        ("DELETE", "/configs/{name}", "Delete a config (YAML + Markdown)"),
    ]
    df = pd.DataFrame(endpoints, columns=["Method", "Endpoint", "Description"])
    st.dataframe(df, hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab 4: Config Builder — CSV fields → YAML + Markdown
# ══════════════════════════════════════════════════════════════════════════════

def _empty_field_row() -> dict:
    """Return a blank field row for the data editor."""
    return {
        "field_name": "",
        "field_description": "",
        "section": "General",
        "data_type": "text",
        "example_value": "",
        "extraction_logic": "DIRECT",
        "expression_template": "",
    }


def _safe_text(value: Any) -> str:
    """Coerce optional editor values to a stripped string."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _normalize_config_key(name: Any) -> str:
    """Normalize config names for duplicate checks (mirrors snake_case intent)."""
    return "_".join(_safe_text(name).lower().split())


def _sync_cb_fields_from_editor() -> None:
    """Sync manual form rows from data_editor widget state into session state."""
    editor_value = st.session_state.get("cb_data_editor")
    if editor_value is None:
        return

    expected_cols = [
        "field_name",
        "field_description",
        "section",
        "data_type",
        "example_value",
        "extraction_logic",
        "expression_template",
    ]

    if isinstance(editor_value, dict) and any(
        k in editor_value for k in ("edited_rows", "added_rows", "deleted_rows")
    ):
        base_df = st.session_state.get("cb_fields_df")
        if not isinstance(base_df, pd.DataFrame) or base_df.empty:
            base_df = pd.DataFrame([_empty_field_row()])
        else:
            base_df = base_df.copy()

        deleted_rows = editor_value.get("deleted_rows", []) or []
        if deleted_rows:
            valid_idx = [i for i in deleted_rows if 0 <= int(i) < len(base_df)]
            if valid_idx:
                base_df = base_df.drop(index=valid_idx)

        edited_rows = editor_value.get("edited_rows", {}) or {}
        for idx, changed_cols in edited_rows.items():
            row_idx = int(idx)
            if row_idx < 0 or row_idx >= len(base_df):
                continue
            for col, value in (changed_cols or {}).items():
                if col in expected_cols:
                    base_df.at[row_idx, col] = value

        added_rows = editor_value.get("added_rows", []) or []
        if added_rows:
            defaults = _empty_field_row()
            normalized_new_rows = []
            for row in added_rows:
                merged = defaults.copy()
                if isinstance(row, dict):
                    merged.update(row)
                normalized_new_rows.append(merged)
            base_df = pd.concat(
                [base_df, pd.DataFrame(normalized_new_rows)],
                ignore_index=True,
            )

        df = base_df.reset_index(drop=True)
    elif isinstance(editor_value, pd.DataFrame):
        df = editor_value.copy()
    else:
        df = pd.DataFrame(editor_value)

    for col, default in _empty_field_row().items():
        if col not in df.columns:
            df[col] = default

    st.session_state.cb_fields_df = df[expected_cols].copy()


def render_config_builder_tab() -> None:
    """Render the Config Builder tab for creating extraction configs."""
    st.header("🛠️ Config Builder")
    st.caption(
        "Define extraction fields via form or CSV upload. "
        "The system generates a YAML config + Markdown extraction instruction file."
    )

    # ── Sub-tabs: Create / Manage ──────────────────────────────────────────
    create_tab, manage_tab = st.tabs(["➕ Create Config", "📂 Manage Configs"])

    # ══════════════════════════════════════════════════════════════════════════
    # CREATE CONFIG
    # ══════════════════════════════════════════════════════════════════════════
    with create_tab:
        st.subheader("Define Fields")

        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            config_name_input = st.text_input(
                "Config Name",
                value="",
                placeholder="e.g. invoice_extraction",
                help="Unique name (will be converted to snake_case)",
                key="cb_config_name",
            )
        with col_meta2:
            domain_input = st.text_input(
                "Domain",
                value="general",
                placeholder="e.g. healthcare, finance, legal",
                key="cb_domain",
            )

        existing_config_keys: set[str] = set()
        configs_data = _cached_api_get("/configs")
        if configs_data:
            for cfg_name in configs_data.get("configs", []):
                key = _normalize_config_key(cfg_name)
                if key:
                    existing_config_keys.add(key)

        markdown_data = _cached_api_get("/configs/markdowns")
        if markdown_data:
            for md_name in markdown_data.get("markdowns", []):
                md_base = _safe_text(md_name)
                if md_base.endswith(".md"):
                    md_base = md_base[:-3]
                key = _normalize_config_key(md_base)
                if key:
                    existing_config_keys.add(key)

        entered_config_key = _normalize_config_key(config_name_input)
        config_name_exists = bool(
            entered_config_key and entered_config_key in existing_config_keys
        )

        if config_name_exists:
            st.error(
                "This config name already exists. Please choose a different name "
                "to avoid overwriting saved files."
            )

        st.divider()

        # ── Input method selector ──────────────────────────────────────────
        input_method = st.radio(
            "Input Method",
            options=["📝 Manual Form", "📤 CSV Upload"],
            horizontal=True,
            key="cb_input_method",
        )

        fields_data: list[dict] = []
        all_rows: list[dict] = []

        if input_method == "📤 CSV Upload":
            st.info(
                "Upload a CSV with columns: "
                "`field_name`, `field_description`, `section`, `data_type`, "
                "`example_value`, `extraction_logic`, `expression_template`  \n"
                "Only `field_name` is required."
            )
            csv_file = st.file_uploader(
                "Upload CSV",
                type=["csv"],
                key="cb_csv_upload",
            )
            if csv_file:
                try:
                    df_csv = pd.read_csv(csv_file)
                    if "field_name" not in df_csv.columns:
                        st.error("CSV must have a `field_name` column.")
                    else:
                        # Fill defaults
                        defaults = {
                            "field_description": "",
                            "section": "General",
                            "data_type": "text",
                            "example_value": "",
                            "extraction_logic": "DIRECT",
                            "expression_template": "",
                        }
                        for col, default in defaults.items():
                            if col not in df_csv.columns:
                                df_csv[col] = default
                            else:
                                df_csv[col] = df_csv[col].fillna(default)

                        st.success(f"Loaded {len(df_csv)} fields from CSV")
                        st.dataframe(df_csv, use_container_width=True, hide_index=True)
                        fields_data = df_csv.to_dict("records")
                        all_rows = fields_data
                except Exception as exc:
                    st.error(f"Failed to parse CSV: {exc}")

            # Download template
            template_csv = (
                "field_name,field_description,section,data_type,"
                "example_value,extraction_logic,expression_template\n"
                "invoice_number,Unique invoice identifier,Header,text,INV-001,DIRECT,\n"
                "total_amount,Total invoice amount,Totals,monetary,$1500.00,DIRECT,\n"
                "tax_amount,Tax computed from subtotal,Totals,monetary,$150.00,EXPRESSION,"
                "subtotal * tax_rate\n"
            )
            st.download_button(
                "📥 Download CSV Template",
                data=template_csv,
                file_name="cmsvs_fields_template.csv",
                mime="text/csv",
            )

        else:
            # ── Manual form using st.data_editor ───────────────────────────
            if "cb_fields_df" not in st.session_state:
                if "cb_fields" in st.session_state:
                    st.session_state.cb_fields_df = pd.DataFrame(
                        st.session_state.cb_fields
                    )
                else:
                    st.session_state.cb_fields_df = pd.DataFrame([_empty_field_row()])

            expected_cols = [
                "field_name",
                "field_description",
                "section",
                "data_type",
                "example_value",
                "extraction_logic",
                "expression_template",
            ]
            for col, default in _empty_field_row().items():
                if col not in st.session_state.cb_fields_df.columns:
                    st.session_state.cb_fields_df[col] = default
            st.session_state.cb_fields_df = st.session_state.cb_fields_df[expected_cols]

            edited_df = st.data_editor(
                st.session_state.cb_fields_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "field_name": st.column_config.TextColumn(
                        "Field Name *", help="Required. e.g. invoice_number"
                    ),
                    "field_description": st.column_config.TextColumn(
                        "Description", help="What this field represents"
                    ),
                    "section": st.column_config.TextColumn(
                        "Section", help="Logical grouping", default="General"
                    ),
                    "data_type": st.column_config.SelectboxColumn(
                        "Data Type",
                        options=["text", "monetary", "percentage", "date", "number"],
                        default="text",
                    ),
                    "example_value": st.column_config.TextColumn(
                        "Example", help="Example expected value"
                    ),
                    "extraction_logic": st.column_config.SelectboxColumn(
                        "Logic",
                        options=["DIRECT", "EXPRESSION"],
                        default="DIRECT",
                    ),
                    "expression_template": st.column_config.TextColumn(
                        "Expression", help="Only for EXPRESSION logic"
                    ),
                },
                key="cb_data_editor",
                on_change=_sync_cb_fields_from_editor,
            )

            # Keep a DataFrame in session state to avoid coercion/reset jitter.
            if "cb_fields_df" not in st.session_state:
                st.session_state.cb_fields_df = edited_df.copy()
            all_rows = st.session_state.cb_fields_df.to_dict("records")
            # Filter out empty rows
            fields_data = [
                r for r in all_rows
                if _safe_text(r.get("field_name"))
            ]

        st.divider()

        missing_field_name_rows = [
            i + 1
            for i, row in enumerate(all_rows)
            if not _safe_text(row.get("field_name"))
        ]
        has_missing_field_name = bool(missing_field_name_rows)
        has_any_user_input = any(
            _safe_text(row.get("field_name"))
            or _safe_text(row.get("field_description"))
            or _safe_text(row.get("example_value"))
            or _safe_text(row.get("expression_template"))
            or (_safe_text(row.get("section")) and _safe_text(row.get("section")) != "General")
            or (_safe_text(row.get("data_type")) and _safe_text(row.get("data_type")) != "text")
            or (
                _safe_text(row.get("extraction_logic"))
                and _safe_text(row.get("extraction_logic")) != "DIRECT"
            )
            for row in all_rows
        )

        if has_missing_field_name and has_any_user_input:
            preview_rows = ", ".join(str(i) for i in missing_field_name_rows[:10])
            more = (
                f" (and {len(missing_field_name_rows) - 10} more)"
                if len(missing_field_name_rows) > 10
                else ""
            )
            st.warning(
                "`field_name` is required for every row. "
                f"Missing in row(s): {preview_rows}{more}. "
                "Complete or remove those rows to enable generation."
            )

        # ── Generate button ────────────────────────────────────────────────
        can_generate = bool(
            config_name_input
            and config_name_input.strip()
            and fields_data
            and not has_missing_field_name
            and not config_name_exists
        )

        if st.button(
            "🚀 Generate Config & Markdown",
            type="primary",
            disabled=not can_generate,
            use_container_width=True,
            key="cb_generate_btn",
        ):
            payload = {
                "config_name": config_name_input.strip(),
                "domain": domain_input.strip() or "general",
                "fields": [
                    {
                        "field_name": _safe_text(f.get("field_name")),
                        "field_description": _safe_text(f.get("field_description")),
                        "section": _safe_text(f.get("section")) or "General",
                        "data_type": _safe_text(f.get("data_type")) or "text",
                        "example_value": _safe_text(f.get("example_value")),
                        "extraction_logic": _safe_text(f.get("extraction_logic")) or "DIRECT",
                        "expression_template": _safe_text(f.get("expression_template")) or None,
                    }
                    for f in fields_data
                    if _safe_text(f.get("field_name"))
                ],
            }

            with st.spinner("Generating config files…"):
                result = api_post_json("/configs/create", payload)

            if result:
                _cached_api_get.clear()
                st.success(
                    f"✅ Config **{result['config_name']}** created! "
                    f"({result['total_sections']} sections, {result['total_fields']} fields)"
                )

                # Show Markdown preview
                st.subheader("📄 Generated Markdown (LLM Extraction Instructions)")
                st.markdown(result.get("markdown_preview", ""), unsafe_allow_html=False)

                # Download buttons
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.download_button(
                        "⬇️ Download Markdown (.md)",
                        data=result.get("markdown_preview", ""),
                        file_name=f"{result['config_name']}.md",
                        mime="text/markdown",
                        key="cb_dl_md",
                    )
                with col_dl2:
                    st.download_button(
                        "⬇️ Download Config Info (JSON)",
                        data=json.dumps(result, indent=2),
                        file_name=f"{result['config_name']}_info.json",
                        mime="application/json",
                        key="cb_dl_json",
                    )

    # ══════════════════════════════════════════════════════════════════════════
    # MANAGE CONFIGS (dropdown, preview, delete)
    # ══════════════════════════════════════════════════════════════════════════
    with manage_tab:
        st.subheader("Saved Markdown Configs")

        # Fetch list of markdowns
        md_list_data = api_get("/configs/markdowns")
        md_names: list[str] = md_list_data.get("markdowns", []) if md_list_data else []

        if not md_names:
            st.info(
                "No saved Markdown configs yet. Use the **Create Config** tab to build one."
            )
        else:
            selected_md = st.selectbox(
                "Select a Markdown Config",
                options=md_names,
                key="cb_manage_select",
            )

            if "cb_delete_target" not in st.session_state:
                st.session_state.cb_delete_target = None

            if selected_md:
                col_actions = st.columns([1, 1, 2])

                with col_actions[0]:
                    view_btn = st.button("👁️ View", key="cb_view_btn", use_container_width=True)
                with col_actions[1]:
                    delete_btn = st.button(
                        "🗑️ Delete", key="cb_delete_btn",
                        type="secondary", use_container_width=True,
                    )

                if delete_btn:
                    st.session_state.cb_delete_target = selected_md
                    st.session_state[f"cb_delete_confirm_{selected_md}"] = False

                if view_btn:
                    md_detail = api_get(f"/configs/{selected_md}/markdown")
                    if md_detail:
                        st.markdown(f"**Config:** `{md_detail['config_name']}`")
                        st.markdown(
                            f"**YAML exists:** {'✅' if md_detail['yaml_exists'] else '❌'}"
                        )
                        st.divider()

                        # Render the markdown
                        st.markdown(md_detail["markdown_content"], unsafe_allow_html=False)

                        # Download
                        st.download_button(
                            "⬇️ Download Markdown",
                            data=md_detail["markdown_content"],
                            file_name=f"{selected_md}.md",
                            mime="text/markdown",
                            key="cb_manage_dl",
                        )

                if st.session_state.get("cb_delete_target") == selected_md:
                    confirm_key = f"cb_delete_confirm_{selected_md}"
                    confirm = st.checkbox(
                        f"Confirm deletion of **{selected_md}** (YAML + Markdown)",
                        key=confirm_key,
                    )
                    if confirm:
                        del_result = api_delete(f"/configs/{selected_md}")
                        if del_result:
                            _cached_api_get.clear()
                            st.success(del_result.get("message", "Deleted."))
                            st.session_state.cb_delete_target = None
                            st.rerun()




# ══════════════════════════════════════════════════════════════════════════════
# Tab 5: Manual Validation — Ground Truth vs Solution Output
# ══════════════════════════════════════════════════════════════════════════════

import numpy as np
from collections import defaultdict

# ── Normalisation helpers ──────────────────────────────────────────────────────

def _canonical_result(raw: str) -> str:
    """Map any variant result string to a canonical 3-class label."""
    if raw is None:
        return "ineligible"
    v = str(raw).strip().lower()
    if v in {"match", "exact_match", "semantic_match", "true"}:
        return "match"
    if v in {"mismatch", "conflict", "false"}:
        return "mismatch"
    if v in {"partial_match", "partial"}:
        return "partial_match"
    return "ineligible"


def _canonical_type(raw: str) -> str:
    """Map validation_type variants to a canonical label."""
    if raw is None:
        return "unknown"
    v = str(raw).strip().lower()
    if v in {"exact_match", "exact"}:
        return "exact_match"
    if v in {"semantic_match", "semantic"}:
        return "semantic_match"
    if v in {"conflict"}:
        return "conflict"
    return "other"


def _load_entities(data: dict) -> list[dict]:
    """
    Accept both FUNSD flat format  →  { "entities": [...] }
    and SBC sectioned format       →  { "sections": [{ "entities": [...] }] }
    Returns a flat list of entity dicts.
    """
    # SBC format has top-level "sections"
    if "sections" in data:
        flat = []
        for section in data["sections"]:
            for ent in section.get("entities", []):
                flat.append(ent)
        return flat
    # FUNSD flat format
    return data.get("entities", [])


def _build_entity_index(entities: list[dict]) -> dict[str, dict]:
    """Index entities by entity_name for O(1) lookup."""
    return {e["entity_name"]: e for e in entities if "entity_name" in e}


# ── Metric computation ─────────────────────────────────────────────────────────

RESULT_CLASSES = ["match", "mismatch", "partial_match", "ineligible"]

def compute_confusion_matrix(
    gt_index: dict[str, dict],
    pred_index: dict[str, dict],
) -> tuple[np.ndarray, list[str], list[dict]]:
    """
    Compare ground truth vs predicted validation_result.
    Only scores entities that exist in ground truth.
    Extra entities in prediction are ignored entirely.
    Returns (confusion_matrix, class_labels, per_entity_rows).
    """
    # ── KEY CHANGE: iterate GT only, ignore extras in pred ────────────────────
    gt_names = sorted(gt_index.keys())

    label_to_idx = {lbl: i for i, lbl in enumerate(RESULT_CLASSES)}
    cm   = np.zeros((len(RESULT_CLASSES), len(RESULT_CLASSES)), dtype=int)
    rows = []

    for name in gt_names:
        gt_ent   = gt_index[name]
        pred_ent = pred_index.get(name, {})   # may be absent — that is fine

        gt_result   = _canonical_result(gt_ent.get("validation_result"))
        pred_result = _canonical_result(
            pred_ent.get("validation_result") if pred_ent else None
        )

        gt_type   = _canonical_type(gt_ent.get("validation_type"))
        pred_type = _canonical_type(
            pred_ent.get("validation_type") if pred_ent else None
        )

        correct = gt_result == pred_result
        cm[label_to_idx[gt_result]][label_to_idx[pred_result]] += 1

        rows.append({
            "entity_name": name,
            "gt_result":   gt_result,
            "pred_result": pred_result,
            "gt_type":     gt_type,
            "pred_type":   pred_type,
            "gt_doc_a":    gt_ent.get("doc_a_value", "—"),
            "gt_doc_b":    gt_ent.get("doc_b_value", "—"),
            "pred_doc_a":  pred_ent.get("doc_a_value", "—") if pred_ent else "—",
            "pred_doc_b":  pred_ent.get("doc_b_value", "—") if pred_ent else "—",
            "correct":     correct,
            "in_gt":       True,        # always True — we only walk GT names
            "in_pred":     bool(pred_ent),
        })

    # ── Track ignored extras for display purposes (not scored) ────────────────
    extra_in_pred = sorted(set(pred_index.keys()) - set(gt_index.keys()))

    return cm, RESULT_CLASSES, rows, extra_in_pred


def compute_metrics(cm: np.ndarray, labels: list[str]) -> dict[str, dict]:
    """Compute per-class precision, recall, F1 and overall accuracy."""
    metrics = {}
    total   = cm.sum()
    correct = np.trace(cm)
    accuracy = correct / total if total > 0 else 0.0

    for i, lbl in enumerate(labels):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)
        support   = int(cm[i, :].sum())
        metrics[lbl] = {
            "precision": round(precision, 4),
            "recall":    round(recall, 4),
            "f1":        round(f1, 4),
            "support":   support,
        }

    # Macro averages (exclude zero-support classes)
    active = [lbl for lbl in labels if metrics[lbl]["support"] > 0]
    macro_p  = np.mean([metrics[l]["precision"] for l in active]) if active else 0.0
    macro_r  = np.mean([metrics[l]["recall"]    for l in active]) if active else 0.0
    macro_f1 = np.mean([metrics[l]["f1"]        for l in active]) if active else 0.0

    metrics["__overall__"] = {
        "accuracy":     round(float(accuracy), 4),
        "macro_p":      round(float(macro_p), 4),
        "macro_r":      round(float(macro_r), 4),
        "macro_f1":     round(float(macro_f1), 4),
        "total_entities": int(total),
        "correct":        int(correct),
    }
    return metrics


# ── Plotly confusion matrix ────────────────────────────────────────────────────

def _render_confusion_matrix_plotly(cm: np.ndarray, labels: list[str]) -> None:
    """Render an annotated heatmap confusion matrix using Plotly."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("Plotly not installed — showing raw matrix instead. `pip install plotly`")
        _render_confusion_matrix_fallback(cm, labels)
        return

    # Row-normalised matrix for colour intensity
    row_sums = cm.sum(axis=1, keepdims=True)
    cm_norm  = np.where(row_sums > 0, cm / row_sums, 0.0)

    # ── Build plain-text annotations (no HTML) ─────────────────────────────────
    annotations = []
    for i in range(len(labels)):
        for j in range(len(labels)):
            count = int(cm[i, j])
            pct   = cm_norm[i, j] * 100

            # Two-line text using \n — works in Plotly annotations
            text = f"{count}\n({pct:.1f}%)"

            # White text on dark cells, dark text on light cells
            font_color = "white" if cm_norm[i, j] > 0.55 else "#0b1220"

            annotations.append(
                dict(
                    x=labels[j],
                    y=labels[i],
                    text=text,
                    showarrow=False,
                    font=dict(
                        color=font_color,
                        size=13,
                        family="Space Mono, monospace",
                    ),
                    align="center",
                )
            )

    fig = go.Figure(
        data=go.Heatmap(
            z=cm_norm,
            x=labels,
            y=labels,
            colorscale=[
                [0.0,  "#f0f4fa"],
                [0.33, "#a8d5c2"],
                [0.66, "#3aaa7a"],
                [1.0,  "#0b6a4a"],
            ],
            showscale=True,
            zmin=0,
            zmax=1,
            colorbar=dict(
                title="Row %",
                tickformat=".0%",
                thickness=14,
                len=0.8,
            ),
        )
    )

    fig.update_layout(
        annotations=annotations,
        xaxis=dict(
            title="Predicted",
            side="bottom",
            tickfont=dict(family="Space Mono", size=12, color="#0b3b66"),
        ),
        yaxis=dict(
            title="Ground Truth",
            autorange="reversed",
            tickfont=dict(family="Space Mono", size=12, color="#0b3b66"),
        ),
        font=dict(family="Outfit", size=13),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=10, r=10, t=30, b=10),
        height=420,
    )

    st.plotly_chart(fig, use_container_width=True)

def _render_confusion_matrix_fallback(cm: np.ndarray, labels: list[str]) -> None:
    """Fallback: render confusion matrix as a styled DataFrame."""
    df_cm = pd.DataFrame(cm, index=[f"GT: {l}" for l in labels],
                          columns=[f"Pred: {l}" for l in labels])

    def _color_cells(val):
        max_val = cm.max()
        if max_val == 0:
            return ""
        intensity = int(220 - (val / max_val) * 160)
        return f"background-color: rgb({intensity}, 230, {intensity}); font-weight: bold;"

    st.dataframe(
        df_cm.style.map(_color_cells),
        use_container_width=True,
    )


# ── Per-entity results table ───────────────────────────────────────────────────

def _render_entity_table(rows: list[dict], filter_mode: str) -> None:
    """Render the per-entity comparison table with optional filtering."""
    STATUS_EMOJI = {
        "match":         "✅",
        "mismatch":      "❌",
        "partial_match": "⚠️",
        "ineligible":    "➖",
    }

    filtered = rows
    if filter_mode == "Errors only":
        filtered = [r for r in rows if not r["correct"]]
    elif filter_mode == "Matches only":
        filtered = [r for r in rows if r["correct"]]
    elif filter_mode == "Missing from prediction":
        filtered = [r for r in rows if not r["in_pred"]]
    # "Missing from ground truth" filter removed — those are now ignored entirely

    if not filtered:
        st.success("No entities matching this filter.")
        return

    table_rows = []
    for r in filtered:
        match_icon = "✅" if r["correct"] else "❌"
        gt_icon    = STATUS_EMOJI.get(r["gt_result"],   "?")
        pred_icon  = STATUS_EMOJI.get(r["pred_result"], "?")

        # When entity is missing from prediction, pred columns show a clear marker
        pred_result_display = (
            f"{pred_icon} {r['pred_result']}"
            if r["in_pred"]
            else "⬜ not in output"
        )

        table_rows.append({
            "✓":           match_icon,
            "Entity":      r["entity_name"],
            "GT Result":   f"{gt_icon} {r['gt_result']}",
            "Pred Result": pred_result_display,
            "GT Type":     r["gt_type"],
            "Pred Type":   r["pred_type"] if r["in_pred"] else "—",
            "GT Doc A":    str(r["gt_doc_a"])[:40] if r["gt_doc_a"] else "—",
            "GT Doc B":    str(r["gt_doc_b"])[:40] if r["gt_doc_b"] else "—",
            "Pred Doc A":  str(r["pred_doc_a"])[:40] if r["pred_doc_a"] else "—",
            "Pred Doc B":  str(r["pred_doc_b"])[:40] if r["pred_doc_b"] else "—",
            "In Pred":     "✅" if r["in_pred"] else "❌",
        })

    df = pd.DataFrame(table_rows)

    def _row_style(row):
        if not row["In Pred"] == "✅":
            return ["background-color: #fefce8"] * len(row)   # yellow = missing
        if row["✓"] == "❌":
            return ["background-color: #fff2f2"] * len(row)   # red = wrong
        if row["✓"] == "✅":
            return ["background-color: #f0fdf4"] * len(row)   # green = correct
        return [""] * len(row)

    st.dataframe(
        df.style.apply(_row_style, axis=1),
        use_container_width=True,
        hide_index=True,
    )


# ── Per-validation-type breakdown ─────────────────────────────────────────────

def _render_type_breakdown(rows: list[dict]) -> None:
    """Show accuracy broken down by GT validation_type."""
    by_type: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        t = r["gt_type"]
        by_type[t]["total"]   += 1
        by_type[t]["correct"] += int(r["correct"])

    type_rows = []
    for t, counts in sorted(by_type.items()):
        acc = counts["correct"] / counts["total"] if counts["total"] > 0 else 0
        type_rows.append({
            "Validation Type":  t,
            "Total":            counts["total"],
            "Correct":          counts["correct"],
            "Errors":           counts["total"] - counts["correct"],
            "Accuracy":         f"{acc:.1%}",
        })

    df = pd.DataFrame(type_rows)

    def _acc_color(val):
        try:
            pct = float(val.strip("%")) / 100
            if pct >= 0.9:  return "background-color:#f0fdf4; color:#15803d; font-weight:bold"
            if pct >= 0.7:  return "background-color:#fefce8; color:#b45309; font-weight:bold"
            return "background-color:#fff2f2; color:#b91c1c; font-weight:bold"
        except Exception:
            return ""

    st.dataframe(
        df.style.map(_acc_color, subset=["Accuracy"]),
        use_container_width=True,
        hide_index=True,
    )


# ── Main render function ───────────────────────────────────────────────────────

def render_manual_validation_tab() -> None:
    """Render the Manual Validation tab — GT JSON vs Solution JSON."""

    st.header("📊 Manual Validation")
    st.caption(
        "Upload a **Ground Truth JSON** and a **Solution Output JSON** "
        "(both in FUNSD or SBC format) to evaluate extraction accuracy."
    )

    # ── File upload ────────────────────────────────────────────────────────────
    col_up1, col_up2 = st.columns(2)

    with col_up1:
        st.subheader("Ground Truth JSON")
        gt_file = st.file_uploader(
            "Upload ground truth",
            type=["json"],
            key="mv_gt_upload",
            help="File from datasets/FUNSD/ground_truth/ or datasets/SBC/json/",
        )

    with col_up2:
        st.subheader("Solution Output JSON")
        pred_file = st.file_uploader(
            "Upload solution output",
            type=["json"],
            key="mv_pred_upload",
            help="Output from /validate/gt endpoint or run_pipeline.py",
        )

    # ── Format hint ───────────────────────────────────────────────────────────
    with st.expander("ℹ️ Supported JSON formats", expanded=False):
        col_fmt1, col_fmt2 = st.columns(2)
        with col_fmt1:
            st.markdown("**FUNSD flat format**")
            st.code(
                '{\n'
                '  "entities": [\n'
                '    {\n'
                '      "entity_name": "document_title",\n'
                '      "doc_a_value": "TITLE A",\n'
                '      "doc_b_value": "title a",\n'
                '      "validation_type": "exact_match",\n'
                '      "validation_result": "match"\n'
                '    }\n'
                '  ]\n'
                '}',
                language="json",
            )
        with col_fmt2:
            st.markdown("**SBC sectioned format**")
            st.code(
                '{\n'
                '  "sections": [\n'
                '    {\n'
                '      "section_name": "Plan Overview",\n'
                '      "entities": [\n'
                '        {\n'
                '          "entity_name": "Individual Deductible",\n'
                '          "doc_a_value": "$1,500",\n'
                '          "doc_b_value": "$1,500",\n'
                '          "validation_type": "exact_match",\n'
                '          "validation_result": "match"\n'
                '        }\n'
                '      ]\n'
                '    }\n'
                '  ]\n'
                '}',
                language="json",
            )

    # ── Only proceed when both files are uploaded ──────────────────────────────
    if not gt_file or not pred_file:
        st.info(
            "⬆️ Upload both files to compute evaluation metrics."
        )
        return

    # ── Parse JSON files ───────────────────────────────────────────────────────
    try:
        gt_data   = json.loads(gt_file.read().decode("utf-8"))
        pred_data = json.loads(pred_file.read().decode("utf-8"))
    except json.JSONDecodeError as exc:
        st.error(f"❌ JSON parse error: {exc}")
        return

    gt_entities   = _load_entities(gt_data)
    pred_entities = _load_entities(pred_data)

    if not gt_entities:
        st.error("Ground truth file contains no entities.")
        return
    if not pred_entities:
        st.error("Solution output file contains no entities.")
        return

    gt_index   = _build_entity_index(gt_entities)
    pred_index = _build_entity_index(pred_entities)

    # ── Compute metrics ────────────────────────────────────────────────────────
    cm, labels, rows, extra_in_pred = compute_confusion_matrix(gt_index, pred_index)
    metrics          = compute_metrics(cm, labels)
    overall          = metrics["__overall__"]

    # ── Top-level summary cards ────────────────────────────────────────────────
    st.divider()
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("GT Entities",   len(rows))
    c2.metric("Correct",       overall["correct"])
    c3.metric("Errors",        overall["total_entities"] - overall["correct"])
    c4.metric("Accuracy",      f"{overall['accuracy']:.1%}")
    c5.metric("Macro F1",      f"{overall['macro_f1']:.3f}")
    c6.metric("Ignored Extras", len(extra_in_pred))   # ← replaces "GT Entities" dupe

    st.progress(
        overall["accuracy"],
        text=f"Overall Accuracy: {overall['accuracy']:.2%}  |  "
             f"Macro Precision: {overall['macro_p']:.3f}  |  "
             f"Macro Recall: {overall['macro_r']:.3f}",
    )

    st.divider()

    # ── Main content in tabs ───────────────────────────────────────────────────
    tab_cm, tab_metrics, tab_entities, tab_types, tab_json = st.tabs([
        "🔲 Confusion Matrix",
        "📐 Per-Class Metrics",
        "📋 Entity Detail",
        "🏷️ By Validation Type",
        "📄 Raw JSON Diff",
    ])

    # ── TAB 1: Confusion Matrix ────────────────────────────────────────────────
    with tab_cm:
        st.markdown("### Confusion Matrix")
        st.caption(
            "Rows = Ground Truth label · Columns = Predicted label · "
            "Colour intensity = row-normalised percentage."
        )
        _render_confusion_matrix_plotly(cm, labels)

        # Raw counts table below the heatmap
        with st.expander("Raw counts", expanded=False):
            df_raw = pd.DataFrame(
                cm,
                index=[f"GT: {l}" for l in labels],
                columns=[f"Pred: {l}" for l in labels],
            )
            st.dataframe(df_raw, use_container_width=True)

        # Error analysis
        st.markdown("### Common Error Patterns")
        error_rows = [r for r in rows if not r["correct"]]
        if error_rows:
            error_counts: dict[tuple, int] = defaultdict(int)
            for r in error_rows:
                error_counts[(r["gt_result"], r["pred_result"])] += 1
            sorted_errors = sorted(error_counts.items(), key=lambda x: -x[1])
            for (gt_lbl, pred_lbl), count in sorted_errors:
                pct = count / len(rows) * 100
                st.markdown(
                    f"- GT **`{gt_lbl}`** → Pred **`{pred_lbl}`** : "
                    f"**{count}** entities ({pct:.1f}%)"
                )
        else:
            st.success("🎉 No prediction errors found!")

    # ── TAB 2: Per-Class Metrics ───────────────────────────────────────────────
    with tab_metrics:
        st.markdown("### Per-Class Precision / Recall / F1")

        metric_rows = []
        for lbl in labels:
            m = metrics[lbl]
            metric_rows.append({
                "Class":     lbl,
                "Support":   m["support"],
                "Precision": m["precision"],
                "Recall":    m["recall"],
                "F1":        m["f1"],
            })

        # Macro / weighted rows
        metric_rows.append({
            "Class":     "── macro avg ──",
            "Support":   overall["total_entities"],
            "Precision": overall["macro_p"],
            "Recall":    overall["macro_r"],
            "F1":        overall["macro_f1"],
        })

        df_metrics = pd.DataFrame(metric_rows)

        def _f1_bar(val):
            """Colour F1 score cells by magnitude."""
            try:
                v = float(val)
                if v >= 0.9:  return "background-color:#f0fdf4; color:#15803d; font-weight:bold"
                if v >= 0.7:  return "background-color:#fefce8; color:#b45309; font-weight:bold"
                if v >  0.0:  return "background-color:#fff2f2; color:#b91c1c; font-weight:bold"
            except Exception:
                pass
            return ""

        st.dataframe(
            df_metrics.style.map(
                _f1_bar, subset=["Precision", "Recall", "F1"]
            ).format({"Precision": "{:.4f}", "Recall": "{:.4f}", "F1": "{:.4f}"}),
            use_container_width=True,
            hide_index=True,
        )

        # Coverage stats
        st.divider()
        st.markdown("### Coverage Statistics")

        in_pred      = sum(1 for r in rows if r["in_pred"])
        missing_pred = sum(1 for r in rows if not r["in_pred"])

        cov_col1, cov_col2, cov_col3 = st.columns(3)
        cov_col1.metric("GT Entities (scored)",    len(rows))
        cov_col2.metric("Found in Prediction",     in_pred)
        cov_col3.metric(
            "Missing from Prediction",
            missing_pred,
            delta=f"-{missing_pred}" if missing_pred else None,
            delta_color="inverse",
        )

        if extra_in_pred:
            st.info(
                f"**{len(extra_in_pred)} extra entity/entities** in the prediction "
                f"were **ignored** (not present in ground truth): "
                + ", ".join(f"`{n}`" for n in extra_in_pred[:10])
                + (f" … and {len(extra_in_pred) - 10} more" if len(extra_in_pred) > 10 else "")
            )
    # ── TAB 3: Entity Detail ───────────────────────────────────────────────────
    with tab_entities:
        st.markdown("### Per-Entity Comparison")

        filter_opts = [
            "All",
            "Errors only",
            "Matches only",
            "Missing from prediction",   # GT entity not found in pred output
        ]
        filter_col1, filter_col2 = st.columns([2, 2])
        with filter_col1:
            filter_mode = st.selectbox("Filter", filter_opts, key="mv_filter")
        with filter_col2:
            search_term = st.text_input(
                "Search entity name", placeholder="e.g. document_title", key="mv_search"
            )

        display_rows = rows
        if search_term:
            display_rows = [
                r for r in display_rows
                if search_term.lower() in r["entity_name"].lower()
            ]

        _render_entity_table(display_rows, filter_mode)

        # Download entity comparison as CSV
        download_rows = [
            {
                "entity_name":    r["entity_name"],
                "gt_result":      r["gt_result"],
                "pred_result":    r["pred_result"],
                "correct":        r["correct"],
                "gt_type":        r["gt_type"],
                "pred_type":      r["pred_type"],
                "gt_doc_a_value": r["gt_doc_a"],
                "gt_doc_b_value": r["gt_doc_b"],
                "pred_doc_a_value": r["pred_doc_a"],
                "pred_doc_b_value": r["pred_doc_b"],
            }
            for r in rows
        ]
        csv_data = pd.DataFrame([
            {
                "entity_name":      r["entity_name"],
                "gt_result":        r["gt_result"],
                "pred_result":      r["pred_result"],
                "correct":          r["correct"],
                "gt_type":          r["gt_type"],
                "pred_type":        r["pred_type"],
                "in_pred":          r["in_pred"],       # in_gt removed (always True now)
                "gt_doc_a_value":   r["gt_doc_a"],
                "gt_doc_b_value":   r["gt_doc_b"],
                "pred_doc_a_value": r["pred_doc_a"],
                "pred_doc_b_value": r["pred_doc_b"],
            }
            for r in rows
        ]).to_csv(index=False)
        st.download_button(
            "⬇️ Download Entity Comparison CSV",
            data=csv_data,
            file_name="entity_comparison.csv",
            mime="text/csv",
        )

    # ── TAB 4: By Validation Type ──────────────────────────────────────────────
    with tab_types:
        st.markdown("### Accuracy by Validation Type (Ground Truth)")
        st.caption(
            "Shows how well the model performs across different "
            "comparison scenarios: exact_match, semantic_match, conflict."
        )
        _render_type_breakdown(rows)

        # Predicted type distribution
        st.divider()
        st.markdown("### Predicted Type Distribution")
        pred_type_counts: dict[str, int] = defaultdict(int)
        for r in rows:
            pred_type_counts[r["pred_type"]] += 1
        if pred_type_counts:
            df_pred_dist = pd.DataFrame(
                [{"Predicted Type": t, "Count": c}
                 for t, c in sorted(pred_type_counts.items(), key=lambda x: -x[1])]
            )
            st.dataframe(df_pred_dist, use_container_width=True, hide_index=True)

    # ── TAB 5: Raw JSON Diff ───────────────────────────────────────────────────
    with tab_json:
        st.markdown("### Raw JSON Preview")

        col_j1, col_j2 = st.columns(2)
        with col_j1:
            st.markdown("**Ground Truth** (first 30 entities)")
            preview_gt = {"entities": gt_entities[:30]}
            st.code(
                json.dumps(preview_gt, indent=2)[:3000] + (
                    "\n  … (truncated)" if len(json.dumps(preview_gt)) > 3000 else ""
                ),
                language="json",
            )
        with col_j2:
            st.markdown("**Solution Output** (first 30 entities)")
            preview_pred = {"entities": pred_entities[:30]}
            st.code(
                json.dumps(preview_pred, indent=2)[:3000] + (
                    "\n  … (truncated)" if len(json.dumps(preview_pred)) > 3000 else ""
                ),
                language="json",
            )

        st.divider()
        st.markdown("### Download Full Evaluation Report")
        eval_report = {
            "summary": {
                "accuracy":         overall["accuracy"],
                "macro_f1":         overall["macro_f1"],
                "macro_precision":  overall["macro_p"],
                "macro_recall":     overall["macro_r"],
                "total_entities":   overall["total_entities"],
                "correct":          overall["correct"],
                "errors":           overall["total_entities"] - overall["correct"],
            },
            "per_class_metrics": {
                lbl: metrics[lbl] for lbl in labels
            },
            "confusion_matrix": {
                "labels": labels,
                "matrix": cm.tolist(),
            },
            "per_entity_results": [
                {
                    "entity_name":  r["entity_name"],
                    "gt_result":    r["gt_result"],
                    "pred_result":  r["pred_result"],
                    "correct":      r["correct"],
                    "gt_type":      r["gt_type"],
                    "pred_type":    r["pred_type"],
                }
                for r in rows
            ],
        }
        st.download_button(
            "⬇️ Download Full Evaluation Report (JSON)",
            data=json.dumps(eval_report, indent=2),
            file_name="evaluation_report.json",
            mime="application/json",
        )

# ══════════════════════════════════════════════════════════════════════════════
# Tab: 🔧 Fine-Tune Entities
# ══════════════════════════════════════════════════════════════════════════════

def _ft_api_get(path: str) -> dict | None:
    """GET with targeted error display for fine-tune calls."""
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        st.error(f"API {exc.response.status_code}: {detail}")
        return None
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return None


def _ft_api_patch(path: str, payload: dict) -> dict | None:
    """PATCH JSON for fine-tune save calls."""
    try:
        r = requests.patch(f"{API_BASE}{path}", json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        st.error(f"API {exc.response.status_code}: {detail}")
        return None
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return None


def _ft_api_post_files(path: str, files: dict, data: dict) -> dict | None:
    """POST multipart for extraction preview calls."""
    try:
        r = requests.post(
            f"{API_BASE}{path}", files=files, data=data, timeout=300
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        st.error(f"API {exc.response.status_code}: {detail}")
        return None
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return None


# ── Session-state helpers ──────────────────────────────────────────────────────

def _ft_state(key: str, default=None):
    """Get a fine-tune scoped session state value."""
    full_key = f"ft_{key}"
    if full_key not in st.session_state:
        st.session_state[full_key] = default
    return st.session_state[full_key]


def _ft_set(key: str, value):
    st.session_state[f"ft_{key}"] = value


def _ft_reset_from(key: str):
    """Clear all downstream state when an upstream selector changes."""
    order = [
        "config_name", "section_name",
        "entities_original", "entities_edited",
        "test_file_bytes", "test_file_name",
        "preview_result", "gt_data",
        "confirm_ready",
    ]
    idx = order.index(key) if key in order else len(order)
    for k in order[idx + 1:]:
        st.session_state.pop(f"ft_{k}", None)


# ── Sub-component renderers ────────────────────────────────────────────────────

def _ft_render_step_bar(current: int) -> None:
    """Render a compact 5-step progress indicator."""
    steps = [
        (1, "Select Config"),
        (2, "Select Section"),
        (3, "Edit Descriptions"),
        (4, "Preview & Compare"),
        (5, "Save Config"),
    ]
    cols = st.columns(len(steps))
    for col, (num, label) in zip(cols, steps):
        if num < current:
            icon, bg, fg = "✓", "#eef6ff", "#0b3b66"
        elif num == current:
            icon, bg, fg = str(num), "#eaf6f0", "#0b6a4a"
        else:
            icon, bg, fg = str(num), "#f3f5f9", "#94a3b8"
        col.markdown(
            f"""
            
                {icon}
                {label}
            
            """,
            unsafe_allow_html=True,
        )


def _ft_render_entity_editor(entities: list[dict]) -> list[dict]:
    """
    Render an inline editor for entity descriptions.
    Returns the edited list of entity dicts.
    """
    edited = []

    # Header row
    h1, h2, h3, h4 = st.columns([1.8, 3.5, 1.5, 1.0])
    h1.markdown(
        'ENTITY NAME',
        unsafe_allow_html=True,
    )
    h2.markdown(
        'DESCRIPTION (editable)',
        unsafe_allow_html=True,
    )
    h3.markdown(
        'EXAMPLE VALUE (editable)',
        unsafe_allow_html=True,
    )
    h4.markdown(
        'LOGIC',
        unsafe_allow_html=True,
    )

    st.divider()

    for ent in entities:
        c1, c2, c3, c4 = st.columns([1.8, 3.5, 1.5, 1.0])

        with c1:
            st.markdown(
                f''
                f'{ent["entity_name"]}',
                unsafe_allow_html=True,
            )

        with c2:
            new_desc = st.text_area(
                label=f"desc_{ent['entity_name']}",
                value=ent["entity_description"],
                height=80,
                label_visibility="collapsed",
                key=f"ft_edit_desc_{ent['entity_name']}",
                help="Edit the extraction description the LLM uses to find this entity.",
            )

        with c3:
            new_example = st.text_input(
                label=f"ex_{ent['entity_name']}",
                value=ent["entity_example_value"],
                label_visibility="collapsed",
                key=f"ft_edit_ex_{ent['entity_name']}",
                help="Example value that guides the LLM.",
            )

        with c4:
            logic_color = "#0b6a4a" if ent["entity_extraction_logic"] == "DIRECT" else "#7a3f00"
            logic_bg    = "#eaf6f0" if ent["entity_extraction_logic"] == "DIRECT" else "#fff7ed"
            st.markdown(
                f''
                f'{ent["entity_extraction_logic"]}',
                unsafe_allow_html=True,
            )

        edited.append({
            "entity_name":              ent["entity_name"],
            "entity_description":       new_desc,
            "entity_extraction_logic":  ent["entity_extraction_logic"],
            "entity_example_value":     new_example,
            "data_type":                ent["data_type"],
        })

        st.markdown(
            '',
            unsafe_allow_html=True,
        )

    return edited


def _ft_render_diff_badge(original: str, current: str) -> str:
    """Return an HTML badge showing whether a description changed."""
    if original.strip() == current.strip():
        return 'unchanged'
    return 'EDITED'


def _ft_render_preview_vs_gt(
    preview_entities: list[dict],
    gt_index: dict[str, dict],
    original_entities: list[dict],
    edited_entities: list[dict],
) -> None:
    """
    Side-by-side comparison:
    Left  — extraction result with edited description
    Right — ground truth value (if GT was uploaded)
    """
    orig_map = {e["entity_name"]: e for e in original_entities}
    edit_map = {e["entity_name"]: e for e in edited_entities}

    STATUS_ICON = {
        "FOUND":     ("✅", "#eaf6f0"),
        "NOT_FOUND": ("❌", "#fff2f2"),
        "AMBIGUOUS": ("⚠️", "#fff8f0"),
        "ERROR":     ("🔴", "#fff2f2"),
    }

    MATCH_ICON = {
        "exact":   ("🎯", "#eaf6f0", "EXACT"),
        "close":   ("〰️", "#fefce8", "CLOSE"),
        "missing": ("❓", "#f8fafc", "NO GT"),
        "diff":    ("❌", "#fff2f2", "DIFF"),
    }

    # Column headers
    h0, h1, h2, h3, h4, h5 = st.columns([1.6, 2.2, 1.0, 2.2, 1.0, 0.8])
    for col, label in zip(
        [h0, h1, h2, h3, h4, h5],
        ["ENTITY", "EXTRACTED VALUE", "CONFIDENCE", "GT VALUE", "MATCH", "DESC"],
    ):
        col.markdown(
            f'{label}',
            unsafe_allow_html=True,
        )
    st.divider()

    for ent in preview_entities:
        name          = ent["entity_name"]
        extracted     = ent.get("extracted_value") or "—"
        status_raw    = (ent.get("extraction_status") or "NOT_FOUND").upper()
        confidence    = float(ent.get("confidence", 0.0))
        review_flag   = ent.get("review_required", False)

        # Ground truth lookup
        gt_ent    = gt_index.get(name, {})
        gt_val_a  = gt_ent.get("doc_a_value", "")
        gt_val_b  = gt_ent.get("doc_b_value", "")
        gt_display = gt_val_a or gt_val_b or ""

        # Determine match quality
        if not gt_display:
            match_key = "missing"
        elif extracted == "—" or extracted is None:
            match_key = "diff"
        else:
            ext_lower = extracted.strip().lower()
            gt_lower  = gt_display.strip().lower()
            if ext_lower == gt_lower:
                match_key = "exact"
            elif (ext_lower in gt_lower or gt_lower in ext_lower
                  or _ft_levenshtein_ratio(ext_lower, gt_lower) > 0.75):
                match_key = "close"
            else:
                match_key = "diff"

        match_icon, match_bg, match_label = MATCH_ICON[match_key]
        status_icon, status_bg = STATUS_ICON.get(status_raw, ("?", "#f8fafc"))

        # Confidence colour
        if confidence >= 0.85:   conf_color = "#15803d"
        elif confidence >= 0.60: conf_color = "#b45309"
        else:                    conf_color = "#b91c1c"

        # Description changed badge
        orig_desc = orig_map.get(name, {}).get("entity_description", "")
        edit_desc = edit_map.get(name, {}).get("entity_description", "")
        desc_badge = _ft_render_diff_badge(orig_desc, edit_desc)

        row_bg = match_bg

        c0, c1, c2, c3, c4, c5 = st.columns([1.6, 2.2, 1.0, 2.2, 1.0, 0.8])

        with c0:
            flag = " 🔍" if review_flag else ""
            st.markdown(
                f'{name}{flag}',
                unsafe_allow_html=True,
            )

        with c1:
            st.markdown(
                f''
                f'{status_icon} {extracted}',
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(
                f'{confidence:.0%}',
                unsafe_allow_html=True,
            )

        with c3:
            st.markdown(
                f''
                f'{gt_display or "—"}',
                unsafe_allow_html=True,
            )

        with c4:
            st.markdown(
                f'{match_icon} {match_label}',
                unsafe_allow_html=True,
            )

        with c5:
            st.markdown(
                f''
                f'{desc_badge}',
                unsafe_allow_html=True,
            )

    # Summary metrics
    st.divider()
    total     = len(preview_entities)
    found     = sum(1 for e in preview_entities
                    if (e.get("extraction_status") or "").upper() == "FOUND")
    exact_m   = sum(1 for e in preview_entities
                    if gt_index.get(e["entity_name"], {}).get("doc_a_value","").strip().lower()
                    == (e.get("extracted_value") or "").strip().lower()
                    and e.get("extracted_value"))
    avg_conf  = (sum(float(e.get("confidence",0)) for e in preview_entities) / total
                 if total > 0 else 0.0)

    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric("Entities",    total)
    sm2.metric("Extracted",   f"{found}/{total}")
    sm3.metric("Exact Match", f"{exact_m}/{len(gt_index)}" if gt_index else f"{exact_m}")
    sm4.metric("Avg Conf.",   f"{avg_conf:.0%}")


def _ft_levenshtein_ratio(s1: str, s2: str) -> float:
    """Fast normalised edit distance for fuzzy match detection."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    len1, len2 = len(s1), len(s2)
    # Only use for short strings to keep it O(n*m) reasonable
    if max(len1, len2) > 200:
        return 0.0
    dp = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, len2 + 1):
            temp = dp[j]
            if s1[i-1] == s2[j-1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j-1])
            prev = temp
    return 1.0 - dp[len2] / max(len1, len2)


def _ft_load_gt_index(gt_data: dict) -> dict[str, dict]:
    """Reuse the same loader logic from manual validation tab."""
    entities = _load_entities(gt_data)
    return _build_entity_index(entities)


# ── Main tab renderer ──────────────────────────────────────────────────────────

def render_finetune_tab() -> None:
    """Render the Entity Description Fine-Tuner tab."""

    st.header("🔧 Fine-Tune Entity Descriptions")
    st.caption(
        "Edit entity descriptions section-by-section, preview extractions "
        "against a test document, compare with ground truth, "
        "and confirm saving to the config file."
    )

    # Determine current step for the progress bar
    def _current_ft_step() -> int:
        if f"ft_confirm_ready" in st.session_state: return 5
        if f"ft_preview_result" in st.session_state: return 4
        if f"ft_entities_edited" in st.session_state: return 3
        if f"ft_section_name"    in st.session_state: return 2
        if f"ft_config_name"     in st.session_state: return 1
        return 1

    _ft_render_step_bar(_current_ft_step())

    st.divider()

    # ── STEP 1 & 2: Config + Section selectors ─────────────────────────────────
    st.markdown("### Step 1 — Select Config & Section")

    sel_col1, sel_col2 = st.columns(2)

    with sel_col1:
        configs_data = _ft_api_get("/configs")
        config_list  = configs_data.get("configs", []) if configs_data else []

        if not config_list:
            st.warning("No configs found. Create one in the Config Builder tab first.")
            return

        current_config = _ft_state("config_name")
        config_idx = (
            config_list.index(current_config)
            if current_config in config_list else 0
        )
        selected_config = st.selectbox(
            "Configuration",
            options=config_list,
            index=config_idx,
            key="ft_sel_config",
            help="Choose the YAML config whose entity descriptions you want to tune.",
        )

        if selected_config != _ft_state("config_name"):
            _ft_reset_from("config_name")
            _ft_set("config_name", selected_config)
            st.rerun()

    with sel_col2:
        if not _ft_state("config_name"):
            st.info("Select a config first.")
        else:
            sections_data = _ft_api_get(
                f"/configs/{_ft_state('config_name')}/sections"
            )
            section_list = (
                sections_data.get("sections", []) if sections_data else []
            )

            if not section_list:
                st.warning("No sections found in this config.")
            else:
                current_section = _ft_state("section_name")
                sec_idx = (
                    section_list.index(current_section)
                    if current_section in section_list else 0
                )
                selected_section = st.selectbox(
                    "Section",
                    options=section_list,
                    index=sec_idx,
                    key="ft_sel_section",
                    help="Choose which section's entity descriptions to edit.",
                )

                if selected_section != _ft_state("section_name"):
                    _ft_reset_from("section_name")
                    _ft_set("section_name", selected_section)

                    # Auto-load entities for this section
                    ents_data = _ft_api_get(
                        f"/configs/{_ft_state('config_name')}"
                        f"/sections/{selected_section}/entities"
                    )
                    if ents_data:
                        entities = ents_data.get("entities", [])
                        _ft_set("entities_original", entities)
                        _ft_set("entities_edited",   entities)
                    st.rerun()

    # Guard: need both config + section loaded
    if not _ft_state("config_name") or not _ft_state("section_name"):
        return
    if not _ft_state("entities_original"):
        st.info("Loading entities…")
        return

    st.divider()

    # ── STEP 3: Edit descriptions ──────────────────────────────────────────────
    st.markdown(
        f"### Step 2 — Edit Descriptions · "
        f'{_ft_state("config_name")} / '
        f'{_ft_state("section_name")}',
        unsafe_allow_html=True,
    )

    # Quick-reset button
    if st.button(
        "↩ Reset to original descriptions",
        key="ft_reset_desc",
        help="Discard edits and reload from disk.",
    ):
        _ft_set("entities_edited", _ft_state("entities_original"))
        st.rerun()

    edited_entities = _ft_render_entity_editor(
        _ft_state("entities_edited") or _ft_state("entities_original")
    )
    _ft_set("entities_edited", edited_entities)

    # Show diff summary
    n_changed = sum(
        1 for orig, edit in zip(
            _ft_state("entities_original"),
            edited_entities,
        )
        if orig["entity_description"].strip() != edit["entity_description"].strip()
        or orig["entity_example_value"].strip() != edit["entity_example_value"].strip()
    )
    if n_changed:
        st.info(f"✏️ {n_changed} entity description(s) have been edited.")
    else:
        st.success("No changes yet — descriptions match the saved config.")

    st.divider()

    # ── STEP 4: Upload test document + optional GT ─────────────────────────────
    st.markdown("### Step 3 — Upload Test Document")

    up_col1, up_col2 = st.columns(2)

    with up_col1:
        st.markdown("**Test Document** (required)")
        test_file = st.file_uploader(
            "Upload document for extraction preview",
            type=["pdf","png","jpg","jpeg","tiff","bmp","webp"],
            key="ft_test_doc",
            help="The LLM will extract entities from this document "
                 "using your edited descriptions.",
        )
        if test_file:
            _ft_set("test_file_bytes", test_file.getvalue())
            _ft_set("test_file_name",  test_file.name)
            _ft_set("test_file_type",  test_file.type)

    with up_col2:
        st.markdown("**Ground Truth JSON** (optional — for comparison)")
        gt_file = st.file_uploader(
            "Upload ground truth JSON",
            type=["json"],
            key="ft_gt_json",
            help="Upload a FUNSD or SBC ground truth file to see "
                 "how extracted values compare.",
        )
        if gt_file:
            try:
                gt_data = json.loads(gt_file.read().decode("utf-8"))
                _ft_set("gt_data", gt_data)
                n_gt = len(_load_entities(gt_data))
                st.success(f"✓ Ground truth loaded — {n_gt} entities")
            except json.JSONDecodeError:
                st.error("Invalid JSON file.")

    ft_confidence = st.slider(
        "Confidence Threshold",
        min_value=0.0, max_value=1.0, value=0.75, step=0.05,
        key="ft_conf_slider",
        help="Entities below this confidence will be flagged for review.",
    )

    # Run preview button
    can_preview = bool(_ft_state("test_file_bytes"))
    if st.button(
        "▶ Run Extraction Preview",
        type="primary",
        disabled=not can_preview,
        use_container_width=True,
        key="ft_run_preview",
    ):
        with st.spinner(
            "Running extraction with your edited descriptions… "
            "this may take 20–60 seconds."
        ):
            overrides_payload = json.dumps(edited_entities)
            files = {
                "file": (
                    _ft_state("test_file_name"),
                    _ft_state("test_file_bytes"),
                    _ft_state("test_file_type") or "application/octet-stream",
                )
            }
            data = {
                "entity_overrides":     overrides_payload,
                "confidence_threshold": str(ft_confidence),
            }
            result = _ft_api_post_files(
                f"/configs/{_ft_state('config_name')}"
                f"/sections/{_ft_state('section_name')}/preview",
                files=files,
                data=data,
            )

        if result:
            _ft_set("preview_result", result)
            _ft_set("confirm_ready",  False)
            st.rerun()

    if not can_preview:
        st.caption("⬆️ Upload a test document to enable the preview.")

    # ── STEP 4b: Show preview results ─────────────────────────────────────────
    if _ft_state("preview_result"):
        result = _ft_state("preview_result")
        st.divider()
        st.markdown(
            f"### Step 4 — Preview Results "
            f''
            f'({result.get("processing_time_s",0):.1f}s)',
            unsafe_allow_html=True,
        )

        gt_index: dict[str, dict] = {}
        if _ft_state("gt_data"):
            gt_index = _ft_load_gt_index(_ft_state("gt_data"))
            st.markdown(
                f''
                f'GT loaded — {len(gt_index)} entities',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No ground truth uploaded — comparison column will show '—'")

        _ft_render_preview_vs_gt(
            preview_entities  = result.get("entities", []),
            gt_index          = gt_index,
            original_entities = _ft_state("entities_original"),
            edited_entities   = edited_entities,
        )

        # Per-entity description diff expander
        with st.expander(
            "🔍 View Description Changes vs Original", expanded=False
        ):
            orig_map = {
                e["entity_name"]: e
                for e in _ft_state("entities_original")
            }
            any_diff = False
            for ent in edited_entities:
                name       = ent["entity_name"]
                orig_desc  = orig_map.get(name, {}).get("entity_description", "")
                orig_ex    = orig_map.get(name, {}).get("entity_example_value", "")
                new_desc   = ent["entity_description"]
                new_ex     = ent["entity_example_value"]

                desc_changed = orig_desc.strip() != new_desc.strip()
                ex_changed   = orig_ex.strip()   != new_ex.strip()

                if desc_changed or ex_changed:
                    any_diff = True
                    st.markdown(f"**`{name}`**")
                    if desc_changed:
                        dcol1, dcol2 = st.columns(2)
                        with dcol1:
                            st.markdown(
                                'ORIGINAL DESCRIPTION',
                                unsafe_allow_html=True,
                            )
                            st.code(orig_desc, language=None)
                        with dcol2:
                            st.markdown(
                                'NEW DESCRIPTION',
                                unsafe_allow_html=True,
                            )
                            st.code(new_desc, language=None)
                    if ex_changed:
                        ecol1, ecol2 = st.columns(2)
                        with ecol1:
                            st.markdown(
                                'ORIGINAL EXAMPLE',
                                unsafe_allow_html=True,
                            )
                            st.code(orig_ex, language=None)
                        with ecol2:
                            st.markdown(
                                'NEW EXAMPLE',
                                unsafe_allow_html=True,
                            )
                            st.code(new_ex, language=None)
                    st.markdown("---")

            if not any_diff:
                st.info("No description changes have been made yet.")

        _ft_set("confirm_ready", True)

    # ── STEP 5: Confirm & save ─────────────────────────────────────────────────
    if _ft_state("confirm_ready") and n_changed > 0:
        st.divider()
        st.markdown("### Step 5 — Save to Config File")

        # Final review table
        st.markdown(
            f"The following **{n_changed}** entity description(s) will be "
            f"written to **`{_ft_state('config_name')}.yaml`**:"
        )

        orig_map = {
            e["entity_name"]: e
            for e in _ft_state("entities_original")
        }
        save_rows = []
        for ent in edited_entities:
            name      = ent["entity_name"]
            orig_desc = orig_map.get(name, {}).get("entity_description", "")
            orig_ex   = orig_map.get(name, {}).get("entity_example_value", "")
            if (orig_desc.strip() != ent["entity_description"].strip()
                    or orig_ex.strip() != ent["entity_example_value"].strip()):
                save_rows.append({
                    "Entity":           name,
                    "Field":            (
                        "description + example"
                        if orig_desc.strip() != ent["entity_description"].strip()
                        and orig_ex.strip()  != ent["entity_example_value"].strip()
                        else "description" if orig_desc.strip() != ent["entity_description"].strip()
                        else "example_value"
                    ),
                    "Original":         orig_desc[:60] + "…" if len(orig_desc) > 60 else orig_desc,
                    "New":              ent["entity_description"][:60] + "…"
                                        if len(ent["entity_description"]) > 60
                                        else ent["entity_description"],
                })

        st.dataframe(
            pd.DataFrame(save_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.warning(
            "⚠️ This will **overwrite** the YAML config file on disk. "
            "A timestamped backup will be created automatically before saving.",
            icon="⚠️",
        )

        confirm_col1, confirm_col2 = st.columns([1, 3])
        with confirm_col1:
            confirmed = st.checkbox(
                "I've reviewed the changes above",
                key="ft_confirm_checkbox",
            )
        with confirm_col2:
            if st.button(
                "💾 Save Descriptions to Config",
                type="primary",
                disabled=not confirmed,
                use_container_width=True,
                key="ft_save_btn",
            ):
                updates_payload = [
                    {
                        "entity_name":         e["entity_name"],
                        "entity_description":  e["entity_description"],
                        "entity_example_value": e["entity_example_value"],
                    }
                    for e in edited_entities
                ]
                save_result = _ft_api_patch(
                    f"/configs/{_ft_state('config_name')}"
                    f"/sections/{_ft_state('section_name')}/entities",
                    payload={"updates": updates_payload},
                )
                if save_result:
                    st.success(save_result.get("message", "Saved successfully."))
                    st.info(
                        f"Backup: `{Path(save_result.get('backup_path','')).name}`"
                    )
                    # Refresh: reload entities from disk and clear preview
                    ents_data = _ft_api_get(
                        f"/configs/{_ft_state('config_name')}"
                        f"/sections/{_ft_state('section_name')}/entities"
                    )
                    if ents_data:
                        entities = ents_data.get("entities", [])
                        _ft_set("entities_original", entities)
                        _ft_set("entities_edited",   entities)
                    _ft_set("preview_result", None)
                    _ft_set("confirm_ready",  False)
                    st.rerun()

    elif _ft_state("confirm_ready") and n_changed == 0:
        st.divider()
        st.info(
            "No description changes detected. "
            "Edit one or more entity descriptions above, "
            "then re-run the preview to proceed."
        )
# ══════════════════════════════════════════════════════════════════════════════
# Main app
# ══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    st.title("📄 CMSVS — Document Validation System")
    st.caption(
        "Configurable Multimodal Semantic Validation | Powered by NVIDIA NIM"
    )

    settings = render_sidebar()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔍 Extract Entities",
        "⚖️ Validate Pair",
        "🛠️ Config Builder",
        "🔧 Fine-Tune Entities",   # ← NEW
        "📊 Manual Validation",
        "🔌 API Explorer",
    ])

    with tab1:
        render_extraction_tab(settings)
    with tab2:
        render_validation_tab(settings)
    with tab3:
        render_config_builder_tab()
    with tab4:
        render_finetune_tab()          # ← NEW
    with tab5:
        render_manual_validation_tab()
    with tab6:
        render_api_tab()


if __name__ == "__main__":
    main()