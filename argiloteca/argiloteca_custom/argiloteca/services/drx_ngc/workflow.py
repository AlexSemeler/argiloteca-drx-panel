"""N/G/C orchestration boundary."""

from __future__ import annotations


def build_ngc_workflow(items):
    from ..drx_ngc_workflow import build_ngc_workflow as build

    return build(items)
