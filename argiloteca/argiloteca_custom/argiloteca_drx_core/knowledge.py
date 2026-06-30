"""Fachada de acesso às bases executáveis dos capítulos científicos.

Este módulo permite que scripts, workers e relatórios consultem as bases dos
Capítulos 3, 7 e 8 por uma API única, sem conhecer a localização interna dos
módulos em `argiloteca_drx.diagnostics`.
"""

from __future__ import annotations


def get_scientific_knowledge(chapter=None):
    """Retorna bases de conhecimento por capitulo.

    Args:
        chapter: `3`, `7`, `8` ou `None`. Quando `None`, retorna as três bases.

    Returns:
        dict: Base solicitada ou dicionario com `chapter3`, `chapter7` e
        `chapter8`.
    """
    from argiloteca_drx.diagnostics.chapter3_geometry_knowledge import get_chapter3_geometry_knowledge
    from argiloteca_drx.diagnostics.chapter7_knowledge import get_chapter7_knowledge
    from argiloteca_drx.diagnostics.chapter8_mixed_layer_knowledge import get_chapter8_mixed_layer_knowledge

    requested = str(chapter).strip() if chapter is not None else None
    if requested in {"3", "chapter3"}:
        return get_chapter3_geometry_knowledge()
    if requested in {"7", "chapter7"}:
        return get_chapter7_knowledge()
    if requested in {"8", "chapter8"}:
        return get_chapter8_mixed_layer_knowledge()
    return {
        "chapter3": get_chapter3_geometry_knowledge(),
        "chapter7": get_chapter7_knowledge(),
        "chapter8": get_chapter8_mixed_layer_knowledge(),
    }


def get_rule_indexes():
    """Retorna índices de regras/equações usados por XAI e auditoria."""
    from argiloteca_drx.diagnostics.chapter3_geometry_knowledge import chapter3_equation_index, chapter3_rule_index
    from argiloteca_drx.diagnostics.chapter7_knowledge import chapter7_rule_index
    from argiloteca_drx.diagnostics.chapter8_mixed_layer_knowledge import chapter8_rule_index

    return {
        "chapter3_rules": chapter3_rule_index(),
        "chapter3_equations": chapter3_equation_index(),
        "chapter7_rules": chapter7_rule_index(),
        "chapter8_rules": chapter8_rule_index(),
    }


def scientific_source_summary():
    """Resume fontes bibliograficas registradas nas bases executaveis."""
    knowledge = get_scientific_knowledge()
    return {
        key: {
            "source_id": value["source"]["source_id"],
            "chapter": value["source"]["chapter"],
            "source_book": value["source"].get("source_book"),
            "local_pdf": value["source"].get("local_pdf"),
            "policy": value["source"].get("policy"),
        }
        for key, value in knowledge.items()
    }
