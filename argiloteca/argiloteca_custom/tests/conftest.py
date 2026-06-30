"""Fixtures sintéticas para testes do detector de picos DRX."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _gaussian(x: np.ndarray, center: float, fwhm: float, height: float) -> np.ndarray:
    sigma = fwhm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    return height * np.exp(-0.5 * ((x - center) / sigma) ** 2)


@pytest.fixture
def ground_truth_peaks() -> list[dict[str, float]]:
    """Retorna posições e larguras reais dos picos sintéticos principais."""
    return [
        {"position_two_theta_deg": 12.0, "fwhm_deg": 0.28, "height": 120.0},
        {"position_two_theta_deg": 26.6, "fwhm_deg": 0.22, "height": 200.0},
        {"position_two_theta_deg": 42.0, "fwhm_deg": 0.42, "height": 90.0},
    ]


@pytest.fixture
def synthetic_csv(tmp_path: Path, ground_truth_peaks: list[dict[str, float]]) -> Path:
    """Grava um difratograma sintético reprodutível em CSV."""
    rng = np.random.default_rng(12345)
    two_theta = np.arange(5.0, 65.0 + 0.02, 0.02)
    baseline = 20.0 + 0.03 * (two_theta - 5.0) + 0.0008 * (two_theta - 35.0) ** 2
    signal = baseline.copy()
    for peak in ground_truth_peaks:
        signal += _gaussian(
            two_theta,
            peak["position_two_theta_deg"],
            peak["fwhm_deg"],
            peak["height"],
        )
    intensity = signal + rng.normal(0.0, 2.5, size=two_theta.size)
    filepath = tmp_path / "synthetic_xrd.csv"
    pd.DataFrame({"two_theta": two_theta, "intensity": intensity}).to_csv(filepath, index=False)
    return filepath

