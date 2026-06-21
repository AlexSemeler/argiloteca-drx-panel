"""
Projeto: Painel DRX Argiloteca

Descrição:
Rate-limited, cached HTTP client for controlled Mindat collection.

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

from dataclasses import dataclass
from hashlib import sha1
import json
from pathlib import Path
import ssl
import time
from typing import Any
from urllib import error, request


@dataclass
class FetchResult:
    """Result of a cached or remote request."""

    url: str
    ok: bool
    status: int | None
    body: str | None
    from_cache: bool
    cache_path: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        return {
            "url": self.url,
            "ok": self.ok,
            "status": self.status,
            "from_cache": self.from_cache,
            "cache_path": self.cache_path,
            "error": self.error,
        }


class MindatClient:
    """Simple HTTP client with cache and polite request spacing."""

    def __init__(
        self,
        cache_dir: Path,
        allow_network: bool = False,
        timeout: int = 20,
        min_interval: float = 1.5,
        verify_ssl: bool = True,
        user_agent: str = "ArgilotecaMindatCurator/0.1 (+https://argiloteca.local)",
    ):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            cache_dir: Valor de entrada consumido por esta etapa do fluxo.
            allow_network: Valor de entrada consumido por esta etapa do fluxo.
            timeout: Valor de entrada consumido por esta etapa do fluxo.
            min_interval: Valor de entrada consumido por esta etapa do fluxo.
            verify_ssl: Valor de entrada consumido por esta etapa do fluxo.
            user_agent: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        self.cache_dir = Path(cache_dir)
        self.allow_network = allow_network
        self.timeout = timeout
        self.min_interval = min_interval
        self.verify_ssl = verify_ssl
        self.user_agent = user_agent
        self._last_request_ts = 0.0
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, url: str) -> Path:
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            url: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        return self.cache_dir / f"{sha1(url.encode('utf-8')).hexdigest()}.json"

    def fetch(self, url: str) -> FetchResult:
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            url: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        cache_path = self._cache_path(url)
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return FetchResult(
                url=url,
                ok=bool(cached.get("ok")),
                status=cached.get("status"),
                body=cached.get("body"),
                from_cache=True,
                cache_path=str(cache_path),
                error=cached.get("error"),
            )

        if not self.allow_network:
            return FetchResult(
                url=url,
                ok=False,
                status=None,
                body=None,
                from_cache=False,
                cache_path=str(cache_path),
                error="network_disabled",
            )

        wait = self.min_interval - (time.time() - self._last_request_ts)
        if wait > 0:
            time.sleep(wait)

        headers = {"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"}
        req = request.Request(url, headers=headers)
        context = None if self.verify_ssl else ssl._create_unverified_context()

        try:
            with request.urlopen(req, timeout=self.timeout, context=context) as response:
                body = response.read().decode("utf-8", errors="replace")
                result = FetchResult(
                    url=url,
                    ok=True,
                    status=response.status,
                    body=body,
                    from_cache=False,
                    cache_path=str(cache_path),
                )
        except error.HTTPError as exc:
            result = FetchResult(
                url=url,
                ok=False,
                status=exc.code,
                body=exc.read().decode("utf-8", errors="replace"),
                from_cache=False,
                cache_path=str(cache_path),
                error=f"http_{exc.code}",
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            result = FetchResult(
                url=url,
                ok=False,
                status=None,
                body=None,
                from_cache=False,
                cache_path=str(cache_path),
                error=str(exc),
            )

        cache_path.write_text(
            json.dumps(result.to_dict() | {"body": result.body}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._last_request_ts = time.time()
        return result
