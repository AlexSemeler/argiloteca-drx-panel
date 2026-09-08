"""N/G/C rule-source provenance boundary."""

from __future__ import annotations


def build_ngc_source_rule_summary_contract(workflow_group):
    from ..drx_ngc_workflow import build_ngc_source_rule_summary_contract as build

    return build(workflow_group)
