"""

Business logic layer between FastAPI routes and CMSVS pipeline.
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any

from api.models import (
    ConfigDetailResponse,
    EntityInfo,
    ExtractedEntity,
    ExtractionResponse,
    GroundTruthEntity,
    GroundTruthResponse,
    SectionInfo,
    ValidationEntityResult,
    ValidationResponse,
    ValidationSectionResult,
    ValidationSummary,
)

# ── Paths ─────────────────────────────────────────────────────────────────────

CONFIGS_DIR = Path(__file__).parent.parent / "configs"
SRC_DIR = Path(__file__).parent.parent / "src"


# ── Utility ───────────────────────────────────────────────────────────────────

def _safe_str(value: Any, default: str = "") -> str:
    """Return value as str, or default if value is None."""
    if value is None:
        return default
    return str(value)


def _fev_to_model(fev) -> ExtractedEntity:
    """
    Convert a FinalEntityValue dataclass → ExtractedEntity Pydantic model.

    All string fields are sanitised: None → None (Optional[str] accepted).
    Numeric fields fall back to safe defaults.
    """
    return ExtractedEntity(
        entity_name=_safe_str(fev.entity_name),
        extracted_value=fev.extracted_value,            # Optional[str] — None OK
        extraction_status=_safe_str(
            fev.extraction_status.value
            if hasattr(fev.extraction_status, "value")
            else fev.extraction_status
        ),
        entity_type=_safe_str(
            fev.entity_type.value
            if hasattr(fev.entity_type, "value")
            else fev.entity_type
        ),
        confidence=float(fev.confidence or 0.0),
        source_page=fev.source_page,                    # Optional[int] — None OK
        source_region=fev.source_region or None,        # coerce "" → None for clarity
        review_required=bool(fev.review_required),
        fallback_triggered=bool(fev.fallback_triggered),
        expression_audit=fev.expression_audit,          # Optional[dict] — None OK
    )


# ══════════════════════════════════════════════════════════════════════════════

class CMSVSService:
    """
    Singleton service that wraps the CMSVS pipeline for API use.

    Caches loaded configs to avoid re-parsing on every request.
    Creates fresh pipeline instances per request to avoid state leakage.
    """

    _instance: "CMSVSService | None" = None

    def __init__(self) -> None:
        self._config_cache: dict[str, Any] = {}
        self._nvidia_key = os.environ.get("NVIDIA_API_KEY", "")

    @classmethod
    def get(cls) -> "CMSVSService":
        """Return the singleton service instance."""
        if cls._instance is None:
            cls._instance = CMSVSService()
        return cls._instance

    # ── public ────────────────────────────────────────────────────────────────

    @property
    def nvidia_key_set(self) -> bool:
        return bool(self._nvidia_key)

    def list_configs(self) -> list[str]:
        """Return available config names (without .yaml extension)."""
        if not CONFIGS_DIR.exists():
            return []
        return [p.stem for p in CONFIGS_DIR.glob("*.yaml")]

    def get_config_detail(self, config_name: str) -> ConfigDetailResponse:
        """Load and return structured config detail."""
        config = self._load_config(config_name)
        sections = []
        for s in config.sections:
            entities = [
                EntityInfo(
                    entity_name=e.entity_name,
                    entity_description=e.entity_description,
                    entity_extraction_logic=e.entity_extraction_logic,
                    entity_example_value=e.entity_example_value,
                    data_type=e.data_type,
                )
                for e in s.entities
            ]
            sections.append(SectionInfo(
                section_name=s.section_name,
                section_description=s.section_description,
                section_keywords=s.section_keywords,
                entities=entities,
            ))

        total_entities = sum(len(s.entities) for s in config.sections)
        return ConfigDetailResponse(
            config_name=config.config_name,
            version=config.version,
            domain=config.domain,
            total_sections=len(config.sections),
            total_entities=total_entities,
            sections=sections,
        )

    def extract_document(
        self,
        file_path: str,
        config_name: str,
        confidence_threshold: float = 0.75,
    ) -> ExtractionResponse:
        """
        Run entity extraction on a single document.
        """
        self._check_api_key()

        import sys
        sys.path.insert(0, str(SRC_DIR))

        job_id = str(uuid.uuid4())[:8]
        t0 = time.time()

        config = self._load_config(config_name)
        pipeline = self._build_pipeline(config, confidence_threshold)
        entity_values = pipeline._extract_document(file_path)
        elapsed = round(time.time() - t0, 2)


        found = sum(
            1 for fev in entity_values.values()
            if fev.extracted_value is not None
        )
        review = sum(
            1 for fev in entity_values.values()
            if fev.review_required
        )

        entities = {
            name: _fev_to_model(fev)
            for name, fev in entity_values.items()
        }

        inp_tokens = pipeline.llm_client.input_tokens
        out_tokens = pipeline.llm_client.output_tokens
        cost = (inp_tokens / 1_000_000) * 0.11 + (out_tokens / 1_000_000) * 0.34

        return ExtractionResponse(
            job_id=job_id,
            document_path=Path(file_path).name,
            config_name=config_name,
            total_entities=len(entity_values),
            found_count=found,
            review_count=review,
            processing_time_s=elapsed,
            input_tokens=inp_tokens,
            output_tokens=out_tokens,
            total_cost=cost,
            entities=entities,
        )

    def validate_documents(
        self,
        doc_a_path: str,
        doc_b_path: str,
        config_name: str,
        doc_a_name: str,
        doc_b_name: str,
        confidence_threshold: float = 0.75,
    ) -> ValidationResponse:
        """
        Run full validation pipeline on a document pair.
        """
        self._check_api_key()

        import sys
        sys.path.insert(0, str(SRC_DIR))

        job_id = str(uuid.uuid4())[:8]
        t0 = time.time()

        config = self._load_config(config_name)
        pipeline = self._build_pipeline(config, confidence_threshold)

        doc_a_entities = pipeline._extract_document(doc_a_path)
        doc_b_entities = pipeline._extract_document(doc_b_path)

        validation_report = pipeline._validator.validate(
            doc_a_entities=doc_a_entities,
            doc_b_entities=doc_b_entities,
            doc_a_name=doc_a_name,
            doc_b_name=doc_b_name,
        )

        elapsed = round(time.time() - t0, 2)

        # Map sections
        sections_out = []
        for s in validation_report.section_results:
            entities_out = [
                ValidationEntityResult(
                    entity_name=r.entity_name,
                    section_name=r.section_name,
                    doc_a_value=r.doc_a_value,
                    doc_b_value=r.doc_b_value,
                    doc_a_normalized=r.doc_a_normalized,
                    doc_b_normalized=r.doc_b_normalized,
                    validation_status=_safe_str(
                        r.validation_status.value
                        if hasattr(r.validation_status, "value")
                        else r.validation_status
                    ),
                    discrepancy_type=_safe_str(
                        r.discrepancy_type.value
                        if hasattr(r.discrepancy_type, "value")
                        else r.discrepancy_type
                    ),
                    reasoning=r.reasoning,                 # Optional[str] OK
                    confidence=float(r.confidence or 0.0),
                    review_required=bool(r.review_required),
                    fast_path_match=bool(r.fast_path_match),
                )
                for r in s.entity_results
            ]
            sections_out.append(ValidationSectionResult(
                section_name=s.section_name,
                match_count=s.match_count,
                mismatch_count=s.mismatch_count,
                entities=entities_out,
            ))

        total = validation_report.total_entities
        matches = validation_report.total_matches
        mismatches = validation_report.total_mismatches
        review_count = sum(
            1
            for s in validation_report.section_results
            for r in s.entity_results
            if r.review_required
        )
        fast_path = sum(
            1
            for s in validation_report.section_results
            for r in s.entity_results
            if r.fast_path_match
        )
        inp_tokens = pipeline.llm_client.input_tokens
        out_tokens = pipeline.llm_client.output_tokens
        cost = (inp_tokens / 1_000_000) * 0.11 + (out_tokens / 1_000_000) * 0.34


        return ValidationResponse(
            job_id=job_id,
            doc_a_name=doc_a_name,
            doc_b_name=doc_b_name,
            config_name=config_name,
            processing_time_s=elapsed,
            summary=ValidationSummary(
                total_entities=total,
                total_matches=matches,
                total_mismatches=mismatches,
                total_ineligible=total - matches - mismatches,
                match_rate=round(matches / total, 4) if total else 0.0,
                review_required=review_count,
                fast_path_matches=fast_path,
                sections_processed=len(validation_report.section_results),
                input_tokens=inp_tokens,
                output_tokens=out_tokens,
                total_cost=cost
            ),
            sections=sections_out,
            doc_a_entities={
                name: _fev_to_model(fev)
                for name, fev in doc_a_entities.items()
            },
            doc_b_entities={
                name: _fev_to_model(fev)
                for name, fev in doc_b_entities.items()
            },
        )

    def validate_documents_gt(
        self,
        doc_a_path: str,
        doc_b_path: str,
        config_name: str,
        doc_a_name: str,
        doc_b_name: str,
        confidence_threshold: float = 0.75,
    ) -> GroundTruthResponse:
        """
        Run validation and return M2 ground truth format.
        """
        self._check_api_key()

        import sys
        sys.path.insert(0, str(SRC_DIR))

        job_id = str(uuid.uuid4())[:8]
        t0 = time.time()

        config = self._load_config(config_name)
        pipeline = self._build_pipeline(config, confidence_threshold)

        doc_a_entities = pipeline._extract_document(doc_a_path)
        doc_b_entities = pipeline._extract_document(doc_b_path)

        validation_report = pipeline._validator.validate(
            doc_a_entities=doc_a_entities,
            doc_b_entities=doc_b_entities,
            doc_a_name=doc_a_name,
            doc_b_name=doc_b_name,
        )

        from output.report_generator import ReportGenerator
        gt = ReportGenerator().generate_groundtruth_format(validation_report)

        elapsed = round(time.time() - t0, 2)

        entities = [
            GroundTruthEntity(
                entity_name=e.get("entity_name", ""),
                doc_a_value=e.get("doc_a_value"),
                doc_b_value=e.get("doc_b_value"),
                normalized_value=e.get("normalized_value"),
                validation_type=e.get("validation_type", "semantic_match"),
                validation_result=e.get("validation_result", "ineligible"),
            )
            for e in gt.get("entities", [])
        ]

        return GroundTruthResponse(
            job_id=job_id,
            doc_a_name=doc_a_name,
            doc_b_name=doc_b_name,
            config_name=config_name,
            processing_time_s=elapsed,
            entities=entities,
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _check_api_key(self) -> None:
        if not self._nvidia_key:
            raise ValueError(
                "NVIDIA_API_KEY is not set. "
                "Set it as an environment variable before starting the API."
            )

    def _load_config(self, config_name: str):
        """Load config from cache or disk."""
        if config_name in self._config_cache:
            return self._config_cache[config_name]

        import sys
        sys.path.insert(0, str(SRC_DIR))
        from config.config_parser import CMSVSConfigParser

        config_path = CONFIGS_DIR / f"{config_name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config '{config_name}' not found in {CONFIGS_DIR}"
            )

        config = CMSVSConfigParser().load(config_path)
        self._config_cache[config_name] = config
        return config

    def _build_pipeline(self, config, confidence_threshold: float):
        """Build a fresh CMSVSPipeline instance."""
        import sys
        sys.path.insert(0, str(SRC_DIR))

        from models.nvidia_client import NvidiaEmbeddingClient, NvidiaLLMClient
        from pipeline.cmsvs_pipeline import CMSVSPipeline

        embedding_client = NvidiaEmbeddingClient(api_key=self._nvidia_key)
        llm_client = NvidiaLLMClient(api_key=self._nvidia_key)

        return CMSVSPipeline(
            config=config,
            embedding_client=embedding_client,
            llm_client=llm_client,
            confidence_threshold=confidence_threshold,
        )
    
    def preview_extraction(self, file_path: str, config_name: str, section_name: str, overrides: list[dict], confidence_threshold: float):
        import sys
        import time
        if str(SRC_DIR) not in sys.path:
            sys.path.insert(0, str(SRC_DIR))
            
        from ingestion.document_processor import DocumentProcessor
        from input.input_handler import InputHandler
        from shared_types import EntityType, FinalEntityValue
        from extraction.mllm_extractor import MLLMExtractor
        from extraction.expression_orchestrator import ExpressionOrchestrator
        
        self._check_api_key()
        config = self._load_config(config_name)
        target_section = next((sec for sec in config.sections if sec.section_name == section_name), None)
                
        if not target_section:
            raise ValueError(f"Section '{section_name}' not found in config '{config_name}'.")
            
        # 1. Apply temporary description overrides for the preview
        override_map = {o["entity_name"]: o for o in overrides}
        for ent in target_section.entities:
            if ent.entity_name in override_map:
                o = override_map[ent.entity_name]
                ent.entity_description = o.get("entity_description", ent.entity_description)
                ent.entity_example_value = o.get("entity_example_value", ent.entity_example_value)

        # 2. Get the LLM client and instantiate extractors directly
        pipeline = self._build_pipeline(config, confidence_threshold)
        llm_client = pipeline.llm_client
        
        extractor = MLLMExtractor(llm_client=llm_client, confidence_threshold=confidence_threshold)
        orchestrator = ExpressionOrchestrator(mllm_extractor=extractor, confidence_threshold=confidence_threshold)

        # 3. Load Document (taking up to the first 4 pages for quick preview)
        loaded = DocumentProcessor(InputHandler()).process(file_path)
        images_b64 = [pi.image_base64 for pi in loaded.page_images.values()][:4] 
        
        t0 = time.time()
        
        # 4. Extract Entities
        raw_extractions = extractor.extract_section(section=target_section, page_images_b64=images_b64)
        entity_results = extractor.to_entity_results(raw_extractions)
        
        # 5. Process Expressions
        expression_values = orchestrator.process_all_expression_entities(section=target_section, page_images_b64=images_b64)
        
        # 6. Merge Results
        all_values = {}
        for name, er in entity_results.items():
            if name not in expression_values:
                all_values[name] = FinalEntityValue(
                    entity_name=er.entity_name, 
                    extracted_value=er.extracted_value,
                    extraction_status=er.extraction_status, 
                    entity_type=EntityType.DIRECT,
                    confidence=er.confidence, 
                    source_page=er.source_page,
                    source_region=(er.raw_context or "")[:80], 
                    raw_context=er.raw_context,
                    review_required=er.review_required, 
                    fallback_triggered=er.fallback_triggered,
                    expression_audit=None,
                )
        all_values.update(expression_values)
        
        elapsed = time.time() - t0
        
        # Convert FinalEntityValue -> ExtractedEntity Pydantic Model
        entities_out = [_fev_to_model(fev) for fev in all_values.values()]
        
        return {
            "processing_time_s": elapsed, 
            "entities": entities_out
        }
    def patch_entities(self, config_name: str, section_name: str, updates: list):
        import yaml
        from datetime import datetime
        import shutil
        
        config_path = CONFIGS_DIR / f"{config_name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config '{config_name}' not found.")
            
        with open(config_path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
            
        override_map = {u.entity_name: u for u in updates}
        for sec in raw.get("sections", []):
            if sec.get("section_name") == section_name:
                for ent in sec.get("entities", []):
                    if ent.get("entity_name") in override_map:
                        o = override_map[ent.get("entity_name")]
                        ent["entity_description"] = o.entity_description
                        ent["entity_example_value"] = o.entity_example_value
                        
        backup_name = f"{config_name}_{int(datetime.now().timestamp())}.yaml.bak"
        backup_path = CONFIGS_DIR / backup_name
        shutil.copy(config_path, backup_path)
        
        with open(config_path, "w", encoding="utf-8") as fh:
            yaml.dump(raw, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
        self._config_cache.pop(config_name, None)
        return {"message": "Config updated successfully.", "backup_path": str(backup_path)}