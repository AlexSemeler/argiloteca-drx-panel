"""
Projeto: Painel DRX Argiloteca

Descrição:
Componente do pacote Argiloteca Custom usado para integrar serviços científicos, visualizações e metadados ao InvenioRDM.

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

from .views import create_blueprint


class ArgilotecaUIExtension:
    """Extensão UI da Argiloteca."""

    def __init__(self, app=None):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            app: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            app: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        bp = create_blueprint(app)
        if bp.name not in app.blueprints:
            app.register_blueprint(bp)
        app.extensions["argiloteca_ui"] = self
