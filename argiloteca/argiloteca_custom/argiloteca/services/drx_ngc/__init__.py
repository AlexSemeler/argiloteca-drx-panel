"""Cohesive public boundaries for the legacy-compatible N/G/C workflow."""

from .evidence import build_ngc_evidence_summary_contract
from .grouping import build_ngc_backend_grouping_contract
from .interpretation import interpret_clay_minerals_ngc
from .source_rules import build_ngc_source_rule_summary_contract
from .workflow import build_ngc_workflow

__all__ = [
    "build_ngc_backend_grouping_contract",
    "build_ngc_evidence_summary_contract",
    "build_ngc_source_rule_summary_contract",
    "build_ngc_workflow",
    "interpret_clay_minerals_ngc",
]
