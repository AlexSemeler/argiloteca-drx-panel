"""
Projeto: Painel DRX Argiloteca

Descrição:
Mindat scraping helpers for curated semantic enrichment.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br



Projeto:
Argiloteca / CPAA

Licença:
Preservar licença existente no repositório.

Última revisão:
2026-06-21

Observação:
Este arquivo integra o sistema de análise, comparação e interpretação de difratogramas de raios X para argilominerais.
"""

from .pipeline import run_mindat_pipeline

__all__ = ["run_mindat_pipeline"]
