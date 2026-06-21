"""
Projeto: Painel DRX Argiloteca

Descrição:
Reusable wrappers for advanced DRX preprocessing and peak fitting.

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


def process_advanced_als_curve(*args, **kwargs):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        *args: Valor de entrada consumido por esta etapa do fluxo.
        **kwargs: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    from argiloteca.services.drx import process_advanced_als_curve as _process

    return _process(*args, **kwargs)


def advanced_als_summary(*args, **kwargs):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        *args: Valor de entrada consumido por esta etapa do fluxo.
        **kwargs: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    from argiloteca.services.drx import advanced_als_summary as _summary

    return _summary(*args, **kwargs)


def compact_advanced_als_curve(*args, **kwargs):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        *args: Valor de entrada consumido por esta etapa do fluxo.
        **kwargs: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    from argiloteca.services.drx import compact_advanced_als_curve as _compact

    return _compact(*args, **kwargs)
