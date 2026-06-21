"""
Projeto: Painel DRX Argiloteca

Descrição:
Reusable entrypoint for N/G/C clay-mineral workflow rules.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br


Instituição:
Universidade Federal do Rio Grande do Sul (UFRGS)

Projeto:
Argiloteca / CPAA

Licença:
Preservar licença existente no repositório.

Última revisão:
2026-06-21

Observação:
Este arquivo integra o sistema de análise, comparação e interpretação de difratogramas de raios X para argilominerais.
"""

from __future__ import annotations


def build_ngc_workflow(items):
    """Delegate to the current service implementation while core API stabilizes."""
    from argiloteca.services.drx_ngc_workflow import build_ngc_workflow as _build

    return _build(items)
