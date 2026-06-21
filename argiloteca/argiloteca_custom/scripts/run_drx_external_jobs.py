#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Offline worker for filesystem-backed DRX external jobs. GSAS-II/DARA are never executed inside the Flask request path. This worker claims queued jobs and runs an external command only when the corresponding adapter environment variable is configured.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br

Colaboradores:
- Lucas Jantsch
- Arthur Oliveira

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

import argparse
import sys
from pathlib import Path


CUSTOM_DIR = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parents[2]
for path in (APP_DIR, CUSTOM_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from argiloteca.services.drx_external_jobs import claim_next_external_job, run_external_job_adapter


def main():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    parser = argparse.ArgumentParser(description="Run queued DRX external jobs.")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of queued jobs to process. 0 means no fixed limit.")
    args = parser.parse_args()
    processed = 0
    while True:
        if args.limit and processed >= args.limit:
            break
        job = claim_next_external_job()
        if not job:
            break
        run_external_job_adapter(job)
        processed += 1
        if args.once:
            break
    print(f"processed={processed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
