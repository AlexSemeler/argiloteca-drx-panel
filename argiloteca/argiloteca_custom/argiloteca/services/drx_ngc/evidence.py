"""N/G/C evidence-summary boundary."""

from __future__ import annotations


def build_ngc_evidence_summary_contract(workflow_group):
    from ..drx_ngc_workflow import build_ngc_evidence_summary_contract as build

    return build(workflow_group)
