# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: composition_estimator.py
#
# Descrição.........:
# Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.
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
Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.

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

"""Estimadores de composicao baseados nas tabelas do Capitulo 8.

No painel DRX, este modulo serve para converter uma medida observada
posicional, como Delta 2theta ou uma reflexao diagnostica, na linha tabelada
mais proxima. O retorno carrega o `validation_status` da tabela para impedir
que valores de OCR pendentes sejam tratados como estimativa definitiva.
"""

from .provenance_tracker import load_json


def _nearest(rows, key, value):
    """Seleciona a linha numerica mais proxima dentro de uma tabela curada."""
    usable = [r for r in rows if r.get(key) is not None]
    if value is None or not usable:
        return None
    return min(usable, key=lambda r: abs(float(r[key]) - float(value)))


def estimate_from_table(table_id: str, feature_key: str, value: float) -> dict | None:
    """Estima composicao por uma tabela do Capitulo 8.

    Args:
        table_id: Identificador da tabela, por exemplo `table_8_3`.
        feature_key: Coluna numerica usada para busca, como
            `delta_deg2theta` ou `low_angle_d_A`.
        value: Valor observado no difratograma.

    Returns:
        Dicionario com componente estimado, percentual, linha tabelada e status
        de validacao, ou `None` quando a tabela/coluna nao permite estimativa.
    """
    tables = {t["table_id"]: t for t in load_json("chapter8_tables.json")}
    table = tables.get(table_id)
    if not table:
        return None
    row = _nearest(table.get("rows", []), feature_key, value)
    if not row:
        return None
    component = {"table_8_3": "illite", "table_8_4": "chlorite", "table_8_6": "kaolinite", "table_8_7": "vermiculite"}.get(table_id, "component")
    percent_key = f"percent_{component}"
    return {"table": table_id, "component": component, "percent": row.get(percent_key), "matched_row": row, "validation_status": table.get("validation_status", "valid")}
