"""N/G/C sample grouping boundary."""

from __future__ import annotations


def build_ngc_backend_grouping_contract(items):
    from ..drx_ngc_workflow import build_ngc_backend_grouping_contract as build

    return build(items)
