"""Value object and resolver for explicit X-ray radiation metadata."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


KNOWN_RADIATIONS = MappingProxyType(
    {
        "cuka": ("CuKa", 1.5406),
        "cuka1": ("CuKa1", 1.54056),
        "cuka2": ("CuKa2", 1.54439),
        "moka": ("MoKa", 0.71073),
        "crka": ("CrKa", 2.2897),
        "feka": ("FeKa", 1.93604),
        "coka": ("CoKa", 1.78897),
    }
)


def _normalise_label(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .casefold()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace("α", "a")
        .replace("alpha", "a")
    )


@dataclass(frozen=True)
class RadiationSpec:
    """Explicit, immutable radiation description used by DRX calculations."""

    label: str | None = None
    wavelength_angstrom: float | None = None
    source: str = "unavailable"
    status: str = "available"
    unit: str = "angstrom"
    warnings: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)

    @property
    def available(self) -> bool:
        value = self.wavelength_angstrom
        return (
            self.status == "available"
            and value is not None
            and math.isfinite(float(value))
            and float(value) > 0
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["available"] = self.available
        payload["provenance"] = dict(self.provenance)
        payload["warnings"] = list(self.warnings)
        return payload


def resolve_radiation(
    value: Any = None,
    *,
    label: str | None = None,
    source: str = "user_param",
    provenance: Mapping[str, Any] | None = None,
) -> RadiationSpec:
    """Resolve only explicit labels or positive finite wavelengths."""

    provenance = dict(provenance or {})
    if isinstance(value, RadiationSpec):
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        return RadiationSpec(
            source="unavailable",
            status="unavailable",
            warnings=("Comprimento de onda ou fonte de radiação não informado.",),
            provenance=provenance,
        )
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = None
    if numeric is not None:
        if math.isfinite(numeric) and numeric > 0:
            return RadiationSpec(
                label=label,
                wavelength_angstrom=numeric,
                source=source,
                provenance=provenance,
            )
        return RadiationSpec(
            label=label,
            source=source,
            status="invalid",
            warnings=("Comprimento de onda deve ser finito e positivo.",),
            provenance=provenance,
        )
    key = _normalise_label(value)
    known = KNOWN_RADIATIONS.get(key)
    if known:
        canonical, wavelength = known
        return RadiationSpec(
            label=canonical,
            wavelength_angstrom=wavelength,
            source=source,
            provenance=provenance,
        )
    return RadiationSpec(
        label=str(value).strip(),
        source=source,
        status="unknown",
        warnings=("Fonte de radiação desconhecida; informe o comprimento de onda.",),
        provenance=provenance,
    )
