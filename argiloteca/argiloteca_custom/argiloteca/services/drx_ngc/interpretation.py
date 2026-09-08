"""N/G/C scientific interpretation boundary."""

from __future__ import annotations


def interpret_clay_minerals_ngc(
    sample_id,
    peaks_by_preparation,
    wavelength_a=None,
    metadata=None,
    vocabulary=None,
    diagnostic_rules=None,
    options=None,
):
    from ..drx_ngc_workflow import interpret_clay_minerals_ngc as interpret

    return interpret(
        sample_id,
        peaks_by_preparation,
        wavelength_a=wavelength_a,
        metadata=metadata,
        vocabulary=vocabulary,
        diagnostic_rules=diagnostic_rules,
        options=options,
    )
