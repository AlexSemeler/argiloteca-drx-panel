/**
 * Projeto: Painel DRX Argiloteca
 * Descrição:
 * Orquestra serviços, rotas ou interface do painel DRX para leitura, comparação, interpretação e relatório de difratogramas de raios X da Argiloteca.
 * Autor:
 * Alexandre Ribas Semeler
 * E-mail: alexandre.semeler@ufrgs.br
 * E-mail de documentação científica revisada: alexandre.semler@ufrgs.br
 * Projeto:
 * Argiloteca / CPAA
 * Última revisão:
 * 2026-06-21
 * Este arquivo integra o sistema de análise,
 * comparação e interpretação de difratogramas
 * de raios X para argilominerais.
 * Fundamentação científica revisada:
 * Brindley & Brown (1980), Bailey (1980/1988), Moore & Reynolds (1989/1997),
 * Drits & Tchoubar (1990), Lanson & Bouchet (1995), Meunier, Clays (2005),
 * fluxograma USGS e referências empíricas Pré-Sal UFRGS/Petrobras.
 * Política: interpretação auxiliar, não confirmatória, sem identificação por pico isolado.
 */

(function () {
  // Painel interativo de comparacao DRX. O arquivo organiza fontes diferentes
  // (registro, pacote, snapshot, upload temporario, RRUFF e triagem) em um unico
  // estado de curvas selecionadas, sem persistir alteracoes no navegador.
  const root = document.querySelector(".argilo-drx");
  if (!root) return;

  const recordsUrl = root.dataset.recordsUrl;
  const rawSnapshotUrl = root.dataset.rawSnapshotUrl;
  const rawSnapshotSuggestionsUrl = root.dataset.rawSnapshotSuggestionsUrl;
  const diffractogramUrlTemplate = root.dataset.diffractogramUrlTemplate;
  const neuralEvidenceUrlTemplate = root.dataset.neuralEvidenceUrlTemplate;
  const technicalReportUrlTemplate = root.dataset.technicalReportUrlTemplate;
  const referenceCompareUrlTemplate = root.dataset.referenceCompareUrlTemplate;
  const ngcWorkflowUrl = root.dataset.ngcWorkflowUrl;
  const selectionReportUrl = root.dataset.selectionReportUrl;
  const packageUrlTemplate = root.dataset.packageUrlTemplate;
  const packageCurveUrlTemplate = root.dataset.packageCurveUrlTemplate;
  const externalRawUrl = root.dataset.externalRawUrl;
  const gsas2StatusUrl = root.dataset.gsas2StatusUrl;
  const gsas2ValidateUrl = root.dataset.gsas2ValidateUrl;
  const xrdnetSummaryUrl = root.dataset.xrdnetSummaryUrl;
  const geologistTriageUrl = root.dataset.geologistTriageUrl;
  const geologistSimilarityReviewUrl = root.dataset.geologistSimilarityReviewUrl;
  const rruffOdrCurvesUrl = root.dataset.rruffOdrCurvesUrl;
  const mineralDetailUrlBase = root.dataset.mineralDetailUrlBase || "/argilominerais/";
  const diagnosticPeakRulesCatalogUrl = root.dataset.diagnosticPeakRulesUrl || "/argiloteca/static/data/diagnostic_peak_rules_catalog.json";
  const contextRecordId = root.dataset.contextRecordId || "";
  const contextRecordTitle = root.dataset.contextRecordTitle || "";
  const EXTERNAL_RAW_UPLOAD_TIMEOUT_MS = 240000;
  const NGC_AXIS_ALIGNMENT_MIN_OFFSET = 0.05;
  const DRX_SHOW_RRUFF_ODR_REVIEW_LINK = false;
  const DRX_SHOW_METHODOLOGY_LIMITATIONS = false;
  const DRX_SHOW_OBSERVED_PEAK_DIAGNOSTIC_TABLE = false;
  // Catalogo autorizado para transformar candidatos em links locais; os dados
  // do template sobrescrevem este fallback quando disponiveis.
  const defaultAuthorizedMineralSlugs = [
    "allophane", "amesite", "antigorite", "baileychlore", "beidellite", "bentonite", "berthierine", "bertossaite",
    "biotite", "brammallite", "celadonite", "chamosite", "chlorite", "chlorite-smectite", "chlorite-vermiculite",
    "chrysotile", "clinochlore", "clintonite", "cookeite", "corrensite", "cronstedtite", "dickite", "donbassite",
    "endellite", "falcondoite", "fullers-earth", "glauconite", "greenalite", "greenwoodite", "halloysite",
    "hectorite", "hisingerite", "hydrobiotite", "hydrotalcite", "illite", "illite-smectite", "imogolite", "iowaite",
    "kalifersite", "kaolin", "kaolinite", "kaolinite-smectite", "kerolite", "lepidolite", "lizardite", "loughlinite",
    "manandonite", "manasseite", "margarite", "minnesotaite", "montmorillonite", "motukoreaite", "muscovite",
    "nacrite", "nimite", "nontronite", "odinite", "palygorskite", "paragonite", "pennantite", "phlogopite",
    "pimelite", "pyrophyllite", "raite", "saponite", "sauconite", "sepiolite", "sericite", "serpentine", "smectite",
    "stevensite", "stilpnomelane", "sudoite", "swinefordite", "talc", "tuperssuatsiaite", "vermiculite",
    "volkonskoite", "windhoekite", "yakhontovite", "yofortierite"
  ];
  const defaultAuthorizedMineralAliases = {
    caulinita: "kaolinite",
    clorita: "chlorite",
    "clorita-esmectita": "chlorite-smectite",
    "clorita-vermiculita": "chlorite-vermiculite",
    esmectita: "smectite",
    ilita: "illite",
    "ilita-esmectita": "illite-smectite",
    montmorilonita: "montmorillonite",
    paligorsquita: "palygorskite",
    sepiolita: "sepiolite",
    serpentina: "serpentine",
    talco: "talc",
    vermiculita: "vermiculite",
  };
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function parseAuthorizedMineralSlugs() {
    try {
      const parsed = JSON.parse(root.dataset.authorizedMineralSlugs || "[]");
      return parsed && parsed.length ? parsed : defaultAuthorizedMineralSlugs;
    } catch (error) {
      return defaultAuthorizedMineralSlugs;
    }
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function parseAuthorizedMineralAliases() {
    try {
      const parsed = JSON.parse(root.dataset.authorizedMineralAliases || "{}");
      return Object.assign({}, defaultAuthorizedMineralAliases, parsed && typeof parsed === "object" ? parsed : {});
    } catch (error) {
      return defaultAuthorizedMineralAliases;
    }
  }
  const authorizedMineralSlugs = new Set(parseAuthorizedMineralSlugs());
  const authorizedMineralAliases = parseAuthorizedMineralAliases();
  const form = root.querySelector('[data-role="filters-form"]');
  const recordListEl = root.querySelector('[data-role="record-list"]');
  const statusEl = root.querySelector('[data-role="status"]');
  let statusProgressTimer = null;
  let statusProgressTick = 0;
  function stopStatusProgress(finalMessage) {
    if (statusProgressTimer) {
      window.clearInterval(statusProgressTimer);
      statusProgressTimer = null;
    }
    statusProgressTick = 0;
    if (finalMessage && statusEl) statusEl.textContent = finalMessage;
  }
  function startStatusProgress(baseMessage, steps) {
    if (!statusEl) return;
    stopStatusProgress();
    const progressSteps = steps && steps.length ? steps : ["processando dados"];
    const render = function () {
      const step = progressSteps[statusProgressTick % progressSteps.length];
      const dots = ".".repeat((statusProgressTick % 3) + 1);
      statusEl.textContent = baseMessage + " · " + step + dots;
      statusProgressTick += 1;
    };
    render();
    statusProgressTimer = window.setInterval(render, 900);
  }
  const chartEl = root.querySelector('[data-role="chart"]');
  const tooltipEl = root.querySelector('[data-role="tooltip"]');
  const modeEl = root.querySelector('[data-role="view-mode"]');
  const selectedSummaryEl = root.querySelector('[data-role="selected-summary"]');
  const plotlyChartEl = root.querySelector('[data-role="plotly-chart"]');
  const mineralPanelEl = root.querySelector('[data-role="mineral-panel"]');
  const mineralPanelSectionEl = root.querySelector('[data-role="mineral-panel-section"]');
  const mineralPanelFullscreenEls = Array.from(root.querySelectorAll('[data-role="mineral-panel-fullscreen"], [data-role="drx-header-fullscreen"]'));
  const mineralPanelFullscreenEl = mineralPanelFullscreenEls[0] || null;
  const drxFullscreenSectionEl = root.querySelector('[data-role="drx-fullscreen-section"]') || mineralPanelSectionEl;
  const clearSelectionEl = root.querySelector('[data-role="clear-selection"]');
  const resetZoomEl = root.querySelector('[data-role="reset-zoom"]');
  const togglePeaksEl = root.querySelector('[data-role="toggle-peaks"]');
  const exportCsvEl = root.querySelector('[data-role="export-csv"]');
  const exportJsonEl = root.querySelector('[data-role="export-json"]');
  const exportSvgEl = root.querySelector('[data-role="export-svg"]');
  const exportPdfEl = root.querySelector('[data-role="export-pdf"]');
  const externalRawButtonEl = root.querySelector('[data-role="external-raw-button"]');
  const externalRawFileEl = root.querySelector('[data-role="external-raw-file"]');
  const referenceCompareButtonEl = root.querySelector('[data-role="reference-compare-button"]');
  const referenceCompareFileEl = root.querySelector('[data-role="reference-compare-file"]');
  const openRawPickerEl = root.querySelector('[data-role="open-raw-picker"]');
  const closeRawPickerEl = root.querySelector('[data-role="close-raw-picker"]');
  const rawPickerEl = root.querySelector('[data-role="raw-picker"]');
  const rawPickerFormEl = root.querySelector('[data-role="raw-picker-form"]');
  const rawPickerStatusEl = root.querySelector('[data-role="raw-picker-status"]');
  const rawPickerListEl = root.querySelector('[data-role="raw-picker-list"]');
  const gsas2ValidationPanelEl = root.querySelector('[data-role="gsas2-validation-panel"]');
  const gsas2StatusBadgeEl = root.querySelector('[data-role="gsas2-status-badge"]');
  const gsas2StatusSummaryEl = root.querySelector('[data-role="gsas2-status-summary"]');
  const openSuggestionsEl = root.querySelector('[data-role="open-suggestions"]');
  const openTriageQueueEl = root.querySelector('[data-role="open-triage-queue"]');
  const openSuggestionsFromRawEl = root.querySelector('[data-role="open-suggestions-from-raw"]');
  const loadNgcSuggestionsEl = root.querySelector('[data-role="load-ngc-suggestions"]');
  const loadTriageQueueEl = root.querySelector('[data-role="load-triage-queue"]');
  const closeSuggestionsEl = root.querySelector('[data-role="close-suggestions"]');
  const suggestionsPanelEl = root.querySelector('[data-role="suggestions-panel"]');
  const suggestionsStatusEl = root.querySelector('[data-role="suggestions-status"]');
  const suggestionsListEl = root.querySelector('[data-role="suggestions-list"]');
  const toggleRruffOdrEl = root.querySelector('[data-role="toggle-rruff-odr"]');
  const closeRruffOdrEl = root.querySelector('[data-role="close-rruff-odr"]');
  const rruffOdrPanelEl = root.querySelector('[data-role="rruff-odr-panel"]');
  const rruffOdrCurveEl = root.querySelector('[data-role="rruff-odr-curve"]');
  const rruffOdrTypeEl = root.querySelector('[data-role="rruff-odr-type"]');
  const rruffOdrNormalizeEl = root.querySelector('[data-role="rruff-odr-normalize"]');
  const rruffOdrPeaksEl = root.querySelector('[data-role="rruff-odr-peaks"]');
  const rruffOdrStatusEl = root.querySelector('[data-role="rruff-odr-status"]');
  const rruffOdrChartEl = root.querySelector('[data-role="rruff-odr-chart"]');
  const rruffOdrMetaEl = root.querySelector('[data-role="rruff-odr-meta"]');
  const sampleOptionsEl = root.querySelector('[data-role="sample-options"]');
  const treatmentOptionsEl = root.querySelector('[data-role="treatment-options"]');
  const mineralOptionsEl = root.querySelector('[data-role="mineral-options"]');
  const groupOptionsEl = root.querySelector('[data-role="group-options"]');
  const palette = ["#2f6f73", "#b65f3a", "#5c6f8c", "#7a8f53", "#b9892f", "#7f6686"];
  const selected = new Map();
  let records = [];
  let xDomain = null;
  let dragStart = null;
  let showPeakMarkers = false;
  let staticManifest = null;
  let comparisonSuggestions = [];
  let geologistTriagePayload = null;
  let geologistTriagePromise = null;
  let geologistTriageError = "";
  let geologistTriageById = new Map();
  let geologistSimilarityReview = null;
  let geologistSimilarityReviewPromise = null;
  let xrdnetSummary = null;
  let xrdnetSummaryPromise = null;
  let xrdnetSummaryError = "";
  const neuralEvidenceCache = new Map();
  let ngcWorkflowKey = "";
  let ngcWorkflowPayload = null;
  let ngcWorkflowPromise = null;
  let rruffOdrCurves = [];
  let rruffOdrRejectedCount = 0;
  let rruffOdrTargetSlug = "";
  let rruffOdrTargetLabel = "";
  let rruffOdrLoaded = false;
  let rruffOdrLoadingPromise = null;
  // Descricoes locais curtas para feedback interpretativo imediato no painel.
  const mineralDescriptions = {
    kaolinite: {
      title: "Kaolinite",
      text: "Argilomineral 1:1 do grupo caulinita-serpentina, formado por uma folha tetraedrica de Si-O ligada a uma folha octaedrica de Al-OH. Em DRX costuma apresentar reflexoes proximas de 7,15 A e 3,58 A; sua estrutura tende a nao expandir com glicolacao.",
    },
    halloysite: {
      title: "Halloysite",
      text: "Argilomineral 1:1 relacionado a caulinita, podendo ocorrer hidratado e com morfologias tubulares. A distancia basal pode variar conforme hidratacao; a comparacao entre tratamentos ajuda a separar efeitos de agua interlamelar de fases nao expansivas.",
    },
    illite: {
      title: "Illite",
      text: "Argilomineral 2:1 micaceo, com potassio interlamelar que limita expansao. O pico basal em torno de 10 A e um marcador importante; pouca mudanca apos glicolacao sugere comportamento nao expansivo ou baixa expansibilidade.",
    },
    muscovite: {
      title: "Muscovite",
      text: "Mica dioctaedrica 2:1 com potassio interlamelar bem ordenado. Em comparacao com ilita/sericita, picos mais definidos podem indicar maior cristalinidade ou contribuicao de mica detritica/hidrotermal.",
    },
    brammallite: {
      title: "Brammallite",
      text: "Mica sodica 2:1 relacionada ao grupo da ilita/micas. A interpretacao por DRX deve ser tratada como candidata, pois seus picos podem se sobrepor a outras micas e feldspatos.",
    },
    chlorite: {
      title: "Chlorite",
      text: "Filossilicato 2:1:1 com camada brucitica/hidroxida interlamelar. Reflexoes em torno de 14 A, 7 A e 3,5 A sao relevantes; tende a resistir melhor a glicolacao que esmectitas expansivas.",
    },
    montmorillonite: {
      title: "Montmorillonite",
      text: "Esmectita expansiva 2:1 com cations e agua interlamelar. A comparacao natural x glicolado e central: expansao do pico basal para distancias maiores apoia interpretacao de esmectita expansiva.",
    },
    nontronite: {
      title: "Nontronite",
      text: "Esmectita ferrifera 2:1 expansiva. Mudancas no baixo angulo apos glicolacao podem sustentar expansibilidade, enquanto a posicao/intensidade dos picos deve ser comparada com outras esmectitas.",
    },
    hectorite: {
      title: "Hectorite",
      text: "Esmectita trioctaedrica magnesiana-litio, tambem expansiva. No DRX, a atribuicao deve ser vista como candidata quando nao ha dados quimicos complementares.",
    },
    quartz: {
      title: "Quartz",
      text: "Tectossilicato SiO2, nao argilomineral. Picos intensos, especialmente perto de 3,34 A, podem dominar o padrao e mascarar fases argilosas menos abundantes.",
    },
    albite: {
      title: "Albite",
      text: "Feldspato sodico, tectossilicato. Nao e argilomineral, mas e comum em rochas alteradas e pode gerar sobreposicoes com picos de filossilicatos em regioes de 3 a 4 A.",
    },
    calcite: {
      title: "Calcite",
      text: "Carbonato de calcio, nao argilomineral. O pico forte em torno de 3,03 A pode ser diagnostico, mas deve ser comparado com a mineralogia e contexto da amostra.",
    },
    goethite: {
      title: "Goethite",
      text: "Oxihidroxido de ferro. Pode aparecer como fase secundaria de alteracao; picos de baixa cristalinidade podem ser largos e exigir confirmacao complementar.",
    },
    hematite: {
      title: "Hematite",
      text: "Oxido de ferro. Em sistemas hidrotermais ou alterados pode indicar oxidacao; sua interpretacao deve ser combinada com cor, geoquimica e paragênese.",
    },
  };

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function currentRecordId() {
    const params = new URLSearchParams(window.location.search);
    return params.get("record_id") || contextRecordId || "";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function hasRecordContext() {
    return Boolean(currentRecordId());
  }

  function currentArgilomineralSlug() {
    const params = new URLSearchParams(window.location.search);
    const value = params.get("argilomineral");
    if (!value) return "";
    return resolveMineralSlug(value) || mineralSlug(value);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function currentArgilomineralLabel() {
    const params = new URLSearchParams(window.location.search);
    return params.get("argilomineral") || "";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function formatNumber(value, digits) {
    if (typeof value !== "number" || !Number.isFinite(value)) return "Nao informado";
    return value.toLocaleString("pt-BR", {
      minimumFractionDigits: digits || 0,
      maximumFractionDigits: digits || 2,
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fetchJson(url, options) {
    // Todas as APIs do painel devem responder JSON; erros HTML viram mensagem
    // operacional clara para o usuario recarregar/verificar a sessao local.
    const requestOptions = Object.assign({ credentials: "same-origin" }, options || {});
    requestOptions.headers = Object.assign({ Accept: "application/json" }, (options && options.headers) || {});
    return fetch(url, requestOptions).then(function (response) {
      return response.text().then(function (text) {
        let payload = {};
        try {
          payload = text ? JSON.parse(text) : {};
        } catch (error) {
          throw new Error("A resposta do servidor não veio em JSON. Verifique o endpoint DRX ou recarregue a página.");
        }
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (!response.ok || payload.success === false) {
          throw new Error(payload.error || "Falha ao carregar dados DRX.");
        }
        return payload;
      });
    }).catch(function (error) {
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (error && error.message === "Load failed") {
        throw new Error("Falha ao carregar dados da Argiloteca local. Recarregue a página e tente novamente; se persistir, verifique se o servidor HTTPS local continua ativo.");
      }
      throw error;
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fetchOptionalJson(url) {
    return fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } }).then(function (response) {
      if (response.status === 404) return null;
      return response.text().then(function (text) {
        let payload = {};
        try {
          payload = text ? JSON.parse(text) : {};
        } catch (error) {
          if (response.status === 404) return null;
          throw new Error("A resposta do servidor não veio em JSON. Verifique o endpoint DRX ou recarregue a página.");
        }
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (!response.ok || payload.success === false) {
          throw new Error(payload.error || "Falha ao carregar dados DRX.");
        }
        return payload;
      });
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function uploadRawFormData(url, formData, options) {
    // Upload temporario usa XHR para timeout longo e mensagem especifica sem
    // gravar o RAW no indice local.
    const uploadOptions = options || {};
    return new Promise(function (resolve, reject) {
      const request = new XMLHttpRequest();
      request.open("POST", new URL(url, window.location.origin).toString(), true);
      request.responseType = "text";
      request.withCredentials = true;
      request.setRequestHeader("Accept", "application/json");
      request.onload = function () {
        let payload = {};
        try {
          payload = request.responseText ? JSON.parse(request.responseText) : {};
        } catch (error) {
          reject(new Error("A resposta do servidor não veio em JSON. Verifique se a sessão local da Argiloteca ainda está ativa."));
          return;
        }
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (request.status < 200 || request.status >= 300 || payload.success === false) {
      reject(new Error(payload.error || "Falha ao carregar amostra externa. HTTP " + request.status + "."));
          return;
        }
        resolve(payload);
      };
      request.onerror = function () {
        reject(new Error("Falha no envio da amostra externa para a Argiloteca local. Recarregue a página e tente novamente."));
      };
      request.ontimeout = function () {
        reject(new Error("Tempo esgotado ao enviar a amostra externa."));
      };
      request.timeout = uploadOptions.timeout || EXTERNAL_RAW_UPLOAD_TIMEOUT_MS;
      request.send(formData);
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function queryUrl() {
    const params = new URLSearchParams();
    const urlParams = new URLSearchParams(window.location.search);
    ["argilomineral", "mineral_group", "sample_code", "treatment"].forEach(function (key) {
      const value = urlParams.get(key);
      if (value) params.set(key, value);
    });
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (form) {
      new FormData(form).forEach(function (value, key) {
        if (String(value).trim() !== "") params.set(key, value);
      });
    }
    const query = params.toString();
    return query ? recordsUrl + "?" + query : recordsUrl;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fillSelect(select, values) {
    if (!select) return;
    const current = select.value;
    const first = select.querySelector("option");
    select.innerHTML = "";
    if (first) select.appendChild(first.cloneNode(true));
    (values || []).forEach(function (value) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = treatmentLabel(value);
      select.appendChild(option);
    });
    if (current && (values || []).indexOf(current) >= 0) select.value = current;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadRecords() {
    if (!form || !recordListEl) {
      records = [];
      return Promise.resolve();
    }
    statusEl.textContent = "Carregando registros com difratogramas...";
    return fetchJson(queryUrl())
      .then(function (payload) {
        records = payload.records || [];
        fillSelect(sampleOptionsEl, (payload.filters || {}).sample_code || []);
        fillSelect(treatmentOptionsEl, (payload.filters || {}).treatment || []);
        fillSelect(mineralOptionsEl, (payload.filters || {}).argilomineral || []);
        fillSelect(groupOptionsEl, (payload.filters || {}).mineral_group || []);
        renderRecordList();
        updateStatus();
      })
      .catch(function (error) {
        recordListEl.innerHTML = '<div class="argilo-drx__empty">' + escapeHtml(error.message) + "</div>";
        statusEl.textContent = "Não foi possível carregar os registros DRX.";
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderTags(values) {
    if (!values || !values.length) return '<span class="argilo-drx__tag">Nao informado</span>';
    return values.map(function (value) {
      return '<span class="argilo-drx__tag">' + escapeHtml(value) + "</span>";
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function treatmentLabel(value) {
    const labels = {
      natural: "Natural",
      glicolado: "Glicolado",
      calcinado: "Calcinado",
      indeterminado: "Indeterminado",
      externo: "Externo",
    };
    return labels[value] || value || "Indeterminado";
  }

  function ngcTreatmentRank(value) {
    const normalized = String(value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
    if (["n", "natural", "air_dried", "air-dried", "air dried"].indexOf(normalized) >= 0) return 0;
    if (["g", "glicolado", "glicolada", "glycolated", "ethylene_glycol_solvated", "eg"].indexOf(normalized) >= 0) return 1;
    if (["c", "calcinado", "calcinada", "calcined", "heated", "heated_550c"].indexOf(normalized) >= 0) return 2;
    return 99;
  }

  function sortItemsByNgcTreatment(items) {
    return (items || []).map(function (item, index) {
      return { item: item, index: index, rank: ngcTreatmentRank(item && (item.treatment || item.preparation)) };
    }).sort(function (left, right) {
      return (left.rank - right.rank) || (left.index - right.index);
    }).map(function (entry) {
      return entry.item;
    });
  }

  function selectedItemsInNgcOrder() {
    return sortItemsByNgcTreatment(Array.from(selected.values()));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function inferExternalTreatment(filename) {
    // Heuristica de preparo N/G/C para arquivos soltos, antes de haver metadado
    // curatorial associado ao RAW externo.
    const stem = String(filename || "").replace(/\.[^.]+$/, "");
    const normalized = stem
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
    if (/(^|[-_\s()])(g|gly|glicol|glicolado|glicolada|etileno|ethylene)([-_\s()]|$)/.test(normalized)) {
      return { type: "glicolado", label: "Glicolado", evidence: "Preparo inferido pelo nome do arquivo externo." };
    }
    if (/(^|[-_\s()])(c|cal|calc|calcinado|calcinada|aquecido|heated)([-_\s()]|$)/.test(normalized)) {
      return { type: "calcinado", label: "Calcinado", evidence: "Preparo inferido pelo nome do arquivo externo." };
    }
    if (/(^|[-_\s()])(n|nat|natural|orientada|airdry|air-dry)([-_\s()]|$)/.test(normalized)) {
      return { type: "natural", label: "Natural", evidence: "Preparo inferido pelo nome do arquivo externo." };
    }
    return { type: "indeterminado", label: "Indeterminado", evidence: "Preparo não identificado pelo nome do arquivo externo." };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function inferExternalSampleBase(filename) {
    const stem = String(filename || "").replace(/\.[^.]+$/, "").trim();
    return stem
      .replace(/[\s._-]*\(?\b(N|G|C|NAT|NATURAL|GLY|GLICOL|GLICOLADA|CAL|CALC|CALCINADA)\b\)?$/i, "")
      .replace(/\s+/g, " ")
      .trim() || stem;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function shiftPeakAxisFields(rows, offset, item) {
    // Capitulo 3 aplicado: se a curva recebe offset no eixo experimental 2θ,
    // o d-spacing do pico deixa de ser o mesmo. O painel recalcula d pela
    // Lei de Bragg depois do deslocamento para manter curva, marcador e tabela
    // de evidencias no mesmo sistema geometrico.
    if (!Number.isFinite(offset) || Math.abs(offset) <= 1e-12) return rows || [];
    const axisKeys = [
      "two_theta",
      "twoTheta",
      "center_2theta",
      "observed_two_theta",
      "measured_two_theta",
      "measured_two_theta_min",
      "measured_two_theta_max",
      "fit_window_min_2theta",
      "fit_window_max_2theta",
    ];
    return (rows || []).map(function (row) {
      if (!row || typeof row !== "object") return row;
      const shifted = Object.assign({}, row);
      axisKeys.forEach(function (key) {
        const value = Number(shifted[key]);
        if (Number.isFinite(value)) shifted[key] = Number((value + offset).toFixed(6));
      });
      const theta = Number(shifted.two_theta || shifted.center_2theta || shifted.observed_two_theta);
      if (Number.isFinite(theta)) {
        const d = braggDSpacingForItem(theta, item);
        ["d", "d_spacing", "d_angstrom", "center_d_angstrom"].forEach(function (key) {
          if (shifted[key] !== undefined && Number.isFinite(d)) shifted[key] = Number(d.toFixed(5));
        });
      }
      return shifted;
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function shiftAdvancedCurveAxis(advancedCurve, offset) {
    if (!advancedCurve || !Number.isFinite(offset) || Math.abs(offset) <= 1e-12) return advancedCurve || {};
    const current = advancedCurve.two_theta || [];
    if (!current.length) return advancedCurve;
    return Object.assign({}, advancedCurve, {
      two_theta: current.map(function (value) {
        const number = Number(value);
        return Number.isFinite(number) ? Number((number + offset).toFixed(6)) : value;
      }),
      axis_source: "ngc_external_natural_anchor",
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function applyAxisOffsetToExternalItem(item, offset, options) {
    const details = options || {};
    if (!item || !Number.isFinite(offset) || Math.abs(offset) <= NGC_AXIS_ALIGNMENT_MIN_OFFSET) return false;
    const currentStart = Number((item.twoTheta || [])[0]);
    if (!Number.isFinite(currentStart)) return false;
    item.twoTheta = (item.twoTheta || []).map(function (value) {
      const number = Number(value);
      return Number.isFinite(number) ? Number((number + offset).toFixed(6)) : value;
    });
    const targetStart = Number(item.twoTheta[0]);
    item.detectedPeaks = shiftPeakAxisFields(item.detectedPeaks, offset, item);
    item.advancedPeaks = shiftPeakAxisFields(item.advancedPeaks, offset, item);
    item.fitResults = shiftPeakAxisFields(item.fitResults, offset, item);
    item.advancedCurve = shiftAdvancedCurveAxis(item.advancedCurve, offset);
    item.metadata = Object.assign({}, item.metadata || {}, {
      two_theta_original_start: currentStart,
      two_theta_alignment_target_start: Number.isFinite(Number(details.targetStart)) ? Number(details.targetStart) : targetStart,
      two_theta_start: targetStart,
      two_theta_offset_applied: Number(offset.toFixed(6)),
      two_theta_alignment_method: details.method || "ngc_external_axis_offset",
      two_theta_alignment_sample_base: details.sampleBase || item.sampleBase || sampleBaseForNgc(item),
      curve_source: "arquivo_externo_com_eixo_ajustado",
    });
    return true;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function applyExternalSingleRawAxisFallback(item) {
    if (!item || item.treatment !== "glicolado" || !(item.twoTheta || []).length) return false;
    const currentStart = Number(item.twoTheta[0]);
    if (!Number.isFinite(currentStart)) return false;
    if (Math.abs(currentStart - 3.0) > 0.25) return false;
    return applyAxisOffsetToExternalItem(item, 2.0 - currentStart, {
      method: "ngc_external_glycolated_start_heuristic",
      targetStart: 2.0,
      sampleBase: item.sampleBase || sampleBaseForNgc(item),
    });
  }

  /**
   * Alinha eixos 2θ de RAWs externos de um mesmo grupo N/G/C.
   *
   * A comparação mineralógica entre Natural, Glicolado e Calcinado só é útil
   * quando os deslocamentos instrumentais não mascaram expansão, colapso ou
   * persistência dos picos basais. A rotina aplica a âncora Natural ou offset
   * previamente calculado e registra a origem do ajuste no item exibido.
   * @param {Array<Object>} loadedResults RAWs externos já carregados pelo painel.
   * @returns {Array<Object>} Curvas com metadados de alinhamento 2θ preservados.
   */
  function applyExternalNgcAxisAlignment(loadedResults) {
    // Para lotes N/G/C externos, curva Natural da mesma amostra-base ancora G/C;
    // quando so ha glicolado, uma heuristica conservadora corrige inicio 3 -> 2.
    const items = (loadedResults || [])
      .map(function (result) { return result && result.selectedId ? selected.get(result.selectedId) : null; })
      .filter(Boolean);
    items.forEach(applyExternalSingleRawAxisFallback);
    buildNgcGroups(items).forEach(function (group) {
      const natural = group.natural[0];
      if (!natural || !(natural.twoTheta || []).length) return;
      const targetStart = Number(natural.twoTheta[0]);
      if (!Number.isFinite(targetStart)) return;
      [].concat(group.glicolada || [], group.calcinada || []).forEach(function (item) {
        if (!item || !(item.twoTheta || []).length) return;
        const currentStart = Number(item.twoTheta[0]);
        const offset = targetStart - currentStart;
        applyAxisOffsetToExternalItem(item, offset, {
          method: "ngc_external_natural_anchor",
          targetStart: targetStart,
          sampleBase: group.sampleBase,
        });
      });
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function treatmentBadge(item) {
    const type = item.treatment || "indeterminado";
    return '<span class="argilo-drx__badge argilo-drx__badge--' + escapeHtml(type) + '">' + escapeHtml(item.treatment_label || treatmentLabel(type)) + "</span>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function diffractogramContext(id) {
    let found = null;
    records.some(function (record) {
      return (record.diffractograms || []).some(function (item) {
        if (item.id === id) {
          found = { record: record, diffractogram: item };
          return true;
        }
        return false;
      });
    });
    return found;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function sampleLabel(item) {
    const sample = item.sample || {};
    return item.sampleCode || item.sample_code || sample.sample_code || sample.sample_label || "Nao informado";
  }

  function ngcTreatmentPrefix(item) {
    const rank = ngcTreatmentRank(item && (item.treatment || item.preparation));
    if (rank === 0) return "N";
    if (rank === 1) return "G";
    if (rank === 2) return "C";
    return "";
  }

  function chartSeriesLabel(item) {
    const prefix = ngcTreatmentPrefix(item);
    return (prefix ? prefix + " · " : "") + sampleLabel(item);
  }

  function stackedOffsetForNgcOrder(item, index) {
    const rank = ngcTreatmentRank(item && (item.treatment || item.preparation));
    if (rank === 0) return 2 * 1.15;
    if (rank === 1) return 1 * 1.15;
    if (rank === 2) return 0;
    return index * 1.15;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function analysisLabel(analyses) {
    if (!analyses || !analyses.length) return "Analise nao informada";
    return analyses.map(function (analysis) {
      return analysis.analysis_id || analysis.method || "Analise";
    }).join(", ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function formatScore(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) return "valor nao informado";
    return value.toLocaleString("pt-BR", { maximumFractionDigits: 3 });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderScoreBreakdown(bestMatch) {
    if (!bestMatch || !bestMatch.filename) return "";
    const components = bestMatch.score_components || {};
    const rows = [
      ["Metadados", components.metadata, bestMatch.metadata_score],
      ["Curva completa", components.curve, bestMatch.curve_score],
      ["Picos", components.peak, bestMatch.peak_score],
      ["Candidatos", components.candidate, bestMatch.candidate_score],
    ].map(function (row) {
      const value = Number.isFinite(Number(row[1])) ? Number(row[1]) : (Number.isFinite(Number(row[2])) ? Number(row[2]) : null);
      return [
        "<tr><td>", escapeHtml(row[0]), "</td><td>",
        value === null ? "N/D" : escapeHtml(formatScore(value)),
        "</td></tr>",
      ].join("");
    }).join("");
    return [
      '<details class="argilo-drx__score-details" open>',
      "<summary>Decomposição do score</summary>",
      '<table class="argilo-drx__score-table"><tbody>', rows, "</tbody></table>",
      "</details>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderMatchedPeaks(bestMatch) {
    const peaks = (bestMatch && bestMatch.matched_peaks) || [];
    if (!peaks.length) return "";
    function percent(value) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? formatNumber(numeric, 1) + "%" : "N/D";
    }
    const rows = peaks.slice(0, 6).map(function (peak) {
      return [
        "<tr>",
        "<td>", escapeHtml(formatNumber(Number(peak.external_two_theta), 3)), "</td>",
        "<td>", escapeHtml(formatNumber(Number(peak.package_two_theta), 3)), "</td>",
        "<td>", escapeHtml(formatNumber(Number(peak.delta_two_theta), 4)), "</td>",
        "<td>", escapeHtml(formatNumber(Number(peak.external_d), 3)), "</td>",
        "<td>", escapeHtml(formatNumber(Number(peak.package_d), 3)), "</td>",
        "<td>", escapeHtml(formatNumber(Number(peak.delta_d), 4)), "</td>",
        "<td>", escapeHtml(formatNumber(Number(peak.external_relative_intensity), 1)), "</td>",
        "<td>", escapeHtml(formatNumber(Number(peak.package_relative_intensity), 1)), "</td>",
        "<td>", escapeHtml(percent(peak.relative_intensity_delta_percent)), "</td>",
        "<td>", escapeHtml(formatNumber(Number(peak.external_fwhm), 3)), "</td>",
        "<td>", escapeHtml(formatNumber(Number(peak.package_fwhm), 3)), "</td>",
        "<td>", escapeHtml(percent(peak.fwhm_delta_percent)), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    return [
      '<details class="argilo-drx__score-details">',
      "<summary>Picos casados</summary>",
      '<div class="argilo-drx__table-scroll"><table class="argilo-drx__score-table argilo-drx__score-table--wide">',
      "<thead><tr><th>2θ ext.</th><th>2θ pacote</th><th>Δ2θ</th><th>d ext.</th><th>d pacote</th><th>Δd</th><th>I rel. ext.</th><th>I rel. pacote</th><th>ΔI rel.</th><th>FWHM ext.</th><th>FWHM pacote</th><th>ΔFWHM</th></tr></thead>",
      "<tbody>", rows, "</tbody></table></div>",
      "</details>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function recordUrl(recordId) {
    const id = String(recordId || "").trim();
    return /^[a-z0-9]{5}-[a-z0-9]{5}$/i.test(id) ? "/records/" + encodeURIComponent(id) : "";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function recordButton(recordId, label, explicitUrl) {
    const url = explicitUrl || recordUrl(recordId);
    if (!url) return "";
    return '<a class="ui tiny button" href="' + escapeHtml(url) + '">' + escapeHtml(label || "Abrir registro") + "</a>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRelatedRecordMatches(similarity) {
    const matches = Array.isArray(similarity && similarity.record_matches)
      ? similarity.record_matches
      : (Array.isArray(similarity && similarity.matches) ? similarity.matches : []);
    const seen = new Set();
    const rows = matches.filter(function (match) {
      const recordId = match && (match.record_id || match.package_record_id);
      const key = String(recordId || "") + "|" + String(match && (match.filename || match.sample_code || ""));
      if (!recordId || seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, 5).map(function (match) {
      const recordId = match.record_id || match.package_record_id || "";
      const candidates = (match.mineral_candidates || []).map(function (candidate) {
        return candidate.mineral || candidate.label || candidate.name || "";
      }).filter(Boolean).slice(0, 3).join(", ");
      const loadButton = match.filename || match.sample_code ? [
        '<button class="ui tiny button argilo-drx__load-similar" type="button"',
        ' data-load-similar-raw="1"',
        ' data-record-id="', escapeHtml(recordId), '"',
        ' data-sample-code="', escapeHtml(match.sample_code || ""), '"',
        ' data-filename="', escapeHtml(match.filename || ""), '">',
        'Carregar RAW',
        '</button>',
      ].join("") : "";
      return [
        "<li>",
        "<strong>", escapeHtml(match.sample_code || match.filename || "RAW relacionado"), "</strong>",
        " · ", treatmentBadge({ treatment: match.preparation, treatment_label: match.preparation_label }),
        candidates ? " · candidatos: " + escapeHtml(candidates) : "",
        '<div class="argilo-drx__match-actions">',
        recordButton(recordId, "Abrir registro", match.record_url),
        loadButton,
        "</div>",
        "</li>",
      ].join("");
    }).join("");
    if (!rows) return "";
    return [
      '<details class="argilo-drx__score-details" open>',
      "<summary>Registros relacionados por RAW/argilominerais semelhantes</summary>",
      "<ul>", rows, "</ul>",
      "</details>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mineralSlug(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function resolveMineralSlug(value) {
    const slug = mineralSlug(value);
    if (!slug) return "";
    if (authorizedMineralSlugs.has(slug)) return slug;
    const aliased = authorizedMineralAliases[slug];
    if (aliased && authorizedMineralSlugs.has(aliased)) return aliased;
    return "";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mineralLink(name) {
    const slug = resolveMineralSlug(name);
    if (!slug) return escapeHtml(name || "Mineral nao informado");
    return '<a class="argilo-drx__mineral-link" href="' + escapeHtml(mineralDetailUrlBase) + encodeURIComponent(slug) + '">' + escapeHtml(name) + "</a>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mineralListLinks(names, emptyLabel) {
    const rows = (names || []).filter(Boolean);
    return rows.length ? rows.map(mineralLink).join(", ") : escapeHtml(emptyLabel || "N/D");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function linkKnownMineralText(text) {
    const source = String(text || "");
    const terms = [];
    authorizedMineralSlugs.forEach(function (slug) {
      terms.push({ label: slug.replace(/-/g, " "), slug: slug });
      terms.push({ label: slug, slug: slug });
    });
    Object.keys(authorizedMineralAliases || {}).forEach(function (alias) {
      const slug = authorizedMineralAliases[alias];
      if (slug && authorizedMineralSlugs.has(slug)) terms.push({ label: alias.replace(/-/g, " "), slug: slug });
    });
    const selectedTerms = terms
      .filter(function (term) { return term.label && term.label.length >= 4; })
      .sort(function (left, right) { return right.label.length - left.label.length; });
    const matches = [];
    selectedTerms.forEach(function (term) {
      const pattern = new RegExp("(^|[^A-Za-zÀ-ÿ0-9_-])(" + escapeRegExp(term.label) + ")(?=$|[^A-Za-zÀ-ÿ0-9_-])", "gi");
      let match;
      while ((match = pattern.exec(source)) !== null) {
        const prefixLength = match[1] ? match[1].length : 0;
        matches.push({
          start: match.index + prefixLength,
          end: match.index + prefixLength + match[2].length,
          slug: term.slug,
        });
      }
    });
    matches.sort(function (left, right) {
      return left.start - right.start || (right.end - right.start) - (left.end - left.start);
    });
    const accepted = [];
    matches.forEach(function (match) {
      const overlaps = accepted.some(function (current) {
        return match.start < current.end && match.end > current.start;
      });
      if (!overlaps) accepted.push(match);
    });
    if (!accepted.length) return escapeHtml(source);
    let cursor = 0;
    const html = [];
    accepted.forEach(function (match) {
      html.push(escapeHtml(source.slice(cursor, match.start)));
      html.push('<a class="argilo-drx__mineral-link" href="' + escapeHtml(mineralDetailUrlBase) + encodeURIComponent(match.slug) + '">' + escapeHtml(source.slice(match.start, match.end)) + "</a>");
      cursor = match.end;
    });
    html.push(escapeHtml(source.slice(cursor)));
    return html.join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function escapeRegExp(value) {
    return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function evidenceSummary(candidate) {
    const matches = candidate.matches || [];
    if (!matches.length) return "Sem picos casados informados.";
    return matches.slice(0, 3).map(function (match) {
      return "d ref. " + formatNumber(match.reference_d, 3)
        + " / obs. " + formatNumber(match.observed_d, 3)
        + " A; 2θ obs. " + formatNumber(match.observed_two_theta, 2);
    }).join(" · ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mineralRuleAlias(value) {
    const text = mineralSlug(value);
    if (/smect|esmect|montmor|sapon|beidell|nontron/.test(text)) return "esmectita";
    if (/illite|ilita|mica|sericit|sericita/.test(text)) return "ilita";
    if (/chlor|clorit|chamos|clinocl|nimite|pennant|sudoit|cookeit|donbass/.test(text)) return "clorita";
    if (/kaolin|caulin|halloys/.test(text)) return "caulinita";
    if (/vermicul/.test(text)) return "vermiculita";
    return text;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function ruleAppliesToMineral(mineralName, rule) {
    const mineral = mineralRuleAlias(mineralName);
    const ruleMineral = mineralRuleAlias(rule.mineral);
    if (mineral === ruleMineral) return true;
    if (mineral === "esmectita" && ruleMineral === "esmectita") return true;
    if (mineral === "clorita" && ruleMineral === "clorita") return true;
    return false;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function readableMatchPeak(match) {
    const observedD = Number(match.observed_d || match.observed_d_angstrom);
    const observedTheta = Number(match.observed_two_theta || match.two_theta);
    const referenceD = match.reference_d || [match.expected_d_min, match.expected_d_max].filter(Boolean).join("-");
    return [
      referenceD ? "d ref. " + referenceD : "",
      Number.isFinite(observedD) ? "d obs. " + formatNumber(observedD, 2) + " A" : "",
      Number.isFinite(observedTheta) ? "2θ " + formatNumber(observedTheta, 2) + "°" : "",
    ].filter(Boolean).join(" / ") || "pico casado sem coordenada informada";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function stageMatches(required, stage) {
    if (!required) return true;
    if (required === stage) return true;
    if (required === "H/Calcinado" && /^H(\/|[0-9])/.test(stage || "")) return true;
    return false;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function diagnosticProfileForMineral(mineralName, items) {
    const rules = mineralReflectionRules().filter(function (rule) {
      return ruleAppliesToMineral(mineralName, rule);
    });
    const present = [];
    const absent = [];
    rules.forEach(function (rule) {
      const matches = [];
      items.forEach(function (item) {
        const stage = preparationStage(item);
        if (!stageMatches(rule.required, stage)) return;
        const peak = strongestPeakInDRange(item, rule.min, rule.max);
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (peak) {
          matches.push(stage + " · " + formatPeakCell(peak));
        }
      });
      if (matches.length) {
        present.push(rule.reflection + " esperado em d " + formatNumber(rule.min, 2) + "-" + formatNumber(rule.max, 2) + " A: " + matches.slice(0, 3).join("; "));
      } else {
        absent.push(rule.reflection + " esperado em d " + formatNumber(rule.min, 2) + "-" + formatNumber(rule.max, 2) + " A" + (rule.required ? " no preparo " + rule.required : ""));
      }
    });
    const alias = mineralRuleAlias(mineralName);
    const conflicts = [];
    if (alias === "caulinita") conflicts.push("Pico em ~7 A pode sobrepor clorita; confirmar com ~3,58 A e resposta ao aquecimento.");
    if (alias === "clorita") conflicts.push("Picos em ~14 A e ~7 A podem confundir com esmectita natural, vermiculita ou caulinita; revisar harmônicos.");
    if (alias === "esmectita") conflicts.push("Diagnóstico depende da expansão em EG e colapso térmico; pico natural isolado não é suficiente.");
    if (alias === "ilita") conflicts.push("Pico ~10 A pode ocorrer com micas e outras fases; confirmar estabilidade e reflexões associadas.");
    if (alias === "vermiculita") conflicts.push("Diferenciar de clorita por comportamento térmico e ausência de expansão com EG.");
    if (!rules.length) conflicts.push("Não há regra diagnóstica específica cadastrada para este mineral no painel; usar como candidato mineralógico geral.");
    let recommendation = "Revisar padrão completo, picos casados e contexto da amostra.";
    if (absent.length && present.length) recommendation = "Revisar picos ausentes antes de elevar a confiança.";
    if (!present.length) recommendation = "Tratar como hipótese fraca até haver picos diagnósticos compatíveis.";
    return {
      present: present,
      absent: absent,
      conflicts: conflicts,
      recommendation: recommendation,
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function confidenceFromMineral(mineral) {
    const value = String(mineral.bestConfidence || "").toLowerCase();
    if (value) return mineral.bestConfidence;
    if (Number.isFinite(Number(mineral.bestScore))) {
      if (mineral.bestScore >= 0.7) return "média";
      if (mineral.bestScore >= 0.45) return "baixa/média";
    }
    return "baixa ou não informada";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function htmlEvidenceList(rows, fallback, limit) {
    const selectedRows = (rows || []).filter(Boolean).slice(0, limit || 6);
    if (!selectedRows.length) return "<p class='argilo-drx__mini-note'>" + escapeHtml(fallback || "N/D") + "</p>";
    return "<ul class='argilo-drx__evidence-list'>" + selectedRows.map(function (row) {
      return "<li>" + escapeHtml(row) + "</li>";
    }).join("") + "</ul>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRecordList() {
    if (!recordListEl) return;
    if (!records.length) {
      recordListEl.innerHTML = '<div class="argilo-drx__empty">Nenhum registro com difratograma importado foi encontrado. Importe um .raw para habilitar a comparação.</div>';
      return;
    }
    recordListEl.innerHTML = records.map(function (record) {
      const diffractograms = (record.diffractograms || []).map(function (item) {
        const checked = selected.has(item.id) ? "checked" : "";
        const points = item.metadata && item.metadata.points ? item.metadata.points + " pontos" : "pontos nao informados";
        const sample = item.sample || {};
        const analysisCount = item.traceability && item.traceability.analysis_count ? item.traceability.analysis_count : 0;
        return [
          '<label class="argilo-drx__pick">',
          '<input type="checkbox" data-drx-id="', escapeHtml(item.id), '" ', checked, ">",
          '<span><strong>', escapeHtml(item.sample_code || "Amostra sem codigo"), "</strong>",
          " ", treatmentBadge(item),
          " · ", escapeHtml(item.original_filename || item.id),
          " · ", escapeHtml(points),
          " · ", escapeHtml(sample.locality || "local nao informado"),
          analysisCount ? " · " + analysisCount + " analise(s)" : "",
          "</span>",
          "</label>",
        ].join("");
      }).join("");
      return [
        '<article class="argilo-drx__record">',
        '<h3>', escapeHtml(record.title), "</h3>",
        '<p><strong>Amostras com DRX:</strong> ', escapeHtml((record.diffractograms || []).length), " de ", escapeHtml(record.sample_count || "amostras nao informadas"), "</p>",
        '<p><strong>Registro:</strong> ', escapeHtml(record.sample_locality || "local principal nao informado"), "</p>",
        '<div class="argilo-drx__tags">', renderTags(record.argilominerais), "</div>",
        '<p>',
        recordButton(record.id, "Abrir registro"),
        ' <a class="ui tiny button" href="/analises/', encodeURIComponent(record.id), '">Pacote analitico</a>',
        '</p>',
        '<div class="argilo-drx__record-actions">', diffractograms, "</div>",
        "</article>",
      ].join("");
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function diffractogramUrl(id) {
    return diffractogramUrlTemplate.replace("__id__", encodeURIComponent(id));
  }

  function neuralEvidenceUrl(id) {
    if (!neuralEvidenceUrlTemplate || !id) return "";
    return neuralEvidenceUrlTemplate.replace("__id__", encodeURIComponent(id));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function technicalReportUrl(id) {
    if (!technicalReportUrlTemplate || !id || String(id).indexOf("external:") === 0 || String(id).indexOf("package:") === 0) return "";
    return technicalReportUrlTemplate.replace("__id__", encodeURIComponent(id));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function referenceCompareUrl(id) {
    if (!referenceCompareUrlTemplate || !id || String(id).indexOf("external:") === 0 || String(id).indexOf("package:") === 0) return "";
    return referenceCompareUrlTemplate.replace("__id__", encodeURIComponent(id));
  }

  /**
   * Reduz picos DRX ao conjunto necessário para o contrato backend N/G/C.
   *
   * Mantém d-spacing, 2θ, intensidade, FWHM e origem do pico para que o backend
   * possa avaliar picos basais e companheiros sem depender de lógica científica
   * pesada no navegador.
   * @param {Object} item Difratograma selecionado no painel.
   * @returns {Array<Object>} Picos compactos serializáveis para a API N/G/C.
   */
  function compactNgcPeaks(item) {
    return []
      .concat(item.advancedPeaks || [])
      .concat(item.targetedBasalPeaks || [])
      .concat(item.detectedPeaks || [])
      .concat(item.fitResults || [])
      .filter(function (peak) { return peak && typeof peak === "object"; })
      .slice(0, 80)
      .map(function (peak) {
        const observed = peak.observed_peak || {};
        return {
          peak_index: peak.peak_index || peak.index || peak.peak_id || null,
          two_theta: peak.two_theta || peak["2theta"] || peak.center_2theta || peak.observed_two_theta || observed.two_theta || null,
          d_angstrom: peak.d_angstrom || peak.d || peak.d_spacing || peak.center_d_angstrom || peak.observed_d_angstrom || observed.d_angstrom || null,
          i_abs: peak.i_abs || peak.absolute_intensity || peak.intensity || observed.intensity || peak.height || peak.relative_intensity || null,
          i_norm: peak.i_norm || peak.relative_intensity || observed.relative_intensity || peak.intensity_relative || null,
          relative_intensity: peak.relative_intensity || observed.relative_intensity || peak.i_norm || peak.height || peak.intensity || null,
          fwhm: peak.fwhm || null,
          area: peak.area || null,
          tau: peak.tau || null,
          targeted_range_id: peak.range_id || null,
          targeted_status: peak.status || null,
        };
      });
  }

  /**
   * Monta o payload de um difratograma para interpretação N/G/C no backend.
   *
   * O frontend apenas transporta curva, preparo inferido, candidatos auxiliares
   * e picos direcionados. As regras de esmectita, ilita, caulinita, clorita e
   * interestratificados permanecem centralizadas em Python.
   * @param {Object} item Difratograma selecionado ou carregado via RAW externo.
   * @returns {Object} Contrato mínimo aceito pelo endpoint N/G/C.
   */
  function ngcWorkflowItemPayload(item) {
    const metadata = item.metadata || {};
    const preclassification = item.externalCurvePreclassification || metadata.external_curve_preclassification || item.externalRawPreclassification || metadata.external_raw_preclassification || {};
    const preclassificationItem = item.externalRawPreclassificationItem || preclassification.item || {};
    const preclassificationMetadata = preclassificationItem.metadata || {};
    const d060Payload = preclassification.d060 || {};
    const d060Value = metadata.d060 !== undefined && metadata.d060 !== null
      ? metadata.d060
      : (preclassificationMetadata.d060 !== undefined && preclassificationMetadata.d060 !== null
        ? preclassificationMetadata.d060
        : (d060Payload.status === "inferred_auxiliary" ? d060Payload.d060 : null));
    return {
      id: item.id,
      filename: metadata.original_filename || metadata.filename || item.id,
      sample_code: item.sampleCode || metadata.sample_code || sampleLabel(item),
      sample_base: sampleBaseForNgc(item),
      preparation: item.treatment || metadata.preparation || metadata.treatment || "indeterminado",
      peaks: compactNgcPeaks(item),
      mineral_candidates: (item.mineralCandidates || item.mineral_candidates || []).slice(0, 8).map(function (candidate) {
        return {
          mineral: candidate.mineral || "",
          argilomineral_id: candidate.argilomineral_id || "",
          group: candidate.group || "",
          family: candidate.family || "",
          confidence: candidate.confidence || "",
          source: candidate.source || "",
          override: Boolean(candidate.override),
        };
      }),
      metadata: {
        original_filename: metadata.original_filename || metadata.filename || item.id,
        sample_code: metadata.sample_code || item.sampleCode || sampleLabel(item),
        preparation: metadata.preparation || item.treatment || "indeterminado",
        source: metadata.source || preclassificationMetadata.source,
        source_sha256: metadata.source_sha256 || preclassificationMetadata.source_sha256,
        temporary_upload_path: metadata.temporary_upload_path || preclassificationMetadata.temporary_upload_path,
        d060: d060Value,
        d060_status: metadata.d060_status || preclassificationMetadata.d060_status || d060Payload.status,
        d060_source: metadata.d060_source || preclassificationMetadata.d060_source || d060Payload.source,
        d060_warning: metadata.d060_warning || preclassificationMetadata.d060_warning || d060Payload.warning,
      },
      warnings: [].concat(item.warnings || [], preclassificationItem.warnings || []).filter(Boolean),
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function ngcWorkflowSelectionKey(items) {
    return (items || []).map(function (item) {
      return [
        item.id,
        item.treatment,
        item.metadata && item.metadata.original_filename,
        item.metadata && item.metadata.d060,
        compactNgcPeaks(item).map(function (peak) {
          return [peak.d_angstrom, peak.two_theta, peak.relative_intensity].join(":");
        }).join(","),
      ].join("|");
    }).join("||");
  }

  /**
   * Solicita ao backend a leitura N/G/C para a seleção atual do painel.
   *
   * Usa uma chave de seleção para evitar requisições repetidas e mantém estados
   * de carregamento/erro separados da renderização. O resultado recebido é
   * sempre tratado como evidência auxiliar, não confirmação mineralógica.
   * @param {Array<Object>} items Difratogramas atualmente selecionados.
   * @returns {void} Atualiza o cache local `ngcWorkflowPayload`.
   */
  function refreshNgcWorkflow(items) {
    if (!ngcWorkflowUrl || !items || !items.length) {
      ngcWorkflowKey = "";
      ngcWorkflowPayload = null;
      ngcWorkflowPromise = null;
      return;
    }
    const key = ngcWorkflowSelectionKey(items);
    if (key === ngcWorkflowKey && (ngcWorkflowPayload || ngcWorkflowPromise)) return;
    ngcWorkflowKey = key;
    ngcWorkflowPayload = {
      loading: true,
      stage: "external_curve_preclassification",
      process_steps: [
        "Agrupar amostras externas por amostra-base.",
        "Conferir preparos Natural, Glicolado e Calcinado.",
        "Enviar picos e metadados ao workflow N/G/C backend.",
        "Aplicar regras dos Capítulos 7 e 8 sem alterar a curva original.",
      ],
    };
    ngcWorkflowPromise = fetchJson(ngcWorkflowUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: items.map(ngcWorkflowItemPayload) }),
    })
      .then(function (payload) {
        ngcWorkflowPayload = payload;
        ngcWorkflowPromise = null;
        renderSelectedSummary();
        renderMineralPanel();
        return payload;
      })
      .catch(function (error) {
        ngcWorkflowPayload = {
          success: false,
          error: error && error.message ? error.message : "Falha ao carregar workflow N/G/C backend.",
        };
        ngcWorkflowPromise = null;
        renderSelectedSummary();
        renderMineralPanel();
        return null;
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function firstStoredSelectedItem() {
    return Array.from(selected.values()).find(function (item) {
      return item && referenceCompareUrl(item.id);
    }) || null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function compareReferenceForSelected(file) {
    const item = firstStoredSelectedItem();
    if (!item) {
      if (statusEl) statusEl.textContent = "Selecione uma curva armazenada antes de comparar um padrão de referência.";
      return Promise.resolve(null);
    }
    if (!file) return Promise.resolve(null);
    const url = referenceCompareUrl(item.id);
    const formData = new FormData();
    formData.append("reference_file", file);
    item.referenceComparison = { loading: true, filename: file.name };
    renderSelectedSummary();
    if (statusEl) statusEl.textContent = "Comparando referência " + file.name + " com " + sampleLabel(item) + "...";
    return fetchJson(url, { method: "POST", body: formData })
      .then(function (payload) {
        const selectedItem = selected.get(item.id);
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (selectedItem) {
          selectedItem.referenceComparison = payload;
          selectedItem.technicalReport = payload.technical_report || selectedItem.technicalReport;
        }
        if (statusEl) statusEl.textContent = "Referência comparada: " + (payload.reference_comparison && payload.reference_comparison.matched_peak_count || 0) + " picos casados.";
        renderAll();
        return payload;
      })
      .catch(function (error) {
        const selectedItem = selected.get(item.id);
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (selectedItem) {
          selectedItem.referenceComparison = {
            success: false,
            filename: file.name,
            error: error && error.message ? error.message : "Falha ao comparar referência.",
          };
        }
        if (statusEl) statusEl.textContent = error && error.message ? error.message : "Falha ao comparar referência.";
        renderSelectedSummary();
        return null;
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadNeuralEvidenceForItem(item) {
    if (!item || !item.id || !neuralEvidenceUrlTemplate) return Promise.resolve(null);
    const cached = neuralEvidenceCache.get(item.id);
    if (cached) return Promise.resolve(cached);
    const url = neuralEvidenceUrl(item.id);
    if (!url) return Promise.resolve(null);
    const loading = fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (response) {
        return response.text().then(function (text) {
          let payload = {};
          try {
            payload = text ? JSON.parse(text) : {};
          } catch (error) {
            payload = { success: false, error: "Resposta neural invalida." };
          }
          /**
           * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
           * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
           */
          if (!response.ok || payload.success === false) {
            return {
              success: false,
              matched: Boolean(payload.matched),
              available: payload.available !== false,
              error: payload.error || "Evidencia neural auxiliar nao encontrada.",
            };
          }
          return payload;
        });
      })
      .catch(function (error) {
        return {
          success: false,
          available: false,
          error: error && error.message ? error.message : "Falha ao carregar evidencia neural auxiliar.",
        };
      })
      .then(function (payload) {
        neuralEvidenceCache.set(item.id, payload);
        const selectedItem = selected.get(item.id);
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (selectedItem) {
          selectedItem.neuralEvidence = payload;
          renderAll();
        }
        return payload;
      });
    neuralEvidenceCache.set(item.id, { loading: true, promise: loading });
    return loading;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function packageCurveUrl(recordId) {
    return packageCurveUrlTemplate.replace("__record_id__", encodeURIComponent(recordId));
  }

  function packageUrl(recordId) {
    return packageUrlTemplate.replace("__record_id__", encodeURIComponent(recordId));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function legacyPackageUrl(recordId) {
    return "/argiloteca/analises/" + encodeURIComponent(recordId);
  }

  function fetchPackageJson(recordId, query) {
    const urls = Array.from(new Set([
      packageUrl(recordId) + "?" + query.toString(),
      legacyPackageUrl(recordId) + "?" + query.toString(),
    ]));
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    function tryUrl(index, lastError) {
      if (index >= urls.length) {
        throw lastError || new Error("Falha ao carregar pacote analitico.");
      }
      return fetch(urls[index], { headers: { Accept: "application/json" } })
        .then(function (response) {
          if (response.ok) return response.json();
          /**
           * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
           * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
           */
          if (response.status === 404) {
            return loadStaticManifest(recordId).then(function (manifest) {
              return { success: true, exists: true, items: manifest.items || [], pagination: { total: (manifest.items || []).length, returned: (manifest.items || []).length } };
            });
          }
          throw new Error("Falha ao carregar pacote analitico. HTTP " + response.status + ".");
        })
        .catch(function (error) {
          if (index + 1 < urls.length) return tryUrl(index + 1, error);
          throw new Error(error && error.message && error.message !== "Load failed" ? error.message : "Falha ao carregar pacote analitico. Verifique se a Argiloteca local esta ativa e tente novamente.");
        });
    }
    return tryUrl(0);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function packageDisplayLabel(recordId) {
    return contextRecordTitle || recordId || "snapshot geral RAW";
  }

  function addPackageCurve(recordId, sampleCode, filename, options) {
    // Carrega uma curva ja pertencente a pacote analitico, preservando ALS/FWHM
    // e candidatos mineralogicos recebidos do backend.
    if (!recordId || (!sampleCode && !filename)) return;

    const curveOptions = options || {};
    const query = new URLSearchParams();
    if (sampleCode) query.set("sample_code", sampleCode);
    if (filename) query.set("filename", filename);
    query.set("max_points", "3000");

    statusEl.textContent = "Carregando difratograma do pacote analitico...";
    return fetchJson(packageCurveUrl(recordId) + "?" + query.toString())
      .then(function (payload) {
        const item = payload.item || {};
        const metadata = payload.metadata || {};
        const id = "package:" + recordId + ":" + (payload.sample_code || sampleCode || filename);
        selected.set(id, {
          id: id,
          loadedAsSimilar: Boolean(curveOptions.loadedAsSimilar),
          similaritySource: curveOptions.similaritySource || null,
          record: {
            id: recordId,
            title: contextRecordTitle || "Pacote analitico DRX - " + recordId,
            sample_locality: "Pacote analitico associado ao registro",
            formacao_geologica: "",
            ambiente_formacao: "",
            metodos: "DRX",
          },
          diffractogram: item,
          sampleCode: payload.sample_code || item.sample_code || sampleCode,
          sample: {
            sample_code: payload.sample_code || item.sample_code || sampleCode,
            locality: item.sample_base || "Pacote analitico",
          },
          treatment: item.preparation || "indeterminado",
          treatment_label: item.preparation_label || treatmentLabel(item.preparation),
          treatment_confidence: item.preparation_confidence,
          treatment_evidence: item.preparation_evidence,
          mineralCandidates: item.mineral_candidates || [],
          detectedPeaks: item.detected_peaks || item.peaks || [],
          advancedPeaks: item.advanced_peaks || item.peaks || [],
          targetedBasalPeaks: item.targeted_basal_peaks || [],
          fitResults: item.fit_results || [],
          mineralEvidence: item.mineral_evidence || [],
          mineralCharacterization: item.mineral_characterization || [],
          qcFlags: item.qc_flags || [],
          advancedResultPath: item.advanced_result_path || null,
          advancedSummary: item.advanced_summary || {},
          advancedCurve: payload.advanced_curve || item.advanced_curve || {},
          basalTracking: item.basal_tracking || {},
          mineralClassification: {},
          analyses: [{ analysis_id: "DRX pacote", method: "DRX" }],
          argilominerais: [],
          gruposMinerais: [],
          recordLevelArgilominerais: [],
          traceability: { sample_found: true, analysis_count: 1, source: "pacote_analitico" },
          metadata: Object.assign({}, metadata, {
            original_filename: payload.filename || item.filename || filename,
            sample_code: payload.sample_code || item.sample_code || sampleCode,
            treatment: item.preparation || "indeterminado",
            treatment_label: item.preparation_label || treatmentLabel(item.preparation),
            advanced_result_path: item.advanced_result_path || null,
            advanced_summary: item.advanced_summary || {},
            advanced_curve: payload.advanced_curve || item.advanced_curve || {},
            advanced_peaks: item.advanced_peaks || item.peaks || [],
            targeted_basal_peaks: item.targeted_basal_peaks || [],
            fit_results: item.fit_results || [],
            mineral_evidence: item.mineral_evidence || [],
            mineral_characterization: item.mineral_characterization || [],
            qc_flags: item.qc_flags || [],
            basal_tracking: item.basal_tracking || {},
          }),
          twoTheta: payload.two_theta || [],
          intensity: payload.intensity || [],
        });
        xDomain = null;
        renderAll();
        statusEl.textContent = "Difratograma do pacote carregado. Selecione outros difratogramas para comparar.";
      })
      .catch(function (error) {
        statusEl.textContent = error.message;
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function addSnapshotRaw(diffractogramId, options) {
    // Carrega RAW do snapshot geral. Ele pode ainda nao ter registro publico,
    // mas traz traceability e enriquecimentos derivados para comparacao.
    if (!diffractogramId) return Promise.resolve();
    const snapshotOptions = options || {};
    if (selected.has(diffractogramId)) {
      const existing = selected.get(diffractogramId);
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (existing && snapshotOptions.loadedAsSimilar) {
        existing.loadedAsSimilar = true;
        existing.similaritySource = snapshotOptions.similaritySource || existing.similaritySource || null;
      }
      if (existing && snapshotOptions.geologistTriage) existing.geologistTriage = snapshotOptions.geologistTriage;
      renderAll();
      statusEl.textContent = "Este RAW do snapshot geral já está selecionado.";
      return Promise.resolve();
    }
    statusEl.textContent = "Carregando RAW do snapshot geral...";
    return fetchJson(diffractogramUrl(diffractogramId))
      .then(function (payload) {
        const metadata = payload.metadata || {};
        selected.set(diffractogramId, {
          id: diffractogramId,
          loadedAsSimilar: Boolean(snapshotOptions.loadedAsSimilar),
          similaritySource: snapshotOptions.similaritySource || null,
          geologistTriage: snapshotOptions.geologistTriage || geologistTriageById.get(diffractogramId) || null,
          record: {
            id: "snapshot-geral-raw",
            title: "Snapshot geral de RAW do módulo DRX",
            sample_locality: "Arquivo RAW ainda não associado a registro",
            formacao_geologica: "",
            ambiente_formacao: "",
            metodos: "DRX",
          },
          diffractogram: metadata,
          sampleCode: metadata.sample_code || metadata.original_filename || diffractogramId,
          sample: {
            sample_code: metadata.sample_code || metadata.original_filename || diffractogramId,
            locality: "Snapshot geral DRX",
          },
          treatment: metadata.preparation || metadata.treatment || "indeterminado",
          treatment_label: metadata.preparation_label || metadata.treatment_label || treatmentLabel(metadata.preparation || metadata.treatment),
          treatment_confidence: metadata.preparation_confidence || metadata.treatment_confidence,
          treatment_evidence: metadata.preparation_evidence || metadata.treatment_evidence,
          mineralCandidates: metadata.mineral_candidates || [],
          detectedPeaks: metadata.detected_peaks || metadata.peaks || [],
          advancedPeaks: metadata.advanced_peaks || [],
          targetedBasalPeaks: metadata.targeted_basal_peaks || [],
          fitResults: metadata.fit_results || [],
          mineralEvidence: metadata.mineral_evidence || [],
          mineralCharacterization: metadata.mineral_characterization || [],
          qcFlags: metadata.qc_flags || [],
          advancedResultPath: metadata.advanced_result_path || null,
          advancedSummary: metadata.advanced_summary || {},
          advancedCurve: metadata.advanced_curve || {},
          basalTracking: metadata.basal_tracking || {},
          mineralClassification: metadata.mineral_classification || {},
          analyses: [{ analysis_id: "Snapshot geral RAW", method: "DRX" }],
          argilominerais: metadata.argilominerais || [],
          gruposMinerais: metadata.grupos_minerais || [],
          recordLevelArgilominerais: [],
          traceability: metadata.traceability || { sample_found: false, analysis_count: 0, source: "snapshot_geral_raw" },
          metadata: metadata,
          neuralEvidence: { loading: true },
          twoTheta: payload.two_theta || [],
          intensity: payload.intensity || [],
        });
        loadNeuralEvidenceForItem(selected.get(diffractogramId));
        xDomain = null;
        renderAll();
        statusEl.textContent = "RAW do snapshot geral carregado para comparação.";
      })
      .catch(function (error) {
        statusEl.textContent = error.message;
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function suggestionPreparation(item) {
    const value = String(item && (item.preparation || item.treatment) || "").toLowerCase();
    if (value === "glicolada") return "glicolado";
    if (value === "calcinada") return "calcinado";
    return value;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function suggestionHasCompleteNgcTrio(suggestion) {
    const stages = new Set();
    (suggestion && suggestion.items || []).forEach(function (item) {
      const preparation = suggestionPreparation(item);
      if (preparation) stages.add(preparation);
    });
    return stages.has("natural") && stages.has("glicolado") && stages.has("calcinado");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function bestNgcSuggestionForMineral(suggestions) {
    // Prefere trio Natural/Glicolado/Calcinado completo para diagnostico DRX;
    // pares e grupos ficam como segunda escolha.
    const candidates = (suggestions || []).filter(function (suggestion) {
      return suggestion && (suggestion.items || []).length;
    });
    const completeTrio = candidates.find(function (suggestion) {
      return suggestion.type === "trio" && suggestionHasCompleteNgcTrio(suggestion);
    }) || candidates.find(suggestionHasCompleteNgcTrio);
    if (completeTrio) return completeTrio;
    const preference = ["ng", "nc", "gc", "indeterminado", "replicatas", "mineral", "preparo"];
    return candidates
      .filter(function (suggestion) { return preference.indexOf(suggestion.type) !== -1; })
      .sort(function (left, right) {
        return preference.indexOf(left.type) - preference.indexOf(right.type);
      })[0] || null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function suggestionAutoloadLabel(suggestion) {
    return suggestionHasCompleteNgcTrio(suggestion) ? "Trio N/G/C" : "Grupo comparativo";
  }

  function suggestionItemSnapshotId(item) {
    return item && (item.diffractogram_id || item.id || "");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function addSnapshotSuggestionItems(items) {
    const ids = [];
    (items || []).forEach(function (item) {
      const snapshotId = suggestionItemSnapshotId(item);
      if (snapshotId && ids.indexOf(snapshotId) === -1) ids.push(snapshotId);
    });
    return ids.reduce(function (promise, snapshotId) {
      return promise.then(function () {
        return addSnapshotRaw(snapshotId, { loadedAsSimilar: true, similaritySource: "comparison_suggestion" });
      });
    }, Promise.resolve());
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadSingleMineralSnapshotFromUrl(mineral) {
    const query = new URLSearchParams();
    query.set("argilomineral", mineral);
    query.set("limit", "1");
    query.set("offset", "0");
    statusEl.textContent = "Carregando um difratograma com " + mineral + "...";
    return fetchJson(rawSnapshotUrl + "?" + query.toString())
      .then(function (payload) {
        const item = (payload.items || [])[0];
        const snapshotId = item && (item.diffractogram_id || item.id);
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (!snapshotId) {
          statusEl.textContent = "Nenhum difratograma com " + mineral + " foi encontrado no snapshot geral.";
          return;
        }
        return addSnapshotRaw(snapshotId).then(function () {
          statusEl.textContent = "Difratograma com " + mineral + " carregado automaticamente.";
        });
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadMineralNgcSelectionFromUrl(mineral) {
    if (!rawSnapshotSuggestionsUrl) return Promise.resolve(false);
    const query = new URLSearchParams();
    query.set("argilomineral", mineral);
    query.set("limit", "5000");
    statusEl.textContent = "Procurando trio ou grupo N/G/C com " + mineral + "...";
    return fetchJson(rawSnapshotSuggestionsUrl + "?" + query.toString())
      .then(function (payload) {
        if (payload.success === false) throw new Error(payload.error || "Falha ao carregar grupos N/G/C.");
        const suggestion = bestNgcSuggestionForMineral(payload.suggestions || []);
        if (!suggestion) return false;
        const label = suggestionAutoloadLabel(suggestion);
        return addSnapshotSuggestionItems(suggestion.items).then(function () {
          statusEl.textContent = label + " com " + mineral + " carregado automaticamente.";
          return true;
        });
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadMineralSelectionFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const mineral = params.get("argilomineral");
    if (!mineral || params.get("source") || selected.size || !rawSnapshotUrl) return Promise.resolve();
    return loadMineralNgcSelectionFromUrl(mineral)
      .then(function (loadedTrio) {
        if (loadedTrio) return null;
        return loadSingleMineralSnapshotFromUrl(mineral);
      })
      .catch(function () {
        return loadSingleMineralSnapshotFromUrl(mineral)
          .catch(function (error) {
            statusEl.textContent = error.message;
          });
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function addExternalRaw(file, batchIndex) {
    if (!file) return Promise.resolve(null);
    if (!externalRawUrl) {
      return Promise.resolve({
        success: false,
        file: file.name,
        error: "Endpoint para RAW temporário não configurado nesta página."
      });
    }
    const inferredTreatment = inferExternalTreatment(file.name);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("sample_code", file.name.replace(/\.[^.]+$/, ""));
    formData.append("record_id", currentRecordId());
    const sampleBase = inferExternalSampleBase(file.name);
    const query = new URLSearchParams();
    query.set("max_points", "3000");
    query.set("similarity_scope", "all");
    startStatusProgress("Convertendo amostra externa e procurando similares na Argiloteca: " + file.name, [
      "lendo curva 2θ/intensidade",
      "detectando picos",
      "inferindo preparo N/G/C",
      "montando pré-classificação",
      "comparando com a Argiloteca",
    ]);
    return uploadRawFormData(externalRawUrl + "?" + query.toString(), formData, { timeout: EXTERNAL_RAW_UPLOAD_TIMEOUT_MS })
      .then(function (payload) {
        stopStatusProgress();
        const metadata = payload.metadata || {};
        const id = "external:" + Date.now() + ":" + (batchIndex || 0) + ":" + (payload.filename || file.name);
        selected.set(id, {
          id: id,
          record: {
            id: "arquivo-externo",
            title: "Amostra externa",
            sample_locality: "Comparação temporária",
            formacao_geologica: "",
            ambiente_formacao: "",
            metodos: "DRX",
          },
          diffractogram: {},
          sampleCode: payload.sample_code || metadata.sample_code || file.name,
          sample: {
            sample_code: payload.sample_code || metadata.sample_code || file.name,
            sample_base: sampleBase,
            locality: "Arquivo externo",
          },
          sampleBase: sampleBase,
          treatment: inferredTreatment.type,
          treatment_label: inferredTreatment.label,
          treatment_confidence: inferredTreatment.type === "indeterminado" ? "baixa" : "media",
          treatment_evidence: inferredTreatment.evidence,
          mineralCandidates: payload.mineral_candidates || metadata.mineral_candidates || [],
          detectedPeaks: payload.detected_peaks || metadata.detected_peaks || metadata.peaks || [],
          advancedPeaks: payload.advanced_peaks || metadata.advanced_peaks || [],
          targetedBasalPeaks: payload.targeted_basal_peaks || metadata.targeted_basal_peaks || [],
          fitResults: payload.fit_results || metadata.fit_results || [],
          mineralEvidence: payload.mineral_evidence || metadata.mineral_evidence || [],
          mineralCharacterization: payload.mineral_characterization || metadata.mineral_characterization || [],
          qcFlags: payload.qc_flags || metadata.qc_flags || [],
          advancedResultPath: payload.advanced_result_path || metadata.advanced_result_path || null,
          advancedSummary: payload.advanced_summary || metadata.advanced_summary || {},
          advancedCurve: payload.advanced_curve || metadata.advanced_curve || {},
          basalTracking: payload.basal_tracking || metadata.basal_tracking || {},
          analysisRun: payload.analysis_run || metadata.analysis_run || null,
          technicalReport: payload.technical_report || metadata.technical_report || null,
          diagnosticEvidence: payload.diagnostic_evidence || metadata.diagnostic_evidence || [],
          externalCurvePreclassification: payload.external_curve_preclassification || metadata.external_curve_preclassification || payload.external_raw_preclassification || metadata.external_raw_preclassification || null,
          externalRawPreclassification: payload.external_raw_preclassification || metadata.external_raw_preclassification || payload.external_curve_preclassification || metadata.external_curve_preclassification || null,
          externalRawPreclassificationItem: (payload.external_curve_preclassification || metadata.external_curve_preclassification || payload.external_raw_preclassification || metadata.external_raw_preclassification || {}).item || null,
          gsas2Validation: payload.gsas2_validation || metadata.gsas2_validation || null,
          mineralClassification: {
            source: metadata.mineral_classification_source || "classificacao_temporaria",
            error: metadata.mineral_classification_error || null,
          },
          analyses: [{ analysis_id: "DRX externo", method: "DRX" }],
          argilominerais: [],
          gruposMinerais: [],
          recordLevelArgilominerais: [],
          traceability: { sample_found: false, analysis_count: 0, source: "arquivo_externo_temporario" },
          metadata: metadata,
          packageSimilarity: payload.package_similarity || null,
          twoTheta: payload.two_theta || [],
          intensity: payload.intensity || [],
        });
        return { success: true, file: file.name, selectedId: id, treatment: inferredTreatment.type, similarity: payload.package_similarity || null };
      })
      .catch(function (error) {
        stopStatusProgress();
        const message = error && error.message === "Load failed"
          ? "falha de conexão com o servidor local; recarregue a página e tente novamente"
          : (error && error.message ? error.message : "falha desconhecida no upload");
        return { success: false, file: file.name, error: message };
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function addExternalRawFiles(fileList) {
    const files = Array.from(fileList || []).filter(function (file) {
      return /\.(raw|csv|txt|xy|dat)$/i.test(file.name || "");
    });
    if (!files.length) {
      statusEl.textContent = "Selecione um arquivo externo .raw, .csv, .txt, .xy ou .dat.";
      return;
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (files.length > 3) {
      statusEl.textContent = "Selecione no máximo três amostras externas: natural, glicolada e calcinada.";
      return;
    }
    const treatments = files.map(function (file) { return inferExternalTreatment(file.name).type; });
    const knownTreatments = treatments.filter(function (type) { return type !== "indeterminado"; });
    const duplicated = knownTreatments.some(function (type, index) {
      return knownTreatments.indexOf(type) !== index;
    });
    const indeterminateCount = treatments.filter(function (type) { return type === "indeterminado"; }).length;
    const hints = [];
    if (duplicated) hints.push("há preparos repetidos inferidos pelos nomes");
    if (files.length === 3 && indeterminateCount) hints.push("nem todos os três preparos foram inferidos pelo nome");
    startStatusProgress("Convertendo " + files.length + " amostra(s) externa(s)", [
      "preparando fila de arquivos",
      "lendo curvas externas",
      "extraindo picos",
      "classificando conjunto N/G/C",
    ]);
    const results = [];
    let queue = Promise.resolve();
    files.forEach(function (file, index) {
      queue = queue.then(function () {
        startStatusProgress("Convertendo amostra externa " + (index + 1) + "/" + files.length + ": " + file.name, [
          "lendo curva 2θ/intensidade",
          "detectando picos",
          "inferindo preparo N/G/C",
          "montando pré-classificação",
          "comparando com a Argiloteca",
        ]);
        return addExternalRaw(file, index).then(function (result) {
          results.push(result);
          return result;
        });
      });
    });
    queue.then(function () {
      stopStatusProgress();
      const ok = results.filter(function (result) { return result && result.success; });
      const failed = results.filter(function (result) { return result && !result.success; });
      applyExternalNgcAxisAlignment(ok);
      xDomain = null;
      renderAll();
      const treatmentText = ok.map(function (result) {
        return treatmentLabel(result.treatment);
      }).join(", ");
      const similarityNotes = ok.map(function (result) {
        const similarity = result.similarity || {};
        if (!similarity.available) return "";
        if (similarity.status === "igual") return result.file + ": já existe interpretação na Argiloteca";
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (similarity.status === "muito_parecido" || similarity.status === "parecido") {
          const best = similarity.best_match || {};
          return result.file + ": parecido com " + (best.sample_code || best.filename || "arquivo do pacote");
        }
        return "";
      }).filter(Boolean);
      stopStatusProgress([
        ok.length + " amostra(s) externa(s) adicionada(s)",
        ok.length ? "pré-classificação N/G/C acionada no painel" : "",
        treatmentText ? "preparos: " + treatmentText : "",
        similarityNotes.length ? similarityNotes.join("; ") : "",
        hints.length ? "atenção: " + hints.join("; ") : "",
        failed.length ? failed.length + " falha(s): " + failed.map(function (result) {
          return result.file + (result.error ? " (" + result.error + ")" : "");
        }).join(", ") : "",
        "Use CSV ou PDF para exportar o resultado.",
      ].filter(Boolean).join(". "));
    }).catch(function (error) {
      stopStatusProgress(error && error.message ? error.message : "Falha ao converter amostras externas.");
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadPackageSelectionFromUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("source") === "snapshot") {
      let snapshotIds = [];
      const snapshotId = params.get("snapshot_id");
      const snapshotIdsParam = params.get("snapshot_ids");
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (snapshotIdsParam) {
        try {
          snapshotIds = JSON.parse(snapshotIdsParam);
        } catch (error) {
          statusEl.textContent = "Nao foi possivel ler a selecao de RAWs do snapshot geral.";
          return;
        }
      } else if (snapshotId) {
        snapshotIds = [snapshotId];
      }
      snapshotIds = (Array.isArray(snapshotIds) ? snapshotIds : []).filter(Boolean);
      if (!snapshotIds.length) return;
      statusEl.textContent = "Carregando " + snapshotIds.length + " RAW(s) do snapshot geral para comparacao...";
      return snapshotIds.reduce(function (promise, diffractogramId) {
        return promise.then(function () {
          return addSnapshotRaw(diffractogramId);
        });
      }, Promise.resolve()).then(function () {
        statusEl.textContent = snapshotIds.length + " RAW(s) do snapshot geral carregado(s) para comparacao.";
      });
    }
    if (params.get("source") !== "package") return;
    const recordId = params.get("record_id");
    const samplesParam = params.get("samples");
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (samplesParam) {
      let samples = [];
      try {
        samples = JSON.parse(samplesParam);
      } catch (error) {
        statusEl.textContent = "Nao foi possivel ler a selecao de amostras do pacote analitico.";
        return;
      }
      if (!Array.isArray(samples) || !samples.length) return;
      statusEl.textContent = "Carregando " + samples.length + " difratograma(s) selecionado(s) do pacote analitico...";
      return samples.reduce(function (promise, sample) {
        return promise.then(function () {
          return addPackageCurve(recordId, sample.sample_code, sample.filename);
        });
      }, Promise.resolve()).then(function () {
        statusEl.textContent = samples.length + " difratograma(s) selecionado(s) carregado(s) para comparacao.";
      });
    }
    return addPackageCurve(recordId, params.get("sample_code"), params.get("filename"));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRawPickerItems(items) {
    if (!rawPickerListEl) return;
    if (!items.length) {
      rawPickerListEl.innerHTML = '<div class="argilo-drx__empty">Nenhuma amostra RAW encontrada para os filtros.</div>';
      return;
    }
    rawPickerListEl.innerHTML = items.map(function (item) {
      const candidates = (item.mineral_candidates || []).slice(0, 2).map(function (candidate) {
        return candidate.mineral;
      }).filter(Boolean).join(", ");
      const snapshotId = item.diffractogram_id || item.id || "";
      const isSnapshotItem = item.source === "snapshot_geral_raw" || String(snapshotId).indexOf("snapshot:") === 0;
      const selectedKey = isSnapshotItem ? snapshotId : "package:" + item.record_id + ":" + item.sample_code;
      const alreadySelected = selected.has(selectedKey);
      const actionAttribute = isSnapshotItem
        ? 'data-add-global-raw="' + escapeHtml(snapshotId) + '"'
        : 'data-add-raw-sample="' + escapeHtml(item.sample_code || "") + '" data-filename="' + escapeHtml(item.filename || "") + '"';
      return [
        '<article class="argilo-drx__raw-item">',
        '<div><strong>', escapeHtml(item.sample_code || "Amostra sem codigo"), "</strong> ", treatmentBadge({ treatment: item.preparation, treatment_label: item.preparation_label }),
        '<p>', escapeHtml(item.filename || ""), " · ", escapeHtml(candidates || "sem candidato mineralogico"), "</p></div>",
        '<button class="ui tiny ', alreadySelected ? "" : "primary ", 'button" type="button" ', actionAttribute, " ", alreadySelected ? "disabled" : "", ">",
        alreadySelected ? "Adicionada" : "Adicionar",
        "</button>",
        "</article>",
      ].join("");
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrCurveLabel(curve) {
    // RRUFF ODR entra como camada opcional confirmada por checksum/amostra, nao
    // como substituto automatico de WebMineral ou da curadoria local.
    return [
      curve.argilomineral_id || curve.searched_name || "argilomineral",
      curve.rruff_id || "RRUFF",
      curve.sample || "amostra",
      curve.file_type === "processed_xy" ? "Processed" : "RAW",
    ].filter(Boolean).join(" | ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function isValidRruffOdrChecksum(value) {
    return /^[a-f0-9]{64}$/i.test(String(value || ""));
  }

  function isConfirmedRruffOdrCurve(curve) {
    return Boolean(
      curve &&
      isValidRruffOdrChecksum(curve.sha256) &&
      String(curve.rruff_id || "").trim() &&
      String(curve.sample || "").trim() &&
      Array.isArray(curve.points) &&
      curve.points.length
    );
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrPolicyText() {
    return "Camada opcional de revisão; WebMineral fica como fallback/comparação quando há RRUFF ODR confirmado.";
  }

  function rruffOdrCurveMineralSlug(curve) {
    return resolveMineralSlug(curve && (curve.argilomineral_id || curve.searched_name || curve.mineral_name))
      || mineralSlug(curve && (curve.argilomineral_id || curve.searched_name || curve.mineral_name));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrCurveMatchesSlug(curve, slug) {
    return Boolean(slug && rruffOdrCurveMineralSlug(curve) === slug);
  }

  function rruffOdrCurvesForSlug(slug, curves) {
    if (!slug) return [];
    return (curves || rruffOdrCurves).filter(function (curve) {
      return rruffOdrCurveMatchesSlug(curve, slug);
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrActiveTarget() {
    if (rruffOdrTargetSlug) {
      return { slug: rruffOdrTargetSlug, label: rruffOdrTargetLabel || rruffOdrTargetSlug, source: "rruff" };
    }
    return activePanelArgilomineral(selectedItemsInNgcOrder());
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function setRruffOdrTargetMineral(slug, label) {
    rruffOdrTargetSlug = resolveMineralSlug(slug) || mineralSlug(slug);
    rruffOdrTargetLabel = label || slug || "";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function syncRruffOdrTypeToTarget() {
    const target = rruffOdrActiveTarget();
    if (!target || !target.slug || !rruffOdrTypeEl) return;
    const targetCurves = rruffOdrCurvesForSlug(target.slug);
    if (!targetCurves.length) return;
    const currentType = rruffOdrTypeEl.value || "raw_xy";
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    const hasCurrentType = currentType === "all" || targetCurves.some(function (curve) {
      return curve.file_type === currentType;
    });
    if (hasCurrentType) return;
    if (targetCurves.some(function (curve) { return curve.file_type === "raw_xy"; })) {
      rruffOdrTypeEl.value = "raw_xy";
    } else if (targetCurves.some(function (curve) { return curve.file_type === "processed_xy"; })) {
      rruffOdrTypeEl.value = "processed_xy";
    } else {
      rruffOdrTypeEl.value = "all";
    }
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrFilteredCurves() {
    const type = rruffOdrTypeEl ? rruffOdrTypeEl.value : "raw_xy";
    const target = rruffOdrActiveTarget();
    const curves = type === "all" ? rruffOdrCurves : rruffOdrCurves.filter(function (curve) {
      return curve.file_type === type;
    });
    if (!target || !target.slug) return curves;
    return curves.filter(function (curve) {
      return rruffOdrCurveMatchesSlug(curve, target.slug);
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrPreferredCurveIndex(curves) {
    const slug = currentArgilomineralSlug();
    if (!slug) return curves.length ? curves[0].__rruffIndex : -1;
    const match = curves.find(function (curve) {
      return mineralSlug(curve.argilomineral_id || curve.searched_name || curve.mineral_name) === slug;
    });
    return match ? match.__rruffIndex : (curves.length ? curves[0].__rruffIndex : -1);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function populateRruffOdrSelect() {
    if (!rruffOdrCurveEl) return;
    const previous = rruffOdrCurveEl.value;
    syncRruffOdrTypeToTarget();
    const curves = rruffOdrFilteredCurves();
    rruffOdrCurveEl.innerHTML = "";
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!curves.length) {
      const target = rruffOdrActiveTarget();
      const option = document.createElement("option");
      option.value = "";
      option.textContent = target && target.slug
        ? "Sem curva RRUFF ODR confirmada para " + (target.label || target.slug)
        : "Sem curva RRUFF ODR para o filtro atual";
      rruffOdrCurveEl.appendChild(option);
      return;
    }
    curves.forEach(function (curve) {
      const option = document.createElement("option");
      option.value = String(curve.__rruffIndex);
      option.textContent = rruffOdrCurveLabel(curve);
      rruffOdrCurveEl.appendChild(option);
    });
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (previous && curves.some(function (curve) { return String(curve.__rruffIndex) === previous; })) {
      rruffOdrCurveEl.value = previous;
    } else {
      const preferred = rruffOdrPreferredCurveIndex(curves);
      if (preferred >= 0) rruffOdrCurveEl.value = String(preferred);
    }
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function selectedRruffOdrCurve() {
    if (!rruffOdrCurveEl) return null;
    const selectedIndex = Number(rruffOdrCurveEl.value);
    const target = rruffOdrActiveTarget();
    const filteredCurves = rruffOdrFilteredCurves();
    return rruffOdrCurves.find(function (curve) {
      return curve.__rruffIndex === selectedIndex && (!target || !target.slug || rruffOdrCurveMatchesSlug(curve, target.slug));
    }) || filteredCurves[0] || null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrNormalizedY(curve, values) {
    const normalize = rruffOdrNormalizeEl ? rruffOdrNormalizeEl.checked : true;
    if (!normalize) return values;
    const max = Number(curve.intensity_max) || Math.max.apply(null, values.filter(Number.isFinite)) || 1;
    return values.map(function (value) {
      return Number.isFinite(value) ? value / max : null;
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRruffOdrMeta(curve) {
    if (!rruffOdrMetaEl || !curve) return;
    const typeLabel = curve.file_type === "processed_xy" ? "Processed XY" : "RAW XY";
    const thetaRange = formatNumber(Number(curve.two_theta_min), 2) + "-" + formatNumber(Number(curve.two_theta_max), 2) + " 2θ";
    rruffOdrMetaEl.innerHTML = [
      '<div><strong>Mineral</strong><span>', mineralLink(curve.mineral_name || curve.searched_name || curve.argilomineral_id), "</span></div>",
      '<div><strong>RRUFF</strong><span>', escapeHtml(curve.rruff_id || "N/D"), " · ", escapeHtml(curve.sample || "amostra nao informada"), "</span></div>",
      '<div><strong>Curva</strong><span>', escapeHtml(typeLabel), " · ", escapeHtml(formatNumber(Number(curve.points_count), 0)), " pontos originais</span></div>",
      '<div><strong>Faixa</strong><span>', escapeHtml(thetaRange), "</span></div>",
      '<div><strong>SHA256</strong><span>', escapeHtml(String(curve.sha256 || "").slice(0, 18) || "N/D"), "</span></div>",
      '<div><strong>Integridade</strong><span>checksum, RRUFF ID e amostra confirmados</span></div>',
      '<div><strong>Política</strong><span>', escapeHtml(rruffOdrPolicyText()), "</span></div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRruffOdrStatus(curve, rendererLabel) {
    if (!rruffOdrStatusEl || !curve) return;
    const target = rruffOdrActiveTarget();
    const rejectedText = rruffOdrRejectedCount
      ? " " + rruffOdrRejectedCount + " curva(s) incompleta(s) ocultada(s)."
      : "";
    const rendererText = rendererLabel ? " Renderização: " + rendererLabel + "." : "";
    const targetText = target && target.slug ? " Mineral ativo: " + (target.label || target.slug) + "." : "";
    rruffOdrStatusEl.textContent = rruffOdrCurves.length + " curvas RRUFF ODR confirmadas; exibindo " + rruffOdrCurveLabel(curve) + "." + targetText + rejectedText + rendererText;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRruffOdrAbsenceRule(target) {
    if (!target || !target.slug) return;
    if (rruffOdrStatusEl) {
      rruffOdrStatusEl.textContent = "Regra de ausência RRUFF ODR: sem curva confirmada para " + (target.label || target.slug) + ".";
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (rruffOdrChartEl) {
      rruffOdrChartEl.innerHTML = [
        '<div class="argilo-drx__rruff-absence">',
        "<h3>Regra de ausência temporária</h3>",
        "<p>Não há curva RRUFF ODR confirmada para <strong>", escapeHtml(target.label || target.slug), "</strong> neste pacote derivado.</p>",
        "<p>A hipótese mineralógica não deve ser descartada apenas por ausência de RRUFF ODR. Compensar com comportamento N/G/C, picos diagnósticos observados, CMS/Handbook quando disponíveis, QC do processamento e WebMineral apenas como fallback/comparação.</p>",
        "<p>Marcar como pendente de amostra RRUFF ODR curada até haver checksum, RRUFF ID e amostra confirmados para este argilomineral.</p>",
        "</div>",
      ].join("");
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (rruffOdrMetaEl) {
      rruffOdrMetaEl.innerHTML = [
        '<div><strong>Mineral</strong><span>', escapeHtml(target.label || target.slug), "</span></div>",
        '<div><strong>Status RRUFF ODR</strong><span>ausente no manifesto confirmado</span></div>',
        '<div><strong>Compensação</strong><span>N/G/C, picos diagnósticos, CMS/Handbook e QC</span></div>',
        '<div><strong>Fallback</strong><span>WebMineral só como comparação auxiliar</span></div>',
      ].join("");
    }
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrScale(value, domainMin, domainMax, rangeMin, rangeMax) {
    if (!Number.isFinite(value)) return null;
    if (domainMax === domainMin) return (rangeMin + rangeMax) / 2;
    return rangeMin + ((value - domainMin) / (domainMax - domainMin)) * (rangeMax - rangeMin);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrLinePath(points, sx, sy) {
    let started = false;
    return points.map(function (point) {
      const x = sx(Number(point[0]));
      const y = sy(Number(point[1]));
      if (!Number.isFinite(x) || !Number.isFinite(y)) {
        started = false;
        return "";
      }
      const prefix = started ? "L" : "M";
      started = true;
      return prefix + svgNumber(x) + " " + svgNumber(y);
    }).filter(Boolean).join(" ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rruffOdrTicks(minValue, maxValue, count) {
    const ticks = [];
    const total = Math.max(2, count || 5);
    if (!Number.isFinite(minValue) || !Number.isFinite(maxValue)) return ticks;
    for (let index = 0; index < total; index += 1) {
      ticks.push(minValue + ((maxValue - minValue) * index / (total - 1)));
    }
    return ticks;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRruffOdrSvgChart(curve, xValues, rawY, yValues) {
    const width = 960;
    const height = 520;
    const margin = { top: 34, right: 30, bottom: 58, left: 68 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const xMin = Math.min.apply(null, xValues);
    const xMax = Math.max.apply(null, xValues);
    const finiteY = yValues.filter(Number.isFinite);
    const yMin = Math.min(0, Math.min.apply(null, finiteY));
    const yMax = Math.max.apply(null, finiteY);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    const yLimit = yMax === yMin ? yMax + 1 : yMax;
    const sx = function (value) { return rruffOdrScale(value, xMin, xMax, margin.left, margin.left + plotWidth); };
    const sy = function (value) { return rruffOdrScale(value, yMin, yLimit, margin.top + plotHeight, margin.top); };
    const pathPoints = xValues.map(function (xValue, index) {
      return [xValue, yValues[index]];
    });
    const path = rruffOdrLinePath(pathPoints, sx, sy);
    const xTicks = rruffOdrTicks(xMin, xMax, 7).map(function (tick) {
      const x = sx(tick);
      return [
        '<line x1="', svgNumber(x), '" y1="', svgNumber(margin.top), '" x2="', svgNumber(x), '" y2="', svgNumber(margin.top + plotHeight), '" stroke="#edf2f0"/>',
        '<text x="', svgNumber(x), '" y="', svgNumber(height - 22), '" text-anchor="middle">', escapeHtml(formatNumber(tick, 1)), "</text>",
      ].join("");
    }).join("");
    const yTicks = rruffOdrTicks(yMin, yLimit, 6).map(function (tick) {
      const y = sy(tick);
      return [
        '<line x1="', svgNumber(margin.left), '" y1="', svgNumber(y), '" x2="', svgNumber(width - margin.right), '" y2="', svgNumber(y), '" stroke="#edf2f0"/>',
        '<text x="', svgNumber(margin.left - 10), '" y="', svgNumber(y + 4), '" text-anchor="end">', escapeHtml(formatNumber(tick, 2)), "</text>",
      ].join("");
    }).join("");
    const max = Number(curve.intensity_max) || Math.max.apply(null, rawY.filter(Number.isFinite)) || 1;
    const peakMarks = rruffOdrPeaksEl && rruffOdrPeaksEl.checked && curve.peaks && curve.peaks.length
      ? curve.peaks.map(function (peak) {
        const peakX = Number(peak.two_theta);
        const peakRawY = Number(peak.intensity);
        if (!Number.isFinite(peakX) || !Number.isFinite(peakRawY)) return "";
        const peakY = rruffOdrNormalizeEl && rruffOdrNormalizeEl.checked ? peakRawY / max : peakRawY;
        const x = sx(peakX);
        const y = sy(peakY);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return "";
        return [
          '<g class="argilo-drx__rruff-peak">',
          '<line x1="', svgNumber(x - 4), '" y1="', svgNumber(y - 4), '" x2="', svgNumber(x + 4), '" y2="', svgNumber(y + 4), '"/>',
          '<line x1="', svgNumber(x - 4), '" y1="', svgNumber(y + 4), '" x2="', svgNumber(x + 4), '" y2="', svgNumber(y - 4), '"/>',
          "<title>pico 2θ ", escapeHtml(formatNumber(peakX, 2)), " · I ", escapeHtml(formatNumber(peakY, 3)), "</title>",
          "</g>",
        ].join("");
      }).join("")
      : "";
    const yAxisTitle = rruffOdrNormalizeEl && rruffOdrNormalizeEl.checked ? "Intensidade normalizada" : "Intensidade";
    rruffOdrChartEl.innerHTML = [
      '<svg class="argilo-drx__rruff-svg" viewBox="0 0 ', width, " ", height, '" role="img" aria-label="Curva RRUFF ODR">',
      '<rect x="0" y="0" width="', width, '" height="', height, '" fill="#ffffff"/>',
      '<text x="', margin.left, '" y="22" class="argilo-drx__rruff-svg-title">', escapeHtml(rruffOdrCurveLabel(curve)), "</text>",
      '<g class="argilo-drx__rruff-svg-grid">', xTicks, yTicks, "</g>",
      '<rect x="', margin.left, '" y="', margin.top, '" width="', plotWidth, '" height="', plotHeight, '" fill="none" stroke="#aebdb8"/>',
      '<path d="', path, '" fill="none" stroke="#2f6f73" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>',
      peakMarks,
      '<text x="', margin.left + plotWidth / 2, '" y="', height - 6, '" text-anchor="middle">2θ</text>',
      '<text transform="translate(18 ', margin.top + plotHeight / 2, ') rotate(-90)" text-anchor="middle">', escapeHtml(yAxisTitle), "</text>",
      '<g class="argilo-drx__rruff-svg-legend"><line x1="', width - 190, '" y1="20" x2="', width - 160, '" y2="20"/><text x="', width - 152, '" y="24">', curve.file_type === "processed_xy" ? "Processed XY" : "RAW XY", "</text></g>",
      "</svg>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRruffOdrPlot() {
    if (!rruffOdrPanelEl || rruffOdrPanelEl.hidden || !rruffOdrChartEl) return;
    const curve = selectedRruffOdrCurve();
    if (!curve) {
      const target = rruffOdrActiveTarget();
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (target && target.slug) {
        renderRruffOdrAbsenceRule(target);
        return;
      }
      if (rruffOdrStatusEl) rruffOdrStatusEl.textContent = "Nenhuma curva RRUFF ODR disponivel para o filtro atual.";
      rruffOdrChartEl.innerHTML = "";
      if (rruffOdrMetaEl) rruffOdrMetaEl.innerHTML = "";
      return;
    }
    const points = (curve.points || []).filter(function (point) {
      return point && Number.isFinite(Number(point[0])) && Number.isFinite(Number(point[1]));
    });
    const xValues = points.map(function (point) { return Number(point[0]); });
    const rawY = points.map(function (point) { return Number(point[1]); });
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!xValues.length || !rawY.length) {
      if (rruffOdrStatusEl) rruffOdrStatusEl.textContent = "Curva RRUFF ODR sem pontos numericos validos para desenhar.";
      rruffOdrChartEl.innerHTML = "";
      if (rruffOdrMetaEl) rruffOdrMetaEl.innerHTML = "";
      return;
    }
    const yValues = rruffOdrNormalizedY(curve, rawY);
    const traces = [{
      x: xValues,
      y: yValues,
      mode: "lines",
      name: curve.file_type === "processed_xy" ? "Processed XY" : "RAW XY",
      line: { color: "#2f6f73", width: 1.5 },
      hovertemplate: "2θ %{x:.2f}<br>I %{y:.3f}<extra></extra>",
    }];
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (rruffOdrPeaksEl && rruffOdrPeaksEl.checked && curve.peaks && curve.peaks.length) {
      const max = Number(curve.intensity_max) || Math.max.apply(null, rawY.filter(Number.isFinite)) || 1;
      traces.push({
        x: curve.peaks.map(function (peak) { return Number(peak.two_theta); }).filter(Number.isFinite),
        y: curve.peaks.map(function (peak) {
          const value = Number(peak.intensity);
          if (!Number.isFinite(value)) return null;
          return rruffOdrNormalizeEl && rruffOdrNormalizeEl.checked ? value / max : value;
        }),
        mode: "markers",
        name: "Picos",
        marker: { color: "#b65f3a", size: 6, symbol: "x" },
        hovertemplate: "pico 2θ %{x:.2f}<br>I %{y:.3f}<extra></extra>",
      });
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (window.Plotly && typeof window.Plotly.react === "function") {
      window.Plotly.react(rruffOdrChartEl, traces, {
        autosize: true,
        margin: { t: 22, r: 22, b: 52, l: 62 },
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        xaxis: {
          title: "2θ",
          gridcolor: "#d8e1dd",
          zeroline: false,
        },
        yaxis: {
          title: rruffOdrNormalizeEl && rruffOdrNormalizeEl.checked ? "Intensidade normalizada" : "Intensidade",
          gridcolor: "#d8e1dd",
          zeroline: false,
        },
        showlegend: true,
        legend: { orientation: "h", x: 0, y: 1.12 },
        font: { family: "inherit", color: "#27342f" },
      }, {
        displaylogo: false,
        responsive: true,
      });
      renderRruffOdrMeta(curve);
      renderRruffOdrStatus(curve, "Plotly");
      return;
    }
    renderRruffOdrSvgChart(curve, xValues, rawY, yValues);
    renderRruffOdrMeta(curve);
    renderRruffOdrStatus(curve, "SVG local offline");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadRruffOdrCurves() {
    if (!rruffOdrCurvesUrl) {
      if (rruffOdrStatusEl) rruffOdrStatusEl.textContent = "Manifesto RRUFF ODR nao configurado.";
      return Promise.resolve([]);
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (rruffOdrLoaded) {
      populateRruffOdrSelect();
      renderRruffOdrPlot();
      return Promise.resolve(rruffOdrCurves);
    }
    if (rruffOdrLoadingPromise) return rruffOdrLoadingPromise;
    if (rruffOdrStatusEl) rruffOdrStatusEl.textContent = "Carregando referencias RRUFF ODR...";
    rruffOdrLoadingPromise = fetchJson(rruffOdrCurvesUrl)
      .then(function (payload) {
        const sourceCurves = Array.isArray(payload) ? payload : ((payload && payload.curves) || []);
        const preparedCurves = sourceCurves.map(function (curve, index) {
          const preparedCurve = Object.assign({}, curve || {});
          preparedCurve.__rruffIndex = index;
          return preparedCurve;
        });
        rruffOdrRejectedCount = preparedCurves.filter(function (curve) {
          return !isConfirmedRruffOdrCurve(curve);
        }).length;
        rruffOdrCurves = preparedCurves.filter(isConfirmedRruffOdrCurve);
        rruffOdrLoaded = true;
        syncRruffOdrTypeToTarget();
        populateRruffOdrSelect();
        renderRruffOdrPlot();
        return rruffOdrCurves;
      })
      .catch(function (error) {
        if (rruffOdrStatusEl) rruffOdrStatusEl.textContent = error.message || "Falha ao carregar referencias RRUFF ODR.";
        throw error;
      })
      .finally(function () {
        rruffOdrLoadingPromise = null;
      });
    return rruffOdrLoadingPromise;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function showRruffOdrPanel(target) {
    if (!rruffOdrPanelEl) return;
    if (target && target.slug) {
      setRruffOdrTargetMineral(target.slug, target.label);
    } else {
      const activeTarget = activePanelArgilomineral(selectedItemsInNgcOrder());
      if (activeTarget && activeTarget.slug) setRruffOdrTargetMineral(activeTarget.slug, activeTarget.label);
      else setRruffOdrTargetMineral("", "");
    }
    rruffOdrPanelEl.hidden = false;
    if (toggleRruffOdrEl) toggleRruffOdrEl.setAttribute("aria-pressed", "true");
    loadRruffOdrCurves()
      .then(function () {
        renderMineralPanel();
      })
      .catch(function () {});
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function syncRruffOdrWithActivePanelMineral() {
    if (!rruffOdrPanelEl || rruffOdrPanelEl.hidden || !rruffOdrLoaded) return;
    const activeTarget = activePanelArgilomineral(selectedItemsInNgcOrder());
    if (activeTarget && activeTarget.slug) setRruffOdrTargetMineral(activeTarget.slug, activeTarget.label);
    else setRruffOdrTargetMineral("", "");
    syncRruffOdrTypeToTarget();
    populateRruffOdrSelect();
    renderRruffOdrPlot();
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function staticManifestUrl(recordId) {
    return "/argiloteca/static/data/analytical_packages/" + encodeURIComponent(recordId) + "/drx_manifest.json";
  }

  function loadStaticManifest(recordId) {
    if (staticManifest && staticManifest.record_id === recordId) return Promise.resolve(staticManifest);
    return fetch(staticManifestUrl(recordId), { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("Manifesto do pacote analitico nao encontrado para " + recordId + ".");
        return response.json();
      })
      .then(function (manifest) {
        staticManifest = manifest;
        return staticManifest;
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadPackageItems(recordId) {
    if (!recordId && rawSnapshotUrl) {
      const limit = 500;
      const allItems = [];
      function fetchSnapshotPage(offset) {
        const query = new URLSearchParams();
        query.set("limit", String(limit));
        query.set("offset", String(offset));
        return fetchJson(rawSnapshotUrl + "?" + query.toString())
          .then(function (payload) {
            const items = payload.items || [];
            items.forEach(function (item) { allItems.push(item); });
            const pagination = payload.pagination || {};
            const total = Number(pagination.total || allItems.length);
            const returned = Number(pagination.returned || items.length);
            if (returned > 0 && allItems.length < Math.min(total, 2000)) return fetchSnapshotPage(offset + returned);
            return allItems;
          });
      }
      return fetchSnapshotPage(0);
    }
    const limit = 500;
    const allItems = [];
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    function fetchPage(offset) {
      const query = new URLSearchParams();
      query.set("limit", String(limit));
      query.set("offset", String(offset));
      return fetchPackageJson(recordId, query)
        .then(function (payload) {
          if (payload.success === false) throw new Error(payload.error || "Falha ao carregar pacote analitico.");
          if (payload.exists === false) throw new Error(payload.message || "Nenhum pacote analitico foi encontrado para este registro.");
          const items = payload.items || [];
          items.forEach(function (item) { allItems.push(item); });
          const pagination = payload.pagination || {};
          const total = Number(pagination.total || allItems.length);
          const returned = Number(pagination.returned || items.length);
          if (returned > 0 && allItems.length < total) return fetchPage(offset + returned);
          return allItems;
        });
    }
    return fetchPage(0)
      .catch(function (error) {
        if (staticManifest && staticManifest.record_id === recordId) return staticManifest.items || [];
        return loadStaticManifest(recordId).then(function (manifest) { return manifest.items || []; }).catch(function () {
          throw error;
        });
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function itemMatchesRawPickerFilters(item, q, preparation) {
    if (preparation && item.preparation !== preparation) return false;
    if (!q) return true;
    const normalized = q.toLowerCase();
    const values = [
      item.sample_code,
      item.sample_base,
      item.filename,
      item.preparation_label,
      item.status,
    ];
    (item.mineral_candidates || []).forEach(function (candidate) {
      values.push(candidate.mineral, candidate.group, candidate.formula);
    });
    return values.some(function (value) {
      return String(value || "").toLowerCase().indexOf(normalized) !== -1;
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function rawPickerPayloadFromStaticManifest(manifest) {
    const formData = new FormData(rawPickerFormEl);
    const q = String(formData.get("q") || "").trim();
    const preparation = String(formData.get("preparation") || "").trim();
    let items = manifest.items || [];
    items = items.filter(function (item) {
      return itemMatchesRawPickerFilters(item, q, preparation);
    });
    return {
      success: true,
      items: items.slice(0, 80),
      pagination: { total: items.length, limit: 80, offset: 0, returned: Math.min(items.length, 80) },
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fetchRawPickerPayload(recordId, query) {
    if (!recordId && rawSnapshotUrl) {
      return fetchJson(rawSnapshotUrl + "?" + query.toString());
    }
    return fetchPackageJson(recordId, query)
      .then(function (payload) {
        if (payload.success === false) throw new Error(payload.error || "Falha ao carregar amostras RAW.");
        return payload;
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadRawPickerItems() {
    const recordId = currentRecordId();
    const query = new URLSearchParams();
    query.set("limit", "40");
    query.set("offset", "0");
    new FormData(rawPickerFormEl).forEach(function (value, key) {
      if (String(value).trim() !== "") query.set(key, value);
    });
    rawPickerStatusEl.textContent = recordId
      ? "Carregando amostras RAW do pacote " + packageDisplayLabel(recordId) + "..."
      : "Carregando arquivos RAW do snapshot geral do módulo DRX...";
    fetchRawPickerPayload(recordId, query)
      .then(function (payload) {
        rawPickerStatusEl.textContent = (payload.pagination && payload.pagination.total ? payload.pagination.total : 0) + " amostra(s) encontrada(s).";
        renderRawPickerItems(payload.items || []);
      })
      .catch(function (error) {
        rawPickerStatusEl.textContent = error.message;
        rawPickerListEl.innerHTML = "";
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadSuggestionItems(recordId) {
    if (recordId) return loadPackageItems(recordId);
    if (!rawSnapshotUrl) return Promise.resolve([]);
    const query = new URLSearchParams();
    query.set("limit", "300");
    query.set("offset", "0");
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (rawPickerFormEl) {
      new FormData(rawPickerFormEl).forEach(function (value, key) {
        if (String(value).trim() !== "") query.set(key, value);
      });
    }
    return fetchRawPickerPayload(null, query)
      .then(function (payload) {
        if (payload.success === false) throw new Error(payload.error || "Falha ao carregar snapshot RAW.");
        return payload.items || [];
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadSuggestionPayload(recordId) {
    if (recordId || !rawSnapshotSuggestionsUrl) {
      return loadSuggestionItems(recordId).then(function (items) {
        return { success: true, items: items || [] };
      });
    }
    const query = new URLSearchParams();
    query.set("limit", "80");
    query.set("compact", "1");
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (rawPickerFormEl) {
      new FormData(rawPickerFormEl).forEach(function (value, key) {
        if (String(value).trim() !== "") query.set(key, value);
      });
    }
    return fetchJson(rawSnapshotSuggestionsUrl + "?" + query.toString())
      .then(function (payload) {
        if (payload.success === false) throw new Error(payload.error || "Falha ao carregar sugestões do snapshot RAW.");
        return payload;
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildComparisonSuggestions(items) {
    const grouped = new Map();
    const byPreparation = { natural: [], glicolado: [], calcinado: [], indeterminado: [] };
    const byMineral = new Map();
    (items || []).forEach(function (item) {
      const base = item.sample_base || item.sample_code || item.filename;
      const group = grouped.get(base) || { sampleBase: base, items: {}, allItems: [] };
      if (item.preparation && !group.items[item.preparation]) group.items[item.preparation] = item;
      group.allItems.push(item);
      grouped.set(base, group);
      if (byPreparation[item.preparation]) byPreparation[item.preparation].push(item);
      (item.mineral_candidates || []).slice(0, 3).forEach(function (candidate) {
        if (!candidate.mineral) return;
        const bucket = byMineral.get(candidate.mineral) || [];
        bucket.push(item);
        byMineral.set(candidate.mineral, bucket);
      });
    });
    const suggestions = [];
    const add = function (type, label, priority, group, suggestionItems) {
      const seen = new Set();
      const uniqueItems = suggestionItems.filter(function (item) {
        const key = item.sample_code || item.filename;
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (uniqueItems.length >= 2) {
        suggestions.push({ type: type, label: label, priority: priority, group: group, items: uniqueItems.slice(0, 6) });
      }
    };
    grouped.forEach(function (group) {
      const natural = group.items.natural;
      const glicolado = group.items.glicolado;
      const calcinado = group.items.calcinado;
      const indeterminado = group.items.indeterminado;
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (natural && glicolado && calcinado) {
        add("trio", "Natural x glicolado x calcinado", 1, group, [natural, glicolado, calcinado]);
      } else if (natural && glicolado) {
        add("ng", "Natural x glicolado", 2, group, [natural, glicolado]);
      } else if (natural && calcinado) {
        add("nc", "Natural x calcinado", 3, group, [natural, calcinado]);
      } else if (glicolado && calcinado) {
        add("gc", "Glicolado x calcinado", 4, group, [glicolado, calcinado]);
      }
      if (indeterminado && (natural || glicolado || calcinado)) {
        add("indeterminado", "Arquivo indeterminado x preparação conhecida", 5, group, [indeterminado, natural, glicolado, calcinado].filter(Boolean));
      }
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (group.allItems.length >= 3) {
        add("replicatas", "Conjunto com múltiplos arquivos da mesma amostra-base", 8, group, group.allItems);
      }
    });
    byMineral.forEach(function (mineralItems, mineral) {
      const sampleBases = new Set(mineralItems.map(function (item) { return item.sample_base || item.sample_code; }));
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (sampleBases.size >= 2) {
        add("mineral", "Mesmo candidato mineralógico: " + mineral, 6, { sampleBase: "Mineral: " + mineral }, mineralItems);
      }
    });
    Object.keys(byPreparation).forEach(function (preparation) {
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (byPreparation[preparation].length >= 3) {
        add("preparo", "Comparar arquivos com preparo " + treatmentLabel(preparation), 7, { sampleBase: "Preparo: " + treatmentLabel(preparation) }, byPreparation[preparation]);
      }
    });
    return suggestions.sort(function (left, right) {
      return (left.priority - right.priority) || String(left.group.sampleBase).localeCompare(String(right.group.sampleBase));
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderSuggestions(suggestions) {
    comparisonSuggestions = suggestions;
    if (!suggestionsListEl) return;
    if (!suggestions.length) {
      suggestionsListEl.innerHTML = '<div class="argilo-drx__empty">Nenhum par natural/glicolado/calcinado foi identificado no pacote.</div>';
      return;
    }
    suggestionsListEl.innerHTML = suggestions.map(function (suggestion, index) {
      const files = suggestion.items.map(function (item) {
        return escapeHtml(item.sample_code || item.filename) + " " + treatmentBadge({ treatment: item.preparation, treatment_label: item.preparation_label });
      }).join(" · ");
      return [
        '<article class="argilo-drx__suggestion-item">',
        '<div><strong>', escapeHtml(suggestion.group.sampleBase), '</strong><p>', escapeHtml(suggestion.label), '<br>', files, '</p></div>',
        '<button class="ui tiny primary button" type="button" data-add-suggestion="', index, '">Adicionar grupo</button>',
        '</article>',
      ].join("");
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function comparisonSuggestionRank(suggestion) {
    if (suggestionHasCompleteNgcTrio(suggestion)) return 0;
    if (suggestion && suggestion.type === "ng") return 1;
    if (suggestion && (suggestion.type === "nc" || suggestion.type === "gc")) return 2;
    if (suggestion && suggestion.type === "indeterminado") return 3;
    return 4 + Number(suggestion && suggestion.priority || 0);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function prioritizeComparisonSuggestions(suggestions) {
    return (suggestions || []).slice().sort(function (left, right) {
      return (comparisonSuggestionRank(left) - comparisonSuggestionRank(right))
        || String((left.group || {}).sampleBase || "").localeCompare(String((right.group || {}).sampleBase || ""));
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function indexGeologistTriage(payload) {
    const index = new Map();
    Object.values((payload && payload.queues) || {}).forEach(function (queue) {
      (queue.items || []).forEach(function (item) {
        if (item && item.snapshot_id) index.set(item.snapshot_id, item);
        if (item && item.id) index.set(item.id, item);
      });
    });
    geologistTriageById = index;
    return payload;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function triageQueueFromSnapshotSuggestions(payload) {
    const queues = {
      alta: {
        label: "Fila alta",
        description: "Amostras com trio N/G/C ou conjunto de preparações suficiente para revisao prioritaria.",
        items: [],
        total: 0,
      },
      media: {
        label: "Fila media",
        description: "Amostras com pares de tratamentos ou evidencias parciais para revisao.",
        items: [],
        total: 0,
      },
      sem_consenso: {
        label: "Sem consenso",
        description: "Amostras sem consenso claro entre tratamentos e candidatos.",
        items: [],
        total: 0,
      },
      baixa: {
        label: "Baixa/insuficiente",
        description: "Amostras com evidencia incompleta ou menor prioridade operacional.",
        items: [],
        total: 0,
      },
    };
    (payload && payload.suggestions || []).forEach(function (suggestion) {
      const target = suggestion.type === "trio" ? "alta" : (suggestion.type === "ng" || suggestion.type === "nc" || suggestion.type === "gc" ? "media" : "sem_consenso");
      (suggestion.items || []).forEach(function (rawItem) {
        const topCandidate = (rawItem.mineral_candidates || [])[0] || {};
        const evidence = [];
        if (suggestion.label) evidence.push("Conjunto: " + suggestion.label);
        if (topCandidate.mineral) evidence.push("Candidato principal: " + topCandidate.mineral);
        if (rawItem.grupos_minerais && rawItem.grupos_minerais.length) evidence.push("Grupos: " + rawItem.grupos_minerais.slice(0, 4).join(", "));
        queues[target].items.push({
          id: rawItem.id || rawItem.diffractogram_id,
          snapshot_id: rawItem.diffractogram_id || rawItem.id,
          sample_code: rawItem.sample_code,
          source_file: rawItem.filename || rawItem.original_filename,
          treatment: rawItem.treatment || rawItem.preparation,
          webmineral: {
            top: topCandidate.mineral || (rawItem.argilominerais || [])[0],
            score: topCandidate.score,
            confidence: topCandidate.confidence,
          },
          xrdnet: {},
          evidence: evidence,
          evidence_chips: [
            { kind: "sample", label: "Amostra", value: rawItem.sample_base || (suggestion.group || {}).sampleBase },
            { kind: "treatment", label: "Preparo", value: rawItem.treatment_label || rawItem.preparation_label },
            { kind: "policy", label: "Política", value: "triagem auxiliar" },
          ],
        });
      });
    });
    Object.keys(queues).forEach(function (key) {
      queues[key].total = queues[key].items.length;
    });
    return {
      schema_version: "argiloteca.drx.geologist_triage.from_snapshot_suggestions.v1",
      source: "raw_snapshot_suggestions",
      queues: queues,
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadGeologistTriage() {
    // Fila externa de triagem geologica e cacheada localmente para nao repetir
    // downloads a cada renderizacao ou clique no painel.
    if (geologistTriagePayload || geologistTriageError) return Promise.resolve(geologistTriagePayload);
    if (geologistTriagePromise) return geologistTriagePromise;
    geologistTriagePromise = (geologistTriageUrl ? fetchOptionalJson(geologistTriageUrl) : Promise.resolve(null))
      .then(function (payload) {
        if (payload) return payload;
        if (!rawSnapshotSuggestionsUrl) return null;
        const url = rawSnapshotSuggestionsUrl + (rawSnapshotSuggestionsUrl.indexOf("?") === -1 ? "?" : "&") + "limit=80&compact=1";
        return fetchJson(url).then(triageQueueFromSnapshotSuggestions);
      })
      .then(function (payload) {
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (!payload) {
          geologistTriageError = "Fila de triagem geológica não disponível.";
          return null;
        }
        geologistTriageError = "";
        geologistTriagePayload = indexGeologistTriage(payload);
        return geologistTriagePayload;
      })
      .catch(function (error) {
        geologistTriageError = error && error.message ? error.message : "Falha ao carregar fila de triagem geológica.";
        return null;
      })
      .then(function (payload) {
        geologistTriagePromise = null;
        return payload;
      });
    return geologistTriagePromise;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadGeologistSimilarityReview() {
    if (!geologistSimilarityReviewUrl) return Promise.resolve(null);
    if (geologistSimilarityReview) return Promise.resolve(geologistSimilarityReview);
    if (geologistSimilarityReviewPromise) return geologistSimilarityReviewPromise;
    geologistSimilarityReviewPromise = fetchOptionalJson(geologistSimilarityReviewUrl)
      .then(function (payload) {
        geologistSimilarityReview = payload;
        return payload;
      })
      .catch(function () {
        return null;
      })
      .then(function (payload) {
        geologistSimilarityReviewPromise = null;
        return payload;
      });
    return geologistSimilarityReviewPromise;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderEvidenceChips(chips) {
    const rows = (chips || []).filter(Boolean);
    if (!rows.length) return "";
    return '<div class="argilo-drx__evidence-chips">' + rows.map(function (chip) {
      return '<span class="argilo-drx__evidence-chip argilo-drx__evidence-chip--' + escapeHtml(chip.kind || "evidence") + '">'
        + '<strong>' + escapeHtml(chip.label || "Evidência") + '</strong> '
        + escapeHtml(chip.value || "N/D")
        + '</span>';
    }).join("") + "</div>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function geologistQueueOrder() {
    return ["alta", "media", "sem_consenso", "baixa"];
  }

  function geologistQueueTitle(key, queue) {
    const labels = {
      alta: "Fila alta",
      media: "Fila média",
      sem_consenso: "Sem consenso",
      baixa: "Baixa/insuficiente",
    };
    return (queue && queue.label ? labels[key] || queue.label : labels[key]) || key;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderGeologistQueueItem(item) {
    const web = item.webmineral || {};
    const xrd = item.xrdnet || {};
    const evidence = (item.evidence || []).slice(0, 4).map(function (row) {
      return "<li>" + escapeHtml(row) + "</li>";
    }).join("");
    const webLine = web.top
      ? "WebMineral fallback/comparação: " + web.top + " · " + (web.confidence || "conf. N/D")
      : "WebMineral fallback/comparação: sem candidato";
    const xrdLine = xrd.top
      ? "XRDNet auxiliar: " + xrd.top + " · " + xrdnetPercent(xrd.probability)
      : "XRDNet auxiliar: sem predição";
    return [
      '<article class="argilo-drx__suggestion-item argilo-drx__triage-item">',
      "<div>",
      '<div class="argilo-drx__triage-head"><strong>', escapeHtml(item.sample_code || item.source_file || item.snapshot_id), "</strong>",
      treatmentBadge({ treatment: item.treatment, treatment_label: treatmentLabel(item.treatment) }), "</div>",
      "<p>", escapeHtml(item.source_file || "Arquivo não informado"), "</p>",
      renderEvidenceChips(item.evidence_chips),
      '<ul class="argilo-drx__evidence-list">', evidence, "</ul>",
      "<p><strong>", escapeHtml(webLine), "</strong><br><strong>", escapeHtml(xrdLine), "</strong></p>",
      "</div>",
      '<button class="ui tiny primary button" type="button" data-add-triage="', escapeHtml(item.snapshot_id || item.id), '">Carregar curva</button>',
      "</article>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderGeologistTriageQueue(payload, review) {
    comparisonSuggestions = [];
    if (!suggestionsListEl) return;
    if (!payload || !payload.queues) {
      suggestionsListEl.innerHTML = '<div class="argilo-drx__empty">' + escapeHtml(geologistTriageError || "Fila de triagem geológica não disponível.") + "</div>";
      return;
    }
    const reviewCounts = (review && review.counts) || {};
    const reviewText = review
      ? "Sugestões N/G/C revisadas: " + escapeHtml(review.total || 0)
        + " · prioridade geólogo " + escapeHtml(reviewCounts.prioridade_geologo || 0)
        + " · úteis " + escapeHtml(reviewCounts.revisao_util || 0)
        + " · baixa prioridade " + escapeHtml(reviewCounts.baixa_prioridade || 0)
      : "Sugestões N/G/C revisadas ainda não carregadas.";
    const sections = geologistQueueOrder().map(function (key) {
      const queue = payload.queues[key];
      if (!queue) return "";
      const visible = (queue.items || []).slice(0, key === "alta" ? 32 : 24);
      const rows = visible.map(renderGeologistQueueItem).join("");
      return [
        '<section class="argilo-drx__triage-queue argilo-drx__triage-queue--', escapeHtml(key), '">',
        "<h3>", escapeHtml(geologistQueueTitle(key, queue)), " · ", escapeHtml(queue.total || 0), "</h3>",
        "<p>", escapeHtml(queue.description || "Fila de revisão geológica."), "</p>",
        rows || '<div class="argilo-drx__empty">Sem itens nesta fila.</div>',
        Number(queue.total || 0) > visible.length ? '<p class="argilo-drx__mini-note">Exibindo ' + escapeHtml(visible.length) + ' de ' + escapeHtml(queue.total) + ' itens desta fila.</p>' : "",
        "</section>",
      ].join("");
    }).join("");
    suggestionsStatusEl.textContent = "Fila do geólogo: alta, média, sem consenso e baixa. " + reviewText;
    suggestionsListEl.innerHTML = [
      '<div class="argilo-drx__triage-summary">',
      "<strong>Triagem assistida para curadoria.</strong> XRDNet aparece apenas como evidência neural auxiliar; a identificação depende de picos, preparo N/G/C, RRUFF ODR confirmado quando disponível, WebMineral como fallback/comparação e QC ALS.",
      "</div>",
      sections,
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadGeologistTriageQueue() {
    if (!suggestionsStatusEl || !suggestionsListEl) return;
    suggestionsStatusEl.textContent = "Carregando fila de triagem geológica...";
    suggestionsListEl.innerHTML = "";
    Promise.all([loadGeologistTriage(), loadGeologistSimilarityReview()])
      .then(function (results) {
        renderGeologistTriageQueue(results[0], results[1]);
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function addTriageCandidate(snapshotId) {
    const item = geologistTriageById.get(snapshotId);
    if (!snapshotId) return Promise.resolve();
    statusEl.textContent = "Carregando curva da fila do geólogo...";
    return addSnapshotRaw(snapshotId, {
      loadedAsSimilar: false,
      similaritySource: "geologist_triage_queue",
      geologistTriage: item || null,
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadComparisonSuggestions() {
    const recordId = currentRecordId();
    suggestionsStatusEl.textContent = recordId
      ? "Calculando sugestões do pacote " + packageDisplayLabel(recordId) + "..."
      : "Calculando sugestões do snapshot geral DRX...";
    Promise.all([loadSuggestionPayload(recordId), loadGeologistSimilarityReview()])
      .then(function (results) {
        const payload = results[0];
        const review = results[1];
        const suggestions = prioritizeComparisonSuggestions(payload.suggestions || buildComparisonSuggestions(payload.items || []));
        const pagination = payload.pagination || {};
        const meta = payload.meta || {};
        const totalSuggestions = Number(pagination.total || suggestions.length);
        const returnedSuggestions = Number(pagination.returned || suggestions.length);
        const reviewCounts = (review && review.counts) || {};
        const reviewText = review
          ? " Revisão N/G/C: " + Number(reviewCounts.prioridade_geologo || 0) + " prioridade geólogo, "
            + Number(reviewCounts.revisao_util || 0) + " úteis, "
            + Number(reviewCounts.baixa_prioridade || 0) + " baixa prioridade."
          : "";
        suggestionsStatusEl.textContent = recordId
          ? totalSuggestions + " sugestão(ões) encontradas: preparações, minerais candidatos, indeterminados e replicatas."
          : totalSuggestions + " conjunto(s) encontrado(s) em " + Number(meta.items_total || 0) + " RAW do snapshot geral."
            + (returnedSuggestions < totalSuggestions ? " Exibindo " + returnedSuggestions + "." : "")
            + reviewText;
        renderSuggestions(suggestions);
      })
      .catch(function (error) {
        suggestionsStatusEl.textContent = error.message;
        suggestionsListEl.innerHTML = "";
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function addSuggestion(index) {
    const suggestion = comparisonSuggestions[index];
    if (!suggestion) return;
    const recordId = currentRecordId();
    statusEl.textContent = "Adicionando grupo sugerido...";
    Promise.all(suggestion.items.map(function (item) {
      const snapshotId = item.diffractogram_id || item.id || "";
      if (item.source === "snapshot_geral_raw" || String(snapshotId).indexOf("snapshot:") === 0) {
        return addSnapshotRaw(snapshotId, { loadedAsSimilar: true, similaritySource: "comparison_suggestion" });
      }
      return addPackageCurve(recordId, item.sample_code, item.filename, { loadedAsSimilar: true, similaritySource: "comparison_suggestion" });
    })).then(function () {
      statusEl.textContent = "Grupo sugerido adicionado ao gráfico.";
      renderSuggestions(comparisonSuggestions);
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function toggleSelection(id, checked) {
    if (!checked) {
      selected.delete(id);
      xDomain = null;
      renderAll();
      return;
    }
    const context = diffractogramContext(id);
    if (!context) return;
    const record = context.record;
    const diffractogram = context.diffractogram;
    statusEl.textContent = "Carregando difratograma selecionado...";
    fetchJson(diffractogramUrl(id))
      .then(function (payload) {
        const metadata = payload.metadata || {};
        selected.set(id, {
          id: id,
          record: record,
          diffractogram: diffractogram,
          sampleCode: diffractogram.sample_code || metadata.sample_code,
          sample: diffractogram.sample || {},
          treatment: diffractogram.treatment || metadata.treatment || "indeterminado",
          treatment_label: diffractogram.treatment_label || metadata.treatment_label || "Indeterminado",
          treatment_confidence: diffractogram.treatment_confidence || metadata.treatment_confidence,
          treatment_evidence: diffractogram.treatment_evidence || metadata.treatment_evidence,
          mineralCandidates: diffractogram.mineral_candidates || metadata.mineral_candidates || [],
          detectedPeaks: diffractogram.detected_peaks || diffractogram.peaks || metadata.detected_peaks || metadata.peaks || [],
          advancedPeaks: diffractogram.advanced_peaks || metadata.advanced_peaks || [],
          targetedBasalPeaks: diffractogram.targeted_basal_peaks || metadata.targeted_basal_peaks || [],
          fitResults: diffractogram.fit_results || metadata.fit_results || [],
          mineralEvidence: diffractogram.mineral_evidence || metadata.mineral_evidence || [],
          mineralCharacterization: diffractogram.mineral_characterization || metadata.mineral_characterization || [],
          qcFlags: diffractogram.qc_flags || metadata.qc_flags || [],
          advancedResultPath: diffractogram.advanced_result_path || metadata.advanced_result_path || null,
          advancedSummary: diffractogram.advanced_summary || metadata.advanced_summary || {},
          advancedCurve: payload.advanced_curve || diffractogram.advanced_curve || metadata.advanced_curve || {},
          basalTracking: diffractogram.basal_tracking || metadata.basal_tracking || {},
          mineralClassification: diffractogram.mineral_classification || metadata.mineral_classification || {},
          analyses: diffractogram.analyses || [],
          argilominerais: diffractogram.argilominerais || [],
          gruposMinerais: diffractogram.grupos_minerais || [],
          recordLevelArgilominerais: diffractogram.record_level_argilominerais || [],
          traceability: diffractogram.traceability || {},
          metadata: metadata,
          neuralEvidence: { loading: true },
          twoTheta: payload.two_theta || [],
          intensity: payload.intensity || [],
        });
        loadNeuralEvidenceForItem(selected.get(id));
        xDomain = null;
        renderAll();
      })
      .catch(function (error) {
        statusEl.textContent = error.message;
        const input = recordListEl && recordListEl.querySelector('[data-drx-id="' + CSS.escape(id) + '"]');
        if (input) input.checked = false;
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function transformedSeries(item, index) {
    return transformedSeriesInfo(item, index).display;
  }

  function finiteNumber(value) {
    if (value === null || value === undefined || value === "") return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function transformedSeriesInfo(item, index) {
    const mode = modeEl.value;
    const values = item.intensity || [];
    let max = 0;
    values.forEach(function (value) {
      const number = finiteNumber(value);
      if (number !== null) max = Math.max(max, number);
    });
    max = max || 1;
    const base = {
      mode: mode,
      display: [],
      beforeOffset: [],
      offset: mode === "stacked" ? stackedOffsetForNgcOrder(item, index) : 0,
      invalidPoints: 0,
    };
    if (mode === "normalized") {
      base.display = values.map(function (value) {
        const number = finiteNumber(value);
        if (number === null) {
          base.invalidPoints += 1;
          return NaN;
        }
        return number / max;
      });
      return base;
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (mode === "area") {
      const area = curveArea(item.twoTheta, item.intensity) || 1;
      base.display = values.map(function (value) {
        const number = finiteNumber(value);
        if (number === null) {
          base.invalidPoints += 1;
          return NaN;
        }
        return number / area;
      });
      return base;
    }
    if (mode === "stacked") {
      base.beforeOffset = values.map(function (value) {
        const number = finiteNumber(value);
        if (number === null) {
          base.invalidPoints += 1;
          return NaN;
        }
        return number / max;
      });
      base.display = base.beforeOffset.map(function (value) {
        return Number.isFinite(value) ? value + base.offset : NaN;
      });
      return base;
    }
    base.display = values.map(function (value) {
      const number = finiteNumber(value);
      if (number === null) {
        base.invalidPoints += 1;
        return NaN;
      }
      return number;
    });
    return base;
  }

  function intensityAxisLabel() {
    const mode = modeEl.value;
    if (mode === "normalized") return "Intensidade normalizada";
    if (mode === "area") return "Intensidade normalizada por área";
    if (mode === "stacked") return "Intensidade normalizada + deslocamento artificial";
    return "Intensidade";
  }

  function explicitWavelengthAngstrom(item) {
    const metadata = item && item.metadata || {};
    const xrdMethod = metadata.xrd_method || {};
    const candidates = [
      metadata.wavelength_angstrom,
      metadata.lambda_angstrom,
      metadata.lambda_A,
      metadata.lambda,
      metadata.wavelength,
      xrdMethod.wavelength_angstrom,
      xrdMethod.lambda_angstrom,
      xrdMethod.lambda_A,
      xrdMethod.lambda,
      xrdMethod.wavelength,
    ];
    for (let index = 0; index < candidates.length; index += 1) {
      const value = candidates[index];
      const number = Number(value);
      if (Number.isFinite(number) && number > 0) return number;
      const text = String(value || "").toLowerCase();
      if (/cu\s*k|cuka|cu\s*kα|cu\s*kalpha/.test(text)) return CU_K_ALPHA_WAVELENGTH;
    }
    const radiation = String(metadata.radiation || metadata.radiation_source || xrdMethod.radiation || "").toLowerCase();
    if (/cu\s*k|cuka|cu\s*kα|cu\s*kalpha/.test(radiation)) return CU_K_ALPHA_WAVELENGTH;
    return null;
  }

  function braggDSpacingForItem(twoTheta, item) {
    return braggDSpacing(twoTheta, explicitWavelengthAngstrom(item));
  }

  function dSpacingText(twoTheta, item, explicitValue) {
    const lambda = explicitWavelengthAngstrom(item);
    if (!Number.isFinite(lambda)) return "d: indisponível — λ não informado";
    const explicit = Number(explicitValue);
    if (Number.isFinite(explicit) && explicit > 0) return "d " + formatNumber(explicit, 3) + " Å";
    const calculated = braggDSpacing(twoTheta, lambda);
    if (Number.isFinite(calculated)) return "d " + formatNumber(calculated, 3) + " Å";
    return "d: indisponível — λ não informado";
  }

  function axisModeForItem(item) {
    const metadata = item && item.metadata || {};
    const visualization = metadata.visualization || {};
    return visualization.axis_mode || (usesClassifiedAxis(item) ? "classified_or_aligned_axis" : "loaded_axis");
  }

  function axisOffsetForItem(item) {
    const metadata = item && item.metadata || {};
    const value = metadata.two_theta_offset_applied;
    return value === undefined || value === null || value === "" ? null : value;
  }

  function axisStateRequiresBadge(item) {
    const mode = String(axisModeForItem(item) || "");
    const metadata = item && item.metadata || {};
    const text = [
      mode,
      metadata.curve_source,
      metadata.visualization_payload_mode,
      metadata.axis_correction_source,
    ].join(" ").toLowerCase();
    return Boolean(
      usesClassifiedAxis(item)
      || axisOffsetForItem(item) !== null
      || /classific|aligned|alinh|corrig|ngc|quartzo|quartz|correct/.test(text)
    );
  }

  function chartAxisAnnotation(items) {
    return (items || []).some(axisStateRequiresBadge)
      ? "Eixo 2θ alinhado/corrigido — não é o eixo bruto original"
      : "";
  }

  function chartSeriesPoints(item, seriesInfo) {
    const xValues = item.twoTheta || [];
    const yValues = seriesInfo.display || [];
    const length = Math.max(xValues.length, yValues.length);
    const points = [];
    let invalidPoints = 0;
    for (let index = 0; index < length; index += 1) {
      const x = finiteNumber(xValues[index]);
      const y = finiteNumber(yValues[index]);
      const raw = finiteNumber((item.intensity || [])[index]);
      const beforeOffset = finiteNumber((seriesInfo.beforeOffset || [])[index]);
      const valid = x !== null && y !== null;
      if (!valid) invalidPoints += 1;
      points.push({
        x: x !== null ? x : null,
        y: valid ? y : null,
        raw: raw !== null ? raw : null,
        beforeOffset: beforeOffset !== null ? beforeOffset : null,
        offset: seriesInfo.offset || 0,
        originalIndex: index,
        valid: valid,
      });
    }
    return { points: points, invalidPoints: invalidPoints };
  }

  function svgLineSegments(points, baseX, sx, sy) {
    const segments = [];
    let current = [];
    (points || []).forEach(function (point) {
      const x = Number(point.x);
      const y = Number(point.y);
      const valid = point.valid && Number.isFinite(x) && Number.isFinite(y) && x >= baseX[0] && x <= baseX[1];
      if (!valid) {
        if (current.length) segments.push(current);
        current = [];
        return;
      }
      current.push([svgNumber(sx(x)), svgNumber(sy(y))].join(","));
    });
    if (current.length) segments.push(current);
    return segments;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function curveArea(xValues, yValues) {
    let area = 0;
    for (let index = 0; index < (xValues || []).length - 1; index += 1) {
      const x0 = finiteNumber(xValues[index]);
      const x1 = finiteNumber(xValues[index + 1]);
      const y0Value = finiteNumber(yValues[index]);
      const y1Value = finiteNumber(yValues[index + 1]);
      if (x0 !== null && x1 !== null && y0Value !== null && y1Value !== null) {
        const y0 = Math.max(0, y0Value);
        const y1 = Math.max(0, y1Value);
        area += Math.abs(x1 - x0) * ((y0 + y1) / 2);
      }
    }
    return area > 0 ? area : 0;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function showSvgChart() {
    if (plotlyChartEl) {
      plotlyChartEl.hidden = true;
      if (window.Plotly && typeof window.Plotly.purge === "function") window.Plotly.purge(plotlyChartEl);
    }
    chartEl.hidden = false;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function showPlotlyChart() {
    if (!plotlyChartEl) return false;
    chartEl.hidden = true;
    chartEl.onmousemove = null;
    chartEl.onmouseleave = null;
    tooltipEl.hidden = true;
    plotlyChartEl.hidden = false;
    return true;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function extent(values) {
    const finite = values.filter(Number.isFinite);
    if (!finite.length) return [0, 1];
    return [Math.min.apply(null, finite), Math.max.apply(null, finite)];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function niceTicks(min, max, count) {
    if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) return [min || 0];
    const step = (max - min) / Math.max(1, count - 1);
    const ticks = [];
    for (let index = 0; index < count; index += 1) ticks.push(min + step * index);
    return ticks;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function firstNonEmptySeries() {
    for (let index = 0; index < arguments.length; index += 1) {
      const values = arguments[index] || [];
      if (values.length) return values;
    }
    return [];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function numericSeries(values) {
    return (values || []).map(function (value) {
      const number = Number(value);
      return Number.isFinite(number) ? number : NaN;
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function alignedNumericSeries(values, length) {
    const series = numericSeries(values);
    return series.length === length ? series : [];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function svgNumber(value) {
    return Number.isFinite(value) ? value.toFixed(3) : "0";
  }

  function hasFiniteSeriesValue(values) {
    return (values || []).some(function (value) { return Number.isFinite(value); });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function usesClassifiedAxis(item) {
    const metadata = item && item.metadata || {};
    const advanced = item && item.advancedCurve || {};
    const curveSource = String(metadata.curve_source || "");
    const axisSource = String(advanced.axis_source || "");
    return Boolean(
      metadata.two_theta_offset_applied !== undefined
      || /classificacao_mineralogica_raw|arquivo_externo_com_eixo_ajustado/.test(curveSource)
      || /classificacao_mineralogica_raw|ngc_external/.test(axisSource)
    );
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function advancedScriptSeries(item) {
    // Curva avancada usa a mesma base 2theta classificada quando o backend ja
    // aplicou alinhamento, evitando deslocar picos ALS em relacao ao RAW.
    const advanced = item.advancedCurve || {};
    if (!advanced.available) return null;
    const xSource = usesClassifiedAxis(item)
      ? firstNonEmptySeries(item.twoTheta, advanced.two_theta)
      : firstNonEmptySeries(advanced.two_theta, item.twoTheta);
    const xValues = alignedNumericSeries(xSource, xSource.length);
    if (!xValues.length || !hasFiniteSeriesValue(xValues)) return null;
    const length = xValues.length;
    const raw = alignedNumericSeries(firstNonEmptySeries(advanced.intensity_raw, item.intensity), length);
    const filtered = alignedNumericSeries(firstNonEmptySeries(advanced.intensity_filtered, advanced.intensity_raw, item.intensity), length);
    const baseline = alignedNumericSeries(advanced.baseline || [], length);
    const corrected = alignedNumericSeries(firstNonEmptySeries(advanced.intensity_corrected, advanced.intensity_normalized), length);
    if (!hasFiniteSeriesValue(raw) || !hasFiniteSeriesValue(baseline) || !hasFiniteSeriesValue(corrected)) return null;
    return {
      xValues: xValues,
      raw: raw,
      filtered: hasFiniteSeriesValue(filtered) ? filtered : raw,
      baseline: baseline,
      corrected: corrected,
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function advancedScriptChartData(items) {
    if (items.length !== 1) return null;
    const series = advancedScriptSeries(items[0]);
    if (!series) return null;
    return { item: items[0], series: series };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function paddedDomain(values, includeZero) {
    const finite = (values || []).filter(Number.isFinite);
    if (!finite.length) return [0, 1];
    let min = Math.min.apply(null, finite);
    let max = Math.max.apply(null, finite);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (includeZero) {
      min = Math.min(0, min);
      max = Math.max(0, max);
    }
    if (min === max) max = min + 1;
    const padding = (max - min) * 0.045;
    return [includeZero && min === 0 ? 0 : min - padding, max + padding];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function scriptLinePoints(xValues, yValues, baseX, sx, sy) {
    return xValues.map(function (xValue, index) {
      const yValue = yValues[index];
      if (!Number.isFinite(xValue) || !Number.isFinite(yValue) || xValue < baseX[0] || xValue > baseX[1]) return null;
      return [svgNumber(sx(xValue)), svgNumber(sy(yValue))].join(",");
    }).filter(Boolean).join(" ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function nearestArrayPoint(xValues, yValues, theta) {
    let bestIndex = -1;
    let bestDelta = Infinity;
    xValues.forEach(function (value, index) {
      const delta = Math.abs(Number(value) - theta);
      if (Number.isFinite(delta) && delta < bestDelta) {
        bestDelta = delta;
        bestIndex = index;
      }
    });
    if (bestIndex < 0 || !Number.isFinite(yValues[bestIndex])) return null;
    return { x: Number(xValues[bestIndex]), y: Number(yValues[bestIndex]) };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mapAdvancedPeak(peak, item) {
    peak = peak || {};
    const sourcePeak = peak.source_peak || {};
    // O Python envia picos ALS/lmfit com nomes de campo diferentes conforme a
    // origem: pico global, pico basal direcionado ou ajuste pseudo-Voigt. O JS
    // normaliza para o contrato visual minimo: 2θ, d, intensidade, intensidade
    // relativa, indice e fonte.
    const twoTheta = Number(peak.two_theta || peak.twoTheta || peak.center_2theta || sourcePeak.two_theta || sourcePeak.twoTheta);
    const dSpacing = Number(peak.d || peak.d_spacing || peak.d_angstrom || peak.center_d_angstrom || sourcePeak.d || sourcePeak.d_spacing || sourcePeak.d_angstrom) || braggDSpacingForItem(twoTheta, item);
    const intensity = Number(peak.intensity || peak.height || peak.amplitude || sourcePeak.intensity || sourcePeak.height);
    const relative = Number(
      peak.relative_intensity ||
      peak.intensity_relative ||
      peak.height ||
      sourcePeak.relative_intensity ||
      sourcePeak.intensity_relative ||
      intensity
    );
    return {
      two_theta: twoTheta,
      d: dSpacing,
      intensity: intensity,
      relative_intensity: relative,
      index: peak.index || peak.peak_index || sourcePeak.index || sourcePeak.peak_index,
      source: peak.source || peak.detection_method || "processamento avançado ALS",
      method: peak.method || peak.detection_method || peak.algorithm,
      fwhm: peak.fwhm || peak.fwhm_2theta || peak.width,
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function advancedScriptPeaks(item, baseX) {
    // A visualizacao prefere picos avancados enviados pelo Python porque eles
    // ja passaram por ALS, FWHM e conversao Bragg. Quando o item veio de eixo
    // classificado ou nao tem pico avancado, o painel cai para observedPeaks().
    const explicit = (usesClassifiedAxis(item) ? [] : (item.advancedPeaks || (item.metadata && item.metadata.advanced_peaks) || []))
      .map(function (peak) { return mapAdvancedPeak(peak, item); })
      .filter(function (peak) { return Number.isFinite(peak.two_theta); });
    const peaks = explicit.length ? explicit : observedPeaks(item);
    return peaks
      .filter(function (peak) {
        const theta = Number(peak.two_theta);
        return Number.isFinite(theta) && theta >= 4 && theta >= baseX[0] && theta <= baseX[1];
      })
      .sort(function (left, right) {
        const rightValue = Number(right.relative_intensity || right.intensity) || 0;
        const leftValue = Number(left.relative_intensity || left.intensity) || 0;
        return rightValue - leftValue;
      })
      .slice(0, 7);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function pushScriptPanelGrid(nodes, panel, baseX, yDomain, sx, sy, showXLabels) {
    niceTicks(baseX[0], baseX[1], 7).forEach(function (tick) {
      const x = sx(tick);
      nodes.push('<line class="argilo-drx__script-grid" x1="' + x + '" y1="' + panel.top + '" x2="' + x + '" y2="' + panel.bottom + '"></line>');
      if (showXLabels) nodes.push('<text x="' + x + '" y="' + (panel.bottom + 24) + '" text-anchor="middle">' + formatNumber(tick, 0) + "</text>");
    });
    niceTicks(yDomain[0], yDomain[1], 5).forEach(function (tick) {
      const y = sy(tick);
      nodes.push('<line class="argilo-drx__script-grid" x1="' + panel.left + '" y1="' + y + '" x2="' + panel.right + '" y2="' + y + '"></line>');
      nodes.push('<text x="' + (panel.left - 9) + '" y="' + (y + 4) + '" text-anchor="end">' + formatNumber(tick, 0) + "</text>");
    });
    nodes.push('<line class="argilo-drx__axis" x1="' + panel.left + '" y1="' + panel.bottom + '" x2="' + panel.right + '" y2="' + panel.bottom + '"></line>');
    nodes.push('<line class="argilo-drx__axis" x1="' + panel.left + '" y1="' + panel.top + '" x2="' + panel.left + '" y2="' + panel.bottom + '"></line>');
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function pushScriptLegend(nodes, x, y, entries) {
    nodes.push('<rect class="argilo-drx__script-legend-box" x="' + (x - 10) + '" y="' + (y - 16) + '" width="252" height="' + (entries.length * 18 + 10) + '"></rect>');
    entries.forEach(function (entry, index) {
      const rowY = y + index * 18;
      if (entry.marker === "x") {
        nodes.push('<line class="argilo-drx__script-peak-x" x1="' + x + '" y1="' + (rowY - 5) + '" x2="' + (x + 10) + '" y2="' + (rowY + 5) + '"></line>');
        nodes.push('<line class="argilo-drx__script-peak-x" x1="' + x + '" y1="' + (rowY + 5) + '" x2="' + (x + 10) + '" y2="' + (rowY - 5) + '"></line>');
      } else {
        const dash = entry.dashed ? ' stroke-dasharray="6 4"' : "";
        nodes.push('<line x1="' + x + '" y1="' + rowY + '" x2="' + (x + 28) + '" y2="' + rowY + '" stroke="' + entry.color + '" stroke-width="' + (entry.width || 2) + '"' + dash + '></line>');
      }
      nodes.push('<text x="' + (x + 36) + '" y="' + (rowY + 4) + '">' + escapeHtml(entry.label) + "</text>");
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderScriptStyleAdvancedChart(item, series) {
    const width = 960;
    const height = 520;
    const panelLeft = 64;
    const panelRight = width - 24;
    const plotW = panelRight - panelLeft;
    const upper = { left: panelLeft, right: panelRight, top: 34, bottom: 222 };
    upper.height = upper.bottom - upper.top;
    const lower = { left: panelLeft, right: panelRight, top: 288, bottom: 468 };
    lower.height = lower.bottom - lower.top;
    const baseX = xDomain || extent(series.xValues);
    const upperDomain = paddedDomain(series.raw.concat(series.filtered, series.baseline), true);
    const lowerDomain = paddedDomain(series.corrected, true);
    const sx = function (value) { return panelLeft + ((value - baseX[0]) / (baseX[1] - baseX[0] || 1)) * plotW; };
    const syUpper = function (value) { return upper.top + upper.height - ((value - upperDomain[0]) / (upperDomain[1] - upperDomain[0] || 1)) * upper.height; };
    const syLower = function (value) { return lower.top + lower.height - ((value - lowerDomain[0]) / (lowerDomain[1] - lowerDomain[0] || 1)) * lower.height; };
    const label = String((item.metadata && item.metadata.original_filename) || sampleLabel(item) || "difratograma").slice(0, 84);
    const classifiedAxis = usesClassifiedAxis(item);
    const nodes = [];

    nodes.push('<text class="argilo-drx__script-title" x="' + (width / 2) + '" y="20" text-anchor="middle">' + (classifiedAxis ? "Processamento com eixo classificado: " : "Processamento e Remoção de Background: ") + escapeHtml(label) + "</text>");
    pushScriptPanelGrid(nodes, upper, baseX, upperDomain, sx, syUpper, false);
    nodes.push('<polyline class="argilo-drx__script-curve argilo-drx__script-curve--raw" points="' + scriptLinePoints(series.xValues, series.raw, baseX, sx, syUpper) + '"></polyline>');
    nodes.push('<polyline class="argilo-drx__script-curve argilo-drx__script-curve--filtered" points="' + scriptLinePoints(series.xValues, series.filtered, baseX, sx, syUpper) + '"></polyline>');
    nodes.push('<polyline class="argilo-drx__script-curve argilo-drx__script-curve--baseline" points="' + scriptLinePoints(series.xValues, series.baseline, baseX, sx, syUpper) + '"></polyline>');
    nodes.push('<text x="19" y="' + (upper.top + upper.height / 2) + '" transform="rotate(-90 19 ' + (upper.top + upper.height / 2) + ')" text-anchor="middle">Intensidade (cps)</text>');
    pushScriptLegend(nodes, 704, 52, [
      { label: classifiedAxis ? "Sinal classificado (eixo corrigido)" : "Sinal Original", color: "#aeb8ff", width: 1.6 },
      { label: "Sinal Filtrado (Savitzky-Golay)", color: "#ff1f1f", width: 2 },
      { label: "Background (ALS)", color: "#111111", width: 2, dashed: true },
      { label: "Início da Busca", color: "#777777", width: 1.6, dashed: true },
    ]);

    nodes.push('<text class="argilo-drx__script-title" x="' + (width / 2) + '" y="268" text-anchor="middle">Sinal Final Pronto para Análise</text>');
    pushScriptPanelGrid(nodes, lower, baseX, lowerDomain, sx, syLower, true);
    nodes.push('<polyline class="argilo-drx__script-curve argilo-drx__script-curve--corrected" points="' + scriptLinePoints(series.xValues, series.corrected, baseX, sx, syLower) + '"></polyline>');
    nodes.push('<text x="19" y="' + (lower.top + lower.height / 2) + '" transform="rotate(-90 19 ' + (lower.top + lower.height / 2) + ')" text-anchor="middle">Intensidade (cps)</text>');
    nodes.push('<text x="' + (width / 2) + '" y="514" text-anchor="middle">2Theta (°)</text>');
    pushScriptLegend(nodes, 730, 308, [
      { label: "Sinal Final (Sem Background)", color: "#008000", width: 2 },
      { label: "Top 7 Picos", marker: "x" },
    ]);

    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (baseX[0] <= 4 && baseX[1] >= 4) {
      const searchX = sx(4);
      nodes.push('<line class="argilo-drx__script-search-line" x1="' + searchX + '" y1="' + upper.top + '" x2="' + searchX + '" y2="' + upper.bottom + '"></line>');
      nodes.push('<line class="argilo-drx__script-search-line" x1="' + searchX + '" y1="' + lower.top + '" x2="' + searchX + '" y2="' + lower.bottom + '"></line>');
    }

    advancedScriptPeaks(item, baseX).forEach(function (peak) {
      // Os marcadores sao posicionados pelo 2θ do pico e pela intensidade da
      // curva corrigida no ponto mais proximo. Assim o marcador visual aponta
      // para o sinal exibido, enquanto a tabela conserva d-spacing e FWHM.
      const point = nearestArrayPoint(series.xValues, series.corrected, Number(peak.two_theta));
      if (!point) return;
      const x = sx(point.x);
      const y = syLower(point.y);
      nodes.push('<line class="argilo-drx__script-peak-x" x1="' + (x - 5) + '" y1="' + (y - 5) + '" x2="' + (x + 5) + '" y2="' + (y + 5) + '"></line>');
      nodes.push('<line class="argilo-drx__script-peak-x" x1="' + (x - 5) + '" y1="' + (y + 5) + '" x2="' + (x + 5) + '" y2="' + (y - 5) + '"></line>');
    });

    return nodes.join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderChart() {
    // Renderizacao principal: Plotly. O SVG abaixo permanece fallback tecnico
    // para ambientes sem Plotly ou para exportacao legada.
    const items = selectedItemsInNgcOrder();
    chartEl.innerHTML = "";
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!items.length) {
      showSvgChart();
      chartEl.innerHTML = '<text x="40" y="80">Selecione registros com DRX para iniciar.</text>';
      chartEl.onmousemove = null;
      chartEl.onmouseleave = null;
      return;
    }

    if (renderPlotlyMainChart(items)) return;

    const advancedChart = advancedScriptChartData(items);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (advancedChart) {
      showSvgChart();
      chartEl.innerHTML = renderScriptStyleAdvancedChart(advancedChart.item, advancedChart.series);
      tooltipEl.hidden = true;
      chartEl.onmousemove = null;
      chartEl.onmouseleave = null;
      return;
    }

    showSvgChart();

    const width = 960;
    const height = 520;
    const margin = { top: 20, right: 18, bottom: 48, left: 62 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;
    const allX = items.flatMap(function (item) { return item.twoTheta; });
    const baseX = xDomain || extent(allX);
    const transformedInfo = items.map(transformedSeriesInfo);
    const transformed = transformedInfo.map(function (series) { return series.display; });
    const pointSets = items.map(function (item, index) { return chartSeriesPoints(item, transformedInfo[index]); });
    const allY = pointSets.flatMap(function (series) {
      return series.points.map(function (point) { return point.y; }).filter(Number.isFinite);
    });
    const yExt = extent(allY);
    const yMin = modeEl.value === "absolute" ? Math.min(0, yExt[0]) : 0;
    const yMax = yExt[1] || 1;
    const sx = function (value) { return margin.left + ((value - baseX[0]) / (baseX[1] - baseX[0] || 1)) * plotW; };
    const sy = function (value) { return margin.top + plotH - ((value - yMin) / (yMax - yMin || 1)) * plotH; };
    const nodes = [];

    niceTicks(baseX[0], baseX[1], 8).forEach(function (tick) {
      const x = sx(tick);
      nodes.push('<line class="argilo-drx__grid" x1="' + x + '" y1="' + margin.top + '" x2="' + x + '" y2="' + (height - margin.bottom) + '"></line>');
      nodes.push('<text x="' + x + '" y="' + (height - 24) + '" text-anchor="middle">' + formatNumber(tick, 2) + "</text>");
    });
    niceTicks(yMin, yMax, 6).forEach(function (tick) {
      const y = sy(tick);
      nodes.push('<line class="argilo-drx__grid" x1="' + margin.left + '" y1="' + y + '" x2="' + (width - margin.right) + '" y2="' + y + '"></line>');
      nodes.push('<text x="' + (margin.left - 10) + '" y="' + (y + 4) + '" text-anchor="end">' + formatNumber(tick, 2) + "</text>");
    });
    nodes.push('<line class="argilo-drx__axis" x1="' + margin.left + '" y1="' + (height - margin.bottom) + '" x2="' + (width - margin.right) + '" y2="' + (height - margin.bottom) + '"></line>');
    nodes.push('<line class="argilo-drx__axis" x1="' + margin.left + '" y1="' + margin.top + '" x2="' + margin.left + '" y2="' + (height - margin.bottom) + '"></line>');
    nodes.push('<text x="' + (width / 2) + '" y="' + (height - 4) + '" text-anchor="middle">2θ (°)</text>');
    nodes.push('<text x="18" y="' + (height / 2) + '" transform="rotate(-90 18 ' + (height / 2) + ')" text-anchor="middle">' + escapeHtml(intensityAxisLabel()) + '</text>');
    const axisWarning = chartAxisAnnotation(items);
    if (axisWarning) nodes.push('<text x="' + margin.left + '" y="16" class="argilo-drx__mini-note">' + escapeHtml(axisWarning) + '</text>');

    items.forEach(function (item, index) {
      const color = palette[index % palette.length];
      svgLineSegments(pointSets[index].points, baseX, sx, sy).forEach(function (segment) {
        nodes.push('<polyline class="argilo-drx__curve" data-series="' + index + '" stroke="' + color + '" points="' + segment.join(" ") + '"></polyline>');
      });
      nodes.push('<text x="' + (width - margin.right - 8) + '" y="' + (margin.top + 20 + index * 18) + '" text-anchor="end" fill="' + color + '">' + escapeHtml(chartSeriesLabel(item)).slice(0, 42) + "</text>");
    });
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (showPeakMarkers) {
      nodes.push(renderPeakMarkers(items, transformed, baseX, sx, sy, palette));
    }

    chartEl.innerHTML = nodes.join("");
    chartEl.onmousemove = function (event) {
      showTooltip(event, items, baseX, margin, plotW, transformedInfo);
    };
    chartEl.onmouseleave = function () {
      tooltipEl.hidden = true;
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderPlotlyMainChart(items) {
    if (!plotlyChartEl || !window.Plotly || typeof window.Plotly.react !== "function") return false;
    const baseX = xDomain || extent(items.flatMap(function (item) { return item.twoTheta; }));
    const traces = items.map(function (item, index) {
      const seriesInfo = transformedSeriesInfo(item, index);
      const pointSet = chartSeriesPoints(item, seriesInfo);
      const text = pointSet.points.map(function (point) {
        const mineralLabel = Number.isFinite(point.x) ? peakMineralLabelForTheta(item, point.x) : "";
        const rows = [
          "<strong>" + escapeHtml(chartSeriesLabel(item)) + "</strong>",
          "preparo: " + escapeHtml(treatmentLabel(item.treatment || item.preparation)),
          "2θ " + (Number.isFinite(point.x) ? formatNumber(point.x, 3) + "°" : "indisponível"),
          dSpacingText(point.x, item),
          "I exibida " + (Number.isFinite(point.y) ? formatNumber(point.y, 3) : "indisponível"),
          "modo: " + intensityAxisLabel(),
          "axis_mode: " + escapeHtml(axisModeForItem(item)),
        ];
        if (modeEl.value === "stacked") {
          rows.push("I antes do offset " + (Number.isFinite(point.beforeOffset) ? formatNumber(point.beforeOffset, 3) : "indisponível"));
          rows.push("offset aplicado " + formatNumber(point.offset || 0, 3));
        } else if (Number.isFinite(point.raw)) {
          rows.push("I bruta " + formatNumber(point.raw, 3));
        }
        const offset = axisOffsetForItem(item);
        if (offset !== null) rows.push("two_theta_offset_applied: " + escapeHtml(offset));
        if (pointSet.invalidPoints) rows.push("pontos inválidos/lacunas na série: " + pointSet.invalidPoints);
        if (mineralLabel) rows.push(escapeHtml(mineralLabel));
        return rows.join("<br>");
      });
      return {
        x: pointSet.points.map(function (point) { return point.x; }),
        y: pointSet.points.map(function (point) { return point.y; }),
        text: text,
        type: "scatter",
        mode: "lines",
        name: chartSeriesLabel(item),
        line: { color: palette[index % palette.length], width: 2 },
        connectgaps: false,
        hovertemplate: "%{text}<extra></extra>",
      };
    });
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (showPeakMarkers) {
      items.forEach(function (item, itemIndex) {
        const seriesInfo = transformedSeriesInfo(item, itemIndex);
        const ySeries = seriesInfo.display;
        const peakX = [];
        const peakY = [];
        const peakText = [];
        observedPeaks(item).slice(0, 12).forEach(function (peak) {
          // Plotly recebe os picos como uma segunda trace de marcadores. O eixo
          // X e sempre 2θ; o texto mostra d-spacing quando disponivel, porque a
          // interpretacao mineralogica e feita em Å.
          const theta = Number(peak.two_theta);
          const point = nearestSeriesPoint(item, ySeries, theta);
          if (!point) return;
          peakX.push(theta);
          peakY.push(point.y);
          const mineralLabel = peakMineralLabelForTheta(item, theta);
          const source = peak.source || peak.detection_method || peak.method || "não informada";
          const method = peak.method || peak.detection_method || peak.algorithm || "";
          const fwhm = Number(peak.fwhm || peak.fwhm_2theta || peak.width);
          peakText.push([
            "fonte: " + escapeHtml(source),
            "2θ " + formatNumber(theta, 3) + "°",
            dSpacingText(theta, item, peak.d),
            "intensidade " + (Number.isFinite(Number(peak.intensity)) ? formatNumber(Number(peak.intensity), 3) : "indisponível"),
            Number.isFinite(fwhm) ? "FWHM " + formatNumber(fwhm, 3) + "°2θ" : "",
            method ? "método: " + escapeHtml(method) : "",
            mineralLabel || "",
          ].filter(Boolean).join("<br>"));
        });
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (peakX.length) {
          traces.push({
            x: peakX,
            y: peakY,
            text: peakText,
            type: "scatter",
            mode: "markers+text",
            name: chartSeriesLabel(item) + " picos",
            marker: { color: palette[itemIndex % palette.length], size: 7, symbol: "x" },
            textposition: "top center",
            hovertemplate: "%{text}<extra></extra>",
            showlegend: false,
          });
        }
      });
    }
    showPlotlyChart();
    window.Plotly.react(plotlyChartEl, traces, {
      autosize: true,
      margin: { l: 58, r: 16, t: 14, b: 46 },
      xaxis: { title: "2θ (°)", range: xDomain || baseX, zeroline: false },
      yaxis: { title: intensityAxisLabel(), rangemode: modeEl.value === "absolute" ? "tozero" : "nonnegative" },
      annotations: chartAxisAnnotation(items) ? [{
        xref: "paper",
        yref: "paper",
        x: 0,
        y: 1.08,
        xanchor: "left",
        yanchor: "bottom",
        showarrow: false,
        text: chartAxisAnnotation(items),
        font: { size: 11, color: "#7a5a00" },
        bgcolor: "rgba(255, 244, 204, 0.92)",
        bordercolor: "#d4a62a",
        borderwidth: 1,
        borderpad: 4,
      }] : [],
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#fbfdfc",
      hovermode: "x unified",
      legend: { orientation: "h", y: -0.14 },
    }, {
      displaylogo: false,
      responsive: true,
    });
    plotlyChartEl.on("plotly_relayout", function (eventData) {
      if (eventData && Number.isFinite(eventData["xaxis.range[0]"]) && Number.isFinite(eventData["xaxis.range[1]"])) {
        xDomain = [Number(eventData["xaxis.range[0]"]), Number(eventData["xaxis.range[1]"])];
      }
    });
    return true;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function nearestSeriesPoint(item, ySeries, theta) {
    let bestIndex = -1;
    let bestDelta = Infinity;
    (item.twoTheta || []).forEach(function (value, index) {
      const thetaValue = finiteNumber(value);
      const delta = thetaValue === null ? NaN : Math.abs(thetaValue - theta);
      if (Number.isFinite(delta) && delta < bestDelta) {
        bestDelta = delta;
        bestIndex = index;
      }
    });
    if (bestIndex < 0) return null;
    const y = Number(ySeries[bestIndex]);
    if (!Number.isFinite(y)) return null;
    return {
      theta: Number(item.twoTheta[bestIndex]),
      y: y,
      delta: bestDelta,
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderPeakMarkers(items, transformed, baseX, sx, sy, colors) {
    // Fallback SVG dos marcadores de pico: usa observedPeaks(), limita a faixa
    // visivel do eixo 2θ e prioriza maior intensidade relativa para evitar que
    // rotulos secundarios poluam a leitura da curva.
    const nodes = [];
    items.forEach(function (item, itemIndex) {
      const color = colors[itemIndex % colors.length];
      const peaks = observedPeaks(item)
        .filter(function (peak) {
          const theta = Number(peak.two_theta);
          return Number.isFinite(theta) && theta >= baseX[0] && theta <= baseX[1];
        })
        .sort(function (left, right) {
          return (Number(right.relative_intensity) || 0) - (Number(left.relative_intensity) || 0);
        })
        .slice(0, 8);
      peaks.forEach(function (peak, peakIndex) {
        const theta = Number(peak.two_theta);
        const point = nearestSeriesPoint(item, transformed[itemIndex] || [], theta);
        if (!point) return;
        const x = sx(theta);
        const y = sy(point.y);
        const labelY = Math.max(18, y - 10 - ((peakIndex % 3) * 11));
        const label = Number.isFinite(Number(peak.d))
          ? dSpacingText(theta, item, peak.d)
          : "2θ " + formatNumber(theta, 2) + "°";
        nodes.push('<line class="argilo-drx__peak-line" x1="' + x + '" y1="' + y + '" x2="' + x + '" y2="' + (y - 22) + '" stroke="' + color + '"></line>');
        nodes.push('<circle class="argilo-drx__peak-dot" cx="' + x + '" cy="' + y + '" r="3.5" fill="' + color + '"></circle>');
        nodes.push('<text class="argilo-drx__peak-label" x="' + Math.min(900, x + 5) + '" y="' + labelY + '">' + escapeHtml(label) + '</text>');
      });
    });
    return nodes.join("");
  }

  function peakMineralLabelForTheta(item, theta) {
    const thetaValue = Number(theta);
    if (!Number.isFinite(thetaValue)) return "";
    let nearestPeak = null;
    let bestThetaDelta = Infinity;
    observedPeaks(item).forEach(function (peak) {
      const peakTheta = Number(peak.two_theta);
      if (!Number.isFinite(peakTheta)) return;
      const delta = Math.abs(peakTheta - thetaValue);
      if (delta < bestThetaDelta) {
        bestThetaDelta = delta;
        nearestPeak = peak;
      }
    });
    if (!nearestPeak || bestThetaDelta > 0.28) return "";
    const match = matchPeakToCandidate(nearestPeak, item);
    if (match && match.candidate && match.candidate.mineral) {
      return "Argilomineral: " + match.candidate.mineral;
    }
    const dValue = Number(nearestPeak.d) || braggDSpacingForItem(thetaValue, item);
    const minerals = Array.from(new Set(mineralReflectionRules().filter(function (rule) {
      return Number.isFinite(dValue) && dValue >= rule.min && dValue <= rule.max;
    }).map(function (rule) {
      return rule.mineral;
    }).filter(Boolean))).slice(0, 3);
    if (minerals.length) {
      return "Argilomineral: " + minerals.join(" / ");
    }
    return "";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function showTooltip(event, items, domain, margin, plotW, transformedInfo) {
    const rect = chartEl.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 960;
    if (x < margin.left || x > margin.left + plotW) {
      tooltipEl.hidden = true;
      return;
    }
    const theta = domain[0] + ((x - margin.left) / plotW) * (domain[1] - domain[0]);
    const rows = items.map(function (item, itemIndex) {
      const seriesInfo = transformedInfo && transformedInfo[itemIndex] || transformedSeriesInfo(item, itemIndex);
      const pointSet = chartSeriesPoints(item, seriesInfo);
      let bestPoint = null;
      let bestDistance = Infinity;
      pointSet.points.forEach(function (point) {
        if (!point.valid || !Number.isFinite(point.x)) return;
        const distance = Math.abs(point.x - theta);
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (distance < bestDistance) {
          bestDistance = distance;
          bestPoint = point;
        }
      });
      if (!bestPoint) return [
        "<div><strong>", escapeHtml(chartSeriesLabel(item)), "</strong> ",
        "sem ponto válido próximo; lacunas/pontos inválidos: ", pointSet.invalidPoints,
        "</div>",
      ].join("");
      const mineralLabel = peakMineralLabelForTheta(item, bestPoint.x);
      const offset = axisOffsetForItem(item);
      const stackedRows = modeEl.value === "stacked"
        ? [
          "<br><span class='argilo-drx__mini-note'>I antes do offset ",
          Number.isFinite(bestPoint.beforeOffset) ? formatNumber(bestPoint.beforeOffset, 3) : "indisponível",
          "; offset aplicado ", formatNumber(bestPoint.offset || 0, 3),
          "</span>",
        ].join("")
        : "";
      return [
        "<div><strong>", escapeHtml(chartSeriesLabel(item)), "</strong> ", treatmentBadge(item),
        ": 2θ ", formatNumber(bestPoint.x, 3), "°",
        ", ", dSpacingText(bestPoint.x, item),
        ", I exibida ", formatNumber(bestPoint.y, 3),
        "<br><span class='argilo-drx__mini-note'>modo: ", escapeHtml(intensityAxisLabel()),
        "; axis_mode: ", escapeHtml(axisModeForItem(item)),
        offset !== null ? "; two_theta_offset_applied: " + escapeHtml(offset) : "",
        pointSet.invalidPoints ? "; lacunas/pontos inválidos: " + pointSet.invalidPoints : "",
        "</span>",
        stackedRows,
        mineralLabel ? "<br><span class='argilo-drx__mini-note'>" + escapeHtml(mineralLabel) + "</span>" : "",
        "</div>",
      ].join("");
    }).join("");
    tooltipEl.innerHTML = rows;
    tooltipEl.style.left = Math.min(rect.width - 300, Math.max(8, event.clientX - rect.left + 12)) + "px";
    tooltipEl.style.top = Math.max(8, event.clientY - rect.top + 12) + "px";
    tooltipEl.hidden = false;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function compareByCandidateScore(left, right) {
    const leftScore = Number(left && left.score);
    const rightScore = Number(right && right.score);
    if (!Number.isFinite(leftScore) && !Number.isFinite(rightScore)) return 0;
    if (!Number.isFinite(leftScore)) return 1;
    if (!Number.isFinite(rightScore)) return -1;
    return rightScore - leftScore;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function candidateMatchesMineralSlug(candidate, targetSlug) {
    if (!targetSlug) return false;
    const candidateSlug = resolveMineralSlug(candidate && candidate.mineral) || mineralSlug(candidate && candidate.mineral);
    return Boolean(candidateSlug && candidateSlug === targetSlug);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function bestScoredClayCandidate(item, preferredMineralSlug) {
    const candidates = (item && item.mineralCandidates || [])
      .filter(isAuthorizedClayMineral)
      .sort(compareByCandidateScore);
    if (preferredMineralSlug) {
      const preferred = candidates.filter(function (candidate) {
        return candidateMatchesMineralSlug(candidate, preferredMineralSlug);
      });
      if (preferred.length) return preferred.sort(compareByCandidateScore)[0];
    }
    return candidates[0] || null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderBestScoredClayCandidate(candidate) {
    if (!candidate) return "N/D";
    return mineralLink(candidate.mineral || "Argilomineral candidato");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function geologistTriageForItem(item) {
    if (!item) return null;
    return item.geologistTriage || geologistTriageById.get(item.id) || geologistTriageById.get(item.diffractogram && item.diffractogram.id) || null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function candidatePeakEvidence(candidate, item) {
    const matches = (candidate && candidate.matches) || [];
    if (matches.length) {
      return matches.slice(0, 5).map(readableMatchPeak);
    }
    return observedPeaks(item).slice(0, 5).map(function (peak) {
      return [
        Number.isFinite(Number(peak.d)) ? "d obs. " + formatNumber(Number(peak.d), 2) + " A" : "",
        Number.isFinite(Number(peak.two_theta)) ? "2θ " + formatNumber(Number(peak.two_theta), 2) + "°" : "",
        Number.isFinite(Number(peak.relative_intensity)) ? "Irel " + formatNumber(Number(peak.relative_intensity), 1) : "",
      ].filter(Boolean).join(" / ") || "pico observado sem coordenada completa";
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function qcEvidenceForItem(item) {
    const flags = (item.qcFlags || []).map(function (flag) {
      return typeof flag === "string" ? flag : (flag.code || flag.flag || String(flag));
    }).filter(Boolean);
    const advanced = item.advancedCurve || {};
    const summary = item.advancedSummary || {};
    const rows = [];
    rows.push("ALS/background: " + (advanced.baseline_method || summary.baseline_method || "N/D"));
    rows.push("Normalização: " + (advanced.normalization || summary.normalization || "N/D"));
    rows.push("QC: " + (flags.length ? flags.slice(0, 5).join(", ") : "sem flag registrada"));
    return rows;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderCandidateEvidenceBlock(item, candidate) {
    const triage = geologistTriageForItem(item);
    const web = (triage && triage.webmineral) || {};
    const xrd = (triage && triage.xrdnet) || {};
    const chips = [];
    if (triage) chips.push({ label: "Fila", value: triage.queue_label || triage.triage_confidence, kind: "queue" });
    chips.push({ label: "Preparo", value: treatmentLabel(item.treatment), kind: "ngc" });
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (triage && typeof triage.basal_peak_count_2_12_5 !== "undefined") {
      chips.push({ label: "Picos basais", value: triage.basal_peak_count_2_12_5, kind: triage.basal_peak_count_2_12_5 ? "peak" : "warning" });
    }
    if (web.top) chips.push({ label: "WebMineral fallback", value: web.top + " · " + formatScore(web.score), kind: "webmineral" });
    if (xrd.top) chips.push({ label: "XRDNet auxiliar", value: xrd.top + " · " + xrdnetPercent(xrd.probability), kind: "xrdnet" });
    else chips.push({ label: "XRDNet auxiliar", value: "sem predição", kind: "warning" });
    const peakRows = candidatePeakEvidence(candidate, item).map(function (row) {
      return "<li>" + escapeHtml(row) + "</li>";
    }).join("");
    const triageRows = triage && (triage.evidence || []).length
      ? (triage.evidence || []).slice(0, 4).map(function (row) { return "<li>" + escapeHtml(row) + "</li>"; }).join("")
      : "<li>" + escapeHtml(item.treatment_evidence || "Preparo N/G/C não documentado para esta curva.") + "</li>";
    const qcRows = qcEvidenceForItem(item).map(function (row) {
      return "<li>" + escapeHtml(row) + "</li>";
    }).join("");
    return [
      '<div class="argilo-drx__candidate-evidence">',
      "<h4>Evidências do candidato</h4>",
      renderEvidenceChips(chips),
      '<div class="argilo-drx__evidence-grid">',
      "<div><strong>Picos usados</strong><ul>", peakRows || "<li>N/D</li>", "</ul></div>",
      "<div><strong>N/G/C e triagem</strong><ul>", triageRows, "</ul></div>",
      "<div><strong>QC ALS</strong><ul>", qcRows, "</ul></div>",
      "</div>",
      "</div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderGeologistEvidencePanel(items) {
    if (hasBackendNgcCompleteGroup()) {
      return [
        '<section class="compact-section argilo-drx__geologist-evidence-panel">',
        "<h2>Evidências para o geólogo</h2>",
        '<p class="note">Seleção N/G/C completa detectada. A leitura mineralógica principal foi consolidada pelo workflow N/G/C backend; candidatos individuais por arquivo ficam apenas como evidência secundária para revisão.</p>',
        "</section>",
      ].join("");
    }
    const rows = (items || []).map(function (item) {
      const candidate = bestScoredClayCandidate(item, currentArgilomineralSlug());
      return [
        '<article class="argilo-drx__evidence-card">',
        "<h3>", escapeHtml(sampleLabel(item)), "</h3>",
        "<p><strong>Arquivo:</strong> ", escapeHtml((item.metadata || {}).original_filename || item.id), "</p>",
        "<p><strong>Candidato principal:</strong> ", renderBestScoredClayCandidate(candidate), "</p>",
        renderCandidateEvidenceBlock(item, candidate),
        "</article>",
      ].join("");
    }).join("");
    return [
      '<section class="compact-section argilo-drx__geologist-evidence-panel">',
      "<h2>Evidências para o geólogo</h2>",
      '<p class="note">Cada candidato combina picos observados/casados, preparo N/G/C, RRUFF ODR confirmado quando disponível, WebMineral como fallback/comparação, XRDNet como evidência neural auxiliar e QC do processamento ALS. A leitura continua pendente de curadoria.</p>',
      rows || "<p>N/D</p>",
      "</section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function backendNgcGroups() {
    if (!ngcWorkflowPayload || ngcWorkflowPayload.loading || ngcWorkflowPayload.success === false) return [];
    return ngcWorkflowPayload.groups || [];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function hasBackendNgcCompleteGroup() {
    return backendNgcGroups().some(function (group) {
      const preps = group.available_preparations || [];
      return preps.indexOf("natural") >= 0 && preps.indexOf("glicolado") >= 0 && preps.indexOf("calcinado") >= 0;
    });
  }

  function bestNgcDiagnosticCandidate(group) {
    const diagnostic = group && group.diagnostic_interpretation || {};
    const clay = group && group.clay_interpretation || {};
    const clayCandidates = clay.candidates || [];
    const ambiguous7a = clayCandidates.find(function (row) {
      return row && row.candidateId === "kaolin_chlorite_overlap_7a" && row.status !== "descartado";
    });
    if (ambiguous7a) {
      return {
        label: ambiguous7a.candidateLabelPt || ambiguous7a.candidateId,
        score: ambiguous7a.score,
        confidence: ambiguous7a.status,
      };
    }
    const combined = diagnostic.combined_candidates || [];
    const candidate = combined.find(function (row) {
      return row && row.label;
    });
    if (candidate) {
      return {
        label: candidate.label,
        score: candidate.score,
        confidence: candidate.confidence,
      };
    }
    const clayCandidate = clayCandidates.find(function (row) {
      return row && row.status !== "descartado" && (Number(row.score) || 0) > 0;
    });
    if (clayCandidate) {
      return {
        label: clayCandidate.candidateLabelPt || clayCandidate.candidateId,
        score: clayCandidate.score,
        confidence: clayCandidate.confidence,
      };
    }
    const script = group && group.script_report || {};
    if ((script.detected_minerals || []).length) {
      return {
        label: script.detected_minerals[0],
        score: undefined,
        confidence: undefined,
      };
    }
    const best = group && group.best_candidate || {};
    if (best.mineral_candidate) {
      return {
        label: best.mineral_candidate,
        score: best.score,
        confidence: best.confidence,
      };
    }
    return null;
  }

  function ngcCandidateDisplayName(candidate) {
    return candidate && (
      candidate.mineral
      || candidate.mineral_candidate
      || candidate.candidateLabelPt
      || candidate.candidateId
      || candidate.label
    ) || "";
  }

  function ngcCandidateScore(candidate) {
    const values = [
      candidate && candidate.ngc_group_score,
      candidate && candidate.basal_diagnostic_score,
      candidate && candidate.score,
      candidate && candidate.evidence_weight,
    ];
    for (let index = 0; index < values.length; index += 1) {
      const value = Number(values[index]);
      if (Number.isFinite(value)) return value;
    }
    return null;
  }

  function ngcCandidateStatus(candidate) {
    return candidate && (
      candidate.candidate_status
      || candidate.status
      || candidate.role
      || candidate.confidence
    ) || "";
  }

  function rankedNgcCandidates(group) {
    const explicit = []
      .concat(group && group.candidates || [])
      .concat(group && group.probable_minerals || [])
      .concat(group && group.possible_minerals || [])
      .concat(group && group.accessory_minerals || []);
    if (explicit.length) {
      const seen = new Set();
      return explicit.filter(function (candidate) {
        const name = ngcCandidateDisplayName(candidate);
        if (!name) return false;
        const key = name.toLowerCase();
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }).sort(function (a, b) {
        return (ngcCandidateScore(b) || 0) - (ngcCandidateScore(a) || 0);
      });
    }
    const diagnostic = group && group.diagnostic_interpretation || {};
    return (diagnostic.combined_candidates || []).filter(function (candidate) {
      return Boolean(ngcCandidateDisplayName(candidate));
    });
  }

  function ngcCandidateDiagnosticText(candidate) {
    return [
      ngcCandidateDisplayName(candidate),
      candidate && candidate.family,
      candidate && candidate.group,
      candidate && candidate.label,
      candidate && candidate.mineral_candidate,
      candidate && candidate.candidateId,
    ].filter(Boolean).join(" ").toLowerCase();
  }

  function ngcCandidatePeakWindows(candidate) {
    const text = ngcCandidateDiagnosticText(candidate);
    if (/illite|ilita|mica/.test(text)) return [[9.7, 10.4, "Cap. 7 ilita/mica 001"]];
    if (/kaolin|caulin|halloy|halois/.test(text)) return [[6.9, 7.4, "Cap. 7 caulinita 001"], [3.5, 3.65, "Cap. 7 caulinita 002"]];
    if (/smectite|esmect|montmor|expans/.test(text)) return [[13.0, 15.5, "Cap. 7 esmectita natural"], [16.1, 18.3, "Cap. 7 esmectita glicolada"], [9.7, 10.4, "Cap. 7 colapso térmico"]];
    if (/chlorite|clorit/.test(text)) return [[13.5, 14.9, "Cap. 7 clorita 001"], [7.0, 7.35, "Cap. 7 clorita 002"], [4.65, 4.85, "Cap. 7 clorita 003"], [3.48, 3.6, "Cap. 7 clorita 004"]];
    if (/corrensite|mixed|interstrat|interestrat/.test(text)) return [[24.0, 31.5, "Cap. 8 superestrutura/00l*"], [13.5, 17.5, "Cap. 8 componente expansível/clorítico"], [9.7, 10.5, "Cap. 8 colapso/desidratação"]];
    if (/sepiolite|palygorskite|fibrous|channel/.test(text)) return [[11.8, 12.6, "Cap. 7 sepiolita/paligorsquita"]];
    if (/quartz|quartzo/.test(text)) return [[4.2, 4.35, "Cap. 7 quartzo 100"], [3.32, 3.37, "Cap. 7 quartzo 101"]];
    return [];
  }

  function formatNgcPeakObservation(label, peak, ruleLabel) {
    peak = peak || {};
    const d = Number(peak.d_angstrom || peak.observed_d_angstrom || peak.d || peak.d_spacing);
    const theta = Number(peak.two_theta || peak.observed_two_theta);
    const intensity = Number(peak.intensity_abs || peak.i_abs || peak.intensity);
    if (!Number.isFinite(d)) return "";
    return [
      label ? label + ": " : "",
      "d ", formatNumber(d, 2), " Å",
      Number.isFinite(theta) ? " / 2θ " + formatNumber(theta, 2) + "°" : "",
      Number.isFinite(intensity) ? " / int. " + formatNumber(intensity, 0) : "",
      ruleLabel ? " · " + ruleLabel : "",
    ].join("");
  }

  function diagnosticMatchesCandidate(diagnostic, candidate) {
    const candidateText = ngcCandidateDiagnosticText(candidate);
    const mineral = String(diagnostic && diagnostic.mineral || "").toLowerCase();
    if (!candidateText || !mineral) return false;
    return candidateText.indexOf(mineral) >= 0 || mineral.indexOf(candidateText) >= 0
      || (/illite|ilita|mica/.test(candidateText) && /illite|ilita|mica/.test(mineral))
      || (/kaolin|caulin/.test(candidateText) && /kaolin|caulin/.test(mineral))
      || (/smectite|esmect/.test(candidateText) && /smectite|esmect/.test(mineral))
      || (/chlorite|clorit/.test(candidateText) && /chlorite|clorit/.test(mineral))
      || (/quartz|quartzo/.test(candidateText) && /quartz|quartzo/.test(mineral))
      || (/corrensite|mixed|interstrat/.test(candidateText) && /corrensite|mixed|interstrat/.test(mineral));
  }

  function ngcCandidateRulePeaks(group, candidate) {
    const rows = [];
    const diagnostics = []
      .concat(group && group.interval_diagnostics || [])
      .concat(group && group.diagnoses || [])
      .concat(group && group.script_report && group.script_report.diagnostics || []);
    diagnostics.filter(function (diagnostic) {
      return diagnosticMatchesCandidate(diagnostic, candidate);
    }).forEach(function (diagnostic) {
      const observations = diagnostic.observations || {};
      Object.keys(observations).forEach(function (key) {
        const row = formatNgcPeakObservation(key, (observations[key] || {}).observed_peak || observations[key], "");
        if (row) rows.push(row);
      });
      if (!Object.keys(observations).length && diagnostic.message) rows.push(diagnostic.message);
    });
    const windows = ngcCandidatePeakWindows(candidate);
    const supporting = group && group.supporting_peaks || {};
    Object.keys(supporting).forEach(function (preparation) {
      (supporting[preparation] || []).forEach(function (peak) {
        const d = Number(peak.d || peak.d_spacing || peak.observed_d_angstrom);
        const window = windows.find(function (range) {
          return Number.isFinite(d) && d >= range[0] && d <= range[1];
        });
        if (!window) return;
        const row = formatNgcPeakObservation(preparation, peak, window[2]);
        if (row) rows.push(row);
      });
    });
    const diagnostic = group && group.diagnostic_interpretation || {};
    (diagnostic.behavior_candidates || []).forEach(function (behavior) {
      const values = (behavior && (behavior.values || behavior.relations)) || [];
      const text = [behavior && behavior.behavior].concat(values).join(" ").toLowerCase();
      const candidateText = ngcCandidateDiagnosticText(candidate);
      if (!/mixed|interstrat|corrensite|smectite|esmect|chlorite|clorit/.test(candidateText + " " + text)) return;
      values.slice(0, 2).forEach(function (value) {
        if (typeof value === "string") rows.push(value + " · Cap. 7/8 comportamento N/G/C");
      });
    });
    const unique = [];
    rows.forEach(function (row) {
      if (row && unique.indexOf(row) < 0) unique.push(row);
    });
    return unique.slice(0, 4);
  }

  function renderNgcPrincipalRanking(group) {
    const ranked = rankedNgcCandidates(group).slice(0, 8);
    if (!ranked.length) return "";
    const rows = ranked.map(function (candidate, index) {
      const name = ngcCandidateDisplayName(candidate);
      const peaks = ngcCandidateRulePeaks(group, candidate).map(function (row) {
        return "<li>" + escapeHtml(row) + "</li>";
      }).join("");
      return [
        "<li>",
        index === 0 ? "<strong>" : "",
        mineralLink(name),
        index === 0 ? "</strong>" : "",
        peaks ? "<ul>" + peaks + "</ul>" : '<ul><li class="argilo-drx__mini-note">Picos diagnósticos não vinculados no payload; revisar faixas e evidências abaixo.</li></ul>',
        "</li>",
      ].join("");
    }).join("");
    return [
      '<div class="argilo-drx__ngc-found">',
      "<strong>Ranking mineralógico N/G/C desta seleção</strong>",
      '<p class="argilo-drx__mini-note">Lista ordenada pelo resultado estruturado do workflow. Não representa fase única; use as evidências N/G/C e os picos abaixo para revisar coexistência, mistura ou interestratificação.</p>',
      "<ol>", rows, "</ol>",
      "</div>",
    ].join("");
  }

  function renderNgcCompactRanking(group) {
    const rankingSummary = rankedNgcCandidates(group).slice(0, 5).map(function (candidate, index) {
      const name = ngcCandidateDisplayName(candidate);
      return [
        index === 0 ? "<strong>" : "",
        escapeHtml(name || "candidato"),
        index === 0 ? "</strong>" : "",
      ].join("");
    }).join(" · ");
    return rankingSummary
      ? "<p><strong>Ranking auxiliar N/G/C:</strong> " + rankingSummary + "</p>"
      : '<p class="argilo-drx__mini-note">Sem candidato N/G/C com evidência suficiente.</p>';
  }

  function renderDiagnosticV3Block(group, options) {
    options = options || {};
    const diagnostic = group && group.diagnostic_interpretation || null;
    if (!diagnostic) return "";
    const behaviorLabels = {
      expands_with_glycol: "Expansão com glicolação",
      collapses_after_heating: "Colapso após aquecimento",
      appears_after_heating: "Pico aparece após aquecimento",
      disappears_after_heating: "Pico desaparece após aquecimento",
      persists_after_heating: "Persistência após aquecimento",
      stable_after_glycol: "Estabilidade após glicolação",
      broad_or_shoulder: "Pico largo ou ombro",
      quartz_internal_standard_pattern: "Quartzo como padrão/interferência",
      partial_expansion_with_glycol: "Expansão parcial com glicolação",
      rational_sequence: "Sequência racional",
      ordered_chlorite_smectite: "Clorita/esmectita ordenada",
    };
    function behaviorGroupKey(behavior) {
      if (/expands|collapses|partial_expansion|rational_sequence|ordered_chlorite/i.test(behavior || "")) return "Trajetória N→G→C";
      if (/heating|appears|disappears|persists/i.test(behavior || "")) return "Resposta ao aquecimento";
      if (/stable_after_glycol/i.test(behavior || "")) return "Picos estáveis";
      return "Qualidade e interferências";
    }
    function renderBehaviorCards(rows) {
      const grouped = {};
      (rows || []).slice(0, 10).forEach(function (row) {
        const key = behaviorGroupKey(row && row.behavior);
        grouped[key] = grouped[key] || [];
        grouped[key].push(row);
      });
      return ["Trajetória N→G→C", "Resposta ao aquecimento", "Picos estáveis", "Qualidade e interferências"].map(function (groupName) {
        const items = grouped[groupName] || [];
        if (!items.length) return "";
        const body = items.map(function (row) {
          const label = row && typeof row === "object" ? row.behavior : row;
          const values = row && typeof row === "object" ? (row.values || []) : [];
          const relations = row && typeof row === "object" ? (row.relations || []) : [];
          const valueRows = values.length ? values : relations.map(function (relation) {
            const delta = relation.delta_d !== null && relation.delta_d !== undefined
              ? " · Δd " + formatNumber(Number(relation.delta_d), 3) + " Å"
              : "";
            return [
              relation.source || "N/D",
              " -> ",
              relation.target || "N/D",
              delta,
            ].join("");
          });
          return [
            '<div class="argilo-drx__ngc-evidence-row">',
            "<strong>", escapeHtml(behaviorLabels[label] || label || "Evidência"), "</strong>",
            valueRows.length ? "<span>" + escapeHtml(valueRows.slice(0, 4).join(" | ")) + "</span>" : "",
            "</div>",
          ].join("");
        }).join("");
        return [
          '<article class="argilo-drx__ngc-evidence-card">',
          "<h6>", escapeHtml(groupName), "</h6>",
          body,
          "</article>",
        ].join("");
      }).filter(Boolean).join("");
    }
    function renderRangeDiagnosticCard() {
      const diagnostics = ((group && group.script_report && group.script_report.diagnostics) || (group && group.interval_diagnostics) || []).slice(0, 6);
      if (!diagnostics.length) return "";
      const body = diagnostics.map(function (diagnostic) {
        const observations = diagnostic.observations || {};
        const values = Object.keys(observations).map(function (key) {
          const peak = (observations[key] || {}).observed_peak || {};
          if (!peak.d_angstrom) return "";
          return key + ": d " + formatNumber(Number(peak.d_angstrom), 2) + " Å"
            + (peak.two_theta ? " / 2θ " + formatNumber(Number(peak.two_theta), 2) + "°" : "")
            + (peak.intensity_abs ? " / int. " + formatNumber(Number(peak.intensity_abs), 0) : "");
        }).filter(Boolean).join(" | ");
        return [
          '<div class="argilo-drx__ngc-evidence-row">',
          "<strong>", escapeHtml(diagnostic.mineral || "Inconclusivo"), "</strong>",
          diagnostic.message ? "<span>" + escapeHtml(diagnostic.message) + "</span>" : "",
          values ? "<span>" + escapeHtml(values) + "</span>" : "",
          "</div>",
        ].join("");
      }).join("");
      return [
        '<article class="argilo-drx__ngc-evidence-card">',
        "<h6>Faixas diagnósticas</h6>",
        body,
        "</article>",
      ].join("");
    }
    function sourceRuleTargets(candidate) {
      // Mapeia o candidato exibido no painel para os alvos das regras do
      // Capitulo 7 de "X-Ray Diffraction and the Identification and Analysis
      // of Clay Minerals". O painel trabalha com grupos como kaolin_group ou
      // smectite_group, enquanto a base de conhecimento tambem possui regras
      // transversais como kaolin_vs_chlorite.
      const label = String(candidate && candidate.label || "").toLowerCase();
      const family = String(candidate && candidate.family || "").toLowerCase();
      const targets = [label, family];
      if (label === "smectite_group") targets.push("smectite");
      if (label === "kaolin_group") targets.push("kaolin_vs_chlorite", "kaolinite");
      if (label === "chlorite") targets.push("kaolin_vs_chlorite");
      if (label === "illite_mica") targets.push("illite_mica");
      if (label === "vermiculite") targets.push("vermiculite");
      if (family === "fibrous_channel") targets.push("sepiolite_palygorskite_halloysite");
      return targets.filter(Boolean);
    }
    function normalizeSourceTableId(value) {
      const raw = String(value || "").trim().toLowerCase();
      if (!raw) return "";
      return raw.replace(/^table[_\s-]*/i, "").replace(/\s+/g, "").replace(/[_.-]/g, "");
    }
    function sourceTableForReference(tableRef) {
      const tables = diagnostic.source_reflection_tables || {};
      const wanted = normalizeSourceTableId(tableRef);
      if (!wanted) return null;
      const key = Object.keys(tables).find(function (tableId) {
        const table = tables[tableId] || {};
        return normalizeSourceTableId(tableId).indexOf(wanted) >= 0
          || normalizeSourceTableId(table.reference && table.reference.table) === wanted;
      });
      return key ? tables[key] : null;
    }
    function formatSourceTableCell(value) {
      if (value === null || value === undefined || value === "") return "—";
      if (typeof value === "number" && Number.isFinite(value)) return String(Math.round(value * 1000) / 1000);
      if (Array.isArray(value)) return value.join(", ");
      if (typeof value === "object") return Object.keys(value).map(function (key) {
        return key + ": " + value[key];
      }).join("; ");
      return String(value);
    }
    function renderSourceTablePreview(table) {
      if (!table || !(table.rows || []).length) return "";
      const rows = (table.rows || []).slice(0, 8).map(function (row) {
        return [
          "<tr>",
          "<td>", escapeHtml(formatSourceTableCell(row.mineral || row.source_mineral || row.product)), "</td>",
          "<td>", escapeHtml(formatSourceTableCell(row.reflection || row.role || row.octahedral_type)), "</td>",
          "<td>", escapeHtml(formatSourceTableCell(row.d || row.d060_min || row.d_min)), "</td>",
          "<td>", escapeHtml(formatSourceTableCell(row.d060_max || row.d_max || row.tolerance)), "</td>",
          "<td>", escapeHtml(formatSourceTableCell(row.two_theta)), "</td>",
          "<td>", escapeHtml(formatSourceTableCell(row.intensity)), "</td>",
          "</tr>",
        ].join("");
      }).join("");
      const reference = table.reference || {};
      const title = table.title || reference.table || "Tabela estruturada";
      const notes = (table.notes || []).slice(0, 2).map(function (note) {
        return "<li>" + escapeHtml(note) + "</li>";
      }).join("");
      return [
        '<div class="argilo-drx__source-table-preview">',
        "<p><strong>", escapeHtml(title), "</strong>",
        table.page ? " <span>(p. " + escapeHtml(table.page) + ")</span>" : "",
        "</p>",
        '<div class="argilo-drx__table-scroll"><table class="ui very compact celled table">',
        "<thead><tr><th>Mineral</th><th>Ref./papel</th><th>d inicial Å</th><th>d final/tol. Å</th><th>2θ</th><th>Int.</th></tr></thead>",
        "<tbody>", rows, "</tbody></table></div>",
        notes ? "<ul>" + notes + "</ul>" : "",
        "</div>",
      ].join("");
    }
    function renderSourceRulePanel(candidate) {
      // Renderiza a secao recolhivel "Regra-fonte". Ela usa os objetos
      // source_rule_index e source_mineral_profiles injetados pela engine
      // Python. O loop sobre Object.keys(index) e finito e apenas filtra regras
      // ja recebidas no JSON; nenhuma inferencia mineralogica e feita no
      // frontend.
      const index = diagnostic.source_rule_index || {};
      const profiles = diagnostic.source_mineral_profiles || {};
      const profile = profiles[candidate.label] || profiles[candidate.family] || null;
      const targets = sourceRuleTargets(candidate);
      const rows = Object.keys(index).map(function (key) { return index[key]; }).filter(function (rule) {
        const target = String(rule && rule.target || "").toLowerCase();
        return targets.indexOf(target) >= 0;
      }).slice(0, 3);
      const profileRefs = profile && (profile.references || []).length
        ? (profile.references || []).slice(0, 2).map(function (ref) {
            const parts = [
              ref.page ? "p. " + ref.page : "",
              ref.table ? "Tabela " + ref.table : "",
              ref.figure ? "Figura " + ref.figure : "",
            ].filter(Boolean).join(" · ");
            return "<li>" + escapeHtml(parts || ref.source_id || "referência") + "</li>";
          }).join("")
        : "";
      const ruleRows = rows.map(function (rule) {
        const source = rule.source || {};
        const sourceBits = [
          source.page ? "p. " + source.page : "",
          source.table ? "Tabela " + source.table : "",
          source.figure ? "Figura " + source.figure : "",
        ].filter(Boolean).join(" · ");
        return [
          "<li>",
          "<strong>", escapeHtml(rule.rule_id || "regra"), "</strong>",
          sourceBits ? " <span>(" + escapeHtml(sourceBits) + ")</span>" : "",
          rule.explanation ? "<br><span>" + escapeHtml(rule.explanation) + "</span>" : "",
          "</li>",
        ].join("");
      }).join("");
      const tablePreviews = [];
      const seenTables = new Set();
      function addTablePreview(tableRef) {
        const table = sourceTableForReference(tableRef);
        const tableKey = table && ((table.reference && table.reference.table) || table.title || tableRef);
        if (!table || seenTables.has(tableKey)) return;
        seenTables.add(tableKey);
        tablePreviews.push(renderSourceTablePreview(table));
      }
      rows.forEach(function (rule) {
        addTablePreview(rule && rule.source && rule.source.table);
      });
      if (profile && (profile.references || []).length) {
        (profile.references || []).slice(0, 2).forEach(function (ref) {
          addTablePreview(ref && ref.table);
        });
      }
      if (!profileRefs && !ruleRows && !tablePreviews.length) return "";
      return [
        "<details class='argilo-drx__source-rule'>",
        "<summary>Regra-fonte</summary>",
        profileRefs ? "<p><strong>Perfil mineralógico</strong></p><ul>" + profileRefs + "</ul>" : "",
        ruleRows ? "<p><strong>Regras aplicadas</strong></p><ul>" + ruleRows + "</ul>" : "",
        tablePreviews.length ? "<p><strong>Dados das tabelas</strong></p>" + tablePreviews.join("") : "",
        "</details>",
      ].join("");
    }
    const bestNgcLine = options.showRanking === false ? "" : renderNgcPrincipalRanking(group);
    const candidates = (diagnostic.combined_candidates || []).slice(0, 5).map(function (candidate) {
      const evidences = (candidate.evidences || []).slice(0, 4).map(function (row) {
        return "<li>" + escapeHtml(row.message || row.kind || "Evidência") + "</li>";
      }).join("");
      const competitors = (candidate.competitors || []).slice(0, 3).map(function (row) {
        return "<li>" + escapeHtml(row.competitor || "competidor") + ": " + escapeHtml(row.reason || "") + "</li>";
      }).join("");
      return [
        '<article class="argilo-drx__diagnostic-block">',
        "<strong>", mineralLink(candidate.label || "candidato"), "</strong>",
        "<p>família ", escapeHtml(candidate.family || "N/D"), "</p>",
        candidate.explain ? "<p>" + escapeHtml(candidate.explain) + "</p>" : "",
        evidences ? "<p><strong>Informações que resultam no argilomineral</strong></p><ul>" + evidences + "</ul>" : "",
        renderSourceRulePanel(candidate),
        competitors ? "<p><strong>Competidores</strong></p><ul>" + competitors + "</ul>" : "",
        "</article>",
      ].join("");
    }).join("");
    const behavior = renderBehaviorCards(diagnostic.behavior_candidates || [])
      + (options.showRangeDiagnostics === false ? "" : renderRangeDiagnosticCard());
    const mixed = (diagnostic.mixed_layer_candidates || []).slice(0, 4).map(function (row) {
      return "<li>" + mineralLink(row.mixed_layer_candidate || "interestratificado") + " · " + escapeHtml(row.explanation || "") + "</li>";
    }).join("");
    const ambiguities = (diagnostic.ambiguities || []).slice(0, 5).map(function (row) {
      return "<li>" + escapeHtml(row.window || "janela") + ": " + escapeHtml((row.candidates || []).join(", ")) + "</li>";
    }).join("");
    const oct = diagnostic.octahedral_classification || {};
    const octDetails = oct.octahedral_type ? [
      escapeHtml(oct.octahedral_type),
      oct.d060 !== undefined ? " · d060 " + escapeHtml(formatNumber(Number(oct.d060), 3)) + " Å" : "",
      oct.source ? " · " + escapeHtml(oct.source) : "",
      oct.preparation ? " · preparo " + escapeHtml(oct.preparation) : "",
      oct.intensity !== undefined && oct.intensity !== null ? " · intensidade " + escapeHtml(formatNumber(Number(oct.intensity), 2)) : "",
      " · ",
      escapeHtml(oct.evidence || ""),
    ].join("") : "";
    const warnings = (diagnostic.warnings || []).slice(0, 3).map(function (row) {
      return "<li>" + escapeHtml(row) + "</li>";
    }).join("");
    return [
      '<div class="argilo-drx__ngc-interpretation argilo-drx__ngc-v3">',
      "<h4>Interpretação Mineralógica Assistida</h4>",
      '<p class="argilo-drx__mini-note">Resultado auxiliar. Não substitui interpretação mineralógica completa, refinamento estrutural, modelagem de difratogramas, análise química ou validação por especialista.</p>',
      bestNgcLine,
      options.showCandidates === false ? "" : (candidates ? "<h5>Candidatos por comportamento N-G-C</h5>" + candidates : ""),
      behavior ? "<h5>Resumo das evidências N-G-C</h5><div class='argilo-drx__ngc-evidence-grid'>" + behavior + "</div>" : "",
      octDetails ? "<h5>Classificação 060</h5><p>" + octDetails + "</p>" : "",
      mixed ? "<h5>Interestratificados</h5><ul>" + mixed + "</ul>" : "",
      ambiguities ? "<h5>Ambiguidades</h5><ul>" + ambiguities + "</ul>" : "",
      warnings ? "<h5>Proveniência e limitações</h5><ul>" + warnings + "</ul>" : "",
      "</div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderBackendNgcPrimarySummary() {
    const groups = backendNgcGroups().filter(function (group) {
      const preps = group.available_preparations || [];
      return preps.indexOf("natural") >= 0 && preps.indexOf("glicolado") >= 0 && preps.indexOf("calcinado") >= 0;
    });
    if (!groups.length) return "";
    const cards = groups.map(function (group) {
      const script = group.script_report || {};
      const best = group.best_candidate || {};
      const minerals = (script.detected_minerals || []).length
        ? (script.detected_minerals || []).join(", ")
        : ((group.target_screening || []).filter(function (row) { return row.status && row.status !== "not_observed"; }).map(function (row) { return row.mineral; }).join(", ") || "N/D");
      const diagnostics = (script.diagnostics || group.interval_diagnostics || []).slice(0, 6).map(function (diagnostic) {
        const observations = diagnostic.observations || {};
        const values = Object.keys(observations).map(function (key) {
          const observation = observations[key] || {};
          const peak = observation.observed_peak || {};
          if (!peak.d_angstrom) return "";
          return escapeHtml(key) + ": d " + escapeHtml(formatNumber(Number(peak.d_angstrom), 2)) + " Å"
            + (peak.two_theta ? " / 2θ " + escapeHtml(formatNumber(Number(peak.two_theta), 2)) + "°" : "")
            + (peak.intensity_abs ? " / int. " + escapeHtml(formatNumber(Number(peak.intensity_abs), 0)) : "");
        }).filter(Boolean).join("<br>");
        return [
          "<li>",
          "<strong>", escapeHtml(diagnostic.mineral || "Inconclusivo"), ":</strong> ",
          escapeHtml(diagnostic.message || diagnostic.rule || "Diagnóstico N/G/C"),
          values ? "<br><span class='argilo-drx__mini-note'>" + values + "</span>" : "",
          "</li>",
        ].join("");
      }).join("");
      const screenings = (group.target_screening || []).filter(function (row) {
        return row.status && row.status !== "not_observed";
      }).slice(0, 5).map(function (row) {
        return "<li><strong>" + escapeHtml(row.mineral || "Mineral") + ":</strong> "
          + escapeHtml(row.status || "N/D")
          + "<br><span class='argilo-drx__mini-note'>" + escapeHtml(row.message || "") + "</span></li>";
      }).join("");
      return [
        '<article class="argilo-drx__selected-card argilo-drx__selected-card--ngc">',
        "<h3>Leitura N/G/C principal · ", escapeHtml(group.sample_base || "amostra"), "</h3>",
        "<p><strong>Tratamentos:</strong> Natural, Glicolado, Calcinado</p>",
        "<p><strong>Minerais sinalizados:</strong> ", escapeHtml(minerals), "</p>",
        renderNgcCompactRanking(group),
        renderDiagnosticV3Block(group),
        diagnostics ? "<p><strong>Diagnóstico por faixas:</strong></p><ul>" + diagnostics + "</ul>" : "",
        screenings ? "<p><strong>Triagem mineralógica:</strong></p><ul>" + screenings + "</ul>" : "",
        '<p class="argilo-drx__mini-note">Resultado auxiliar para orientar curadoria; não confirma mineralogia automaticamente.</p>',
        "</article>",
      ].join("");
    }).join("");
    return '<section class="argilo-drx__selected-ngc-summary">' + cards + "</section>";
  }

  function isExternalRawItem(item) {
    return Boolean(
      item &&
      (
        String(item.id || "").indexOf("external:") === 0 ||
        (item.record && item.record.id === "arquivo-externo") ||
        (item.traceability && item.traceability.source === "arquivo_externo_temporario")
      )
    );
  }

  function renderExternalRawFileRows(items) {
    return (items || []).map(function (item) {
      const filename = (item.metadata || {}).original_filename || item.sampleCode || item.id;
      const preclassification = item.externalCurvePreclassification || (item.metadata && item.metadata.external_curve_preclassification) || item.externalRawPreclassification || (item.metadata && item.metadata.external_raw_preclassification) || {};
      const d060 = (item.metadata || {}).d060 || (preclassification.d060 && preclassification.d060.d060);
      const d060Status = (item.metadata || {}).d060_status || (preclassification.d060 && preclassification.d060.status);
      const d060Text = d060
        ? "d060 " + formatNumber(Number(d060), 3) + " Å (" + (d060Status === "inferred_auxiliary" ? "inferido" : "informado") + ")"
        : "d060 indisponível";
      return [
        "<tr>",
        "<td>", escapeHtml(filename || "amostra externa"), "</td>",
        "<td>", treatmentBadge(item), "</td>",
        "<td>", escapeHtml(item.treatment_evidence || "N/D"), "<br><span class='argilo-drx__mini-note'>", escapeHtml(d060Text), "</span></td>",
        "</tr>",
      ].join("");
    }).join("");
  }

  function renderExternalPreclassificationProcess(items, backendLoading) {
    const steps = [
      "1. Ler arquivo externo e preservar eixo 2θ/intensidade.",
      "2. Inferir preparo pelo nome do arquivo: N, G ou C.",
      "3. Converter a curva em item temporário com picos, metadados e SHA-256.",
      "4. Procurar d060 apenas como evidência auxiliar quando houver pico entre 1.485 e 1.555 Å.",
      "5. Agrupar as amostras por amostra-base e enviar ao workflow N/G/C já usado nos dados internos.",
      "6. Renderizar interpretação, ambiguidades, interestratificados e regra-fonte sem modificar o difratograma.",
    ];
    const loaded = (items || []).length;
    return [
      '<div class="argilo-drx__external-preclassification-process">',
      "<p><strong>Processo de pré-classificação</strong>",
      backendLoading ? " <span class='argilo-drx__mini-note'>em andamento</span>" : " <span class='argilo-drx__mini-note'>executado</span>",
      "</p>",
      "<p class='argilo-drx__mini-note'>Amostras externas carregadas: ", escapeHtml(loaded), ". A classificação usa o conjunto temporário; a curva plotada permanece a curva lida.</p>",
      "<ol><li>", steps.map(escapeHtml).join("</li><li>"), "</li></ol>",
      "</div>",
    ].join("");
  }

  function externalSimilarityEntries(items) {
    const seen = new Set();
    return (items || []).map(function (item) {
      const similarity = item.packageSimilarity || {};
      const best = similarity.best_match || {};
      const recordId = best.record_id || similarity.record_id || "";
      const key = [recordId, best.filename || "", best.sample_code || ""].join("|");
      if (!similarity.available || !recordId || seen.has(key)) return "";
      seen.add(key);
      const loadButton = best.filename || best.sample_code ? [
        '<button class="ui tiny button argilo-drx__load-similar" type="button"',
        ' data-load-similar-raw="1"',
        ' data-record-id="', escapeHtml(recordId), '"',
        ' data-sample-code="', escapeHtml(best.sample_code || ""), '"',
        ' data-filename="', escapeHtml(best.filename || ""), '">',
        'Carregar RAW similar',
        '</button>',
      ].join("") : "";
      return [
        "<li>",
        "<strong>", escapeHtml(best.sample_code || best.filename || "RAW similar no banco"), "</strong>",
        best.preparation || best.preparation_label ? " · " + treatmentBadge({ treatment: best.preparation, treatment_label: best.preparation_label }) : "",
        best.filename ? " · arquivo " + escapeHtml(best.filename) : "",
        '<div class="argilo-drx__match-actions">',
        recordButton(recordId, "Abrir registro", best.record_url),
        loadButton,
        "</div>",
        "</li>",
      ].join("");
    }).filter(Boolean);
  }

  function renderExternalSimilarityLinks(items) {
    const entries = externalSimilarityEntries(items);
    const related = (items || []).map(function (item) {
      return renderRelatedRecordMatches(item.packageSimilarity || {});
    }).filter(Boolean).join("");
    if (!entries.length && !related) return "";
    return [
      '<section class="compact-section argilo-drx__external-match">',
      "<h3>RAW similar na Argiloteca</h3>",
      entries.length ? "<ul>" + entries.join("") + "</ul>" : "",
      related,
      "</section>",
    ].join("");
  }

  function renderExternalNgcCandidateEvidenceFromBackend(group) {
    return [
      renderDiagnosticV3Block(group, {
        showCandidates: false,
        showRangeDiagnostics: false,
      }),
    ].join("");
  }

  function renderExternalNgcCandidateEvidenceLocal(items) {
    const assembly = buildMineralAssembly(items || []);
    const bestMineral = bestClayMineralFromAssembly(assembly);
    const groups = buildNgcGroups(items || []);
    const groupRows = groups.slice(0, 3).map(function (group) {
      const score = buildNgcTrajectoryScore(group);
      const evidences = (score.evidences || []).slice(0, 5).map(function (row) {
        return "<li>" + escapeHtml(row) + "</li>";
      }).join("");
      return [
        "<li>",
        "<strong>", escapeHtml(group.sampleBase || "amostra"), ":</strong> ",
        "N ", escapeHtml(group.natural.length || 0), " · G ", escapeHtml(group.glicolada.length || 0), " · C ", escapeHtml(group.calcinada.length || 0),
        evidences ? "<ul>" + evidences + "</ul>" : "",
        "</li>",
      ].join("");
    }).join("");
    const peakRows = bestMineral && (bestMineral.supportPeaks || []).length
      ? bestMineral.supportPeaks.slice(0, 6).map(function (row) { return "<li>" + escapeHtml(row) + "</li>"; }).join("")
      : "";
    return [
      bestMineral ? "<p><strong>Argilomineral resultante:</strong> " + mineralLink(bestMineral.mineral) + "</p>" : '<p class="argilo-drx__mini-note">Sem argilomineral resultante com evidência suficiente.</p>',
      peakRows ? "<p><strong>Picos/observações que sustentam a hipótese:</strong></p><ul>" + peakRows + "</ul>" : "",
      groupRows ? "<p><strong>Composição N/G/C do conjunto externo:</strong></p><ul>" + groupRows + "</ul>" : "",
    ].join("");
  }

  function renderExternalGsas2Validation(items) {
    const rows = (items || []).map(function (item) {
      const validation = item.gsas2Validation || (item.metadata && item.metadata.gsas2_validation) || null;
      if (!validation) return "";
      const warnings = validation.warnings || [];
      const jobId = validation.job_id || "N/D";
      const instrument = validation.instrument_path || "não configurado";
      const peakMode = validation.allow_peak_refinement ? "picos semeados enviados" : "somente importação/GPX";
      return [
        "<tr>",
        "<td>", escapeHtml((item.metadata || {}).original_filename || item.sampleCode || item.id), "</td>",
        "<td>", escapeHtml(validation.status || "registrado"), "</td>",
        "<td>", escapeHtml(jobId), "</td>",
        "<td>", escapeHtml(instrument), "</td>",
        "<td>", escapeHtml(peakMode), "</td>",
        "<td>", escapeHtml(warnings.slice(0, 2).join(" | ") || "sem aviso"), "</td>",
        "</tr>",
      ].join("");
    }).filter(Boolean).join("");
    if (!rows) return "";
    return [
      '<section class="compact-section argilo-drx__external-match">',
      "<h3>Validação GSAS-II do RAW externo</h3>",
      "<p>GSAS-II foi registrado como job externo auxiliar. O resultado não substitui a leitura N/G/C.</p>",
      '<div class="argilo-drx__table-scroll"><table class="ui very compact celled table">',
      "<thead><tr><th>Arquivo</th><th>Status</th><th>Job</th><th>Instrumento</th><th>Modo</th><th>Avisos</th></tr></thead><tbody>",
      rows,
      "</tbody></table></div>",
      "</section>",
    ].join("");
  }

  function renderExternalRawMergedNgcPanel(items) {
    const groups = backendNgcGroups();
    const completeGroups = groups.filter(function (group) {
      const preps = group.available_preparations || [];
      return preps.indexOf("natural") >= 0 && preps.indexOf("glicolado") >= 0 && preps.indexOf("calcinado") >= 0;
    });
    const backendGroup = completeGroups[0] || groups[0] || null;
    const localGroups = buildNgcGroups(items || []);
    const localComplete = localGroups.some(function (group) {
      return group.natural.length && group.glicolada.length && group.calcinada.length;
    });
    const statusText = localComplete ? "trio N/G/C completo" : "conjunto N/G/C incompleto";
    const backendLoading = ngcWorkflowPayload && ngcWorkflowPayload.loading;
    const backendError = ngcWorkflowPayload && ngcWorkflowPayload.success === false ? ngcWorkflowPayload.error : "";
    const preclassification = backendGroup && (backendGroup.external_curve_preclassification || backendGroup.external_raw_preclassification) || null;
    const d060Rows = preclassification && (preclassification.d060 || []).length
      ? (preclassification.d060 || []).map(function (row) {
          return [
            "<li>",
            escapeHtml(row.filename || "amostra externa"),
            row.preparation ? " · " + escapeHtml(treatmentLabel(row.preparation)) : "",
            row.d060 ? " · d060 " + escapeHtml(formatNumber(Number(row.d060), 3)) + " Å" : " · d060 indisponível",
            row.status ? " · " + escapeHtml(row.status) : "",
            row.warning ? "<br><span class='argilo-drx__mini-note'>" + escapeHtml(row.warning) + "</span>" : "",
            "</li>",
          ].join("");
        }).join("")
      : "";
    const sourceBlock = backendLoading
      ? '<p class="argilo-drx__mini-note">Calculando análise N/G/C do conjunto externo...</p>'
      : (backendGroup ? renderExternalNgcCandidateEvidenceFromBackend(backendGroup) : renderExternalNgcCandidateEvidenceLocal(items));
    return [
      '<section class="argilo-drx__selected-ngc-summary">',
      '<article class="argilo-drx__selected-card argilo-drx__selected-card--ngc">',
      "<h3>Pré-classificação de amostras externas N/G/C</h3>",
      "<p>Pré-classificação auxiliar baseada nas amostras externas carregadas. Não substitui revisão mineralógica.</p>",
      "<p><strong>Status do conjunto:</strong> ", escapeHtml(statusText), "</p>",
      renderExternalPreclassificationProcess(items, backendLoading),
      '<div class="argilo-drx__table-scroll"><table class="ui very compact celled table">',
      "<thead><tr><th>Arquivo</th><th>Preparo</th><th>Critério</th></tr></thead><tbody>",
      renderExternalRawFileRows(items) || "<tr><td colspan='3'>Nenhuma amostra externa selecionada.</td></tr>",
      "</tbody></table></div>",
      backendError ? '<p class="argilo-drx__mini-note">Workflow N/G/C backend indisponível: ' + escapeHtml(backendError) + '</p>' : "",
      d060Rows ? "<p><strong>Classificação 060 preliminar</strong></p><ul>" + d060Rows + "</ul>" : "",
      sourceBlock,
      renderExternalSimilarityLinks(items),
      '<p class="argilo-drx__mini-note">Leitura auxiliar para curadoria: o argilomineral resulta da combinação de tratamento N/G/C e picos basais/companheiros.</p>',
      "</article>",
      "</section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderSelectedClayEvidence(candidate) {
    if (!candidate) return "N/D";
    return [
      mineralLink(candidate.mineral || "Argilomineral candidato"),
      "(" + escapeHtml(mineralClass(candidate) || "Argilomineral") + ")",
      escapeHtml(evidenceSummary(candidate)),
    ].join(" ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function compareByMineralRowScore(left, right) {
    return compareByCandidateScore({ score: left && left.bestScore }, { score: right && right.bestScore });
  }

  function clayMineralsFromAssembly(assembly) {
    return (assembly || [])
      .filter(function (row) { return isAuthorizedClayMineral(row.candidate); })
      .sort(compareByMineralRowScore);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function bestClayMineralFromAssembly(assembly) {
    const contextMineralSlug = currentArgilomineralSlug();
    const clayMinerals = clayMineralsFromAssembly(assembly);
    const preferredClayMinerals = contextMineralSlug
      ? clayMinerals.filter(function (row) { return candidateMatchesMineralSlug(row.candidate, contextMineralSlug); })
      : [];
    return preferredClayMinerals[0] || clayMinerals[0] || null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function activePanelArgilomineral(items, assembly) {
    const contextSlug = currentArgilomineralSlug();
    if (contextSlug) {
      return {
        slug: contextSlug,
        label: currentArgilomineralLabel() || contextSlug,
        source: "url",
      };
    }
    const panelAssembly = assembly || buildMineralAssembly(items || []);
    const selectedMineral = bestClayMineralFromAssembly(panelAssembly);
    const slug = resolveMineralSlug(selectedMineral && selectedMineral.mineral) || mineralSlug(selectedMineral && selectedMineral.mineral);
    if (!slug) return null;
    return {
      slug: slug,
      label: selectedMineral.mineral || slug,
      source: "panel",
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRruffOdrReviewLink(target) {
    if (!DRX_SHOW_RRUFF_ODR_REVIEW_LINK) return "";
    if (!target || !target.slug) {
      return [
        "<section class='compact-section argilo-drx__rruff-link-card argilo-drx__rruff-link-card--missing'>",
        "<h2>Referência RRUFF ODR</h2>",
        "<p class='note warning'>Sem argilomineral ativo para vincular à camada RRUFF ODR.</p>",
        "</section>",
      ].join("");
    }
    const matches = rruffOdrLoaded ? rruffOdrCurvesForSlug(target.slug) : [];
    const hasMatch = rruffOdrLoaded && matches.length;
    const title = hasMatch
      ? "RRUFF ODR vinculado ao mesmo mineral"
      : (rruffOdrLoaded ? "Regra de ausência RRUFF ODR" : "RRUFF ODR a verificar");
    const note = hasMatch
      ? matches.length + " curva(s) RRUFF ODR confirmada(s) para " + (target.label || target.slug) + ". A camada de revisão abrirá somente esse mineral."
      : (rruffOdrLoaded
        ? "Não há curva RRUFF ODR confirmada para " + (target.label || target.slug) + ". Até haver amostra curada, compensar com N/G/C, picos diagnósticos, CMS/Handbook e WebMineral apenas como fallback/comparação."
        : "A disponibilidade RRUFF ODR será conferida ao abrir a camada de revisão para " + (target.label || target.slug) + ".");
    return [
      "<section class='compact-section argilo-drx__rruff-link-card", hasMatch ? "" : " argilo-drx__rruff-link-card--missing", "'>",
      "<h2>", escapeHtml(title), "</h2>",
      "<p><strong>Mineral ativo:</strong> ", mineralLink(target.label || target.slug), "</p>",
      "<p class='note", hasMatch ? "" : " warning", "'>", escapeHtml(note), "</p>",
      "<button class='ui tiny primary button' type='button' data-open-rruff-odr-mineral='", escapeHtml(target.slug), "' data-open-rruff-odr-label='", escapeHtml(target.label || target.slug), "'>",
      hasMatch ? "Abrir RRUFF ODR deste mineral" : "Abrir regra RRUFF ODR",
      "</button>",
      "</section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function interpretationStrengthLabel(mineral) {
    if (!mineral) return "Evidência insuficiente";
    const score = Number(mineral.bestScore);
    const rank = mineral.bestConfidenceRank || confidenceRank(mineral.bestConfidence);
    if (rank >= 3 || (Number.isFinite(score) && score >= 0.75)) return "Interpretação forte/provável";
    if (rank >= 2 || (Number.isFinite(score) && score >= 0.45)) return "Interpretação possível";
    return "Evidência fraca/não conclusiva";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function alternativeClayMinerals(assembly, selectedMineral) {
    const selectedSlug = resolveMineralSlug(selectedMineral && selectedMineral.mineral) || mineralSlug(selectedMineral && selectedMineral.mineral);
    return clayMineralsFromAssembly(assembly).filter(function (row) {
      const slug = resolveMineralSlug(row.mineral) || mineralSlug(row.mineral);
      return slug && slug !== selectedSlug;
    }).slice(0, 3);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function alternativeClayMineralsHtml(assembly, selectedMineral) {
    const alternatives = alternativeClayMinerals(assembly, selectedMineral);
    if (!alternatives.length) return "Nenhum candidato alternativo forte no conjunto selecionado.";
    return alternatives.map(function (row) {
      return mineralLink(row.mineral);
    }).join("<br>");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function selectedNgcCurveComparisonText(scoreDetails) {
    const shifts = scoreDetails && scoreDetails.shifts || {};
    const rows = [];
    if (Number.isFinite(Number(shifts.natural_to_glycolated))) rows.push("N→G Δd " + formatNumber(Number(shifts.natural_to_glycolated), 2) + " Å");
    if (Number.isFinite(Number(shifts.glycolated_to_calcined))) rows.push("G→C Δd " + formatNumber(Number(shifts.glycolated_to_calcined), 2) + " Å");
    const evidences = (scoreDetails && scoreDetails.evidences || []).slice(0, 3);
    const detail = rows.concat(evidences).join("; ");
    return "Compare as curvas N/G/C completas" + (detail ? ": " + detail : ": observe deslocamento, expansão, colapso ou estabilidade dos picos basais.");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderSelectedNgcCompleteSummary(items) {
    const completeGroups = buildNgcGroups(items).filter(function (group) {
      return group.natural.length && group.glicolada.length && group.calcinada.length;
    });
    if (!completeGroups.length) return "";
    const rows = completeGroups.map(function (group) {
      const groupItems = [group.natural[0], group.glicolada[0], group.calcinada[0]].filter(Boolean);
      const assembly = buildMineralAssembly(groupItems);
      const bestMineral = bestClayMineralFromAssembly(assembly);
      const scoreDetails = buildNgcTrajectoryScore(group);
      const evidence = bestMineral
        ? mineralLink(bestMineral.mineral)
          + " (" + escapeHtml(bestMineral.classLabel || bestMineral.group || "Argilomineral") + ")"
          + ". " + escapeHtml((bestMineral.evidences || []).filter(Boolean)[0] || evidenceSummary(bestMineral.candidate))
        : "N/D";
      return [
        '<article class="argilo-drx__selected-card argilo-drx__selected-card--ngc">',
        "<h3>Trio N/G/C completo · ", escapeHtml(group.sampleBase), "</h3>",
        "<p><strong>Principais evidências:</strong> ", evidence, "</p>",
        "<p><strong>Compare as curvas:</strong> ", escapeHtml(selectedNgcCurveComparisonText(scoreDetails)), "</p>",
        "<p><strong>Sugestão de argilomineral:</strong> ", bestMineral ? mineralLink(bestMineral.mineral) : "N/D", "</p>",
        "</article>",
      ].join("");
    }).join("");
    return '<section class="argilo-drx__selected-ngc-summary">' + rows + "</section>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderReferenceComparisonBlock(item) {
    const payload = item && item.referenceComparison;
    if (!payload) return "";
    if (payload.loading) {
      return [
        '<div class="argilo-drx__reference-match">',
        '<p><strong>Comparação com referência:</strong> processando ', escapeHtml(payload.filename || "referência"), "...</p>",
        "</div>",
      ].join("");
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (payload.success === false) {
      return [
        '<div class="argilo-drx__reference-match argilo-drx__reference-match--warning">',
        '<p><strong>Comparação com referência:</strong> ', escapeHtml(payload.error || "falha na comparação"), "</p>",
        "</div>",
      ].join("");
    }
    const comparison = payload.reference_comparison || payload;
    const pattern = payload.reference_pattern || {};
    if (!comparison || !comparison.schema_version) return "";
    const rows = (comparison.matches || []).slice(0, 5).map(function (match) {
      return [
        "<li>",
        "ref. ", escapeHtml(match.reference_peak_index || "N/D"),
        " · 2θ ", escapeHtml(formatNumber(match.reference_two_theta, 3)),
        " ↔ obs. ", escapeHtml(formatNumber(match.observed_two_theta, 3)),
        " · Δ ", escapeHtml(formatNumber(match.delta_two_theta, 3)),
        "</li>",
      ].join("");
    }).join("");
    return [
      '<div class="argilo-drx__reference-match">',
      '<p><strong>Comparação com referência:</strong> ', escapeHtml(pattern.filename || comparison.reference_filename || "referência"), "</p>",
      '<p>Score ', escapeHtml(formatScore(comparison.score)),
      " · cobertura ponderada ", escapeHtml(formatScore(comparison.weighted_coverage)),
      " · ", escapeHtml(comparison.matched_peak_count || 0), " de ", escapeHtml(comparison.reference_peak_count || 0), " picos casados.</p>",
      rows ? "<ul>" + rows + "</ul>" : '<p class="argilo-drx__mini-note">Nenhum pico casado dentro da tolerância configurada.</p>',
      '<p class="argilo-drx__mini-note">Comparação automatizada auxiliar; não confirma fase mineralógica isoladamente.</p>',
      "</div>",
    ].join("");
  }

  /**
   * Renderiza a seção principal de interpretação N/G/C de argilominerais.
   *
   * O bloco prioriza grupos completos N/G/C sobre candidatos isolados por RAW,
   * mostra evidências a favor/contra, picos companheiros e avisos de sobreposição
   * como 7 Å caulinita/clorita e 3,33 Å ilita/quartzo.
   * @returns {string} HTML seguro para a área de leitura geral do painel.
   */
  function renderNgcBackendWorkflowBlock() {
    if (!ngcWorkflowUrl || !ngcWorkflowPayload) return "";
    if (ngcWorkflowPayload.loading) {
      return [
        '<section class="argilo-drx__selected-ngc-summary">',
        '<article class="argilo-drx__selected-card argilo-drx__selected-card--ngc">',
        "<h3>Workflow N/G/C backend</h3>",
        '<p class="argilo-drx__mini-note">Calculando interpretação N/G/C auxiliar no backend...</p>',
        "</article>",
        "</section>",
      ].join("");
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (ngcWorkflowPayload.success === false) {
      return [
        '<section class="argilo-drx__selected-ngc-summary">',
        '<article class="argilo-drx__selected-card argilo-drx__selected-card--ngc">',
        "<h3>Workflow N/G/C backend</h3>",
        '<p class="argilo-drx__mini-note">', escapeHtml(ngcWorkflowPayload.error || "Workflow N/G/C indisponível."), "</p>",
        "</article>",
        "</section>",
      ].join("");
    }
    const groups = (ngcWorkflowPayload.groups || []).slice(0, 4);
    if (!groups.length) return "";
    const rows = groups.map(function (group) {
      const best = group.best_candidate || {};
      const evidence = (best.evidence || []).slice(0, 3).map(function (row) {
        const peak = row.observed_peak || {};
        return [
          "<li>",
          escapeHtml(row.label || row.range_key || "Evidência"),
          peak.d_angstrom ? " · d " + escapeHtml(formatNumber(Number(peak.d_angstrom), 2)) + " Å" : "",
          row.preparation ? " · " + escapeHtml(treatmentLabel(row.preparation)) : "",
          "</li>",
        ].join("");
      }).join("");
      const warnings = (best.warnings || group.warnings || []).slice(0, 2).map(function (warning) {
        return "<li>" + escapeHtml(warning) + "</li>";
      }).join("");
      const intervalDiagnostics = (group.interval_diagnostics || []).slice(0, 6).map(function (diagnostic) {
        const observations = diagnostic.observations || {};
        const values = Object.keys(observations).map(function (key) {
          const observation = observations[key] || {};
          const peak = observation.observed_peak || {};
          if (!peak.d_angstrom) return "";
          return escapeHtml(key) + " d " + escapeHtml(formatNumber(Number(peak.d_angstrom), 2)) + " Å";
        }).filter(Boolean).join(" · ");
        return "<li><strong>" + escapeHtml(diagnostic.mineral || "Inconclusivo") + ":</strong> "
          + escapeHtml(diagnostic.message || diagnostic.rule || "Diagnóstico por intervalo")
          + (values ? "<br><span class='argilo-drx__mini-note'>" + values + "</span>" : "")
          + "</li>";
      }).join("");
      const scriptReport = group.script_report || {};
      const scriptMinerals = (scriptReport.detected_minerals || []).length
        ? "<p><strong>Minerais sinalizados pelo script:</strong> " + escapeHtml((scriptReport.detected_minerals || []).join(", ")) + "</p>"
        : '<p class="argilo-drx__mini-note">Nenhum mineral sinalizado pelo script N/G/C.</p>';
      const scriptDiagnostics = (scriptReport.diagnostics || []).slice(0, 6).map(function (diagnostic) {
        const observations = diagnostic.observations || {};
        const values = Object.keys(observations).map(function (key) {
          const observation = observations[key] || {};
          const peak = observation.observed_peak || {};
          if (!peak.d_angstrom) return "";
          const intensity = Number(peak.intensity_abs || peak.relative_intensity || 0);
          return escapeHtml(key) + " d " + escapeHtml(formatNumber(Number(peak.d_angstrom), 2)) + " Å"
            + (Number.isFinite(intensity) && intensity > 0 ? " · int. " + escapeHtml(formatNumber(intensity, 1)) : "");
        }).filter(Boolean).join(" · ");
        return [
          "<li>",
          "<strong>", escapeHtml(diagnostic.mineral || "Inconclusivo"), ":</strong> ",
          escapeHtml(diagnostic.message || diagnostic.rule || "Diagnóstico por intervalo"),
          values ? "<br><span class='argilo-drx__mini-note'>" + values + "</span>" : "",
          "</li>",
        ].join("");
      }).join("");
      const scriptPeakTables = (scriptReport.peak_tables || []).slice(0, 3).map(function (table) {
        const peakRows = (table.peaks || []).slice(0, 15).map(function (peak) {
          return [
            "<tr>",
            "<td>", escapeHtml(peak.peak_index || ""), "</td>",
            "<td>", escapeHtml(formatNumber(Number(peak.two_theta), 3)), "</td>",
            "<td>", escapeHtml(formatNumber(Number(peak.d_angstrom), 3)), "</td>",
            "<td>", escapeHtml(formatNumber(Number(peak.intensity_abs), 1)), "</td>",
            "<td>", escapeHtml(formatNumber(Number(peak.relative_intensity), 1)), "</td>",
            "<td>", peak.fwhm !== null && peak.fwhm !== undefined ? escapeHtml(formatNumber(Number(peak.fwhm), 3)) : "N/D", "</td>",
            "</tr>",
          ].join("");
        }).join("");
        return [
          '<div class="argilo-drx__script-table">',
          "<p><strong>Tabela de picos - ", escapeHtml(treatmentLabel(table.preparation)), "</strong>",
          table.filename ? " · " + escapeHtml(table.filename) : "",
          "</p>",
          '<div class="argilo-drx__table-scroll"><table class="ui very compact celled table">',
          "<thead><tr><th>Índice</th><th>2θ</th><th>d Å</th><th>Int.</th><th>Norm.</th><th>FWHM</th></tr></thead>",
          "<tbody>", peakRows || "<tr><td colspan='6'>Sem picos disponíveis.</td></tr>", "</tbody>",
          "</table></div>",
          "</div>",
        ].join("");
      }).join("");
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      function renderObservationValues(observations) {
        return Object.keys(observations || {}).map(function (key) {
          const observation = observations[key] || {};
          const peak = observation.observed_peak || {};
          if (!peak.d_angstrom) return "";
          return escapeHtml(key) + " d " + escapeHtml(formatNumber(Number(peak.d_angstrom), 2)) + " Å";
        }).filter(Boolean).join(" · ");
      }
      const targetScreening = (group.target_screening || []).slice(0, 5).map(function (screening) {
        const statusLabel = {
          detected: "detectado",
          possible: "possível",
          not_observed: "não observado",
          mixed_layer_suspected: "mistura/interestratificado possível",
        }[screening.status] || screening.status || "N/D";
        const values = renderObservationValues(screening.observations || {});
        const companionValues = renderObservationValues(screening.companion_peaks || {});
        const behavior = screening.ngc_behavior || {};
        return [
          "<li>",
          "<strong>", escapeHtml(screening.mineral || "Mineral"), ":</strong> ",
          escapeHtml(statusLabel),
          "<br><span>", escapeHtml(screening.message || ""), "</span>",
          values ? "<br><span class='argilo-drx__mini-note'>" + values + "</span>" : "",
          companionValues && companionValues !== values ? "<br><span class='argilo-drx__mini-note'>Picos companheiros: " + companionValues + "</span>" : "",
          behavior.message ? "<br><span class='argilo-drx__mini-note'>Comportamento N/G/C: " + escapeHtml(behavior.message) + " (" + escapeHtml(behavior.status || "N/D") + ")</span>" : "",
          "</li>",
        ].join("");
      }).join("");
      const clayInterpretation = group.clay_interpretation || {};
      const clayWarnings = (clayInterpretation.globalWarnings || []).slice(0, 4).map(function (warning) {
        return "<li>" + escapeHtml(warning) + "</li>";
      }).join("");
      const missingPreparations = (clayInterpretation.missingPreparations || []).length
        ? '<p class="argilo-drx__mini-note">Preparações faltantes: ' + escapeHtml((clayInterpretation.missingPreparations || []).map(treatmentLabel).join(", ")) + "</p>"
        : "";
      const clayCandidates = (clayInterpretation.candidates || []).slice(0, 6).map(function (candidate) {
        const evidenceFor = (candidate.evidenceFor || []).slice(0, 4).map(function (row) {
          return "<li>" + escapeHtml(row) + "</li>";
        }).join("");
        const evidenceAgainst = (candidate.evidenceAgainst || []).slice(0, 3).map(function (row) {
          return "<li>" + escapeHtml(row) + "</li>";
        }).join("");
        const overlaps = (candidate.overlaps || []).slice(0, 3).map(function (row) {
          return "<li>" + escapeHtml(row) + "</li>";
        }).join("");
        const tests = (candidate.recommendedAdditionalTests || []).slice(0, 4).map(function (row) {
          return "<li>" + escapeHtml(row) + "</li>";
        }).join("");
        return [
          '<article class="argilo-drx__diagnostic-block">',
          "<strong>", escapeHtml(candidate.candidateLabelPt || candidate.candidateId || "Candidato"), "</strong>",
          "<p><span>Status: ", escapeHtml(candidate.status || "N/D"), "</span>",
          " · <span>família ", escapeHtml(candidate.family || "N/D"), "</span>",
          " · <span>nível ", escapeHtml(candidate.level || "N/D"), "</span></p>",
          candidate.explanationPt ? "<p>" + escapeHtml(candidate.explanationPt) + "</p>" : "",
          evidenceFor ? "<p><strong>Evidências a favor</strong></p><ul>" + evidenceFor + "</ul>" : "",
          evidenceAgainst ? "<p><strong>Evidências contra/conflitos</strong></p><ul>" + evidenceAgainst + "</ul>" : "",
          overlaps ? "<p><strong>Sobreposições conhecidas</strong></p><ul>" + overlaps + "</ul>" : "",
          tests ? "<p><strong>Testes adicionais</strong></p><ul>" + tests + "</ul>" : "",
          "</article>",
        ].join("");
      }).join("");
      const clayInterpretationBlock = clayCandidates
        ? [
          '<div class="argilo-drx__ngc-interpretation">',
          "<p><strong>Interpretação N–G–C de argilominerais</strong></p>",
          '<p class="argilo-drx__mini-note">Candidatos ordenados por comportamento entre Natural/Glicolado/Calcinado. WebMineral entra como catálogo auxiliar; não é confirmação por d/I isolado.</p>',
          missingPreparations,
          clayCandidates,
          clayWarnings ? "<p><strong>Limitações globais</strong></p><ul>" + clayWarnings + "</ul>" : "",
          "</div>",
        ].join("")
        : "";
      const mixedWarnings = (group.mixed_layer_warnings || []).slice(0, 4).map(function (warning) {
        return "<li>" + escapeHtml(warning) + "</li>";
      }).join("");
      const targetedRows = (group.targeted_basal_peaks || []).filter(function (row) {
        return row && row.status && row.status !== "not_found";
      }).slice(0, 8).map(function (row) {
        return [
          "<li>",
          "<strong>", escapeHtml(row.mineral || "Mineral"), "</strong>",
          row.label ? " · " + escapeHtml(row.label) : "",
          " · ", escapeHtml(row.status || "N/D"),
          row.observed_d_angstrom ? " · d " + escapeHtml(formatNumber(Number(row.observed_d_angstrom), 2)) + " Å" : "",
          row.intensity ? " · intensidade " + escapeHtml(formatNumber(Number(row.intensity), 1)) : "",
          row.preparation ? " · " + escapeHtml(treatmentLabel(row.preparation)) : "",
          "</li>",
        ].join("");
      }).join("");
      return [
        '<article class="argilo-drx__selected-card argilo-drx__selected-card--ngc">',
        "<h3>Workflow N/G/C backend · ", escapeHtml(group.sample_base || "amostra"), "</h3>",
        "<p><strong>Status:</strong> ", escapeHtml(group.status || "N/D"),
        " · <strong>preparos:</strong> ", escapeHtml((group.available_preparations || []).map(treatmentLabel).join(", ") || "N/D"), "</p>",
        renderNgcCompactRanking(group),
        renderDiagnosticV3Block(group),
        clayInterpretationBlock,
        scriptReport.title ? "<p><strong>" + escapeHtml(scriptReport.title) + ":</strong></p>" + scriptMinerals + (scriptDiagnostics ? "<ul>" + scriptDiagnostics + "</ul>" : "") + scriptPeakTables : "",
        evidence ? "<ul>" + evidence + "</ul>" : "",
        targetScreening ? "<p><strong>Triagem direcionada:</strong></p><ul>" + targetScreening + "</ul>" : "",
        targetedRows ? "<p><strong>Picos basais direcionados:</strong></p><ul>" + targetedRows + "</ul>" : "",
        intervalDiagnostics ? "<p><strong>Diagnóstico por faixas d-spacing:</strong></p><ul>" + intervalDiagnostics + "</ul>" : "",
        mixedWarnings ? "<p><strong>Avisos de mistura/interestratificação:</strong></p><ul>" + mixedWarnings + "</ul>" : "",
        warnings ? '<p class="argilo-drx__mini-note">Avisos:</p><ul>' + warnings + "</ul>" : "",
        '<p class="argilo-drx__mini-note">', escapeHtml(best.interpretation_policy || ngcWorkflowPayload.interpretation_policy || "Workflow auxiliar; não confirma mineralogia."), "</p>",
        "</article>",
      ].join("");
    }).join("");
    return '<section class="argilo-drx__selected-ngc-summary">' + rows + "</section>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderSelectedSummary() {
    const items = selectedItemsInNgcOrder();
    if (!items.length) {
      selectedSummaryEl.innerHTML = "<p>A descrição dos registros aparecerá aqui junto com a seleção.</p>";
      return;
    }
    refreshNgcWorkflow(items);
    if (items.length && items.every(isExternalRawItem)) {
      selectedSummaryEl.innerHTML = renderExternalRawMergedNgcPanel(items);
      return;
    }
    const hasBackendNgc = hasBackendNgcCompleteGroup();
    const cards = items.map(function (item, index) {
      const color = palette[index % palette.length];
      const record = item.record;
      const sample = item.sample || {};
      const traceability = item.traceability || {};
      const similarity = item.packageSimilarity || {};
      const bestMatch = similarity.best_match || {};
      const bestMatchRecordId = bestMatch.record_id || similarity.record_id || currentRecordId();
      const similarRecordButton = bestMatchRecordId ? recordButton(bestMatchRecordId, "Abrir registro semelhante", bestMatch.record_url) : "";
      const loadSimilarButton = bestMatch.filename || bestMatch.sample_code ? [
        '<p><button class="ui tiny button argilo-drx__load-similar" type="button"',
        ' data-load-similar-raw="1"',
        ' data-record-id="', escapeHtml(bestMatchRecordId), '"',
        ' data-sample-code="', escapeHtml(bestMatch.sample_code || ""), '"',
        ' data-filename="', escapeHtml(bestMatch.filename || ""), '">',
        'Carregar RAW semelhante no gráfico',
        '</button></p>',
      ].join("") : "";
      const similarityBlock = similarity.available ? [
        '<div class="argilo-drx__external-match">',
        '<p><strong>Comparação com registros da Argiloteca:</strong> ', escapeHtml(similarity.message || "Sem resultado informado."), "</p>",
        bestMatch.filename ? '<p><strong>Mais semelhante:</strong> ' + escapeHtml(bestMatch.sample_code || bestMatch.filename) + " · " + treatmentBadge({ treatment: bestMatch.preparation, treatment_label: bestMatch.preparation_label }) + "</p>" : "",
        similarRecordButton ? '<p>' + similarRecordButton + "</p>" : "",
        renderMatchedPeaks(bestMatch),
        loadSimilarButton,
        renderRelatedRecordMatches(similarity),
        bestMatch.has_interpretation ? '<p><strong>Interpretação existente:</strong> há picos/candidatos mineralógicos já indexados na Argiloteca para esse arquivo.</p>' : "",
        (bestMatch.evidence || []).length ? '<ul>' + bestMatch.evidence.slice(0, 4).map(function (evidence) { return "<li>" + escapeHtml(evidence) + "</li>"; }).join("") + "</ul>" : "",
        "</div>",
      ].join("") : "";
      const bestClayCandidate = hasBackendNgc ? null : bestScoredClayCandidate(item, currentArgilomineralSlug());
      const bestClayMineral = bestClayCandidate ? [bestClayCandidate.mineral] : [];
      const reportUrl = technicalReportUrl(item.id);
      const reportButton = reportUrl
        ? '<a class="ui tiny button" href="' + escapeHtml(reportUrl) + '" target="_blank" rel="noopener">Relatório técnico</a>'
        : (item.technicalReport ? '<span class="argilo-drx__mini-note">Relatório técnico backend disponível no payload desta sessão.</span>' : "");
      return [
        '<article class="argilo-drx__selected-card" style="border-left-color:', color, '">',
        '<h3>', escapeHtml(record.title), "</h3>",
        record.id ? '<p><strong>Registro:</strong> ' + recordButton(record.id, "Abrir registro na Argiloteca") + "</p>" : "",
        '<p><strong>Arquivo:</strong> ', escapeHtml(item.metadata.original_filename || item.id), "</p>",
        '<p><strong>Amostra:</strong> ', escapeHtml(sampleLabel(item)), "</p>",
        hasBackendNgc ? '<p><strong>Leitura mineralógica:</strong> consolidada no bloco N/G/C principal.</p>' : '<p><strong>Argilomineral:</strong> ' + renderBestScoredClayCandidate(bestClayCandidate) + "</p>",
        '<p><strong>Preparo DRX:</strong> ', treatmentBadge(item), " · ", escapeHtml(item.treatment_evidence || "criterio nao informado"), "</p>",
        hasBackendNgc ? "" : '<p><strong>Local:</strong> ' + escapeHtml(sample.locality || record.sample_locality || "Nao informado") + "</p>",
        hasBackendNgc ? "" : '<p><strong>Análise:</strong> ' + escapeHtml(analysisLabel(item.analyses)) + "</p>",
        hasBackendNgc ? "" : '<p><strong>Formação:</strong> ' + escapeHtml(record.formacao_geologica || record.ambiente_formacao || "Nao informado") + "</p>",
        hasBackendNgc ? "" : '<p><strong>Método:</strong> ' + escapeHtml((item.analyses[0] && item.analyses[0].method) || record.metodos || "Nao informado") + "</p>",
        hasBackendNgc ? "" : '<p><strong>Rastreabilidade:</strong> ' + (traceability.sample_found ? "amostra vinculada" : "amostra nao encontrada no registro") + " · " + escapeHtml(traceability.analysis_count || 0) + " analise(s)</p>",
        hasBackendNgc ? "" : renderCandidateEvidenceBlock(item, bestClayCandidate),
        similarityBlock,
        hasBackendNgc ? "" : renderReferenceComparisonBlock(item),
        hasBackendNgc ? "" : renderNeuralEvidenceBlock(item),
        hasBackendNgc ? "" : renderXrdnetContextBlock(item),
        '<div class="argilo-drx__tags">', renderTags(bestClayMineral), "</div>",
        reportButton ? '<p>' + reportButton + '</p>' : "",
        '<button class="ui button" type="button" data-remove-drx="', escapeHtml(item.id), '">Remover</button>',
        "</article>",
      ].join("");
    }).join("");
    selectedSummaryEl.innerHTML = (hasBackendNgc ? renderBackendNgcPrimarySummary() : renderNgcBackendWorkflowBlock()) + cards + (hasBackendNgc ? "" : renderSelectedNgcCompleteSummary(items));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function aggregateMinerals(items) {
    const byMineral = new Map();
    items.forEach(function (item) {
      const candidates = (item.mineralCandidates || []).slice();
      (item.mineralEvidence || []).forEach(function (evidence) {
        if (!evidence || !evidence.mineral_candidate) return;
        candidates.push({
          mineral: evidence.mineral_candidate,
          group: "Evidência assistida DRX",
          score: evidence.evidence_weight,
          confidence: evidence.confidence,
          evidence: evidence.explanation,
          matches: [{
            observed_two_theta: evidence.observed_two_theta,
            observed_d: evidence.observed_d_angstrom,
            reference_d: [evidence.expected_d_min, evidence.expected_d_max].filter(Boolean).join("-"),
          }],
        });
      });
      (item.mineralCharacterization || []).forEach(function (summary) {
        if (!summary || !summary.mineral) return;
        candidates.push({
          mineral: summary.mineral,
          group: summary.group || "Caracterização assistida DRX",
          score: summary.score,
          confidence: summary.confidence,
          evidence: summary.recommendation,
          characterization: summary,
          matches: (summary.supporting_peaks || []).map(function (peak) {
            return {
              observed_two_theta: peak.two_theta,
              observed_d: peak.d_angstrom,
              relative_intensity: peak.intensity_relative,
              preparation: peak.preparation,
            };
          }),
        });
      });
      candidates.forEach(function (candidate) {
        const name = candidate.mineral || "Mineral nao informado";
        const key = name.toLowerCase();
        const bucket = byMineral.get(key) || {
          mineral: name,
          group: candidate.group || "Grupo nao informado",
          count: 0,
          bestScore: null,
          bestConfidence: null,
          samples: [],
          treatments: new Set(),
          evidences: [],
          supportPeaks: [],
          missingConfirmatoryPeaks: [],
          outOfRangeConfirmatoryPeaks: [],
          conflicts: [],
          limitations: [],
          recommendations: [],
        };
        bucket.count += 1;
        if (typeof candidate.score === "number" && (bucket.bestScore === null || candidate.score > bucket.bestScore)) {
          bucket.bestScore = candidate.score;
          bucket.bestConfidence = candidate.confidence;
        }
        bucket.samples.push(sampleLabel(item) + " (" + treatmentLabel(item.treatment) + ")");
        bucket.treatments.add(treatmentLabel(item.treatment));
        (candidate.matches || []).slice(0, 5).forEach(function (match) {
          bucket.supportPeaks.push(sampleLabel(item) + " · " + treatmentLabel(item.treatment) + ": " + readableMatchPeak(match));
        });
        bucket.evidences.push({
          sample: sampleLabel(item),
          treatment: item.treatment,
          confidence: candidate.confidence,
          score: candidate.score,
          summary: evidenceSummary(candidate),
        });
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (candidate.characterization) {
          (candidate.characterization.missing_confirmatory_peaks || []).forEach(function (peak) {
            bucket.missingConfirmatoryPeaks.push(
              (peak.preparation && peak.preparation !== "any" ? treatmentLabel(peak.preparation) + " · " : "") +
              (peak.label || "pico confirmatório") +
              " esperado em d " +
              formatNumber(peak.expected_d_min, 2) +
              "-" +
              formatNumber(peak.expected_d_max, 2) +
              " Å"
            );
          });
          (candidate.characterization.out_of_range_confirmatory_peaks || []).forEach(function (peak) {
            const expected = [
              formatNumber(peak.expected_two_theta_min, 2),
              formatNumber(peak.expected_two_theta_max, 2),
            ].filter(Boolean).join("-");
            const measured = [
              formatNumber(peak.measured_two_theta_min, 2),
              formatNumber(peak.measured_two_theta_max, 2),
            ].filter(Boolean).join("-");
            bucket.outOfRangeConfirmatoryPeaks.push(
              (peak.preparation && peak.preparation !== "any" ? treatmentLabel(peak.preparation) + " · " : "") +
              (peak.label || "reflexão confirmatória") +
              " esperada em 2θ " +
              (expected || "N/D") +
              "°; faixa medida " +
              (measured || "N/D") +
              "°"
            );
          });
          (candidate.characterization.conflicts || []).forEach(function (conflict) {
            bucket.conflicts.push(conflict);
          });
          (candidate.characterization.limitations || []).forEach(function (limitation) {
            bucket.limitations.push(limitation);
          });
          /**
           * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
           * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
           */
          if (candidate.characterization.recommendation) {
            bucket.recommendations.push(candidate.characterization.recommendation);
          }
        }
        byMineral.set(key, bucket);
      });
    });
    return Array.from(byMineral.values()).sort(function (left, right) {
      return (right.count - left.count) || ((right.bestScore || 0) - (left.bestScore || 0));
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderMineralPanel() {
    if (!mineralPanelEl) return;
    const items = selectedItemsInNgcOrder();
    if (!items.length) {
      mineralPanelEl.innerHTML = [
        "<p>Selecione difratogramas para ver minerais candidatos e evidências de picos.</p>",
        renderMethodologyLimitations([]),
      ].join("");
      return;
    }
    mineralPanelEl.innerHTML = renderMineralPanelReport(items);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderMineralPanelReport(items) {
    const assembly = buildMineralAssembly(items);
    const peakRows = buildPeakRows(items);
    const uncertainties = interpretationUncertainties(assembly, peakRows, items);
    const recommendations = recommendationsFor(items, assembly);
    const rruffTarget = activePanelArgilomineral(items, assembly);
    const hasBackendNgc = hasBackendNgcCompleteGroup();
    const missingCandidates = items.filter(function (item) {
      return !(item.mineralCandidates || []).length && !(item.mineralEvidence || []).length;
    });
    const missingNotice = missingCandidates.length
      ? "<p class='note warning'>" + escapeHtml(missingCandidates.length) + " difratograma(s) selecionado(s) ainda sem candidatos mineralógicos vinculados.</p>"
      : "";
    return [
      "<div class='argilo-drx__report-panel'>",
      "<section class='cover'><h2>Leitura Geral</h2>",
      "<p class='meta'>", escapeHtml(items.length), " difratograma(s) selecionado(s). ", hasBackendNgc ? "A leitura principal usa o trio N/G/C backend." : "A leitura abaixo segue a mesma lógica do PDF exportado.", "</p>",
      "<p class='note warning'>Resultados dependem da qualidade do difratograma, preparação da amostra e sobreposição de picos. A identificação final requer curadoria.</p>",
      hasBackendNgc ? "" : missingNotice,
      "</section>",
      hasBackendNgc ? renderBackendNgcPrimarySummary() : renderExecutiveSummary(items, assembly, peakRows),
      renderRruffOdrReviewLink(rruffTarget),
      hasBackendNgc ? "" : renderGeologistEvidencePanel(items),
      hasBackendNgc ? "" : renderSemTituloNgcDiagnosticPanel(items),
      renderMethodologyLimitations(items),
      renderPeakTable(peakRows),
      renderDiagnosticCriteria(peakRows),
      hasBackendNgc ? "" : "<section class='compact-section'><h2>Interpretação preliminar</h2><p>" + geologicalInterpretationHtml(assembly) + "</p></section>",
      "<section class='compact-section'><h2>Limitações da interpretação</h2>", htmlList(uncertainties.concat([
        "Ausência de quantificação por Rietveld neste relatório.",
        "Possível orientação preferencial e efeitos de preparação podem alterar intensidades relativas.",
        "Integração com petrografia, FRX, MEV/EDS e dados de campo é recomendada.",
      ])), "</section>",
      "<section class='compact-section'><h2>Recomendações para refinamento</h2>", htmlList(recommendations), "</section>",
      "</div>",
    ].join("");
  }


  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function xrdnetPercent(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return "N/D";
    return (numeric * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "%";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function xrdnetPredictionBadges(predictions) {
    const rows = (predictions || []).slice(0, 3);
    if (!rows.length) return '<span class="argilo-drx__tag">sem predição</span>';
    return rows.map(function (prediction) {
      return '<span class="argilo-drx__tag argilo-drx__tag--xrdnet">' + escapeHtml(prediction.label)
        + ' · ' + escapeHtml(xrdnetPercent(prediction.probability)) + '</span>';
    }).join(" ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function neuralEvidenceCandidateRows(candidates) {
    const rows = (candidates || []).slice(0, 4);
    if (!rows.length) {
      return '<p class="argilo-drx__mini-note">Nenhum candidato neural foi incluído no índice compacto.</p>';
    }
    return '<div class="argilo-drx__neural-candidates">' + rows.map(function (candidate) {
      const matches = (candidate.matches || []).slice(0, 3).map(function (match) {
        const observed = match.observed_two_theta != null ? formatNumber(match.observed_two_theta, 2) + "°2θ" : "pico observado";
        const reference = match.reference_d_angstrom != null ? "ref. d=" + formatNumber(match.reference_d_angstrom, 2) + " Å" : "referência";
        return "<li>" + escapeHtml(observed + " · " + reference) + "</li>";
      }).join("");
      const candidateMeta = [
        candidate.confidence ? "<strong>conf.:</strong> " + escapeHtml(candidate.confidence) : "",
        candidate.matched_lines != null ? "<strong>linhas:</strong> " + escapeHtml(candidate.matched_lines) : "",
      ].filter(Boolean).join(" · ");
      return [
        '<article class="argilo-drx__neural-candidate">',
        '<h5>', mineralLink(candidate.mineral || candidate.title_pt || candidate.argilomineral_id || "Mineral candidato"), "</h5>",
        candidateMeta ? "<p>" + candidateMeta + "</p>" : "",
        matches ? '<ul class="argilo-drx__evidence-list">' + matches + "</ul>" : "",
        "</article>",
      ].join("");
    }).join("") + "</div>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function neuralEvidenceQualityLine(evidence) {
    const quality = evidence.quality || {};
    const metrics = quality.metrics || {};
    const parts = [];
    if (metrics.original_points != null) parts.push("pontos originais " + metrics.original_points);
    if (metrics.grid_points != null) parts.push("grade " + metrics.grid_points);
    if (metrics.peaks_total != null) parts.push("picos " + metrics.peaks_total);
    if (metrics.reconstruction_correlation_mapped != null) parts.push("corr. " + formatNumber(metrics.reconstruction_correlation_mapped, 2));
    return parts.length ? parts.join(" · ") : "métricas compactas não informadas";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function neuralEvidenceBinsHtml(bins) {
    const rows = (bins || []).slice(0, 5);
    if (!rows.length) return "";
    return [
      '<div class="argilo-drx__neural-bins">',
      '<strong>Faixas 2θ relevantes:</strong> ',
      rows.map(function (row) {
        const start = row.two_theta_min != null ? formatNumber(row.two_theta_min, 1) : "?";
        const end = row.two_theta_max != null ? formatNumber(row.two_theta_max, 1) : "?";
        return '<span class="argilo-drx__tag argilo-drx__tag--neural">' + escapeHtml(start + "-" + end + "° · " + formatScore(row.importance)) + "</span>";
      }).join(""),
      "</div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderNeuralEvidenceBlock(item) {
    if (!neuralEvidenceUrlTemplate) return "";
    const payload = item.neuralEvidence || neuralEvidenceCache.get(item.id);
    if (!payload) {
      loadNeuralEvidenceForItem(item);
      return [
        '<div class="argilo-drx__neural-context">',
        '<h4>Evidência neural auxiliar</h4>',
        '<p>Carregando evidência neural pré-computada...</p>',
        "</div>",
      ].join("");
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (payload.loading) {
      return [
        '<div class="argilo-drx__neural-context">',
        '<h4>Evidência neural auxiliar</h4>',
        '<p>Carregando evidência neural pré-computada...</p>',
        "</div>",
      ].join("");
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (payload.success === false) {
      if (payload.available && payload.matched === false) return "";
      return [
        '<div class="argilo-drx__neural-context argilo-drx__neural-context--warning">',
        '<h4>Evidência neural auxiliar</h4>',
        '<p>', escapeHtml(payload.error || "Índice neural auxiliar indisponível."), "</p>",
        "</div>",
      ].join("");
    }
    const evidence = payload.evidence || {};
    const warnings = [].concat(evidence.warnings || [], (evidence.quality && evidence.quality.warnings) || []);
    const xrdnet = evidence.xrdnet || {};
    return [
      '<div class="argilo-drx__neural-context">',
      '<h4>Evidência neural auxiliar</h4>',
      '<p><strong>Fonte:</strong> ', escapeHtml(evidence.filename || evidence.sample_id || evidence.source_curve || "índice neural pré-computado"), "</p>",
      xrdnet.top_predictions ? '<div class="argilo-drx__tags">' + xrdnetPredictionBadges(xrdnet.top_predictions) + "</div>" : "",
      neuralEvidenceCandidateRows(evidence.candidates),
      '<p class="argilo-drx__mini-note"><strong>Qualidade:</strong> ', escapeHtml(neuralEvidenceQualityLine(evidence)), "</p>",
      neuralEvidenceBinsHtml(evidence.explain_bins),
      warnings.length ? '<p class="argilo-drx__mini-note argilo-drx__mini-note--warning"><strong>Avisos:</strong> ' + escapeHtml(warnings.slice(0, 3).join("; ")) + "</p>" : "",
      '<p class="argilo-drx__mini-note">Triagem neural experimental; não confirma mineralogia. Validar com picos diagnósticos, preparo N/G/C e curadoria geológica.</p>',
      "</div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function xrdnetNormalize(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\.[a-z0-9]+$/i, "")
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function xrdnetBasename(value) {
    return String(value || "").split(/[\\/]/).pop();
  }

  function xrdnetTerms(values) {
    const terms = new Set();
    (values || []).forEach(function (value) {
      [value, xrdnetBasename(value)].forEach(function (candidate) {
        const term = xrdnetNormalize(candidate);
        if (term && term.length > 3) terms.add(term);
      });
    });
    return Array.from(terms);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function xrdnetRowTerms(row) {
    return xrdnetTerms([
      row.curve_id,
      row.sample_id,
      row.source_file,
      row.source_curve,
      row.curve_path,
      row.prediction_path,
    ]);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function xrdnetItemTerms(item) {
    const metadata = item.metadata || {};
    const diffractogram = item.diffractogram || {};
    const sample = item.sample || {};
    const similarity = item.packageSimilarity || {};
    const bestMatch = similarity.best_match || {};
    return xrdnetTerms([
      item.id,
      item.sampleCode,
      item.advancedResultPath,
      sampleLabel(item),
      sample.sample_code,
      sample.sample_label,
      metadata.original_filename,
      metadata.filename,
      metadata.sample_code,
      metadata.advanced_result_path,
      metadata.source_curve,
      metadata.curve_path,
      diffractogram.id,
      diffractogram.filename,
      diffractogram.original_filename,
      diffractogram.sample_code,
      diffractogram.curve_path,
      bestMatch.filename,
      bestMatch.sample_code,
      bestMatch.source_file,
      bestMatch.source_curve,
      bestMatch.curve_path,
      bestMatch.advanced_result_path,
    ]);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function xrdnetTermsMatch(rowTerm, itemTerm) {
    if (!rowTerm || !itemTerm) return false;
    if (rowTerm === itemTerm) return true;
    if (rowTerm.length < 8 || itemTerm.length < 8) return false;
    return rowTerm.indexOf(itemTerm) !== -1 || itemTerm.indexOf(rowTerm) !== -1;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function xrdnetPredictionForItem(item) {
    const rows = (xrdnetSummary && xrdnetSummary.rows) || [];
    const itemTerms = xrdnetItemTerms(item);
    let fallback = null;
    rows.some(function (row) {
      const rowTerms = xrdnetRowTerms(row);
      const exact = rowTerms.some(function (rowTerm) {
        return itemTerms.some(function (itemTerm) {
          return rowTerm === itemTerm;
        });
      });
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (exact) {
        fallback = row;
        return true;
      }
      if (!fallback && rowTerms.some(function (rowTerm) {
        return itemTerms.some(function (itemTerm) {
          return xrdnetTermsMatch(rowTerm, itemTerm);
        });
      })) {
        fallback = row;
      }
      return false;
    });
    return fallback;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function shouldShowXrdnetForItem(item) {
    if (!item) return false;
    const similarity = item.packageSimilarity || {};
    const bestMatch = similarity.best_match || {};
    return Boolean(
      item.loadedAsSimilar
      || (similarity.available && (bestMatch.filename || bestMatch.sample_code || bestMatch.score))
    );
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function ensureXrdnetSummary() {
    if (!xrdnetSummaryUrl || xrdnetSummary || xrdnetSummaryError) return Promise.resolve(xrdnetSummary);
    if (xrdnetSummaryPromise) return xrdnetSummaryPromise;
    xrdnetSummaryPromise = fetchJson(xrdnetSummaryUrl)
      .then(function (summary) {
        xrdnetSummary = summary;
        xrdnetSummaryError = "";
        return summary;
      })
      .catch(function (error) {
        xrdnetSummaryError = error && error.message ? error.message : "Falha ao carregar resumo neural XRDNet.";
        return null;
      })
      .then(function (summary) {
        xrdnetSummaryPromise = null;
        return summary;
      });
    return xrdnetSummaryPromise;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderXrdnetContextBlock(item) {
    if (!shouldShowXrdnetForItem(item)) return "";
    if (
      item.neuralEvidence
      && item.neuralEvidence.success
      && item.neuralEvidence.evidence
      && item.neuralEvidence.evidence.xrdnet
    ) {
      return "";
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!xrdnetSummaryUrl) {
      return [
        '<div class="argilo-drx__xrdnet-context argilo-drx__xrdnet-context--warning">',
        '<h4>Evidência neural auxiliar</h4>',
        '<p>RAW semelhante detectado, mas a fonte JSON neural não está configurada nesta página.</p>',
        '</div>',
      ].join("");
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (xrdnetSummaryError) {
      return [
        '<div class="argilo-drx__xrdnet-context argilo-drx__xrdnet-context--warning">',
        '<h4>Evidência neural auxiliar</h4>',
        '<p>RAW semelhante detectado, mas o resumo neural não pôde ser lido: ', escapeHtml(xrdnetSummaryError), '</p>',
        '</div>',
      ].join("");
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!xrdnetSummary) {
      ensureXrdnetSummary().then(function () {
        renderAll();
      });
      return [
        '<div class="argilo-drx__xrdnet-context">',
        '<h4>Evidência neural auxiliar</h4>',
        '<p>Carregando predição neural para o RAW semelhante...</p>',
        '</div>',
      ].join("");
    }
    const row = xrdnetPredictionForItem(item);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!row) {
      return [
        '<div class="argilo-drx__xrdnet-context argilo-drx__xrdnet-context--warning">',
        '<h4>Evidência neural auxiliar</h4>',
        '<p>RAW semelhante detectado; nenhum JSON neural correspondente foi encontrado para este arquivo.</p>',
        '</div>',
      ].join("");
    }
    const labels = (row.labels || []).slice(0, 4);
    const similarityLabel = item.loadedAsSimilar ? "RAW semelhante carregado" : "RAW semelhante detectado";
    return [
      '<div class="argilo-drx__xrdnet-context">',
      '<h4>Evidência neural auxiliar</h4>',
      '<p><strong>', similarityLabel, ':</strong> ', escapeHtml(row.source_file || item.metadata.original_filename || sampleLabel(item)), '</p>',
      '<div class="argilo-drx__tags">', xrdnetPredictionBadges(row.top_predictions), '</div>',
      labels.length ? '<p><strong>Rótulos derivados:</strong> ' + labels.map(mineralLink).join(", ") + '</p>' : "",
      '<p class="argilo-drx__mini-note">Predição neural auxiliar para o RAW similar carregado; confirmar com picos, preparo N/G/C e interpretação mineralógica.</p>',
      '</div>',
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function isMineralPanelFullscreen() {
    return Boolean(
      (document.fullscreenElement && document.fullscreenElement === drxFullscreenSectionEl)
      || (drxFullscreenSectionEl && drxFullscreenSectionEl.classList.contains("argilo-drx__main--fullscreen"))
    );
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function syncMineralPanelFullscreenButton() {
    mineralPanelFullscreenEls.forEach(function (button) {
      button.textContent = isMineralPanelFullscreen() ? "Sair da tela cheia" : "Tela cheia";
      button.setAttribute("aria-pressed", isMineralPanelFullscreen() ? "true" : "false");
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function toggleMineralPanelFullscreen() {
    if (!drxFullscreenSectionEl) return;
    if (document.fullscreenElement === drxFullscreenSectionEl && document.exitFullscreen) {
      document.exitFullscreen().catch(function () {
        drxFullscreenSectionEl.classList.remove("argilo-drx__main--fullscreen");
        syncMineralPanelFullscreenButton();
      });
      return;
    }
    if (drxFullscreenSectionEl.classList.contains("argilo-drx__main--fullscreen")) {
      drxFullscreenSectionEl.classList.remove("argilo-drx__main--fullscreen");
      syncMineralPanelFullscreenButton();
      return;
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (drxFullscreenSectionEl.requestFullscreen) {
      drxFullscreenSectionEl.requestFullscreen().then(syncMineralPanelFullscreenButton).catch(function () {
        drxFullscreenSectionEl.classList.add("argilo-drx__main--fullscreen");
        syncMineralPanelFullscreenButton();
      });
      return;
    }
    drxFullscreenSectionEl.classList.add("argilo-drx__main--fullscreen");
    syncMineralPanelFullscreenButton();
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function updateStatus() {
    const count = selected.size;
    if (count === 1) {
      statusEl.textContent = "Selecione pelo menos dois difratogramas para comparar.";
    } else if (count > 1) {
      statusEl.textContent = count + " difratogramas selecionados.";
    } else if (!records.length) {
      statusEl.textContent = "Nenhum difratograma importado no indice DRX.";
    } else {
      statusEl.textContent = "Selecione pelo menos dois difratogramas para comparar.";
    }
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderAll() {
    renderChart();
    renderSelectedSummary();
    renderMineralPanel();
    syncRruffOdrWithActivePanelMineral();
    renderRecordList();
    updateStatus();
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function exportCsv() {
    const items = selectedItemsInNgcOrder();
    if (!items.length) return;
    const rows = ["diffractogram_id,record_id,sample_code,treatment,two_theta,intensity"];
    items.forEach(function (item) {
      item.twoTheta.forEach(function (theta, index) {
        rows.push([
          item.id,
          item.record.id,
          item.sampleCode || "",
          item.treatment || "",
          theta,
          item.intensity[index],
        ].map(function (value) { return '"' + String(value).replace(/"/g, '""') + '"'; }).join(","));
      });
    });
    download("argiloteca_drx_comparacao.csv", "text/csv;charset=utf-8", rows.join("\n"));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function exportJson() {
    const items = selectedItemsInNgcOrder();
    if (!items.length) return;
    const payload = {
      schema_version: "argiloteca.drx.panel_export.v1",
      exported_at: new Date().toISOString(),
      view_parameters: {
        mode: modeEl.value,
        show_peak_markers: showPeakMarkers,
        x_domain: xDomain,
        renderer: plotlyChartEl && !plotlyChartEl.hidden ? "plotly" : "svg",
      },
      backend_selection_report_url: selectionReportUrl || null,
      ngc_workflow: ngcWorkflowPayload && !ngcWorkflowPayload.loading ? ngcWorkflowPayload : null,
      diffractograms: items.map(function (item, index) {
        const transformed = transformedSeries(item, index);
        return {
          id: item.id,
          record_id: item.record && item.record.id,
          sample_code: item.sampleCode || "",
          filename: item.metadata && item.metadata.original_filename || item.id,
          treatment: item.treatment || "",
          source_sha256: item.metadata && item.metadata.source_sha256,
          analysis_run: item.metadata && item.metadata.analysis_run || item.analysisRun || null,
          technical_report_schema: item.technicalReport && item.technicalReport.schema_version || null,
          peak_processing: item.metadata && item.metadata.peak_processing || {},
          xrd_method: item.metadata && item.metadata.xrd_method || {},
          qc_flags: item.qcFlags || [],
          detected_peaks: item.detectedPeaks || [],
          advanced_peaks: item.advancedPeaks || [],
          reference_comparison: item.referenceComparison && item.referenceComparison.reference_comparison || null,
          neural_evidence_status: item.neuralEvidence && item.neuralEvidence.success,
          curve: {
            two_theta: item.twoTheta || [],
            intensity: item.intensity || [],
            transformed_intensity: transformed,
            transformation: modeEl.value,
          },
        };
      }),
    };
    download("argiloteca_drx_comparacao.json", "application/json;charset=utf-8", JSON.stringify(payload, null, 2));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function exportSvg() {
    if (!selected.size) return;
    const svg = chartEl.cloneNode(true);
    svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    download("argiloteca_drx_comparacao.svg", "image/svg+xml;charset=utf-8", svg.outerHTML);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mineralDescription(candidate) {
    const key = String(candidate.mineral || "").trim().toLowerCase();
    return mineralDescriptions[key] || {
      title: candidate.mineral || "Mineral candidato",
      text: "Candidato mineralogico identificado por casamento de picos. A estrutura cristalina nao esta descrita no catalogo local deste relatorio; trate a atribuicao como evidencia para curadoria e compare com dados quimicos, preparo da amostra e contexto geologico.",
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function uniqueMineralCandidates(items) {
    const byName = new Map();
    items.forEach(function (item) {
      (item.mineralCandidates || []).slice(0, 5).forEach(function (candidate) {
        const key = String(candidate.mineral || "").toLowerCase();
        if (!key) return;
        const previous = byName.get(key);
        if (!previous || (candidate.score || 0) > (previous.score || 0)) byName.set(key, candidate);
      });
    });
    return Array.from(byName.values()).sort(function (left, right) {
      return (right.score || 0) - (left.score || 0);
    });
  }

  const CU_K_ALPHA_WAVELENGTH = 1.54056;
  // Bloco diagnostico local em d-spacing para relatorio e triagem N/G/C.
  const PEAK_DETECTION_DESCRIPTION = "biblioteca científica Python SciPy usada para encontrar picos em uma sequência numérica, como uma curva de DRX.";
  const DIAGNOSTIC_PEAK_MIN_TWO_THETA = 2;
  const DIAGNOSTIC_PEAK_MAX_TWO_THETA = 32;
  const DIAGNOSTIC_PEAK_MAX_D_ANGSTROM = 32;
  const SEM_TITULO_NGC_DIAGNOSTIC_RANGES = {
    illite10A: [9.73, 10.38],
    illite10ANatural: [9.84, 10.36],
    illite10AGlycolated: [9.82, 10.30],
    illite10ACalcined: [9.73, 10.38],
    kaolinite7A: [6.96, 7.42],
    kaolinite7ANatural: [6.97, 7.42],
    kaolinite7AGlycolated: [6.96, 7.42],
    kaolinite7ACalcinedCheck: [6.96, 7.42],
    smectiteNatural: [13.46, 16.86],
    smectiteGlycolated: [16.06, 18.31],
    smectiteCalcined: [9.65, 10.37],
    chlorite14A: [13.58, 14.87],
    chlorite14ANatural: [13.74, 14.74],
    chlorite14AGlycolated: [13.83, 14.72],
    chlorite14ACalcined: [13.58, 14.87],
    quartz101: [3.27, 3.42],
    quartz101Natural: [3.28, 3.41],
    quartz101Glycolated: [3.28, 3.42],
    quartz101Calcined: [3.27, 3.42],
    quartz100: [4.23, 4.35],
  };
  let diagnosticPeakRulesCatalog = null;

  function catalogRangePair(rangeId, fallback) {
    const row = diagnosticPeakRulesCatalog && diagnosticPeakRulesCatalog.named_ranges && diagnosticPeakRulesCatalog.named_ranges[rangeId];
    if (!row) return fallback;
    const dMin = Number(row.d_min);
    const dMax = Number(row.d_max);
    if (!Number.isFinite(dMin) || !Number.isFinite(dMax)) return fallback;
    return [dMin, dMax];
  }

  function hydrateDiagnosticPeakRulesCatalog(payload) {
    if (!payload || payload.policy !== "argiloteca_rule_based_diagnostic") return;
    diagnosticPeakRulesCatalog = payload;
    const mapping = payload.frontend_sem_titulo_ranges || {};
    Object.keys(mapping).forEach(function (key) {
      SEM_TITULO_NGC_DIAGNOSTIC_RANGES[key] = catalogRangePair(mapping[key], SEM_TITULO_NGC_DIAGNOSTIC_RANGES[key]);
    });
  }

  if (typeof fetch === "function") {
    fetch(diagnosticPeakRulesCatalogUrl, { credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) throw new Error("diagnostic_peak_rules_catalog unavailable");
        return response.json();
      })
      .then(hydrateDiagnosticPeakRulesCatalog)
      .catch(function () {
        // O painel mantem os fallbacks locais quando o catalogo estatico ainda
        // nao foi publicado ou o navegador esta offline.
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function braggDSpacing(twoTheta, wavelength) {
    // Capitulo 3 aplicado: o difratometro mede 2θ, mas a Lei de Bragg usa θ.
    // Esta conversao divide 2θ por dois antes de calcular d = λ/(2 sen θ).
    // No JavaScript isso serve para renderizacao e evidencias. O cliente nao
    // assume Cu Kα silenciosamente: λ precisa vir dos metadados do arquivo,
    // da radiação declarada ou de parametro explicito.
    const value = Number(twoTheta);
    const lambda = Number(wavelength);
    if (!Number.isFinite(lambda) || lambda <= 0 || !Number.isFinite(value) || value <= 0) return null;
    const thetaRadians = (value / 2) * Math.PI / 180;
    const denominator = 2 * Math.sin(thetaRadians);
    if (!Number.isFinite(denominator) || denominator <= 0) return null;
    const result = lambda / denominator;
    return Number.isFinite(result) && result > 0 ? result : null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function braggTwoTheta(dSpacing, wavelength) {
    // Conversao inversa usada para transformar janelas mineralogicas em Å em
    // posicoes no eixo 2θ da visualizacao. A condicao λ/(2d) <= 1 preserva a
    // restricao geometrica de observabilidade do Capitulo 3.
    const value = Number(dSpacing);
    const lambda = Number(wavelength);
    if (!Number.isFinite(lambda) || lambda <= 0) return null;
    if (!Number.isFinite(value) || value <= 0) return null;
    const ratio = lambda / (2 * value);
    if (!Number.isFinite(ratio) || ratio <= 0 || ratio > 1) return null;
    return 2 * Math.asin(ratio) * 180 / Math.PI;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mineralSlugName(value) {
    return String(value || "").trim().toLowerCase();
  }

  function mineralClass(candidate) {
    const name = mineralSlugName(candidate && candidate.mineral);
    const group = mineralSlugName(candidate && candidate.group);
    if (isAuthorizedClayMineral(candidate) || /montmorillonite|smectite|esmectite|chlorite|kaolinite|illite|mica|muscovite|nontronite|hectorite|halloysite|sericite|saponite/.test(name + " " + group)) {
      if (/montmorillonite|smectite|esmectite|nontronite|hectorite|saponite/.test(name)) return "Argilomineral expansivo / esmectita";
      if (/chlorite|clinochlore|chamosite/.test(name)) return "Argilomineral 2:1:1";
      if (/kaolinite|halloysite|dickite|nacrite/.test(name)) return "Argilomineral 1:1";
      if (/illite|mica|muscovite|sericite|brammallite/.test(name)) return "Argilomineral micáceo";
      return "Argilomineral";
    }
    if (/calcite|dolomite|ankerite|siderite|carbonate|carbonato/.test(name + " " + group)) return "Carbonato";
    if (/albite|feldspar|feldspato|orthoclase|microcline|plagioclase/.test(name + " " + group)) return "Feldspato / silicato não argiloso";
    if (/quartz|silica|silicato/.test(name + " " + group)) return "Silicato não argiloso";
    if (/hematite|goethite|magnetite|oxide|hydroxide|óxido|oxido|hidróxido|hidroxido/.test(name + " " + group)) return "Óxido/hidróxido de ferro";
    return "Outro mineral candidato";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mineralGeologicalRole(mineralName, group) {
    const name = mineralSlugName(mineralName);
    const cls = String(group || "").toLowerCase();
    if (/calcite/.test(name)) return "Pode indicar carbonatação, cimentação carbonática, veios, componente sedimentar carbonático ou alteração hidrotermal, conforme o contexto.";
    if (/albite/.test(name)) return "Pode indicar contribuição feldspática detrítica, origem ígnea/vulcanoclástica, alteração sódica ou feldspatização.";
    if (/quartz/.test(name)) return "Componente silicático comum; pode ser detrítico, hidrotermal ou da rocha encaixante e tende a dominar alguns picos.";
    if (/montmorillonite|smectite|esmectite|nontronite|hectorite|saponite/.test(name + " " + cls)) return "Sugere fase expansiva associável a alteração de vidro vulcânico, intemperismo, diagênese inicial ou condições alcalinas, se confirmada por N/G/C.";
    if (/chlorite|clinochlore|chamosite/.test(name + " " + cls)) return "Compatível com alteração de minerais ferromagnesianos, contribuição máfica/metamórfica, hidrotermalismo ou baixo grau metamórfico.";
    if (/kaolinite|halloysite|dickite|nacrite/.test(name + " " + cls)) return "Pode indicar intemperismo ácido, lixiviação e alteração feldspática; exige atenção à sobreposição com clorita.";
    if (/illite|mica|muscovite|sericite|brammallite/.test(name + " " + cls)) return "Pode refletir contribuição detrítica micácea, maturidade diagenética ou alteração potássica.";
    if (/hematite|goethite/.test(name)) return "Pode indicar oxidação, alteração supergênica ou fases ferruginosas associadas ao sistema geológico.";
    return "Papel geológico não conclusivo com os dados disponíveis; requer integração com litologia e geoquímica.";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function confidenceRank(confidence) {
    const value = String(confidence || "").toLowerCase();
    if (value === "confirmed_by_rules") return 3;
    if (value === "probable_by_rules") return 2;
    if (value === "possible_by_rules") return 1;
    if (value.indexOf("alta") >= 0 || value === "high") return 3;
    if (value.indexOf("media") >= 0 || value.indexOf("média") >= 0 || value === "medium") return 2;
    if (value.indexOf("baixa") >= 0 || value === "low") return 1;
    return 0;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function confidenceLabel(rank) {
    if (rank >= 3) return "confirmed_by_rules";
    if (rank >= 2) return "probable_by_rules";
    if (rank >= 1) return "possible_by_rules";
    return "não informada";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function statusFromEvidence(candidate) {
    const rank = confidenceRank(candidate.confidence);
    const score = Number(candidate.score);
    if (rank >= 3 || (Number.isFinite(score) && score >= 0.75)) return "provável";
    if (rank >= 2 || (Number.isFinite(score) && score >= 0.45)) return "possível";
    return "não conclusivo";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function allCandidateRows(items) {
    const rows = [];
    items.forEach(function (item) {
      (item.mineralCandidates || []).forEach(function (candidate) {
        if (!candidate || !candidate.mineral) return;
        rows.push({ item: item, candidate: candidate });
      });
    });
    return rows;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildMineralAssembly(items) {
    const byName = new Map();
    allCandidateRows(items).forEach(function (entry) {
      const candidate = entry.candidate;
      const key = mineralSlugName(candidate.mineral);
      const current = byName.get(key) || {
        mineral: candidate.mineral,
        group: candidate.group || mineralClass(candidate),
        classLabel: mineralClass(candidate),
        treatments: new Set(),
        files: new Set(),
        bestScore: null,
        bestConfidenceRank: 0,
        bestConfidence: null,
        evidences: [],
        candidate: candidate,
        hasDiagnosticRangePeak: false,
      };
      current.treatments.add(treatmentLabel(entry.item.treatment));
      current.files.add(entry.item.metadata.original_filename || entry.item.id);
      if (typeof candidate.score === "number" && (current.bestScore === null || candidate.score > current.bestScore)) {
        current.bestScore = candidate.score;
        current.candidate = candidate;
      }
      const rank = confidenceRank(candidate.confidence);
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (rank > current.bestConfidenceRank) {
        current.bestConfidenceRank = rank;
        current.bestConfidence = candidate.confidence;
      }
      current.evidences.push(evidenceSummary(candidate));
      current.hasDiagnosticRangePeak = current.hasDiagnosticRangePeak || candidateHasDiagnosticRangePeak(candidate);
      byName.set(key, current);
    });
    return Array.from(byName.values()).sort(function (left, right) {
      return (right.bestScore || 0) - (left.bestScore || 0);
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function classifyAssemblyByClass(assembly) {
    const classes = {
      "Argilominerais": [],
      "Carbonatos": [],
      "Feldspatos/silicatos não argilosos": [],
      "Outros": [],
    };
    assembly.forEach(function (mineral) {
      if (/Argilomineral/.test(mineral.classLabel)) classes["Argilominerais"].push(mineral.mineral);
      else if (/Carbonato/.test(mineral.classLabel)) classes["Carbonatos"].push(mineral.mineral);
      else if (/Feldspato|Silicato/.test(mineral.classLabel)) classes["Feldspatos/silicatos não argilosos"].push(mineral.mineral);
      else classes["Outros"].push(mineral.mineral);
    });
    return classes;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function generalInterpretationConfidence(assembly, peakRows, items) {
    if (!assembly.length || !peakRows.length) return "baixa";
    const ranks = assembly.map(function (row) { return row.bestConfidenceRank || confidenceRank(row.bestConfidence); });
    const average = ranks.reduce(function (sum, value) { return sum + value; }, 0) / Math.max(ranks.length, 1);
    const hasNgc = items.some(function (item) { return item.treatment === "natural"; }) && items.some(function (item) { return item.treatment === "glicolado"; });
    if (average >= 2.4 && hasNgc) return "alta";
    if (average >= 1.4) return "média";
    return "baixa";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function relativeIntensityAt(item, index) {
    const values = item.intensity || [];
    const maxValue = Math.max.apply(null, values.filter(function (value) { return Number.isFinite(Number(value)); }));
    const current = Number(values[index]);
    if (!Number.isFinite(current) || !Number.isFinite(maxValue) || maxValue <= 0) return null;
    return (current / maxValue) * 100;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function simplePeakPicking(item, options) {
    // Peak picking leve no cliente para relatorio visual; nao grava resultados
    // e nao substitui a classificacao mineralogica derivada.
    const twoTheta = item.twoTheta || [];
    const intensity = item.intensity || [];
    if (twoTheta.length !== intensity.length || twoTheta.length < 5) return [];
    const settings = Object.assign({
      minRelativeIntensity: 10,
      minDistanceTwoTheta: 0.15,
      maxPeaks: 10,
    }, options || {});
    const maxValue = Math.max.apply(null, intensity.map(Number).filter(Number.isFinite));
    if (!Number.isFinite(maxValue) || maxValue <= 0) return [];
    const candidates = [];
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    for (let index = 1; index < intensity.length - 1; index += 1) {
      const prev = finiteNumber(intensity[index - 1]);
      const current = finiteNumber(intensity[index]);
      const next = finiteNumber(intensity[index + 1]);
      const theta = finiteNumber(twoTheta[index]);
      if (prev === null || current === null || next === null || theta === null) continue;
      const relative = (current / maxValue) * 100;
      if (relative < settings.minRelativeIntensity) continue;
      if (current >= prev && current >= next && (current > prev || current > next)) {
        candidates.push({
          two_theta: theta,
          d: braggDSpacingForItem(theta, item),
          intensity: current,
          relative_intensity: relative,
          index: index,
          source: "peak-picking simples",
        });
      }
    }
    candidates.sort(function (left, right) { return (right.relative_intensity || 0) - (left.relative_intensity || 0); });
    const accepted = [];
    candidates.forEach(function (peak) {
      const tooClose = accepted.some(function (row) {
        return Math.abs((row.two_theta || 0) - (peak.two_theta || 0)) < settings.minDistanceTwoTheta;
      });
      if (!tooClose && accepted.length < settings.maxPeaks) accepted.push(peak);
    });
    return accepted.sort(function (left, right) { return (left.two_theta || 0) - (right.two_theta || 0); });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function observedPeaks(item) {
    const sourcePeaks = (item.detectedPeaks || []).map(function (peak) {
      const twoTheta = Number(peak.two_theta || peak.twoTheta);
      return {
        two_theta: twoTheta,
        d: Number(peak.d || peak.d_spacing || peak.d_angstrom) || braggDSpacingForItem(twoTheta, item),
        method: peak.method || peak.detection_method || peak.algorithm,
        fwhm: peak.fwhm || peak.fwhm_2theta || peak.width,
        intensity: Number(peak.intensity),
        relative_intensity: Number(peak.relative_intensity || peak.intensity_relative),
        index: peak.index,
        source: peak.source || peak.detection_method || "picos detectados",
      };
    }).filter(isDiagnosticPeak);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (sourcePeaks.length) {
      return sourcePeaks.slice(0, 12);
    }
    return simplePeakPicking(item, { maxPeaks: 10 }).filter(isDiagnosticPeak);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function isDiagnosticPeak(peak) {
    const dValue = Number(peak && peak.d);
    return isDiagnosticPeakTwoTheta(peak && peak.two_theta) && (!Number.isFinite(dValue) || isDiagnosticPeakDSpacing(dValue));
  }

  function isDiagnosticPeakDSpacing(value) {
    const dSpacing = Number(value);
    return Number.isFinite(dSpacing) && dSpacing <= DIAGNOSTIC_PEAK_MAX_D_ANGSTROM;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function hasDiagnosticCandidate(value) {
    const text = String(value || "").trim();
    return Boolean(text && text !== "N/D");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function isDiagnosticPeakTwoTheta(value) {
    const twoTheta = Number(value);
    return Number.isFinite(twoTheta) && twoTheta >= DIAGNOSTIC_PEAK_MIN_TWO_THETA && twoTheta <= DIAGNOSTIC_PEAK_MAX_TWO_THETA;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function matchObservedDSpacing(match) {
    return Number(match && (match.observed_d || match.observed_d_angstrom || match.d || match.d_angstrom));
  }

  function matchObservedTwoTheta(match) {
    const direct = Number(match && (match.observed_two_theta || match.two_theta));
    if (Number.isFinite(direct)) return direct;
    return braggTwoTheta(matchObservedDSpacing(match));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function candidateHasDiagnosticRangePeak(candidate) {
    return (candidate && candidate.matches || []).some(function (match) {
      const observedD = matchObservedDSpacing(match);
      return isDiagnosticPeakTwoTheta(matchObservedTwoTheta(match))
        && (!Number.isFinite(observedD) || isDiagnosticPeakDSpacing(observedD));
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function matchPeakToCandidate(peak, item) {
    let best = null;
    let bestDelta = Infinity;
    (item.mineralCandidates || []).forEach(function (candidate) {
      (candidate.matches || []).forEach(function (match) {
        const observedTheta = Number(match.observed_two_theta);
        const observedD = Number(match.observed_d);
        let delta = Infinity;
        if (Number.isFinite(observedTheta) && Number.isFinite(peak.two_theta)) delta = Math.abs(observedTheta - peak.two_theta);
        else if (Number.isFinite(observedD) && Number.isFinite(peak.d)) delta = Math.abs(observedD - peak.d);
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (delta < bestDelta) {
          bestDelta = delta;
          best = { candidate: candidate, match: match };
        }
      });
    });
    if (best && bestDelta <= 0.25) return best;
    return null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function diagnosticObservation(peak, item, match) {
    const d = Number(peak.d);
    const treatment = item.treatment || "indeterminado";
    const mineral = match && match.candidate && match.candidate.mineral;
    const ranges = SEM_TITULO_NGC_DIAGNOSTIC_RANGES;
    if (Number.isFinite(d)) {
      if (d >= ranges.smectiteGlycolated[0] && d <= ranges.smectiteGlycolated[1] && treatment === "glicolado") return "Pico basal em 16,06-18,31 Å após glicolação; compatível com fase expansiva, não conclusivo isoladamente.";
      if (d >= ranges.chlorite14A[0] && d <= ranges.chlorite14A[1]) return "Reflexão basal em 13,58-14,87 Å; compatível com clorita, exige comparação N/G/C e harmônicos.";
      if (d >= ranges.illite10A[0] && d <= ranges.illite10A[1]) return "Reflexão em 9,73-10,38 Å; compatível com ilita/mica se persistente e sem expansão.";
      if (d >= ranges.kaolinite7A[0] && d <= ranges.kaolinite7A[1]) return "Reflexão em 6,96-7,42 Å; compatível com caulinita/clorita, atenção à sobreposição.";
      if (d >= 3.0 && d <= 3.1 && /calcite/i.test(mineral || "")) return "Pico forte compatível com calcita quando acompanhado por outros picos de carbonato.";
      if (d >= 3.15 && d <= 3.25 && /albite|feldspar/i.test(mineral || "")) return "Pico compatível com feldspato; pode sobrepor fases silicáticas.";
    }
    return match ? "Pico usado no casamento com candidato mineral; requer revisão do padrão completo." : "Pico observado sem associação mineral diagnóstica automática.";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildPeakRows(items) {
    const rows = [];
    items.forEach(function (item) {
      const peaks = observedPeaks(item);
      if (!peaks.length) {
        rows.push({
          treatment: treatmentLabel(item.treatment),
          sample: sampleLabel(item),
          file: item.metadata.original_filename || item.id,
          twoTheta: null,
          d: null,
          relativeIntensity: null,
          mineral: "N/D",
          reflection: "N/D",
          observation: "Dados insuficientes para peak-picking defensivo.",
          confidence: "baixa",
        });
        return;
      }
      peaks.filter(isDiagnosticPeak).slice(0, 8).forEach(function (peak) {
        const match = matchPeakToCandidate(peak, item);
        rows.push({
          treatment: treatmentLabel(item.treatment),
          sample: sampleLabel(item),
          file: item.metadata.original_filename || item.id,
          twoTheta: peak.two_theta,
          d: peak.d,
          relativeIntensity: Number.isFinite(peak.relative_intensity) ? peak.relative_intensity : relativeIntensityAt(item, peak.index),
          mineral: match && match.candidate ? match.candidate.mineral : "N/D",
          reflection: match && match.match && match.match.reference_d ? "d ref. " + formatNumber(match.match.reference_d, 2) + " Å" : "N/D",
          observation: diagnosticObservation(peak, item, match),
          confidence: match && match.candidate ? (match.candidate.confidence || "não informada") : "baixa",
        });
      });
    });
    return rows.sort(function (left, right) {
      return String(left.sample).localeCompare(String(right.sample)) || String(left.treatment).localeCompare(String(right.treatment)) || ((left.twoTheta || 0) - (right.twoTheta || 0));
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function methodPayload(item) {
    const diffractogram = item.diffractogram || {};
    const metadata = item.metadata || {};
    const xrdMethod = diffractogram.xrd_method || metadata.xrd_method || (item.advancedSummary && item.advancedSummary.xrd_method) || {};
    const peakProcessing = diffractogram.peak_processing || metadata.peak_processing || (item.advancedSummary && item.advancedSummary.peak_processing) || {};
    return {
      xrdMethod: xrdMethod,
      peakProcessing: peakProcessing,
      wavelength: Number(xrdMethod.wavelength_angstrom || metadata.wavelength_angstrom || CU_K_ALPHA_WAVELENGTH),
      wavelengthAssumed: xrdMethod.wavelength_assumed !== false && !metadata.wavelength_angstrom,
      parser: xrdMethod.parser || metadata.parser || metadata.raw_parser || "argiloteca_internal",
      detection: peakDetectionDescription(peakProcessing.peak_detection_method),
      fit: peakProcessing.fit_method || "lmfit PseudoVoigt quando disponível; fallback por máximo local na janela",
      fwhmPolicy: peakProcessing.fwhm_policy || "FWHM (Full Width at Half Maximum; largura total à meia altura) estimado em 2θ; no fallback, não corrige a função instrumental.",
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function peakDetectionDescription(value) {
    const text = String(value || "").trim();
    const normalized = text.toLowerCase();
    if (!text || normalized === "scipy.signal.find_peaks" || normalized === "find_peaks" || /scipy.*find_peaks/.test(normalized)) {
      return PEAK_DETECTION_DESCRIPTION;
    }
    return text;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderMethodologyLimitations(items) {
    if (!DRX_SHOW_METHODOLOGY_LIMITATIONS) return "";
    const methods = items.length ? items.map(methodPayload) : [methodPayload({})];
    const wavelengths = Array.from(new Set(methods.map(function (method) {
      return formatNumber(method.wavelength, 5) + " Å" + (method.wavelengthAssumed ? " assumido" : " informado");
    })));
    const parsers = Array.from(new Set(methods.map(function (method) { return method.parser; }).filter(Boolean))).slice(0, 6);
    const detections = Array.from(new Set(methods.map(function (method) { return method.detection; }).filter(Boolean))).slice(0, 4);
    const fits = Array.from(new Set(methods.map(function (method) { return method.fit; }).filter(Boolean))).slice(0, 4);
    const fwhmPolicies = Array.from(new Set(methods.map(function (method) { return method.fwhmPolicy; }).filter(Boolean))).slice(0, 4);
    return [
      "<section class='compact-section'><h2>Base metodológica e limitações</h2>",
      "<p>A conversão entre 2θ e d-spacing usa a lei de Bragg, <strong>λ = 2 d sinθ</strong>, com θ igual à metade de 2θ. O registro abaixo documenta as premissas usadas na leitura dos RAW selecionados.</p>",
      "<table class='compact-table'><thead><tr><th>Aspecto</th><th>Registro metodológico</th></tr></thead><tbody>",
      "<tr><td>Comprimento de onda</td><td>", escapeHtml(wavelengths.join("; ") || "1,54056 Å assumido"), "</td></tr>",
      "<tr><td>Leitura RAW/parser</td><td>", escapeHtml(parsers.join("; ") || "N/D"), "</td></tr>",
      "<tr><td>Método de pico</td><td>", escapeHtml(detections.join("; ") || "N/D"), "</td></tr>",
      "<tr><td>Ajuste/perfil</td><td>", escapeHtml(fits.join("; ") || "N/D"), "</td></tr>",
      "<tr><td>FWHM e intensidade</td><td>", escapeHtml(fwhmPolicies.join("; ") || "FWHM (Full Width at Half Maximum; largura total à meia altura) e intensidades relativas não equivalem a quantificação modal."), "</td></tr>",
      "</tbody></table>",
      "<p class='note warning'>FWHM significa Full Width at Half Maximum, em português largura total à meia altura. Em DRX, é a largura do pico em 2θ medida nos dois pontos onde a intensidade vale metade da intensidade máxima. Picos mais largos podem indicar cristalitos menores, microdeformação, defeitos estruturais ou alargamento instrumental. Para cálculos como Scherrer, D = Kλ/(β cosθ), β é o FWHM em radianos e deve estar corrigido pelo alargamento instrumental. Intensidades relativas podem ser afetadas por orientação preferencial, preparo da lâmina, background, sobreposição de picos e faixa angular medida. Reflexões esperadas fora da faixa escaneada devem ser tratadas como não medidas, não como ausentes.</p>",
      "</section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mainEvidences(peakRows, assembly) {
    const contextMineralSlug = currentArgilomineralSlug();
    const clayMinerals = (assembly || [])
      .filter(function (row) { return isAuthorizedClayMineral(row.candidate); })
      .sort(function (left, right) {
        const leftScore = Number(left.bestScore);
        const rightScore = Number(right.bestScore);
        if (!Number.isFinite(leftScore) && !Number.isFinite(rightScore)) return 0;
        if (!Number.isFinite(leftScore)) return 1;
        if (!Number.isFinite(rightScore)) return -1;
        return rightScore - leftScore;
      });
    const preferredClayMinerals = contextMineralSlug
      ? clayMinerals.filter(function (row) { return candidateMatchesMineralSlug(row.candidate, contextMineralSlug); })
      : [];
    const bestClayMineral = preferredClayMinerals[0] || clayMinerals[0];
    if (!bestClayMineral) return [];
    const evidence = (bestClayMineral.evidences || []).filter(Boolean)[0] || "evidência DRX não informada";
    return [
      mineralLink(bestClayMineral.mineral)
        + " (" + escapeHtml(bestClayMineral.classLabel || bestClayMineral.group || "Argilomineral") + ")"
        + ", confiança " + escapeHtml(bestClayMineral.bestConfidence || confidenceLabel(bestClayMineral.bestConfidenceRank))
        + ". " + escapeHtml(evidence),
    ];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function interpretationUncertainties(assembly, peakRows, items) {
    const rows = [];
    if (assembly.some(function (row) { return row.bestConfidenceRank <= 1; })) rows.push("Há candidatos com confiança baixa ou não informada.");
    if (!peakRows.length || peakRows.every(function (row) { return row.twoTheta === null; })) rows.push("Tabela de picos insuficiente para diagnóstico robusto.");
    if (!items.some(function (item) { return item.treatment === "glicolado"; })) rows.push("Ausência de glicolação limita diagnóstico de argilas expansivas.");
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!items.some(function (item) { return item.treatment === "calcinado"; })) rows.push("Ausência de calcinação limita confirmação de colapso/estabilidade basal.");
    rows.push("Sobreposição de picos pode afetar a atribuição mineralógica.");
    return Array.from(new Set(rows));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function recommendationsFor(items, assembly) {
    const rows = [
      "Revisar manualmente os principais picos e suas sobreposições.",
      "Comparar lâminas natural, glicolada e calcinada sempre que disponíveis.",
      "Integrar DRX com litologia, descrição macroscópica, profundidade e geoquímica.",
    ];
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!items.some(function (item) { return item.treatment === "calcinado"; })) rows.push("Adicionar preparo calcinado para testar colapso/estabilidade de picos basais.");
    return rows;
  }

  function interpretationPeakEvidenceRows(peakRows, selectedMineral) {
    if (!selectedMineral) return ["Nenhum argilomineral principal foi definido para justificar os picos."];
    const targetSlug = resolveMineralSlug(selectedMineral.mineral) || mineralSlug(selectedMineral.mineral);
    const rows = (peakRows || [])
      .filter(function (row) {
        return row.twoTheta !== null
          && hasDiagnosticCandidate(row.mineral)
          && candidateMatchesMineralSlug({ mineral: row.mineral }, targetSlug);
      })
      .slice(0, 3)
      .map(function (row) {
        const observation = row.observation && row.observation !== "N/D" && row.observation.indexOf("Pico usado no casamento") !== 0
          ? row.observation
          : "";
        return [
          row.treatment + ": d obs. " + formatNumber(row.d, 3) + " Å",
          "2θ obs. " + formatNumber(row.twoTheta, 2) + "°",
          row.reflection && row.reflection !== "N/D" ? row.reflection : "",
          observation,
        ].filter(Boolean).join("; ");
      });
    if (rows.length) return rows;
    const evidence = (selectedMineral.evidences || []).filter(Boolean)[0] || evidenceSummary(selectedMineral.candidate);
    return [evidence || "Nenhum pico casado foi encontrado na faixa diagnóstica exibida."];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function treatmentCoverageText(items) {
    const treatments = Array.from(new Set((items || []).map(function (item) {
      return treatmentLabel(item.treatment);
    }).filter(Boolean)));
    return treatments.length ? treatments.join(", ") : "tratamentos não informados";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function interpretationNgcEvidenceRows(items, selectedMineral) {
    const targetSlug = resolveMineralSlug(selectedMineral && selectedMineral.mineral) || mineralSlug(selectedMineral && selectedMineral.mineral);
    const rows = [];
    const groups = buildNgcGroups(items || []);
    const completeGroups = groups.filter(function (group) {
      return group.natural.length && group.glicolada.length && group.calcinada.length;
    });
    (completeGroups.length ? completeGroups : groups).forEach(function (group) {
      const groupItems = [].concat(group.natural, group.glicolada, group.calcinada).filter(Boolean);
      if (!groupItems.length) return;
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (targetSlug) {
        const groupHasMineral = buildMineralAssembly(groupItems).some(function (row) {
          return candidateMatchesMineralSlug(row.candidate, targetSlug);
        });
        if (!groupHasMineral) return;
      }
      const scoreDetails = buildNgcTrajectoryScore(group);
      const hypotheses = (scoreDetails.hypotheses || []).slice(0, 2).join("; ");
      rows.push(
        group.sampleBase + ": " + selectedNgcCurveComparisonText(scoreDetails)
        + (hypotheses ? ". Leitura N/G/C: " + hypotheses : "")
      );
    });
    if (rows.length) return rows.slice(0, 1);
    return [
      "Tratamentos disponíveis: " + treatmentCoverageText(items) + ". Comparação N/G/C completa não está disponível para sustentar deslocamento, expansão, colapso ou estabilidade basal deste candidato.",
    ];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function interpretationHtmlList(rows) {
    return rows && rows.length
      ? "<ul>" + rows.map(function (row) { return "<li>" + escapeHtml(row) + "</li>"; }).join("") + "</ul>"
      : "<p>N/D</p>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function interpretationRelationRow(label, html) {
    return "<tr><th>" + escapeHtml(label) + "</th><td>" + html + "</td></tr>";
  }

  function renderInterpretationRelationRows(items, assembly, peakRows) {
    const selectedMineral = bestClayMineralFromAssembly(assembly);
    const uncertainties = interpretationUncertainties(assembly, peakRows, items)
      .concat(["Dados comparados com WebMineral como fallback/comparação; falta comparar com a composição química."])
      .slice(0, 5);
    const suggestedMineral = selectedMineral
      ? mineralLink(selectedMineral.mineral)
        + " · " + escapeHtml(interpretationStrengthLabel(selectedMineral))
        + " · confiança " + escapeHtml(selectedMineral.bestConfidence || confidenceLabel(selectedMineral.bestConfidenceRank))
      : "N/D";
    return [
      interpretationRelationRow("Argilomineral sugerido", suggestedMineral),
      interpretationRelationRow("Picos que sustentam", interpretationHtmlList(interpretationPeakEvidenceRows(peakRows, selectedMineral))),
      interpretationRelationRow("Comportamento N/G/C", interpretationHtmlList(interpretationNgcEvidenceRows(items, selectedMineral))),
      interpretationRelationRow("Candidatos alternativos", alternativeClayMineralsHtml(assembly, selectedMineral)),
      interpretationRelationRow("Limitação da leitura", interpretationHtmlList(uncertainties)),
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function abundanceClass(mineral) {
    const score = Number(mineral.bestScore);
    const occurrences = mineral.treatments ? mineral.treatments.size : 0;
    if (Number.isFinite(score) && score >= 0.75 && occurrences >= 2) return "dominante/maior";
    if (Number.isFinite(score) && score >= 0.55) return "maior";
    if (Number.isFinite(score) && score >= 0.30) return "subordinado";
    if (Number.isFinite(score)) return "traço";
    return "indeterminado";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function geologicalInterpretationText(assembly) {
    if (!assembly.length) return "Não há candidatos mineralógicos suficientes para interpretação preliminar.";
    const sentences = [];
    assembly.forEach(function (mineral) {
      sentences.push(mineral.mineral + ": " + mineralGeologicalRole(mineral.mineral, mineral.classLabel));
    });
    return sentences.slice(0, 7).join(" ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function geologicalInterpretationHtml(assembly) {
    if (!assembly.length) return escapeHtml(geologicalInterpretationText(assembly));
    return assembly.slice(0, 7).map(function (mineral) {
      return mineralLink(mineral.mineral) + ": " + linkKnownMineralText(mineralGeologicalRole(mineral.mineral, mineral.classLabel));
    }).join(" ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function isAuthorizedClayMineral(candidate) {
    return Boolean(resolveMineralSlug(candidate && candidate.mineral));
  }

  function otherMineralsSummary(minerals) {
    const others = minerals.filter(function (candidate) {
      return !isAuthorizedClayMineral(candidate);
    });
    if (!others.length) return "";
    const rows = others.slice(0, 12).map(function (candidate) {
      return [
        "<li>",
        mineralLink(candidate.mineral || "Mineral candidato"),
        " · ", escapeHtml(formatScore(candidate.score)),
        candidate.confidence ? " · " + escapeHtml(candidate.confidence) : "",
        "</li>",
      ].join("");
    }).join("");
    return [
      "<section class='other-minerals'>",
      "<h2>Minerais candidatos fora do vocabulário de argilominerais</h2>",
      "<p>Estes nomes apareceram nos candidatos de DRX, mas não foram descritos neste relatório porque não pertencem ao vocabulário autorizado de argilominerais da Argiloteca.</p>",
      "<ul>", rows, "</ul>",
      others.length > 12 ? "<p>Outros " + escapeHtml(others.length - 12) + " candidato(s) foram omitidos para manter o PDF sintético.</p>" : "",
      "</section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function reportRows(items) {
    return items.map(function (item) {
      return [
        "<tr>",
        "<td>", escapeHtml(sampleLabel(item)), "</td>",
        "<td>", escapeHtml(item.metadata.original_filename || item.id), "</td>",
        "<td>", escapeHtml(treatmentLabel(item.treatment)), "</td>",
        "<td>", mineralListLinks((item.mineralCandidates || []).slice(0, 3).map(function (candidate) { return candidate.mineral; }), "Sem candidato"), "</td>",
        "</tr>",
      ].join("");
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function truncateReportText(value, maxLength) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    const limit = maxLength || 520;
    if (text.length <= limit) return text;
    return text.slice(0, limit - 1).trim() + "...";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function reportSampleSummary(items) {
    const rows = items.map(function (item) {
      const candidates = (item.mineralCandidates || [])
        .slice(0, 2)
        .map(function (candidate) { return candidate.mineral; })
        .filter(Boolean)
        .join(", ");
      return [
        "<li><strong>", escapeHtml(sampleLabel(item)), "</strong>",
        " · ", escapeHtml(treatmentLabel(item.treatment)),
        " · ", escapeHtml(item.metadata.original_filename || item.id),
        candidates ? " · candidatos: " + escapeHtml(candidates) : "",
        "</li>",
      ].join("");
    }).join("");
    return rows ? "<ul class='sample-list'>" + rows + "</ul>" : "";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function styledReportSvg() {
    const svg = chartEl.cloneNode(true);
    svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    svg.setAttribute("width", "960");
    svg.setAttribute("height", "520");
    svg.setAttribute("style", "background:#ffffff;border:1px solid #d8e1dd;border-radius:8px;");
    const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
    style.textContent = [
      ".argilo-drx__grid{stroke:#d8e1dd;stroke-width:1;opacity:.9}",
      ".argilo-drx__axis{stroke:#6f827b;stroke-width:1.3}",
      ".argilo-drx__curve{fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-width:2.2}",
      "text{fill:#4f625c;font-family:Arial,sans-serif;font-size:13px}",
    ].join("");
    svg.insertBefore(style, svg.firstChild);
    Array.from(svg.querySelectorAll(".argilo-drx__curve")).forEach(function (curve, index) {
      if (!curve.getAttribute("stroke")) curve.setAttribute("stroke", palette[index % palette.length]);
      curve.setAttribute("stroke-width", "2.2");
      curve.setAttribute("fill", "none");
    });
    Array.from(svg.querySelectorAll("text")).forEach(function (text) {
      text.setAttribute("fill", text.getAttribute("fill") || "#4f625c");
      text.setAttribute("font-family", "Arial, sans-serif");
    });
    return svg.outerHTML;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function reportCurveData(item, minTheta, maxTheta) {
    const rows = [];
    const maxIntensity = Math.max.apply(null, (item.intensity || []).map(Number).filter(Number.isFinite));
    (item.twoTheta || []).forEach(function (theta, index) {
      const x = Number(theta);
      const y = Number((item.intensity || [])[index]);
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;
      if (x < minTheta || x > maxTheta) return;
      rows.push({ x: x, y: maxIntensity > 0 ? y / maxIntensity : y });
    });
    return rows;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function lowAngleReportSvg(items, peakRows) {
    const width = 960;
    const height = 300;
    const margin = { left: 56, right: 24, top: 34, bottom: 44 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;
    const minTheta = 2;
    const maxTheta = 12;
    const yMax = Math.max(1, items.length || 1);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    function xScale(value) {
      return margin.left + ((value - minTheta) / (maxTheta - minTheta)) * plotW;
    }
    function yScale(value, offset) {
      return margin.top + plotH - ((value + offset) / yMax) * plotH;
    }
    const paths = [];
    items.forEach(function (item, index) {
      const rows = reportCurveData(item, minTheta, maxTheta);
      if (!rows.length) return;
      const offset = index * 0.85;
      const d = rows.map(function (row, rowIndex) {
        return (rowIndex ? "L" : "M") + xScale(row.x).toFixed(2) + "," + yScale(row.y * 0.75, offset).toFixed(2);
      }).join(" ");
      paths.push("<path d='" + d + "' fill='none' stroke='" + palette[index % palette.length] + "' stroke-width='2'/>");
      paths.push("<text x='" + (margin.left + 4) + "' y='" + yScale(0.78, offset).toFixed(2) + "'>" + escapeHtml(sampleLabel(item) + " · " + treatmentLabel(item.treatment)) + "</text>");
    });
    const markers = peakRows.filter(function (row) {
      return Number.isFinite(row.twoTheta) && row.twoTheta >= minTheta && row.twoTheta <= maxTheta && Number.isFinite(row.d);
    }).slice(0, 12).map(function (row, index) {
      const x = xScale(row.twoTheta);
      const y = margin.top + 18 + (index % 4) * 18;
      return [
        "<line x1='", x.toFixed(2), "' y1='", margin.top, "' x2='", x.toFixed(2), "' y2='", margin.top + plotH, "' stroke='#9a6a2f' stroke-width='1' stroke-dasharray='4 4'/>",
        "<text x='", Math.min(width - 120, x + 4).toFixed(2), "' y='", y, "' fill='#5c3f1e'>d ", escapeHtml(formatNumber(row.d, 2)), " Å</text>",
      ].join("");
    }).join("");
    const ticks = [2, 4, 6, 8, 10, 12].map(function (tick) {
      const x = xScale(tick);
      return "<line x1='" + x + "' y1='" + (margin.top + plotH) + "' x2='" + x + "' y2='" + (margin.top + plotH + 5) + "' stroke='#6f827b'/><text x='" + (x - 8) + "' y='" + (height - 18) + "'>" + tick + "</text>";
    }).join("");
    return [
      "<svg xmlns='http://www.w3.org/2000/svg' width='960' height='300' viewBox='0 0 960 300' style='background:#fff;border:1px solid #d8e1dd;border-radius:8px'>",
      "<style>text{font-family:Arial,sans-serif;font-size:12px;fill:#4f625c}.title{font-size:16px;font-weight:bold;fill:#243c37}</style>",
      "<text class='title' x='56' y='22'>Ampliação interpretativa: baixos ângulos (2-12° 2θ)</text>",
      "<rect x='", margin.left, "' y='", margin.top, "' width='", plotW, "' height='", plotH, "' fill='#fbfdfc' stroke='#d8e1dd'/>",
      paths.join(""),
      markers,
      ticks,
      "<text x='", margin.left + plotW / 2 - 26, "' y='", height - 4, "'>2θ (°)</text>",
      "<text x='8' y='160' transform='rotate(-90 8 160)'>Intensidade normalizada</text>",
      "</svg>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function htmlList(rows) {
    return rows && rows.length ? "<ul>" + rows.map(function (row) { return "<li>" + escapeHtml(row) + "</li>"; }).join("") + "</ul>" : "<p>N/D</p>";
  }

  function htmlListLinked(rows) {
    return rows && rows.length ? "<ul>" + rows.map(function (row) { return "<li>" + row + "</li>"; }).join("") + "</ul>" : "<p>N/D</p>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderExecutiveSummary(items, assembly, peakRows) {
    const classes = classifyAssemblyByClass(assembly);
    const treatments = Array.from(new Set(items.map(function (item) { return treatmentLabel(item.treatment); }))).join(", ") || "N/D";
    const sampleGroups = Array.from(new Set(buildNgcGroups(items).map(function (group) {
      return group.sampleBase;
    }))).join(", ") || Array.from(new Set(items.map(sampleLabel))).join(", ");
    const clayMinerals = clayMineralsFromAssembly(assembly).map(function (row) { return row.mineral; });
    const nonClayGroups = [
      classes["Carbonatos"].length ? "Carbonatos: " + classes["Carbonatos"].join(", ") : "",
      classes["Feldspatos/silicatos não argilosos"].length ? "Feldspatos/silicatos não argilosos: " + classes["Feldspatos/silicatos não argilosos"].join(", ") : "",
      classes["Outros"].length ? "Outros: " + classes["Outros"].join(", ") : "",
    ].filter(Boolean).join("; ");
    return [
      "<section class='summary-box'><h2>Leitura do Arquivo</h2>",
      "<table class='compact-table'><tbody>",
      "<tr><th>Amostra/grupo</th><td>", escapeHtml(sampleGroups || "N/D"), "</td></tr>",
      "<tr><th>Tratamentos disponíveis</th><td>", escapeHtml(treatments), "</td></tr>",
      "<tr><th>Possíveis Argilominerais</th><td>", mineralListLinks(clayMinerals, "N/D"), "</td></tr>",
      nonClayGroups ? "<tr><th>Fases não argilosas</th><td>" + escapeHtml(nonClayGroups) + "</td></tr>" : "",
      "<tr><th>Confiança geral</th><td>", escapeHtml(generalInterpretationConfidence(assembly, peakRows, items)), "</td></tr>",
      renderInterpretationRelationRows(items, assembly, peakRows),
      "</tbody></table>",
      "</section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function sampleBaseForNgc(item) {
    const treatment = String(item && item.treatment || "").toLowerCase();
    const raw = String(
      (item.sample && item.sample.sample_base)
      || item.sampleBase
      || item.sampleCode
      || (item.metadata && item.metadata.sample_code)
      || sampleLabel(item)
      || ""
    ).trim();
    let base = raw
      .replace(/\.[^.]+$/, "")
      .replace(/[\s_-]*\(?\b(N|G|C|NAT|NATURAL|GLY|GLICOL|GLICOLADA|CAL|CALC|CALCINADA)\b\)?$/i, "")
      .replace(/\s+/g, " ")
      .trim() || raw;
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    const suffix = treatment === "natural"
      ? "N"
      : (treatment === "glicolado" || treatment === "glicolada"
        ? "G"
        : (treatment === "calcinado" || treatment === "calcinada" ? "C" : ""));
    if (suffix && base.length > 4 && base.toUpperCase().endsWith(suffix)) {
      const candidateBase = base.slice(0, -1).trim();
      if (/[0-9A-Z]$/i.test(candidateBase)) base = candidateBase;
    }
    return base;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildNgcGroups(items) {
    const groups = new Map();
    items.forEach(function (item) {
      const base = sampleBaseForNgc(item);
      const group = groups.get(base) || { sampleBase: base, natural: [], glicolada: [], calcinada: [], indeterminado: [] };
      const prep = item.treatment || "indeterminado";
      if (prep === "natural") group.natural.push(item);
      else if (prep === "glicolado" || prep === "glicolada") group.glicolada.push(item);
      else if (prep === "calcinado" || prep === "calcinada") group.calcinada.push(item);
      else group.indeterminado.push(item);
      groups.set(base, group);
    });
    return Array.from(groups.values());
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function preparationStage(item) {
    const treatment = String(item && item.treatment || "").toLowerCase();
    const text = [
      item && item.sampleCode,
      item && item.sample && item.sample.sample_code,
      item && item.metadata && item.metadata.original_filename,
      item && item.metadata && item.metadata.sample_code,
      item && item.id,
    ].filter(Boolean).join(" ").toUpperCase();
    if (treatment === "natural") return "AD/Natural";
    if (treatment === "glicolado" || treatment === "glicolada") return "EG/Glicolado";
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (treatment === "calcinado" || treatment === "calcinada") {
      if (/\bH?400C?\b|[\s_-]400[\s_-]?C?\b/.test(text)) return "H400";
      if (/\bH?550C?\b|[\s_-]550[\s_-]?C?\b/.test(text)) return "H550";
      if (/\bH?500C?\b|[\s_-]500[\s_-]?C?\b/.test(text)) return "H500";
      return "H/Calcinado";
    }
    return "Indeterminado";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function stageLabelForCell(item) {
    return item ? preparationStage(item) + " · " + escapeHtml(item.metadata && item.metadata.original_filename || sampleLabel(item)) : "N/D";
  }

  function formatPeakCell(peak) {
    if (!peak) return "N/D";
    return [
      "d ", formatNumber(Number(peak.d), 2), " Å",
      " / 2θ ", formatNumber(Number(peak.two_theta), 2), "°",
      Number.isFinite(Number(peak.relative_intensity)) ? " / I rel. " + formatNumber(Number(peak.relative_intensity), 1) + "%" : "",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildBasalTrajectoryRows(items) {
    const ranges = SEM_TITULO_NGC_DIAGNOSTIC_RANGES;
    return buildNgcGroups(items).map(function (group) {
      const natural = group.natural[0] || null;
      const glicolada = group.glicolada[0] || null;
      const calcinada = group.calcinada[0] || null;
      const nPeak = strongestPeakInDRange(natural, ranges.smectiteNatural[0], ranges.smectiteNatural[1])
        || strongestPeakInDRange(natural, ranges.chlorite14ANatural[0], ranges.chlorite14ANatural[1])
        || strongestPeakInDRange(natural, ranges.illite10ANatural[0], ranges.illite10ANatural[1]);
      const gPeak = strongestPeakInDRange(glicolada, ranges.smectiteGlycolated[0], ranges.smectiteGlycolated[1])
        || strongestPeakInDRange(glicolada, ranges.chlorite14AGlycolated[0], ranges.chlorite14AGlycolated[1])
        || strongestPeakInDRange(glicolada, ranges.illite10AGlycolated[0], ranges.illite10AGlycolated[1]);
      const cPeak = strongestPeakInDRange(calcinada, ranges.smectiteCalcined[0], ranges.smectiteCalcined[1])
        || strongestPeakInDRange(calcinada, ranges.chlorite14ACalcined[0], ranges.chlorite14ACalcined[1])
        || strongestPeakInDRange(calcinada, ranges.kaolinite7ACalcinedCheck[0], ranges.kaolinite7ACalcinedCheck[1]);
      const nD = nPeak ? Number(nPeak.d) : null;
      const gD = gPeak ? Number(gPeak.d) : null;
      const cD = cPeak ? Number(cPeak.d) : null;
      const flags = [];
      if (!natural) flags.push("MISSING_NATURAL");
      if (!glicolada) flags.push("MISSING_GLYCOLATED");
      if (!calcinada) flags.push("MISSING_CALCINED");
      let interpretation = "evidência insuficiente; interpretação assistida, pendente de curadoria";
      let confidence = "baixa";
      if (Number.isFinite(nD) && Number.isFinite(gD) && Number.isFinite(cD) && gD >= ranges.smectiteGlycolated[0] && gD <= ranges.smectiteGlycolated[1] && cD >= ranges.smectiteCalcined[0] && cD <= ranges.smectiteCalcined[1]) {
        interpretation = "compatível com argilomineral expansivo: expansão em EG e colapso térmico observado";
        confidence = "alta";
        flags.push("POSSIBLE_EXPANSIVE_CLAY");
      } else if (Number.isFinite(gD) && gD >= ranges.smectiteGlycolated[0] && gD <= ranges.smectiteGlycolated[1]) {
        interpretation = "compatível com fase expansiva após glicolação; requer comparação térmica completa";
        confidence = calcinada ? "média" : "baixa";
        flags.push("POSSIBLE_EXPANSIVE_CLAY");
      } else if ([nD, gD, cD].filter(function (d) { return Number.isFinite(d) && d >= ranges.illite10A[0] && d <= ranges.illite10A[1]; }).length >= 2) {
        interpretation = "compatível com ilita/mica se o pico ~10 Å for estável entre tratamentos";
        confidence = "média";
      } else if ([nD, gD, cD].filter(function (d) { return Number.isFinite(d) && d >= ranges.chlorite14A[0] && d <= ranges.chlorite14A[1]; }).length >= 2) {
        interpretation = "compatível com clorita/vermiculita; diferenciar com harmônicos e resposta ao aquecimento";
        confidence = "média";
        flags.push("POSSIBLE_CHLORITE_KAOLINITE_OVERLAP");
      }
      if (confidence === "baixa") flags.push("LOW_CONFIDENCE");
      return {
        sampleBase: group.sampleBase,
        naturalPeak: nPeak,
        glycolatedPeak: gPeak,
        calcinedPeak: cPeak,
        shiftNG: Number.isFinite(nD) && Number.isFinite(gD) ? gD - nD : null,
        shiftGC: Number.isFinite(gD) && Number.isFinite(cD) ? cD - gD : null,
        interpretation: interpretation,
        confidence: confidence,
        flags: Array.from(new Set(flags)),
      };
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mineralReflectionRules() {
    if (
      diagnosticPeakRulesCatalog
      && Array.isArray(diagnosticPeakRulesCatalog.frontend_mineral_reflection_rules)
      && diagnosticPeakRulesCatalog.frontend_mineral_reflection_rules.length
    ) {
      return diagnosticPeakRulesCatalog.frontend_mineral_reflection_rules.map(function (rule) {
        const fallback = [
          Number(rule.d_min),
          Number(rule.d_max),
        ];
        const fallbackRange = Number.isFinite(fallback[0]) && Number.isFinite(fallback[1]) ? fallback : [null, null];
        const pair = rule.range ? catalogRangePair(rule.range, fallbackRange) : fallbackRange;
        return {
          mineral: rule.mineral,
          reflection: rule.reflection,
          target: rule.target,
          min: pair[0],
          max: pair[1],
          required: rule.required || "",
          note: rule.note || "",
        };
      }).filter(function (rule) {
        return Number.isFinite(rule.min) && Number.isFinite(rule.max);
      });
    }
    return [
      { mineral: "Esmectita/montmorilonita", reflection: "001 em EG", target: 17.0, min: 16.6, max: 18.6, required: "EG/Glicolado", note: "expansão após glicolação; requer trajetória AD→EG→H" },
      { mineral: "Esmectita/montmorilonita", reflection: "001 natural", target: 15.0, min: 13.0, max: 16.5, required: "AD/Natural", note: "basal variável; não conclusivo isoladamente" },
      { mineral: "Esmectita/montmorilonita", reflection: "colapso aquecido", target: 10.0, min: 9.4, max: 10.4, required: "H/Calcinado", note: "colapso térmico próximo de 10 A reforça fase expansiva" },
      { mineral: "Ilita/mica", reflection: "001", target: 10.0, min: 9.7, max: 10.4, required: "", note: "estabilidade entre tratamentos reforça hipótese" },
      { mineral: "Ilita/mica", reflection: "002", target: 5.03, min: 4.85, max: 5.2, required: "", note: "reflexão confirmatória de suporte" },
      { mineral: "Ilita/mica", reflection: "003", target: 3.35, min: 3.28, max: 3.42, required: "", note: "pode sobrepor quartzo/feldspatos; revisar" },
      { mineral: "Clorita", reflection: "001", target: 14.2, min: 13.7, max: 14.6, required: "", note: "pico basal característico; deve sobreviver ao aquecimento e não expandir como esmectita em EG" },
      { mineral: "Clorita", reflection: "002", target: 7.0, min: 6.9, max: 7.8, required: "", note: "sobrepõe caulinita; usar 14 A, 4,7 A e 3,5 A" },
      { mineral: "Clorita", reflection: "003/004", target: 3.5, min: 3.45, max: 3.65, required: "", note: "reflexão de suporte, atenção à caulinita" },
      { mineral: "Clorita", reflection: "harmônico", target: 4.7, min: 4.55, max: 4.9, required: "", note: "reflexão confirmatória de suporte" },
      { mineral: "Caulinita", reflection: "001", target: 7.18, min: 6.9, max: 7.8, required: "", note: "sobrepõe clorita; aquecimento H550 ajuda" },
      { mineral: "Caulinita", reflection: "002", target: 3.58, min: 3.5, max: 3.65, required: "", note: "usar junto com 7,18 A e resposta térmica" },
      { mineral: "Vermiculita", reflection: "001 natural", target: 14.0, min: 13.4, max: 14.8, required: "AD/Natural", note: "14 A sem expansão em EG e colapso térmico apoiam hipótese" },
      { mineral: "Vermiculita", reflection: "sem expansão em EG", target: 14.0, min: 13.4, max: 14.8, required: "EG/Glicolado", note: "permanência em ~14 A após EG diferencia de esmectita expansiva" },
      { mineral: "Vermiculita", reflection: "colapso aquecido", target: 10.0, min: 9.5, max: 10.5, required: "H/Calcinado", note: "colapso térmico deve ser revisado com protocolo de aquecimento" },
    ];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildConfirmatoryReflectionRows(items) {
    return mineralReflectionRules().map(function (rule) {
      const matches = [];
      items.forEach(function (item) {
        const stage = preparationStage(item);
        if (!stageMatches(rule.required, stage)) return;
        const peak = strongestPeakInDRange(item, rule.min, rule.max);
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (peak) {
          matches.push({
            stage: stage,
            file: item.metadata && item.metadata.original_filename || sampleLabel(item),
            peak: peak,
          });
        }
      });
      let status = "não observado";
      let confidence = "baixa";
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (matches.length >= 2) {
        status = "evidência de suporte";
        confidence = "média";
      } else if (matches.length === 1) {
        status = "observação isolada";
      }
      return {
        mineral: rule.mineral,
        reflection: rule.reflection,
        expected: formatNumber(rule.min, 2) + "-" + formatNumber(rule.max, 2) + " Å",
        observed: matches.map(function (match) {
          return match.stage + ": " + formatPeakCell(match.peak);
        }).join("; ") || "N/D",
        files: matches.map(function (match) { return match.file; }).join("; ") || "N/D",
        status: status,
        confidence: confidence,
        note: rule.note,
      };
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildConfirmatoryMineralComparison(items) {
    const byMineral = new Map();
    buildConfirmatoryReflectionRows(items).forEach(function (row) {
      const bucket = byMineral.get(row.mineral) || {
        mineral: row.mineral,
        observed: [],
        absent: [],
        notes: [],
        files: [],
      };
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (row.status === "não observado") {
        bucket.absent.push(row.reflection + " (" + row.expected + ")");
      } else {
        bucket.observed.push(row.reflection + " esperado " + row.expected + ": " + row.observed);
        if (row.files && row.files !== "N/D") bucket.files.push(row.files);
      }
      if (row.note) bucket.notes.push(row.note);
      byMineral.set(row.mineral, bucket);
    });

    return Array.from(byMineral.values()).map(function (row) {
      const observedCount = row.observed.length;
      const absentCount = row.absent.length;
      let status = "não conclusivo";
      let confidence = "baixa";
      let hypothesis = "evidência insuficiente";
      if (/esmectita/i.test(row.mineral)) {
        const hasEg = row.observed.some(function (text) { return /001 em EG/.test(text); });
        const hasHeated = row.observed.some(function (text) { return /colapso aquecido/.test(text); });
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (hasEg && hasHeated) {
          status = "compatível";
          confidence = "média/alta";
          hypothesis = "compatível com argilomineral expansivo por trajetória AD→EG→H";
        } else if (hasEg) {
          status = "parcial";
          confidence = "média";
          hypothesis = "compatível com fase expansiva, mas requer aquecimento/calcinado";
        }
      } else if (/vermiculita/i.test(row.mineral)) {
        const stable14 = row.observed.some(function (text) { return /001 natural/.test(text); }) && row.observed.some(function (text) { return /sem expansão/.test(text); });
        const heated = row.observed.some(function (text) { return /colapso aquecido/.test(text); });
        /**
         * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (stable14 && heated) {
          status = "compatível";
          confidence = "média";
          hypothesis = "compatível com vermiculita, pendente de revisão térmica";
        } else if (stable14) {
          status = "parcial";
          confidence = "baixa/média";
          hypothesis = "14 A sem expansão em EG; falta evidência térmica";
        }
      } else if (observedCount >= 2) {
        status = "compatível";
        confidence = "média";
        hypothesis = "reflexões confirmatórias múltiplas observadas";
      } else if (observedCount === 1) {
        status = "parcial";
        confidence = "baixa/média";
        hypothesis = "reflexão isolada observada; requer confirmação";
      }
      const conflicts = Array.from(new Set(row.notes)).filter(Boolean);
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      const recommendation = status === "compatível"
        ? "Revisar sobreposição e coerência entre tratamentos antes de curadoria."
        : observedCount
          ? "Buscar picos ausentes e comparar tratamentos adicionais."
          : "Não usar como interpretação sem evidência de pico compatível.";
      return {
        mineral: row.mineral,
        status: status,
        hypothesis: hypothesis,
        confidence: confidence,
        observed: row.observed,
        absent: row.absent.slice(0, Math.max(0, absentCount)),
        conflicts: conflicts,
        files: Array.from(new Set(row.files.join("; ").split("; ").filter(Boolean))),
        recommendation: recommendation,
      };
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderConfirmatoryReflectionPanel(items) {
    const rows = buildConfirmatoryMineralComparison(items);
    if (!rows.length) return "";
    const body = rows.map(function (row) {
      return [
        "<tr>",
        "<td>", mineralLink(row.mineral), "</td>",
        "<td>", escapeHtml(row.status), "</td>",
        "<td>", escapeHtml(row.hypothesis), "</td>",
        "<td>", htmlEvidenceList(row.observed, "N/D", 4), "</td>",
        "<td>", htmlEvidenceList(row.absent, "N/D", 4), "</td>",
        "<td>", htmlEvidenceList(row.conflicts, "Sem conflito específico.", 3), "</td>",
        "<td>", escapeHtml(row.confidence), "</td>",
        "<td>", escapeHtml(row.recommendation), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    return [
      '<section class="argilo-drx__confirmatory-panel">',
      "<h3>Comparação por reflexões confirmatórias</h3>",
      '<p class="argilo-drx__note">Esta tabela cruza picos observados com reflexões diagnósticas esperadas. O resultado é conservador e depende da qualidade do difratograma, preparo e sobreposição de picos.</p>',
      '<div class="argilo-drx__table-scroll">',
      '<table class="argilo-drx__confirmatory-table">',
      "<thead><tr><th>Mineral</th><th>Status</th><th>Hipótese</th><th>Picos que sustentam</th><th>Picos ausentes importantes</th><th>Conflitos</th><th>Confiança</th><th>Recomendação</th></tr></thead>",
      "<tbody>", body, "</tbody></table></div></section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildDiagnosticCompletenessRows(items, peakRows) {
    const peakCountByBase = new Map();
    peakRows.forEach(function (row) {
      const key = String(row.sample || row.file || "").replace(/\.[^.]+$/, "");
      peakCountByBase.set(key, (peakCountByBase.get(key) || 0) + (Number.isFinite(row.twoTheta) ? 1 : 0));
    });
    return buildNgcGroups(items).map(function (group) {
      const allItems = [].concat(group.natural, group.glicolada, group.calcinada, group.indeterminado);
      const flags = [];
      allItems.forEach(function (item) {
        (item.qcFlags || []).forEach(function (flag) { flags.push(typeof flag === "string" ? flag : (flag.code || flag.flag || String(flag))); });
      });
      if (!group.natural.length) flags.push("MISSING_NATURAL");
      if (!group.glicolada.length) flags.push("MISSING_GLYCOLATED");
      if (!group.calcinada.length) flags.push("MISSING_CALCINED");
      const peaks = allItems.reduce(function (count, item) {
        return count + observedPeaks(item).filter(function (peak) { return Number.isFinite(Number(peak.two_theta)); }).length;
      }, 0);
      const knownTreatments = [group.natural.length, group.glicolada.length, group.calcinada.length].filter(Boolean).length;
      let status = "revisar";
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (knownTreatments === 3 && peaks >= 6 && !flags.some(function (flag) { return /ERROR|LOW|SUSPECT/i.test(flag); })) status = "completa";
      else if (knownTreatments >= 2 && peaks >= 3) status = "parcial";
      else if (peaks < 3) status = "fraca";
      const recommendation = status === "completa"
        ? "Conjunto adequado para interpretação assistida, mantendo revisão manual."
        : status === "parcial"
          ? "Completar tratamentos ausentes e revisar picos basais."
          : "Reprocessar/validar RAW e revisar qualidade do difratograma.";
      return {
        sampleBase: group.sampleBase,
        treatments: [
          group.natural.length ? "AD/Natural" : "",
          group.glicolada.length ? "EG/Glicolado" : "",
          group.calcinada.length ? "H/Calcinado" : "",
          group.indeterminado.length ? "Indeterminado" : "",
        ].filter(Boolean).join(", ") || "N/D",
        peaks: peaks,
        status: status,
        flags: Array.from(new Set(flags)).slice(0, 8),
        recommendation: recommendation,
      };
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function strongestPeakInDRange(item, minD, maxD) {
    if (!item) return null;
    const peaks = observedPeaks(item).filter(function (peak) {
      const d = Number(peak.d);
      return Number.isFinite(d) && d >= minD && d <= maxD;
    });
    peaks.sort(function (left, right) {
      const leftRelative = Number(left.relative_intensity);
      const rightRelative = Number(right.relative_intensity);
      if (Number.isFinite(rightRelative) || Number.isFinite(leftRelative)) {
        return (Number.isFinite(rightRelative) ? rightRelative : 0) - (Number.isFinite(leftRelative) ? leftRelative : 0);
      }
      return (Number(right.intensity) || 0) - (Number(left.intensity) || 0);
    });
    return peaks[0] || null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function semTituloRangeLabel(range) {
    return formatNumber(range[0], 2) + "-" + formatNumber(range[1], 2) + " Å";
  }

  function semTituloPeakIntensity(peak) {
    if (!peak) return 0;
    const intensity = Number(peak.intensity);
    if (Number.isFinite(intensity) && intensity > 0) return intensity;
    const relative = Number(peak.relative_intensity);
    return Number.isFinite(relative) && relative > 0 ? relative : 0;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function strongestSemTituloPeak(item, range) {
    if (!item) return null;
    const peaks = observedPeaks(item).filter(function (peak) {
      const d = Number(peak.d);
      return Number.isFinite(d) && d >= range[0] && d <= range[1];
    });
    peaks.sort(function (left, right) {
      return semTituloPeakIntensity(right) - semTituloPeakIntensity(left);
    });
    return peaks[0] || null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function semTituloPeak(item, range) {
    const peak = strongestSemTituloPeak(item, range);
    return peak ? { peak: peak, intensity: semTituloPeakIntensity(peak) } : null;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function semTituloPeakEvidence(label, row) {
    if (!row || !row.peak) return "";
    return label + ": " + formatPeakCell(row.peak) + " / int. " + formatNumber(row.intensity, 0);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function semTituloNgcStatus(group) {
    const known = [group.natural.length, group.glicolada.length, group.calcinada.length].filter(Boolean).length;
    if (known === 3) return "N/G/C completo";
    if (known > 0) return "N/G/C incompleto";
    return "indeterminado";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function diagnoseSemTituloNgcGroup(group) {
    const ranges = SEM_TITULO_NGC_DIAGNOSTIC_RANGES;
    const natural = group.natural[0] || null;
    const glicolada = group.glicolada[0] || null;
    const calcinada = group.calcinada[0] || null;
    const missing = [];
    if (!natural) missing.push("Natural");
    if (!glicolada) missing.push("Glicolada");
    if (!calcinada) missing.push("Calcinada");
    const missingEvidence = missing.length ? ["conjunto incompleto: falta " + missing.join(", ")] : [];
    const rows = [];

    const n10 = semTituloPeak(natural, ranges.illite10ANatural);
    const g10 = semTituloPeak(glicolada, ranges.illite10AGlycolated);
    const c10 = semTituloPeak(calcinada, ranges.illite10ACalcined);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (n10 && g10 && c10) {
      rows.push({
        mineral: "Ilita",
        diagnosis: "pico estável em " + semTituloRangeLabel(ranges.illite10A) + " nos três tratamentos",
        evidence: missingEvidence.concat([
          semTituloPeakEvidence("N", n10),
          semTituloPeakEvidence("G", g10),
          semTituloPeakEvidence("C", c10),
        ]),
        confidence: "alta",
      });
    }

    const nSmectite = semTituloPeak(natural, ranges.smectiteNatural);
    const gSmectite = semTituloPeak(glicolada, ranges.smectiteGlycolated);
    const cSmectite = semTituloPeak(calcinada, ranges.smectiteCalcined);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (nSmectite && gSmectite && cSmectite) {
      rows.push({
        mineral: "Esmectita",
        diagnosis: "expansão no glicol e colapso térmico conforme a rotina N/G/C",
        evidence: missingEvidence.concat([
          "N esperado " + semTituloRangeLabel(ranges.smectiteNatural) + ": " + semTituloPeakEvidence("N", nSmectite),
          "G esperado " + semTituloRangeLabel(ranges.smectiteGlycolated) + ": " + semTituloPeakEvidence("G", gSmectite),
          "C esperado " + semTituloRangeLabel(ranges.smectiteCalcined) + ": " + semTituloPeakEvidence("C", cSmectite),
        ]),
        confidence: "alta",
      });
    }

    const n7 = semTituloPeak(natural, ranges.kaolinite7ANatural);
    const g7 = semTituloPeak(glicolada, ranges.kaolinite7AGlycolated);
    const c7 = semTituloPeak(calcinada, ranges.kaolinite7ACalcinedCheck);
    if (n7 && g7 && (!c7 || c7.intensity < (0.1 * n7.intensity))) {
      rows.push({
        mineral: "Caulinita",
        diagnosis: "pico de 7 Å presente em N/G e destruído ou muito reduzido na calcinação",
        evidence: missingEvidence.concat([
          "faixa " + semTituloRangeLabel(ranges.kaolinite7A),
          semTituloPeakEvidence("N", n7),
          semTituloPeakEvidence("G", g7),
          c7 ? semTituloPeakEvidence("C", c7) + " (<10% de N)" : "C: pico não observado na faixa",
        ]),
        confidence: "alta",
      });
    }

    const nChlorite = semTituloPeak(natural, ranges.chlorite14ANatural);
    const gChlorite = semTituloPeak(glicolada, ranges.chlorite14AGlycolated);
    const cChlorite = semTituloPeak(calcinada, ranges.chlorite14ACalcined);
    const chloriteReference = nChlorite || gChlorite;
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (cChlorite && chloriteReference) {
      const status = cChlorite.intensity > chloriteReference.intensity ? "intensificado" : "preservado";
      const comparison = nChlorite ? "N/C" : "G/C";
      rows.push({
        mineral: "Clorita",
        diagnosis: "pico basal na faixa " + semTituloRangeLabel(ranges.chlorite14A) + " " + status + " na calcinada (" + comparison + ")",
        evidence: missingEvidence.concat([
          semTituloPeakEvidence("N", nChlorite),
          semTituloPeakEvidence("G", gChlorite),
          semTituloPeakEvidence("C", cChlorite),
        ].filter(Boolean)),
        confidence: nChlorite ? "alta" : "média/alta",
      });
    } else if (cChlorite) {
      rows.push({
        mineral: "Clorita",
        diagnosis: "pico basal na faixa " + semTituloRangeLabel(ranges.chlorite14A) + " observado na calcinada; falta par N/G para confirmar estabilidade",
        evidence: missingEvidence.concat([
          semTituloPeakEvidence("C", cChlorite),
        ]),
        confidence: "média",
      });
    } else if (nChlorite && gChlorite) {
      rows.push({
        mineral: "Clorita",
        diagnosis: "pico basal na faixa " + semTituloRangeLabel(ranges.chlorite14A) + " aparece em N/G; falta calcinada para confirmar sobrevivência térmica",
        evidence: missingEvidence.concat([
          semTituloPeakEvidence("N", nChlorite),
          semTituloPeakEvidence("G", gChlorite),
        ]),
        confidence: "média",
      });
    }

    const nQuartz101 = semTituloPeak(natural, ranges.quartz101Natural);
    const gQuartz101 = semTituloPeak(glicolada, ranges.quartz101Glycolated);
    const cQuartz101 = semTituloPeak(calcinada, ranges.quartz101Calcined);
    const nQuartz100 = semTituloPeak(natural, ranges.quartz100);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (nQuartz101 && gQuartz101 && cQuartz101) {
      rows.push({
        mineral: "Quartzo",
        diagnosis: "pico principal 101 imutável nos três tratamentos",
        evidence: missingEvidence.concat([
          "faixa 101 " + semTituloRangeLabel(ranges.quartz101),
          semTituloPeakEvidence("N", nQuartz101),
          semTituloPeakEvidence("G", gQuartz101),
          semTituloPeakEvidence("C", cQuartz101),
          nQuartz100 ? "pico secundário 100: " + semTituloPeakEvidence("N", nQuartz100) : "",
        ]).filter(Boolean),
        confidence: nQuartz100 ? "alta" : "média/alta",
      });
    }

    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!rows.length) {
      rows.push({
        mineral: "Inconclusivo",
        diagnosis: "minerais primários avaliados não foram confirmados pelas faixas do script",
        evidence: missingEvidence.concat(["picos ausentes, deslocados ou sobrepostos nas janelas diagnósticas"]),
        confidence: "baixa",
      });
    }

    return rows.map(function (row) {
      return Object.assign({}, row, {
        sampleBase: group.sampleBase,
        status: semTituloNgcStatus(group),
      });
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderSemTituloNgcDiagnosticPanel(items) {
    const groups = buildNgcGroups(items).filter(function (group) {
      return group.natural.length || group.glicolada.length || group.calcinada.length || group.indeterminado.length;
    }).sort(function (left, right) {
      const leftComplete = [left.natural.length, left.glicolada.length, left.calcinada.length].filter(Boolean).length;
      const rightComplete = [right.natural.length, right.glicolada.length, right.calcinada.length].filter(Boolean).length;
      return rightComplete - leftComplete || String(left.sampleBase).localeCompare(String(right.sampleBase));
    });
    if (!groups.length) return "";
    const visibleGroups = groups.slice(0, 12);
    const diagnosisRows = visibleGroups.reduce(function (rows, group) {
      return rows.concat(diagnoseSemTituloNgcGroup(group));
    }, []).slice(0, 36);
    const groupBody = visibleGroups.map(function (group) {
      return [
        "<tr>",
        "<td>", escapeHtml(group.sampleBase), "</td>",
        "<td>", escapeHtml(semTituloNgcStatus(group)), "</td>",
        "<td>", escapeHtml(group.natural.length), "</td>",
        "<td>", escapeHtml(group.glicolada.length), "</td>",
        "<td>", escapeHtml(group.calcinada.length), "</td>",
        "<td>", escapeHtml(group.indeterminado.length), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    const diagnosisBody = diagnosisRows.map(function (row) {
      return [
        "<tr>",
        "<td>", escapeHtml(row.sampleBase), "</td>",
        "<td>", escapeHtml(row.status), "</td>",
        "<td>", mineralLink(row.mineral), "</td>",
        "<td>", escapeHtml(row.diagnosis), "</td>",
        "<td>", htmlEvidenceList(row.evidence, "N/D", 5), "</td>",
        "<td>", escapeHtml(row.confidence), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    const hiddenGroups = groups.length > visibleGroups.length
      ? "<p class='meta'>Mostrando " + escapeHtml(visibleGroups.length) + " de " + escapeHtml(groups.length) + " grupo(s) N/G/C na seleção.</p>"
      : "";
    return [
      "<section class='compact-section argilo-drx__ngc-script-panel'><h2>Diagnóstico comparativo N/G/C</h2>",
      "<p class='note'>Leitura por faixas d-spacing reaproveitada do script local sem título0.py. A seção procura presença, permanência, expansão ou destruição térmica dos picos e mantém o resultado como hipótese para curadoria.</p>",
      hiddenGroups,
      "<h3>Conjuntos N/G/C na seleção</h3>",
      "<table class='compact-table'><thead><tr><th>Amostra-base</th><th>Status</th><th>N</th><th>G</th><th>C</th><th>Indet.</th></tr></thead><tbody>",
      groupBody || "<tr><td colspan='6'>N/D</td></tr>",
      "</tbody></table>",
      "<h3>Leitura mineralógica pelas faixas do script</h3>",
      "<table class='compact-table'><thead><tr><th>Amostra-base</th><th>Conjunto</th><th>Leitura</th><th>Diagnóstico</th><th>Evidências</th><th>Confiança</th></tr></thead><tbody>",
      diagnosisBody || "<tr><td colspan='6'>N/D</td></tr>",
      "</tbody></table>",
      "</section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function peakEvidenceText(label, peak) {
    if (!peak) return "";
    return label + " com pico em d " + formatNumber(Number(peak.d), 2) + " Å"
      + " / 2θ " + formatNumber(Number(peak.two_theta), 2) + "°"
      + (Number.isFinite(Number(peak.relative_intensity)) ? " / I rel. " + formatNumber(Number(peak.relative_intensity), 1) + "%" : "");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function stabilityScore() {
    const count = Array.prototype.slice.call(arguments).filter(Boolean).length;
    if (count >= 3) return 1;
    if (count === 2) return 0.75;
    if (count === 1) return 0.35;
    return 0;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildNgcTrajectoryScore(group) {
    // Score interpretativo para trajetorias N/G/C: expansao, colapso termico e
    // estabilidade de picos diagnosticos viram evidencia textual do relatorio.
    const ranges = SEM_TITULO_NGC_DIAGNOSTIC_RANGES;
    const natural = group.natural[0] || null;
    const glicolada = group.glicolada[0] || null;
    const calcinada = group.calcinada[0] || null;
    const missing = [];
    if (!natural) missing.push("natural");
    if (!glicolada) missing.push("glicolado");
    if (!calcinada) missing.push("calcinado");

    const nExpandable = strongestPeakInDRange(natural, ranges.smectiteNatural[0], ranges.smectiteNatural[1]);
    const gExpanded = strongestPeakInDRange(glicolada, ranges.smectiteGlycolated[0], ranges.smectiteGlycolated[1]);
    const cCollapsed = strongestPeakInDRange(calcinada, ranges.smectiteCalcined[0], ranges.smectiteCalcined[1]);
    const nTen = strongestPeakInDRange(natural, ranges.illite10ANatural[0], ranges.illite10ANatural[1]);
    const gTen = strongestPeakInDRange(glicolada, ranges.illite10AGlycolated[0], ranges.illite10AGlycolated[1]);
    const cTen = strongestPeakInDRange(calcinada, ranges.illite10ACalcined[0], ranges.illite10ACalcined[1]);
    const nFourteen = strongestPeakInDRange(natural, ranges.chlorite14ANatural[0], ranges.chlorite14ANatural[1]);
    const gFourteen = strongestPeakInDRange(glicolada, ranges.chlorite14AGlycolated[0], ranges.chlorite14AGlycolated[1]);
    const cFourteen = strongestPeakInDRange(calcinada, ranges.chlorite14ACalcined[0], ranges.chlorite14ACalcined[1]);
    const nSeven = strongestPeakInDRange(natural, ranges.kaolinite7ANatural[0], ranges.kaolinite7ANatural[1]);
    const gSeven = strongestPeakInDRange(glicolada, ranges.kaolinite7AGlycolated[0], ranges.kaolinite7AGlycolated[1]);
    const cSeven = strongestPeakInDRange(calcinada, ranges.kaolinite7ACalcinedCheck[0], ranges.kaolinite7ACalcinedCheck[1]);

    const nD = nExpandable ? Number(nExpandable.d) : null;
    const gD = gExpanded ? Number(gExpanded.d) : null;
    const cD = cCollapsed ? Number(cCollapsed.d) : null;
    const shiftNG = Number.isFinite(nD) && Number.isFinite(gD) ? gD - nD : null;
    const shiftGC = Number.isFinite(gD) && Number.isFinite(cD) ? cD - gD : null;
    const completeness = (3 - missing.length) / 3;
    const expansion = nExpandable && gExpanded && shiftNG !== null && shiftNG >= 1 ? 1 : (gExpanded ? 0.65 : 0);
    const collapse = gExpanded && cCollapsed && shiftGC !== null && shiftGC <= -5 ? 1 : (cCollapsed && (nExpandable || gExpanded) ? 0.55 : 0);
    const stability10 = stabilityScore(nTen, gTen, cTen);
    const stability14 = stabilityScore(nFourteen, gFourteen, cFourteen);
    const stability7 = stabilityScore(nSeven, gSeven, cSeven);
    const stability = Math.max(stability10, stability14, stability7);
    const score = (0.20 * completeness)
      + (0.25 * expansion)
      + (0.20 * collapse)
      + (0.20 * stability)
      + (0.15 * Math.max(expansion, collapse, stability));
    const evidences = [];
    [
      peakEvidenceText("Natural", nExpandable || nFourteen || nTen || nSeven),
      peakEvidenceText("Glicolada", gExpanded || gFourteen || gTen || gSeven),
      peakEvidenceText("Calcinada", cCollapsed || cFourteen || cSeven),
    ].filter(Boolean).forEach(function (text) { evidences.push(text); });
    const candidates = [];
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (expansion >= 1 && collapse >= 1) {
      candidates.push("compatível com esmectita/montmorilonita expansiva");
      evidences.push("expansão N→G e colapso G→C coerentes");
    } else if (expansion > 0) {
      candidates.push("compatível com argilomineral expansivo; requer calcinação/curadoria");
    }
    if (stability10 >= 0.65 && !gExpanded) candidates.push("compatível com ilita/mica por estabilidade em ~10 Å");
    if (stability14 >= 0.65 && !gExpanded) candidates.push("compatível com clorita/vermiculita; revisar comportamento térmico");
    if (stability7 > 0) candidates.push("compatível com caulinita/clorita, requer revisão por sobreposição em ~7 Å");
    if (!candidates.length) candidates.push("evidência insuficiente para hipótese mineralógica N/G/C");
    if (missing.length) evidences.push("limitação: preparo " + missing.join(", preparo ") + " ausente");
    return {
      score: Math.max(0, Math.min(1, score)),
      components: {
        completude_tratamentos: completeness,
        expansao_n_g: expansion,
        colapso_g_c: collapse,
        estabilidade_10a: stability10,
        estabilidade_14a: stability14,
        estabilidade_7a: stability7,
      },
      shifts: {
        natural_to_glycolated: shiftNG,
        glycolated_to_calcined: shiftGC,
      },
      hypotheses: Array.from(new Set(candidates)),
      evidences: Array.from(new Set(evidences)),
      warnings: missing.map(function (name) { return "preparo " + name + " ausente"; }),
    };
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderNgcScoreDetails(row) {
    const components = row.scoreDetails && row.scoreDetails.components || {};
    const rows = [
      ["Completude dos tratamentos", components.completude_tratamentos],
      ["Expansão N→G", components.expansao_n_g],
      ["Colapso G→C", components.colapso_g_c],
      ["Estabilidade ~10 Å", components.estabilidade_10a],
      ["Estabilidade ~14 Å", components.estabilidade_14a],
      ["Estabilidade ~7 Å", components.estabilidade_7a],
    ].map(function (item) {
      return "<tr><td>" + escapeHtml(item[0]) + "</td><td>" + escapeHtml(formatScore(Number(item[1]))) + "</td></tr>";
    }).join("");
    return [
      '<details class="argilo-drx__score-details">',
      "<summary>Critérios N-G-C</summary>",
      '<table class="argilo-drx__score-table"><tbody>', rows, "</tbody></table>",
      "</details>",
    ].join("");
  }

  /**
   * Gera a leitura resumida N/G/C usada nos relatórios da seleção.
   *
   * Esta função é apenas uma camada de apresentação/fallback legado; a fonte
   * primária das regras diagnósticas é o backend. Mantê-la documentada ajuda a
   * evitar que novas regras científicas sejam duplicadas no JavaScript.
   * @param {Array<Object>} items Difratogramas selecionados.
   * @returns {Array<Object>} Linhas resumidas para relatório/interface.
   */
  function buildNgcInterpretations(items) {
    return buildNgcGroups(items).map(function (group) {
      const ranges = SEM_TITULO_NGC_DIAGNOSTIC_RANGES;
      const scoreDetails = buildNgcTrajectoryScore(group);
      const natural = group.natural[0] || null;
      const glicolada = group.glicolada[0] || null;
      const calcinada = group.calcinada[0] || null;
      const evidences = scoreDetails.evidences.slice();
      const candidates = scoreDetails.hypotheses.slice();
      const warnings = [];

      const nExpandable = strongestPeakInDRange(natural, ranges.smectiteNatural[0], ranges.smectiteNatural[1]);
      const gExpanded = strongestPeakInDRange(glicolada, ranges.smectiteGlycolated[0], ranges.smectiteGlycolated[1]);
      const cCollapsed = strongestPeakInDRange(calcinada, ranges.smectiteCalcined[0], ranges.smectiteCalcined[1]);
      const nTen = strongestPeakInDRange(natural, ranges.illite10ANatural[0], ranges.illite10ANatural[1]);
      const gTen = strongestPeakInDRange(glicolada, ranges.illite10AGlycolated[0], ranges.illite10AGlycolated[1]);
      const cTen = strongestPeakInDRange(calcinada, ranges.illite10ACalcined[0], ranges.illite10ACalcined[1]);
      const nFourteen = strongestPeakInDRange(natural, ranges.chlorite14ANatural[0], ranges.chlorite14ANatural[1]);
      const gFourteen = strongestPeakInDRange(glicolada, ranges.chlorite14AGlycolated[0], ranges.chlorite14AGlycolated[1]);
      const cFourteen = strongestPeakInDRange(calcinada, ranges.chlorite14ACalcined[0], ranges.chlorite14ACalcined[1]);
      const nSeven = strongestPeakInDRange(natural, ranges.kaolinite7ANatural[0], ranges.kaolinite7ANatural[1]);
      const gSeven = strongestPeakInDRange(glicolada, ranges.kaolinite7AGlycolated[0], ranges.kaolinite7AGlycolated[1]);
      const cSeven = strongestPeakInDRange(calcinada, ranges.kaolinite7ACalcinedCheck[0], ranges.kaolinite7ACalcinedCheck[1]);

      if (!natural) warnings.push("preparo natural ausente");
      if (!glicolada) warnings.push("preparo glicolado ausente");
      if (!calcinada) warnings.push("preparo calcinado ausente");

      let confidence = scoreDetails.score >= 0.75 && !warnings.length ? "alta" : (scoreDetails.score >= 0.45 ? "média" : "baixa");
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (nExpandable && gExpanded && cCollapsed) {
        evidences.push("trajetória basal sugere expansão após glicolação e colapso próximo de 10 Å após calcinação");
        confidence = "alta";
      } else if ((nExpandable && gExpanded) || gExpanded) {
        confidence = calcinada ? "média" : "baixa";
      }

      const tenCount = [nTen, gTen, cTen].filter(Boolean).length;
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (tenCount >= 2 && !gExpanded) {
        confidence = confidence === "alta" ? confidence : "média";
      }

      const fourteenCount = [nFourteen, gFourteen, cFourteen].filter(Boolean).length;
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (fourteenCount >= 2 && !gExpanded) {
        confidence = confidence === "alta" ? confidence : "média";
      } else if (nFourteen && !gExpanded) {
        candidates.push("pico em ~14 Å não conclusivo; pode envolver clorita, vermiculita ou esmectita natural");
      }

      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (warnings.length) {
        evidences.push("limitação: " + warnings.join(", "));
      }

      return {
        sampleBase: group.sampleBase,
        status: natural && glicolada && calcinada ? "trio completo" : ([natural, glicolada, calcinada].filter(Boolean).length ? "trio incompleto" : "indeterminado"),
        natural: group.natural.length,
        glicolada: group.glicolada.length,
        calcinada: group.calcinada.length,
        indeterminado: group.indeterminado.length,
        candidates: Array.from(new Set(candidates)),
        confidence: confidence,
        ngcScore: scoreDetails.score,
        scoreDetails: scoreDetails,
        evidences: Array.from(new Set(evidences)),
        warnings: warnings,
      };
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderNgcInterpretationPanel(items) {
    const rows = buildNgcInterpretations(items).filter(function (row) {
      return row.natural || row.glicolada || row.calcinada || row.evidences.length;
    });
    if (!rows.length) return "";
    const cards = rows.map(function (row) {
      const evidenceRows = row.evidences.slice(0, 5).map(function (evidence) {
        return "<li>" + escapeHtml(evidence) + "</li>";
      }).join("");
      return [
        '<article class="argilo-drx__mineral-card">',
        "<h3>Comparação N/G/C · ", escapeHtml(row.sampleBase), "</h3>",
        "<p><strong>Status:</strong> ", escapeHtml(row.status), " · <strong>confiança:</strong> ", escapeHtml(row.confidence), "</p>",
        "<p><strong>Hipótese assistida:</strong> ", linkKnownMineralText(row.candidates.join("; ")), "</p>",
        '<ul class="argilo-drx__evidence-list">', evidenceRows, "</ul>",
        '<p class="argilo-drx__note">Interpretação preliminar, pendente de curadoria; não confirma mineral automaticamente.</p>',
        "</article>",
      ].join("");
    }).join("");
    return '<div class="argilo-drx__mineral-grid">' + cards + "</div>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildNgcSummary(items) {
    const groups = buildNgcGroups(items);
    const interpretations = new Map();
    buildNgcInterpretations(items).forEach(function (row) {
      interpretations.set(row.sampleBase, row);
    });
    return groups.map(function (group) {
      const hasN = group.natural.length > 0;
      const hasG = group.glicolada.length > 0;
      const hasC = group.calcinada.length > 0;
      const known = [hasN, hasG, hasC].filter(Boolean).length;
      let status = "indeterminado";
      if (known === 3) status = "trio completo";
      else if (known > 0) status = "trio incompleto";
      const duplicates = []
        .concat(group.natural.length > 1 ? ["natural"] : [])
        .concat(group.glicolada.length > 1 ? ["glicolada"] : [])
        .concat(group.calcinada.length > 1 ? ["calcinada"] : []);
      return {
        sampleBase: group.sampleBase,
        status: status,
        natural: group.natural.length,
        glicolada: group.glicolada.length,
        calcinada: group.calcinada.length,
        indeterminado: group.indeterminado.length,
        duplicates: duplicates,
        interpretation: (interpretations.get(group.sampleBase) || {}).candidates || [],
        confidence: (interpretations.get(group.sampleBase) || {}).confidence || "baixa",
        ngcScore: (interpretations.get(group.sampleBase) || {}).ngcScore,
        evidences: (interpretations.get(group.sampleBase) || {}).evidences || [],
      };
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function basalEvidenceSummary(peakRows) {
    const evidences = [];
    const rows = peakRows.filter(function (row) { return Number.isFinite(row.d); });
    const ranges = SEM_TITULO_NGC_DIAGNOSTIC_RANGES;
    if (rows.some(function (row) { return row.d >= ranges.smectiteGlycolated[0] && row.d <= ranges.smectiteGlycolated[1] && row.treatment === treatmentLabel("glicolado"); })) {
      evidences.push("pico basal próximo de 17 Å em amostra glicolada, compatível com expansão de fase esmectítica");
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (rows.some(function (row) { return row.d >= ranges.chlorite14A[0] && row.d <= ranges.chlorite14A[1]; })) {
      evidences.push("pico basal em 13,58-14,87 Å, compatível com clorita e pendente de comparação N/G/C");
    }
    if (rows.some(function (row) { return row.d >= ranges.illite10A[0] && row.d <= ranges.illite10A[1]; })) {
      evidences.push("pico próximo de 10 Å, compatível com ilita/mica quando estável entre tratamentos");
    }
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (rows.some(function (row) { return row.d >= ranges.kaolinite7A[0] && row.d <= ranges.kaolinite7A[1]; })) {
      evidences.push("pico próximo de 7 Å, compatível com caulinita/clorita e sujeito a sobreposição");
    }
    return evidences.length ? evidences : ["evidência basal insuficiente ou não destacada pelo peak-picking defensivo"];
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderAutomatedAnalysesSection(items, assembly, peakRows) {
    const ngcRows = buildNgcSummary(items);
    const ngcInterpretationRows = buildNgcInterpretations(items);
    const similarityRows = items.map(function (item) {
      const similarity = item.packageSimilarity || {};
      const best = similarity.best_match || {};
      if (!similarity.available && !best.filename) return "";
      return [
        "<li><strong>", escapeHtml(sampleLabel(item)), ":</strong> ",
        escapeHtml(similarity.message || "Comparação de similaridade disponível."),
        best.filename ? " Mais semelhante: " + escapeHtml(best.sample_code || best.filename) + " (" + escapeHtml(formatScore(best.score)) + ")." : "",
        (best.record_url || recordUrl(best.record_id || similarity.record_id)) ? ' <a href="' + escapeHtml(best.record_url || recordUrl(best.record_id || similarity.record_id)) + '">Abrir registro semelhante</a>.' : "",
        (best.evidence || []).length ? " Evidências: " + escapeHtml(best.evidence.slice(0, 3).join("; ")) + "." : "",
        "</li>",
      ].join("");
    }).filter(Boolean).join("");
    const ngcTable = ngcRows.map(function (row) {
      return [
        "<tr>",
        "<td>", escapeHtml(row.sampleBase), "</td>",
        "<td>", escapeHtml(row.status), "</td>",
        "<td>", escapeHtml(formatScore(row.ngcScore)), "</td>",
        "<td>", escapeHtml(row.natural), "</td>",
        "<td>", escapeHtml(row.glicolada), "</td>",
        "<td>", escapeHtml(row.calcinada), "</td>",
        "<td>", escapeHtml(row.indeterminado), "</td>",
        "<td>", escapeHtml(row.duplicates.length ? row.duplicates.join(", ") : "não detectada"), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    const ngcInterpretationTable = ngcInterpretationRows.map(function (row) {
      return [
        "<tr>",
        "<td>", escapeHtml(row.sampleBase), "</td>",
        "<td>", escapeHtml(row.status), "</td>",
        "<td>", escapeHtml(formatScore(row.ngcScore)), "</td>",
        "<td>", linkKnownMineralText(row.candidates.join("; ")), "</td>",
        "<td>", escapeHtml(row.confidence), "</td>",
        "<td>", escapeHtml(row.evidences.slice(0, 4).join("; ") || "N/D"), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    const inventoryRows = items.map(function (item) {
      const metadata = item.metadata || {};
      const points = metadata.points || metadata.num_points || item.totalPoints || (item.twoTheta || []).length || "N/D";
      const format = metadata.detected_format || metadata.format || "N/D";
      const sha = item.sha256 || metadata.sha256 || (item.diffractogram && item.diffractogram.sha256) || "N/D";
      return [
        "<tr>",
        "<td>", escapeHtml(sampleLabel(item)), "</td>",
        "<td>", escapeHtml(metadata.original_filename || item.id), "</td>",
        "<td>", escapeHtml(treatmentLabel(item.treatment)), "</td>",
        "<td>", escapeHtml(points), "</td>",
        "<td>", escapeHtml(format), "</td>",
        "<td>", escapeHtml(String(sha).slice(0, 12)), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    return [
      "<section class='compact-section'><h2>Análises automáticas incorporadas</h2>",
      "<p class='note'>Esta seção resume resultados produzidos pelos scripts de inventário, preparo N/G/C, peak-picking, classificação mineralógica preliminar e similaridade. Todos são apoio à curadoria, não confirmação automática.</p>",
      "<table class='compact-table'><thead><tr><th>Amostra</th><th>Arquivo</th><th>Preparo</th><th>Pontos</th><th>Formato RAW</th><th>SHA-256</th></tr></thead><tbody>",
      inventoryRows || "<tr><td colspan='6'>N/D</td></tr>",
      "</tbody></table>",
      "<h3>Grupo Natural/Glicolada/Calcinada</h3>",
      "<table class='compact-table'><thead><tr><th>Amostra-base</th><th>Status</th><th>Score N/G/C</th><th>N</th><th>G</th><th>C</th><th>Indet.</th><th>Duplicatas</th></tr></thead><tbody>",
      ngcTable || "<tr><td colspan='8'>N/D</td></tr>",
      "</tbody></table>",
      "<h3>Interpretação N/G/C assistida</h3>",
      "<table class='compact-table'><thead><tr><th>Amostra-base</th><th>Status</th><th>Score</th><th>Hipótese conservadora</th><th>Confiança</th><th>Evidências</th></tr></thead><tbody>",
      ngcInterpretationTable || "<tr><td colspan='6'>N/D</td></tr>",
      "</tbody></table>",
      "<h3>Evidências basais</h3>",
      htmlListLinked(basalEvidenceSummary(peakRows).map(linkKnownMineralText)),
      "<h3>Similaridade com pacote analítico</h3>",
      similarityRows ? "<ul>" + similarityRows + "</ul>" : "<p>Nenhuma comparação de similaridade com RAW externo foi anexada nesta seleção.</p>",
      "<p class='meta'>Resumo mineralógico preliminar: ", assembly.length ? assembly.slice(0, 8).map(function (row) { return mineralLink(row.mineral) + " (" + escapeHtml(row.bestConfidence || "conf. N/D") + ")"; }).join(", ") : "sem candidatos", ".</p>",
      "</section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function normalizeReportSeries(values) {
    const numeric = (values || []).map(Number).filter(Number.isFinite);
    const max = Math.max.apply(null, numeric.map(function (value) { return Math.abs(value); }));
    if (!Number.isFinite(max) || max <= 0) return [];
    return (values || []).map(function (value) {
      const number = Number(value);
      return Number.isFinite(number) ? number / max : null;
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function backgroundReportSvg(items) {
    const item = items.find(function (candidate) {
      const advanced = candidate.advancedCurve || {};
      return advanced.available && (advanced.two_theta || []).length && ((advanced.baseline || []).length || (advanced.intensity_corrected || []).length);
    });
    if (!item) return "<p class='note'>Curva de background/corrigida não disponível para a seleção atual. Gere o pacote analítico com processamento avançado para incluir esta figura.</p>";
    const advanced = item.advancedCurve || {};
    const xValues = (advanced.two_theta || []).map(Number);
    const series = [
      { label: "bruta", values: normalizeReportSeries(advanced.intensity_raw || item.intensity || []), color: "#5677b9" },
      { label: "background", values: normalizeReportSeries(advanced.baseline || []), color: "#c28735" },
      { label: "corrigida", values: normalizeReportSeries(advanced.intensity_corrected || advanced.intensity_normalized || []), color: "#2f6f73" },
    ].filter(function (serie) { return serie.values.length === xValues.length && serie.values.some(Number.isFinite); });
    if (!series.length) return "<p class='note'>Metadados avançados encontrados, mas sem séries suficientes para desenhar background/correção.</p>";
    const width = 960;
    const height = 280;
    const margin = { left: 56, right: 24, top: 38, bottom: 42 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;
    const finiteX = xValues.filter(Number.isFinite);
    const minX = Math.min.apply(null, finiteX);
    const maxX = Math.max.apply(null, finiteX);
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    function xScale(value) {
      return margin.left + ((value - minX) / Math.max(0.0001, maxX - minX)) * plotW;
    }
    function yScale(value) {
      return margin.top + plotH - (Math.max(0, Math.min(1.08, value)) / 1.08) * plotH;
    }
    const paths = series.map(function (serie) {
      const d = serie.values.map(function (value, index) {
        const x = xValues[index];
        if (!Number.isFinite(x) || !Number.isFinite(value)) return "";
        return (index ? "L" : "M") + xScale(x).toFixed(2) + "," + yScale(value).toFixed(2);
      }).filter(Boolean).join(" ");
      return "<path d='" + d + "' fill='none' stroke='" + serie.color + "' stroke-width='2'/>";
    }).join("");
    const legend = series.map(function (serie, index) {
      const x = margin.left + index * 150;
      return "<line x1='" + x + "' y1='24' x2='" + (x + 28) + "' y2='24' stroke='" + serie.color + "' stroke-width='3'/><text x='" + (x + 34) + "' y='28'>" + escapeHtml(serie.label) + "</text>";
    }).join("");
    const ticks = [minX, minX + (maxX - minX) / 2, maxX].map(function (tick) {
      const x = xScale(tick);
      return "<line x1='" + x.toFixed(2) + "' y1='" + (margin.top + plotH) + "' x2='" + x.toFixed(2) + "' y2='" + (margin.top + plotH + 5) + "' stroke='#6f827b'/><text x='" + (x - 18).toFixed(2) + "' y='" + (height - 18) + "'>" + escapeHtml(formatNumber(tick, 1)) + "</text>";
    }).join("");
    return [
      "<svg xmlns='http://www.w3.org/2000/svg' width='960' height='280' viewBox='0 0 960 280' style='background:#fff;border:1px solid #d8e1dd;border-radius:8px'>",
      "<style>text{font-family:Arial,sans-serif;font-size:12px;fill:#4f625c}.title{font-size:15px;font-weight:bold;fill:#243c37}</style>",
      "<text class='title' x='56' y='18'>Background e curva corrigida · ", escapeHtml(sampleLabel(item)), "</text>",
      legend,
      "<rect x='", margin.left, "' y='", margin.top, "' width='", plotW, "' height='", plotH, "' fill='#fbfdfc' stroke='#d8e1dd'/>",
      paths,
      ticks,
      "<text x='", margin.left + plotW / 2 - 26, "' y='", height - 4, "'>2θ (°)</text>",
      "<text x='8' y='155' transform='rotate(-90 8 155)'>Intensidade normalizada</text>",
      "</svg>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderBackgroundSection(items) {
    const rows = items.map(function (item) {
      const advanced = item.advancedCurve || {};
      const summary = item.advancedSummary || {};
      const qc = (item.qcFlags || []).map(function (flag) { return typeof flag === "string" ? flag : (flag.code || flag.flag || String(flag)); }).filter(Boolean);
      return [
        "<tr>",
        "<td>", escapeHtml(sampleLabel(item)), "</td>",
        "<td>", escapeHtml(item.metadata && item.metadata.original_filename || item.id), "</td>",
        "<td>", escapeHtml(advanced.available ? "disponível" : (advanced.error || "não disponível")), "</td>",
        "<td>", escapeHtml(advanced.baseline_method || summary.baseline_method || "N/D"), "</td>",
        "<td>", escapeHtml(advanced.normalization || summary.normalization || "N/D"), "</td>",
        "<td>", escapeHtml(advanced.points || summary.points || (item.twoTheta || []).length || "N/D"), "</td>",
        "<td>", escapeHtml(qc.join(", ") || "sem flag registrada"), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    return [
      "<section class='report-section'><h2>Pré-processamento e background</h2>",
      "<p class='note'>Quando há correção N/G/C, o relatório usa o eixo 2θ classificado antes de mostrar background, curva corrigida e evidências de qualidade.</p>",
      "<div class='chart-panel'>", backgroundReportSvg(items), "</div>",
      "<table class='compact-table'><thead><tr><th>Amostra</th><th>Arquivo</th><th>Curva avançada</th><th>Background</th><th>Normalização</th><th>Pontos</th><th>QC</th></tr></thead><tbody>",
      rows || "<tr><td colspan='7'>N/D</td></tr>",
      "</tbody></table></section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderBasalTrajectoryTable(items) {
    const rows = buildBasalTrajectoryRows(items).map(function (row) {
      return [
        "<tr>",
        "<td>", escapeHtml(row.sampleBase), "</td>",
        "<td>", escapeHtml(formatPeakCell(row.naturalPeak)), "</td>",
        "<td>", escapeHtml(formatPeakCell(row.glycolatedPeak)), "</td>",
        "<td>", escapeHtml(formatPeakCell(row.calcinedPeak)), "</td>",
        "<td>", row.shiftNG === null ? "N/D" : escapeHtml(formatNumber(row.shiftNG, 2)), "</td>",
        "<td>", row.shiftGC === null ? "N/D" : escapeHtml(formatNumber(row.shiftGC, 2)), "</td>",
        "<td>", escapeHtml(row.interpretation), "</td>",
        "<td>", escapeHtml(row.confidence), "</td>",
        "<td>", escapeHtml(row.flags.join(", ") || "sem flag"), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    return [
      "<section class='report-section'><h2>Trajetória basal 001 por tratamento</h2>",
      "<p class='note'>A comparação AD/Natural → EG/Glicolado → H400/H500/H550 é usada como evidência assistida. O relatório não confirma mineral automaticamente.</p>",
      "<table class='data-table basal-table'><thead><tr><th>Amostra-base</th><th>AD/Natural</th><th>EG/Glicolado</th><th>H/Calcinado</th><th>Δd N→G</th><th>Δd G→H</th><th>Interpretação assistida</th><th>Conf.</th><th>Flags</th></tr></thead><tbody>",
      rows || "<tr><td colspan='9'>N/D</td></tr>",
      "</tbody></table></section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderConfirmatoryReflectionTable(items) {
    const rows = buildConfirmatoryReflectionRows(items)
      .filter(function (row) { return row.observed && row.observed !== "N/D"; })
      .map(function (row) {
        return [
          "<tr>",
          "<td>", mineralLink(row.mineral), "</td>",
          "<td>", escapeHtml(row.expected), "</td>",
          "<td>", escapeHtml(row.observed), "</td>",
          "<td>", escapeHtml(row.files), "</td>",
          "<td>", escapeHtml(row.confidence), "</td>",
          "<td>", escapeHtml(row.note), "</td>",
          "</tr>",
        ].join("");
      }).join("");
    return [
      "<section class='report-section'><h2>Reflexões confirmatórias de argilominerais</h2>",
      "<table class='data-table confirmatory-table'><thead><tr><th>Argilomineral</th><th>d esperado</th><th>Observado na seleção</th><th>Arquivos</th><th>Conf.</th><th>Nota</th></tr></thead><tbody>",
      rows || "<tr><td colspan='6'>Nenhuma reflexão confirmatória observada na seleção.</td></tr>",
      "</tbody></table></section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderDiagnosticCompletenessTable(items, peakRows) {
    const rows = buildDiagnosticCompletenessRows(items, peakRows).map(function (row) {
      return [
        "<tr>",
        "<td>", escapeHtml(row.sampleBase), "</td>",
        "<td>", escapeHtml(row.treatments), "</td>",
        "<td>", escapeHtml(row.peaks), "</td>",
        "<td>", escapeHtml(row.status), "</td>",
        "<td>", escapeHtml(row.flags.join(", ") || "sem flag"), "</td>",
        "<td>", escapeHtml(row.recommendation), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    return [
      "<section class='report-section'><h2>Qualidade e completude diagnóstica</h2>",
      "<table class='compact-table'><thead><tr><th>Amostra-base</th><th>Tratamentos</th><th>Picos úteis</th><th>Status</th><th>Flags QC</th><th>Recomendação</th></tr></thead><tbody>",
      rows || "<tr><td colspan='6'>N/D</td></tr>",
      "</tbody></table></section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderPeakTable(rows) {
    if (!DRX_SHOW_OBSERVED_PEAK_DIAGNOSTIC_TABLE) return "";
    const filteredRows = rows.filter(function (row) {
      return isDiagnosticPeak({ two_theta: row.twoTheta, d: row.d }) && hasDiagnosticCandidate(row.mineral);
    });
    const body = filteredRows.slice(0, 48).map(function (row) {
      return [
        "<tr>",
        "<td>", escapeHtml(row.treatment), "</td>",
        "<td>", escapeHtml(row.file || row.sample), "</td>",
        "<td>", row.twoTheta === null ? "N/D" : escapeHtml(formatNumber(row.twoTheta, 3)), "</td>",
        "<td>", row.d === null ? "N/D" : escapeHtml(formatNumber(row.d, 3)), "</td>",
        "<td>", escapeHtml(row.reflection || "N/D"), "</td>",
        "<td>", escapeHtml(row.observation || "N/D"), "</td>",
        "<td>", escapeHtml(row.confidence || "N/D"), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    const diagnosticRangeLabel = formatNumber(DIAGNOSTIC_PEAK_MIN_TWO_THETA, 0) + "° e " + formatNumber(DIAGNOSTIC_PEAK_MAX_TWO_THETA, 0) + "°";
    return [
      "<section class='report-section'><h2>Picos observados e evidência diagnóstica</h2>",
      "<p class='meta'>Mostrando apenas picos com candidato mineralógico, 2θ entre ", escapeHtml(diagnosticRangeLabel), " e d Å menor ou igual a ", escapeHtml(formatNumber(DIAGNOSTIC_PEAK_MAX_D_ANGSTROM, 0)), ". d-spacing calculado pela lei de Bragg com λ = ", escapeHtml(formatNumber(CU_K_ALPHA_WAVELENGTH, 4)), " Å (Cu Kα), salvo metadado mais específico ausente no app.</p>",
      "<table class='data-table peak-table'><colgroup><col class='col-treatment'><col class='col-file'><col class='col-num'><col class='col-num'><col class='col-reflection'><col class='col-observation'><col class='col-confidence'></colgroup><thead><tr><th>Trat.</th><th>Arquivo</th><th>2θ</th><th>d Å</th><th>Ref.</th><th>Observação diagnóstica</th><th>Conf.</th></tr></thead><tbody>",
      body || "<tr><td colspan='7'>Nenhum pico com candidato mineralógico, entre " + escapeHtml(diagnosticRangeLabel) + " 2θ e com d Å até " + escapeHtml(formatNumber(DIAGNOSTIC_PEAK_MAX_D_ANGSTROM, 0)) + ".</td></tr>",
      "</tbody></table></section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderDiagnosticCriteria(peakRows) {
    const observed = peakRows.filter(function (row) { return Number.isFinite(row.d); });
    const ranges = SEM_TITULO_NGC_DIAGNOSTIC_RANGES;
    function seen(min, max, treatment) {
      return observed.some(function (row) {
        return row.d >= min && row.d <= max && (!treatment || row.treatment === treatmentLabel(treatment));
      });
    }
    const rows = [
      "Esmectita/montmorilonita: pico basal variável; expansão após glicolação e possível colapso após calcinação. Dados atuais: " + (seen(ranges.smectiteGlycolated[0], ranges.smectiteGlycolated[1], "glicolado") ? "compatível com expansão em 16,06-18,31 Å." : "não conclusivo para expansão em 16,06-18,31 Å."),
      "Clorita: pico basal em 13,58-14,87 Å, com reflexões associadas próximas de 7 Å, 4,7 Å e 3,5 Å; não deve expandir como esmectita. Dados atuais: " + (seen(ranges.chlorite14A[0], ranges.chlorite14A[1]) ? "há pico basal na faixa da clorita, requer comparação com 7 Å e tratamentos." : "sem evidência basal robusta em 13,58-14,87 Å."),
      "Caulinita: picos próximos de 7 Å e 3,57 Å; atenção à sobreposição com clorita. Dados atuais: " + (seen(ranges.kaolinite7A[0], ranges.kaolinite7A[1]) ? "pico em 6,96-7,42 Å observado, não conclusivo isoladamente." : "pico em 6,96-7,42 Å não destacado."),
      "Ilita/mica: pico próximo de 10 Å, sem expansão significativa com glicolação. Dados atuais: " + (seen(ranges.illite10A[0], ranges.illite10A[1]) ? "pico em 9,73-10,38 Å observado, compatível mas requer estabilidade entre tratamentos." : "sem pico em 9,73-10,38 Å destacado."),
      "Interestratificados: picos largos, assimétricos ou deslocados, com comportamento intermediário; requer curadoria manual.",
    ];
    return "<section class='compact-section'><h2>Critérios diagnósticos usados</h2>" + htmlListLinked(rows.map(linkKnownMineralText)) + "</section>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderAssemblyTable(assembly) {
    const rows = assembly.map(function (row) {
      return [
        "<tr>",
        "<td>", mineralLink(row.mineral), "</td>",
        "<td>", escapeHtml(row.classLabel || row.group), "</td>",
        "<td>", escapeHtml(Array.from(row.treatments).join(", ") || "N/D"), "</td>",
        "<td>", escapeHtml(formatScore(row.bestScore)), "</td>",
        "<td>", escapeHtml(row.bestConfidence || confidenceLabel(row.bestConfidenceRank)), "</td>",
        "<td>", escapeHtml((row.evidences || []).filter(Boolean)[0] || "Evidência por casamento de picos; revisar padrão completo."), "</td>",
        "<td>", linkKnownMineralText(mineralGeologicalRole(row.mineral, row.classLabel)), "</td>",
        "<td>", escapeHtml(statusFromEvidence({ score: row.bestScore, confidence: row.bestConfidence })), "</td>",
        "</tr>",
      ].join("");
    }).join("");
    return [
      "<section class='report-section'><h2>Assembleia mineral interpretada</h2>",
      "<table class='data-table assembly-table'><colgroup><col class='col-mineral-wide'><col class='col-group'><col class='col-treatment-wide'><col class='col-score'><col class='col-confidence'><col class='col-evidence'><col class='col-role'><col class='col-status'></colgroup><thead><tr><th>Mineral</th><th>Grupo</th><th>Tratamentos</th><th>Score</th><th>Conf.</th><th>Evidência principal</th><th>Papel provável</th><th>Status</th></tr></thead><tbody>",
      rows || "<tr><td colspan='8'>Nenhum candidato mineralógico disponível.</td></tr>",
      "</tbody></table></section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderAbundanceSection(assembly) {
    const rows = assembly.map(function (row) {
      return "<tr><td>" + mineralLink(row.mineral) + "</td><td>" + escapeHtml(abundanceClass(row)) + "</td><td>" + escapeHtml("Baseado em score, recorrência entre tratamentos e intensidade relativa de picos; não quantitativo.") + "</td></tr>";
    }).join("");
    return [
      "<section class='compact-section'><h2>Abundância relativa</h2>",
      "<p class='note'>Abundância qualitativa baseada em intensidade relativa dos picos. Não equivale a quantificação modal ou percentual por Rietveld.</p>",
      "<table class='compact-table'><thead><tr><th>Mineral</th><th>Classe qualitativa</th><th>Observação</th></tr></thead><tbody>",
      rows || "<tr><td colspan='3'>Indeterminado</td></tr>",
      "</tbody></table></section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderShortMineralCards(assembly) {
    const clayRows = assembly.filter(function (row) {
      return isAuthorizedClayMineral(row.candidate) && row.hasDiagnosticRangePeak;
    });
    const nonClayRows = assembly.filter(function (row) {
      return !isAuthorizedClayMineral(row.candidate);
    });
    const rows = clayRows.slice(0, 12).map(function (row) {
      const summary = mineralDescription(row.candidate || { mineral: row.mineral });
      return [
        "<article class='short-card'><h3>", mineralLink(row.mineral), "</h3>",
        "<p><strong>Nome científico:</strong> ", mineralLink(row.mineral), " · <strong>Grupo:</strong> ", escapeHtml(row.classLabel || row.group), "</p>",
        row.candidate && row.candidate.formula ? "<p><strong>Fórmula:</strong> " + escapeHtml(row.candidate.formula) + "</p>" : "",
        "<p><strong>Score/confiança:</strong> ", escapeHtml(formatScore(row.bestScore)), " · ", escapeHtml(row.bestConfidence || "não informada"), "</p>",
        "<p><strong>Evidência DRX:</strong> ", escapeHtml((row.evidences || [])[0] || "N/D"), "</p>",
        "<p><strong>Significado geológico:</strong> ", linkKnownMineralText(mineralGeologicalRole(row.mineral, row.classLabel)), "</p>",
        "<p><strong>Limitação:</strong> ", escapeHtml(truncateReportText(summary.text || "Interpretação candidata, pendente de curadoria.", 220)), "</p>",
        "</article>",
      ].join("");
    }).join("");
    const nonClayList = nonClayRows.length
      ? "<p class='note'>Minerais não argilominerais encontrados na amostra, listados sem ficha descritiva: " + mineralListLinks(nonClayRows.map(function (row) { return row.mineral; }), "N/D") + ".</p>"
      : "";
    return "<section class='report-section'><h2>Fichas mineralógicas curtas de argilominerais</h2>" + nonClayList + "<div class='short-grid'>" + (rows || "<p>Nenhum argilomineral do vocabulário autorizado com pico entre 2° e 32° 2θ foi encontrado entre os candidatos da seleção atual.</p>") + "</div></section>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderFacts(facts, limit) {
    const rows = (facts || []).slice(0, limit || 8).map(function (fact) {
      const value = fact.href
        ? "<a href=\"" + escapeHtml(fact.href) + "\">" + escapeHtml(fact.value || fact.href) + "</a>"
        : escapeHtml(fact.value || "");
      return "<li><strong>" + escapeHtml(fact.label || "Campo") + ":</strong> " + value + "</li>";
    }).join("");
    return rows ? "<ul>" + rows + "</ul>" : "";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderTechnicalBlocks(blocks) {
    const selected = (blocks || []).filter(function (block) {
      const title = String(block.title || "").toLowerCase();
      const key = String(block.key || "").toLowerCase();
      return /chemistry|quim|geoqu/i.test(title + " " + key) || /petrology|occurrence|associa|refer/i.test(title + " " + key);
    });
    return selected.slice(0, 3).map(function (block) {
      const references = (block.items || []).length
        ? "<ol>" + block.items.slice(0, 3).map(function (item) { return "<li>" + escapeHtml(truncateReportText(item, 260)) + "</li>"; }).join("") + "</ol>"
        : "<p>" + escapeHtml(truncateReportText(block.value || block.summary || "", 360)) + "</p>";
      return "<div class='tech-block'><h4>" + escapeHtml(block.title || "Bloco tecnico") + "</h4>" + references + "</div>";
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderSourceBlocks(blocks) {
    const selectedBlocks = (blocks || []).filter(function (block) {
      const key = String(block.key || "").toLowerCase();
      return key === "handbook_mineralogy";
    });
    return selectedBlocks.slice(0, 1).map(function (block) {
      const links = [
        block.href ? "<a href=\"" + escapeHtml(block.href) + "\">" + escapeHtml(block.href_label || "Abrir ficha do Handbook of Mineralogy") + "</a>" : "",
      ].filter(Boolean).join(" · ");
      const occurrenceFacts = (block.facts || []).filter(function (fact) {
        const label = String(fact.label || "").toLowerCase();
        return /ocorr|occur|associa|association/.test(label);
      });
      return [
        "<div class='source-block'><h4>Handbook of Mineralogy</h4>",
        block.badge ? "<div class='source-badge'>" + escapeHtml(block.badge) + "</div>" : "",
        links ? "<p class='source-links'>" + links + "</p>" : "",
        occurrenceFacts.length ? "<h4>Ocorrência: Associações</h4>" + renderFacts(occurrenceFacts, 4) : "",
        "</div>",
      ].join("");
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderMineralReport(candidate, summary) {
    if (summary && summary.success) {
      return [
        "<section class='mineral-note'>",
        "<h3>", mineralLink(summary.title || candidate.mineral), "</h3>",
        "<p><a href=\"", escapeHtml(summary.page_url || ""), "\">Abrir página completa na Argiloteca</a></p>",
        summary.classic_description ? "<p><strong>Descrição geral:</strong> " + escapeHtml(truncateReportText(String(summary.classic_description).split("\n\n")[0], 420)) + "</p>" : "",
        candidate.confidence ? "<p><strong>Confiança:</strong> " + escapeHtml(candidate.confidence) + "</p>" : "",
        renderTechnicalBlocks(summary.technical_blocks),
        "<h4>Handbook of Mineralogy</h4>",
        renderSourceBlocks(summary.scientific_source_blocks),
        "</section>",
      ].join("");
    }
    const description = mineralDescription(candidate);
    return [
      "<section class='mineral-note'>",
      "<h3>", escapeHtml(description.title), "</h3>",
      "<p>", escapeHtml(description.text), "</p>",
      candidate.confidence ? "<p><strong>Confiança:</strong> " + escapeHtml(candidate.confidence) + "</p>" : "",
      "</section>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fetchMineralReportSummaries(minerals) {
    return Promise.all(minerals.map(function (candidate) {
      const slug = resolveMineralSlug(candidate.mineral);
      if (!slug) return Promise.resolve([candidate.mineral, null]);
      return fetchJson("/argiloteca/argilominerais/" + encodeURIComponent(slug) + "/relatorio")
        .then(function (payload) { return [candidate.mineral, payload]; })
        .catch(function () { return [candidate.mineral, null]; });
    })).then(function (pairs) {
      const summaries = new Map();
      pairs.forEach(function (pair) {
        summaries.set(String(pair[0] || "").toLowerCase(), pair[1]);
      });
      return summaries;
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildPdfHtml(items) {
    // Monta HTML isolado para impressao/salvar PDF mantendo grafico e tabelas
    // no estado atual do painel.
    const svgMarkup = styledReportSvg();
    const assembly = buildMineralAssembly(items);
    const peakRows = buildPeakRows(items);
    const uncertainties = interpretationUncertainties(assembly, peakRows, items);
    const recommendations = recommendationsFor(items, assembly);
    const sampleRows = reportRows(items);
    return [
      "<!doctype html><html><head><meta charset='utf-8'><title>Relatorio DRX Argiloteca</title>",
      "<style>",
      "@page{size:A4 landscape;margin:9mm} body{font-family:Arial,sans-serif;color:#25332f;margin:0;line-height:1.34;background:#fff;font-size:12px}.report{background:#fff;padding:0;min-height:100vh}.cover{border-bottom:4px solid #2f6f73;padding-bottom:8px;margin-bottom:10px}.brand{color:#2f6f73;font-weight:700;text-transform:uppercase;font-size:10px;letter-spacing:.04em} h1{font-size:23px;margin:2px 0 6px;color:#1f302c} h2{font-size:16px;margin:14px 0 7px;border-bottom:1px solid #ccd8d4;padding-bottom:5px;color:#243c37} h3{font-size:13px;margin:0 0 4px;color:#243c37} h4{font-size:12px;margin:8px 0 3px;color:#31524b}.meta{color:#60706a;font-size:11px}.chart-panel{background:#fbfdfc;border:1px solid #ccd8d4;border-radius:8px;padding:8px;margin-top:8px;break-inside:avoid-page} svg{width:100%;height:auto;display:block}.sample-list,.mineral-note ul,.other-minerals ul{margin:5px 0 0 18px;padding:0}.summary-box{background:#f6faf8;border:1px solid #c7d7d2;border-left:5px solid #2f6f73;border-radius:8px;padding:9px 10px;break-inside:avoid-page}.two-cols{display:grid;grid-template-columns:1fr 1fr;gap:10px}.mineral-note{break-inside:avoid-page;border:1px solid #d8e1dd;border-left:5px solid #2f6f73;border-radius:7px;padding:8px 9px;background:#fff;margin:0 0 9px}.note{background:#f6faf8;padding:7px;border-left:4px solid #2f6f73;font-size:11px}.warning{background:#fff8ec;border-left-color:#b9892f}.tech-block,.source-block{background:#f8fbfa;border:1px solid #d8e1dd;border-radius:6px;padding:6px 8px;margin-top:5px}.source-badge{display:inline-block;background:#e7f0ed;color:#31524b;border-radius:999px;padding:2px 7px;font-size:10px}.source-links a,a{color:#2f6f73} p{margin:4px 0 7px} li{margin-bottom:2px;font-size:11px}.data-table,.compact-table{width:100%;border-collapse:collapse;margin:6px 0 10px;table-layout:fixed}.data-table th,.data-table td,.compact-table th,.compact-table td{border:1px solid #d8e1dd;padding:4px 5px;vertical-align:top;word-wrap:break-word}.data-table th,.compact-table th{background:#eaf2ef;color:#243c37;font-weight:700}.data-table{font-size:9.4px}.compact-table{font-size:11px}.data-table td:nth-child(3),.data-table td:nth-child(4),.data-table th:nth-child(3),.data-table th:nth-child(4){text-align:left}.peak-table .col-treatment{width:7%}.peak-table .col-file{width:19%}.peak-table .col-num{width:7%}.peak-table .col-reflection{width:9%}.peak-table .col-observation{width:42%}.peak-table .col-confidence{width:9%}.assembly-table .col-mineral-wide{width:12%}.assembly-table .col-group{width:14%}.assembly-table .col-treatment-wide{width:10%}.assembly-table .col-score{width:6%}.assembly-table .col-confidence{width:7%}.assembly-table .col-evidence{width:22%}.assembly-table .col-role{width:23%}.assembly-table .col-status{width:6%}.short-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.short-card{border:1px solid #d8e1dd;border-radius:7px;padding:7px;background:#fff;break-inside:avoid-page;page-break-inside:avoid;display:block;orphans:3;widows:3}.page-break{break-before:page}.report-section{break-before:page;page-break-before:always}.report-section--chart{break-before:page;page-break-before:always}.compact-section{break-inside:avoid-page;page-break-inside:avoid;margin-top:12px}.summary-box+.report-section{break-before:page}.avoid-break{break-inside:avoid-page}@media print{body{background:#fff}.chart-panel,.tech-block,.source-block,.mineral-note,.note,.summary-box,.short-card{-webkit-print-color-adjust:exact;print-color-adjust:exact}thead{display:table-header-group}tr,.short-card,.mineral-note{break-inside:avoid-page;page-break-inside:avoid}.short-card{break-inside:avoid-page;page-break-inside:avoid}button{display:none}}",
      "</style></head><body>",
      "<main class='report'>",
      "<section class='cover'><div class='brand'>Argiloteca · DRX</div><h1>Relatório de comparação DRX</h1>",
      "<p class='meta'>Gerado em ", escapeHtml(new Date().toLocaleString("pt-BR")), " · ", escapeHtml(items.length), " difratograma(s) comparado(s)</p>",
      "<p><strong>Tipo de relatório:</strong> Comparação DRX com interpretação preliminar</p>",
      "<p class='note warning'>Resultados dependem da qualidade do difratograma, preparação da amostra, sobreposição de picos e critérios de identificação. Candidatos de baixa confiança devem ser tratados como hipóteses mineralógicas.</p>",
      "<table class='compact-table'><thead><tr><th>Amostra</th><th>Arquivo</th><th>Tratamento</th><th>Candidatos principais</th></tr></thead><tbody>", sampleRows, "</tbody></table>",
      "</section>",
      renderExecutiveSummary(items, assembly, peakRows),
      "<section class='report-section report-section--chart'><h2>Gráfico comparativo interpretado</h2>",
      "<p class='meta'>Eixo X: 2θ (°). Eixo Y: intensidade conforme o modo ativo no painel; use as tabelas de picos para inspecionar evidências diagnósticas.</p>",
      "<div class='chart-panel'>", svgMarkup, "</div>",
      "</section>",
      renderMethodologyLimitations(items),
      renderPeakTable(peakRows),
      renderDiagnosticCriteria(peakRows),
      "<section class='compact-section'><h2>Interpretação preliminar</h2><p>", geologicalInterpretationHtml(assembly), "</p></section>",
      "<section class='compact-section'><h2>Limitações da interpretação</h2>", htmlList(uncertainties.concat([
        "Ausência de quantificação por Rietveld neste relatório.",
        "Possível orientação preferencial e efeitos de preparação podem alterar intensidades relativas.",
        "Integração com petrografia, FRX, MEV/EDS e dados de campo é recomendada.",
      ])), "</section>",
      "<section class='compact-section'><h2>Recomendações para refinamento</h2>", htmlList(recommendations), "</section>",
      "</main></body></html>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function exportPdfReport() {
    const items = selectedItemsInNgcOrder();
    if (!items.length) {
      statusEl.textContent = "Selecione ao menos um difratograma para gerar o PDF.";
      return;
    }
    const reportWindow = window.open("", "_blank");
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!reportWindow) {
      statusEl.textContent = "O navegador bloqueou a janela do relatório PDF.";
      return;
    }
    reportWindow.document.open();
    reportWindow.document.write("<p style='font-family:Arial,sans-serif'>Montando relatório DRX com fontes mineralógicas...</p>");
    reportWindow.document.close();
    const html = buildPdfHtml(items);
    reportWindow.document.open();
    reportWindow.document.write(html);
    reportWindow.document.close();
    reportWindow.focus();
    window.setTimeout(function () {
      reportWindow.print();
    }, 500);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function download(filename, type, content) {
    const blob = new Blob([content], { type: type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      loadRecords();
    });
    form.addEventListener("reset", function () {
      window.setTimeout(loadRecords, 0);
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (recordListEl) {
    recordListEl.addEventListener("change", function (event) {
      const id = event.target && event.target.dataset && event.target.dataset.drxId;
      if (id) toggleSelection(id, event.target.checked);
    });
  }
  selectedSummaryEl.addEventListener("click", function (event) {
    const similarButton = event.target.closest("[data-load-similar-raw]");
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (similarButton) {
      similarButton.disabled = true;
      similarButton.textContent = "Carregando RAW semelhante...";
      addPackageCurve(
        similarButton.dataset.recordId || currentRecordId(),
        similarButton.dataset.sampleCode || "",
        similarButton.dataset.filename || "",
        { loadedAsSimilar: true, similaritySource: "package_similarity" },
      ).then(function () {
        similarButton.textContent = "RAW semelhante carregado";
      }).catch(function () {
        similarButton.disabled = false;
        similarButton.textContent = "Tentar carregar novamente";
      });
      return;
    }
    const id = event.target && event.target.dataset && event.target.dataset.removeDrx;
    /**
     * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (id) {
      selected.delete(id);
      xDomain = null;
      renderAll();
    }
  });
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (mineralPanelEl) {
    mineralPanelEl.addEventListener("click", function (event) {
      const rruffButton = event.target.closest("[data-open-rruff-odr-mineral]");
      if (!rruffButton) return;
      showRruffOdrPanel({
        slug: rruffButton.dataset.openRruffOdrMineral || "",
        label: rruffButton.dataset.openRruffOdrLabel || "",
      });
      /**
       * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (rruffOdrPanelEl && typeof rruffOdrPanelEl.scrollIntoView === "function") {
        window.setTimeout(function () {
          rruffOdrPanelEl.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 60);
      }
    });
  }
  clearSelectionEl.addEventListener("click", function () {
    selected.clear();
    xDomain = null;
    renderAll();
  });
  modeEl.addEventListener("change", renderAll);
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (togglePeaksEl) {
    togglePeaksEl.addEventListener("click", function () {
      showPeakMarkers = !showPeakMarkers;
      togglePeaksEl.setAttribute("aria-pressed", showPeakMarkers ? "true" : "false");
      togglePeaksEl.textContent = showPeakMarkers ? "Ocultar picos" : "Mostrar picos";
      renderChart();
    });
  }
  resetZoomEl.addEventListener("click", function () {
    xDomain = null;
    renderChart();
  });
  exportCsvEl.addEventListener("click", exportCsv);
  if (exportJsonEl) exportJsonEl.addEventListener("click", exportJson);
  if (exportSvgEl) exportSvgEl.addEventListener("click", exportSvg);
  exportPdfEl.addEventListener("click", exportPdfReport);
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (externalRawButtonEl && externalRawFileEl) {
    externalRawButtonEl.addEventListener("click", function () {
      externalRawFileEl.click();
    });
    externalRawFileEl.addEventListener("change", function () {
      addExternalRawFiles(externalRawFileEl.files);
      externalRawFileEl.value = "";
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (referenceCompareButtonEl && referenceCompareFileEl) {
    referenceCompareButtonEl.addEventListener("click", function () {
      referenceCompareFileEl.click();
    });
    referenceCompareFileEl.addEventListener("change", function () {
      compareReferenceForSelected(referenceCompareFileEl.files && referenceCompareFileEl.files[0]);
      referenceCompareFileEl.value = "";
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (openRawPickerEl && rawPickerEl) {
    openRawPickerEl.addEventListener("click", function () {
      rawPickerEl.hidden = false;
      loadRawPickerItems();
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (closeRawPickerEl && rawPickerEl) {
    closeRawPickerEl.addEventListener("click", function () {
      rawPickerEl.hidden = true;
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (rawPickerFormEl) {
    rawPickerFormEl.addEventListener("submit", function (event) {
      event.preventDefault();
      loadRawPickerItems();
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (rawPickerListEl) {
    rawPickerListEl.addEventListener("click", function (event) {
      const snapshotButton = event.target.closest("[data-add-global-raw]");
      if (snapshotButton) {
        snapshotButton.disabled = true;
        snapshotButton.textContent = "Carregando...";
        addSnapshotRaw(snapshotButton.dataset.addGlobalRaw).then(function () {
          snapshotButton.textContent = "Adicionada";
          renderRawPickerItems([]);
          loadRawPickerItems();
        }).catch(function () {
          snapshotButton.disabled = false;
          snapshotButton.textContent = "Tentar novamente";
        });
        return;
      }
      const button = event.target.closest("[data-add-raw-sample]");
      if (!button) return;
      const recordId = currentRecordId();
      button.disabled = true;
      button.textContent = "Carregando...";
      addPackageCurve(recordId, button.dataset.addRawSample, button.dataset.filename).then(function () {
        button.textContent = "Adicionada";
      });
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (openSuggestionsEl && suggestionsPanelEl) {
    openSuggestionsEl.addEventListener("click", function () {
      suggestionsPanelEl.hidden = false;
      loadComparisonSuggestions();
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (openTriageQueueEl && suggestionsPanelEl) {
    openTriageQueueEl.addEventListener("click", function () {
      suggestionsPanelEl.hidden = false;
      loadGeologistTriageQueue();
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (toggleRruffOdrEl && rruffOdrPanelEl) {
    toggleRruffOdrEl.addEventListener("click", function () {
      if (rruffOdrPanelEl.hidden) {
        showRruffOdrPanel();
        toggleRruffOdrEl.setAttribute("aria-pressed", "true");
      } else {
        rruffOdrPanelEl.hidden = true;
        toggleRruffOdrEl.setAttribute("aria-pressed", "false");
      }
    });
  }
  /**
   * Atualiza a secao auxiliar GSAS-II. A chamada consulta apenas o backend da
   * Argiloteca, que por sua vez executa o Python do GSAS-II em subprocesso; o
   * navegador nao participa de refinamento nem de leitura direta de arquivos.
   * @returns {Promise<void>} Resultado aplicado ao painel de status.
   */
  function loadGsas2Status() {
    if (!gsas2ValidationPanelEl || !gsas2StatusUrl) return Promise.resolve();
    if (gsas2StatusBadgeEl) gsas2StatusBadgeEl.textContent = "verificando";
    if (gsas2StatusSummaryEl) {
      gsas2StatusSummaryEl.innerHTML = "<div>Status: verificando ambiente externo...</div>";
    }
    return fetch(gsas2StatusUrl, { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (payload) {
        const engine = payload.engine || {};
        const available = Boolean(engine.available);
        if (gsas2StatusBadgeEl) {
          gsas2StatusBadgeEl.textContent = available ? "disponivel" : "indisponivel";
          gsas2StatusBadgeEl.classList.toggle("argilo-drx__badge--ok", available);
          gsas2StatusBadgeEl.classList.toggle("argilo-drx__badge--warn", !available);
        }
        if (!gsas2StatusSummaryEl) return;
        const binaries = engine.binary_modules || {};
        const warnings = engine.warnings || [];
        gsas2StatusSummaryEl.innerHTML = [
          "<div><strong>Status</strong><span>" + escapeHtml(available ? "disponivel" : "indisponivel") + "</span></div>",
          "<div><strong>Python</strong><span>" + escapeHtml(engine.python || "-") + "</span></div>",
          "<div><strong>GSAS-II</strong><span>" + escapeHtml(engine.gsas2_root || "-") + "</span></div>",
          "<div><strong>Scriptable</strong><span>" + escapeHtml(engine.scriptable_import ? "ok" : "falhou") + "</span></div>",
          "<div><strong>Binarios</strong><span>" + escapeHtml(["pyspg", "pypowder", "pydiffax"].map(function (key) {
            return key + "=" + (binaries[key] ? "ok" : "nao");
          }).join(", ")) + "</span></div>",
          "<div><strong>Politica</strong><span>auxiliary_not_confirmatory</span></div>",
          warnings.length
            ? "<div class=\"argilo-drx__gsas2-warnings\"><strong>Avisos</strong><span>" + escapeHtml(warnings.join(" | ")) + "</span></div>"
            : "",
        ].join("");
      })
      .catch(function (error) {
        if (gsas2StatusBadgeEl) {
          gsas2StatusBadgeEl.textContent = "erro";
          gsas2StatusBadgeEl.classList.add("argilo-drx__badge--warn");
        }
        if (gsas2StatusSummaryEl) {
          gsas2StatusSummaryEl.innerHTML = "<div><strong>Status</strong><span>falha ao consultar GSAS-II: " + escapeHtml(error.message || String(error)) + "</span></div>";
        }
      });
  }
  // Ligacao final dos controles: paineis, exportacoes, zoom/pan e carregamentos
  // automaticos ficam concentrados aqui para separar estado, render e eventos.
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (closeRruffOdrEl && rruffOdrPanelEl) {
    closeRruffOdrEl.addEventListener("click", function () {
      rruffOdrPanelEl.hidden = true;
      if (toggleRruffOdrEl) toggleRruffOdrEl.setAttribute("aria-pressed", "false");
    });
  }
  if (rruffOdrCurveEl) rruffOdrCurveEl.addEventListener("change", renderRruffOdrPlot);
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (rruffOdrTypeEl) {
    rruffOdrTypeEl.addEventListener("change", function () {
      populateRruffOdrSelect();
      renderRruffOdrPlot();
    });
  }
  if (rruffOdrNormalizeEl) rruffOdrNormalizeEl.addEventListener("change", renderRruffOdrPlot);
  if (rruffOdrPeaksEl) rruffOdrPeaksEl.addEventListener("change", renderRruffOdrPlot);
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (loadNgcSuggestionsEl && suggestionsPanelEl) {
    loadNgcSuggestionsEl.addEventListener("click", function () {
      loadComparisonSuggestions();
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (loadTriageQueueEl && suggestionsPanelEl) {
    loadTriageQueueEl.addEventListener("click", function () {
      loadGeologistTriageQueue();
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (openSuggestionsFromRawEl && suggestionsPanelEl) {
    openSuggestionsFromRawEl.addEventListener("click", function () {
      if (rawPickerEl) rawPickerEl.hidden = true;
      suggestionsPanelEl.hidden = false;
      loadComparisonSuggestions();
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (closeSuggestionsEl && suggestionsPanelEl) {
    closeSuggestionsEl.addEventListener("click", function () {
      suggestionsPanelEl.hidden = true;
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (suggestionsListEl) {
    suggestionsListEl.addEventListener("click", function (event) {
      const triageButton = event.target.closest("[data-add-triage]");
      if (triageButton) {
        triageButton.disabled = true;
        triageButton.textContent = "Carregando...";
        addTriageCandidate(triageButton.dataset.addTriage).then(function () {
          triageButton.textContent = "Curva carregada";
        });
        return;
      }
      const button = event.target.closest("[data-add-suggestion]");
      if (!button) return;
      addSuggestion(Number(button.dataset.addSuggestion));
    });
  }
  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (mineralPanelFullscreenEls.length) {
    mineralPanelFullscreenEls.forEach(function (button) {
      button.addEventListener("click", toggleMineralPanelFullscreen);
    });
    document.addEventListener("fullscreenchange", syncMineralPanelFullscreenButton);
    syncMineralPanelFullscreenButton();
  }
  chartEl.addEventListener("wheel", function (event) {
    const items = selectedItemsInNgcOrder();
    if (!items.length) return;
    event.preventDefault();
    const allX = items.flatMap(function (item) { return item.twoTheta; });
    const domain = xDomain || extent(allX);
    const rect = chartEl.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    const center = domain[0] + ratio * (domain[1] - domain[0]);
    const factor = event.deltaY > 0 ? 1.15 : 0.85;
    const nextWidth = (domain[1] - domain[0]) * factor;
    xDomain = [center - nextWidth * ratio, center + nextWidth * (1 - ratio)];
    renderChart();
  }, { passive: false });
  chartEl.addEventListener("mousedown", function (event) {
    const items = selectedItemsInNgcOrder();
    if (!items.length) return;
    const allX = items.flatMap(function (item) { return item.twoTheta; });
    dragStart = { clientX: event.clientX, domain: (xDomain || extent(allX)).slice() };
  });
  window.addEventListener("mousemove", function (event) {
    if (!dragStart) return;
    const rect = chartEl.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const span = dragStart.domain[1] - dragStart.domain[0];
    const delta = ((event.clientX - dragStart.clientX) / width) * span;
    xDomain = [dragStart.domain[0] - delta, dragStart.domain[1] - delta];
    renderChart();
  });
  window.addEventListener("mouseup", function () {
    dragStart = null;
  });

  loadRecords()
    .then(loadPackageSelectionFromUrl)
    .then(loadMineralSelectionFromUrl);
  loadGsas2Status();
}());
