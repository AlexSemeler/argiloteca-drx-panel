# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: adapter_geometry_to_simulation.py
#
# Descrição.........:
# Implementa simulação 1D de padrões 00l, cálculo de intensidades e comparação observado × calculado.
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
Implementa simulação 1D de padrões 00l, cálculo de intensidades e comparação observado × calculado.

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

def geometry_payload_to_simulation_inputs(payload):
    """
    Executa a etapa `geometry_payload_to_simulation_inputs` do módulo.

        Args:
            payload:
                Parâmetro utilizado pela etapa `geometry_payload_to_simulation_inputs`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    return {'theta_deg': payload.get('theta_deg'), 'd_A': payload.get('d_A'), 'wavelength_A': payload.get('wavelength_A')}

