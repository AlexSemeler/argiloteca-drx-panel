"""
Projeto: Painel DRX Argiloteca

Descrição:
Helpers for linking Argiloteca minerals to external semantic sources.

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

from .matcher import MineralMatcher
from .vocabulary import VocabularyBundle, VocabularyTerm, load_vocabulary_bundle

__all__ = [
    "MineralMatcher",
    "VocabularyBundle",
    "VocabularyTerm",
    "load_vocabulary_bundle",
]
