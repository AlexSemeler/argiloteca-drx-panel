# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: provenance_tracker.py
#
# Descrição.........:
# Implementa geometria de DRX, Lei de Bragg, conversão 2θ/d-spacing e validação físico-cristalográfica.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""
Implementa geometria de DRX, Lei de Bragg, conversão 2θ/d-spacing e validação físico-cristalográfica.

Responsabilidades:
    - preservar contratos públicos e estruturas JSON consumidas pelo painel;
    - registrar proveniência científica e técnica das operações realizadas;
    - manter separadas etapas de leitura, processamento, diagnóstico e exportação;
    - documentar limites de interpretação mineralógica quando houver regras DRX.

Notas científicas:
    Em módulos DRX, 2θ representa o eixo angular medido no difratograma e
    d-spacing representa o espaçamento interplanar calculado pela Lei de Bragg
    (nλ = 2d sen θ). Preparações natural, glicolada e calcinada são usadas para
    observar expansão, colapso, persistência ou destruição de picos basais.
"""

from __future__ import annotations

from importlib.resources import files
import json

DATA_PACKAGE = "argiloteca_custom.argiloteca_drx.diagnostics.data.diffraction_geometry"


def load_json(name: str):
    """
    Executa a etapa `load_json` do módulo.

        Args:
            name:
                Parâmetro utilizado pela etapa `load_json`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    try:
        return json.loads((files(DATA_PACKAGE) / name).read_text(encoding="utf-8"))
    except Exception:
        from pathlib import Path
        here = Path(__file__).resolve().parents[1] / "diagnostics" / "data" / "diffraction_geometry"
        return json.loads((here / name).read_text(encoding="utf-8"))
