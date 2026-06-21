"""
Projeto: Painel DRX Argiloteca

Descrição:
Componente do pacote Argiloteca Custom usado para integrar serviços científicos, visualizações e metadados ao InvenioRDM.

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

from flask import request

from .traceability import install_ui_serializer_compat
from .views import create_blueprint


def _install_validation_error_logging(app):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        app: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if getattr(app, "_argiloteca_validation_error_logging", False):
        return

    @app.after_request
    def log_api_validation_errors(response):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            response: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        if (
            response.status_code == 400
            and request.path.startswith("/api/records")
            and request.method in {"POST", "PUT"}
        ):
            body = response.get_data(as_text=True)
            app.logger.warning(
                "ARGILOTECA_API_VALIDATION_ERROR %s %s: %s",
                request.method,
                request.path,
                body[:4000],
            )
        return response

    app._argiloteca_validation_error_logging = True


def create_app(app):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        app: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    install_ui_serializer_compat()
    _install_validation_error_logging(app)
    blueprint = create_blueprint(app)
    app.register_blueprint(blueprint)
