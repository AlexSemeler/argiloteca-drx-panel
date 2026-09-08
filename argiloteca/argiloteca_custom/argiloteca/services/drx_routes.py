"""Versioned inventory and shared boundary for public DRX routes.

Route registration remains compatible with the existing ``argiloteca``
blueprint while handlers migrate incrementally out of ``views.py``.
"""

from __future__ import annotations


DRX_PUBLIC_ENDPOINTS = (
    "drx_comparacao",
    "api_drx_registros",
    "api_drx_raw_snapshot",
    "api_drx_raw_snapshot_sugestoes",
    "api_drx_difratograma",
    "api_drx_technical_report",
    "drx_technical_report_html",
    "drx_selection_report_html",
    "drx_selection_report_pdf",
    "api_drx_science_engine_status",
    "api_drx_gsas2_status",
    "api_drx_gsas2_validate_pattern",
    "api_drx_gsas2_compare_job",
    "api_drx_cif_simulate",
    "api_drx_ngc_workflow",
    "api_drx_selection_report",
    "api_drx_runs",
    "api_drx_run_detail",
    "api_drx_references",
    "api_drx_external_job_submit",
    "api_drx_external_job_status",
    "api_drx_reference_compare",
    "api_drx_reference_compare_indexed",
    "api_drx_neural_evidence",
    "api_drx_externo_curva",
    "api_drx_importar",
)


def assert_drx_endpoints_registered(app) -> tuple[str, ...]:
    """Return missing endpoint names without changing route registration."""

    registered = {rule.endpoint.rsplit(".", 1)[-1] for rule in app.url_map.iter_rules()}
    return tuple(name for name in DRX_PUBLIC_ENDPOINTS if name not in registered)
