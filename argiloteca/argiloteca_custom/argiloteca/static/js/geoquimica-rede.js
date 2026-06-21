/**
 * Projeto: Painel DRX Argiloteca
 * Descrição:
 * Apoia visualização e agregação de dados geoquímicos relacionados aos registros da Argiloteca.
 * Autor:
 * Alexandre Ribas Semeler
 * E-mail: alexandre.semeler@ufrgs.br
 * Instituição:
 * Universidade Federal do Rio Grande do Sul (UFRGS)
 * Projeto:
 * Argiloteca / CPAA
 * Última revisão:
 * 2026-06-21
 * Este arquivo integra o sistema de análise,
 * comparação e interpretação de difratogramas
 * de raios X para argilominerais.
 */

(function () {
  // The network page now behaves as a scientific analogy panel:
  // nodes explain records, edges explain why two records are comparable.
  const root = document.querySelector(".argilo-geo-network");
  if (!root) return;

  const graphEl = document.getElementById("argilo-geo-network-graph");
  const form = root.querySelector('[data-role="network-filters"]');
  const statusEl = root.querySelector('[data-role="network-status"]');
  const detailsEl = root.querySelector('[data-role="node-details"]');
  const detailsTitleEl = root.querySelector('[data-role="details-title"]');
  const clusterEl = root.querySelector('[data-role="cluster-summary"]');
  const mineralMapEl = root.querySelector('[data-role="mineral-map-summary"]');
  const overviewEl = root.querySelector('[data-role="composition-overview-list"]');
  const comparisonEl = root.querySelector('[data-role="comparison-content"]');
  const legendEl = root.querySelector('[data-role="legend-content"]');
  const modeIndicatorEl = root.querySelector('[data-role="mode-indicator"]');
  const graphAreaEl = root.querySelector(".argilo-geo-network__graph-area");
  const fullscreenButtonEl = root.querySelector('[data-role="fullscreen-graph"]');
  const networkUrl = root.dataset.networkUrl;
  const recordUrlTemplate = root.dataset.recordUrlTemplate;
  const initialQueryParams = new URLSearchParams(window.location.search);
  let cy = null;
  let lastNetwork = null;
  let recentNodeSelection = [];

  const css = getComputedStyle(document.documentElement);
  const token = function (name, fallback) {
    const value = css.getPropertyValue(name).trim();
    return value || fallback;
  };

  const relationMeta = {
    analogia_composta: {
      label: "Analogia composta",
      color: token("--arg-chart-magnesiana", "#2f6f73"),
    },
    geoquimica_analoga: {
      label: "Analogia geoquímica",
      color: token("--arg-chart-ferruginosa", "#b65f3a"),
    },
    grupo_mineralogico_compativel: {
      label: "Compatibilidade mineralógica",
      color: token("--arg-chart-aluminosa", "#5c6f8c"),
    },
    contexto_geologico_semelhante: {
      label: "Analogia contextual/geológica",
      color: token("--arg-chart-silicosa", "#7a8f53"),
    },
    assinatura_funcional_semelhante: {
      label: "Analogia funcional",
      color: token("--arg-chart-calcica", "#c49a43"),
    },
  };

  const groupPalette = [
    "#2f6f73",
    "#b65f3a",
    "#5c6f8c",
    "#7a8f53",
    "#8f5f7c",
    "#c49a43",
    "#4f7f9f",
    "#8a6a3a",
    "#5e7a50",
  ];

  const confidenceOpacity = {
    alta: 0.95,
    media: 0.72,
    baixa: 0.52,
  };

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
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
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
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
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function formatPercent(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) return "Nao informado";
    return formatNumber(value, 2) + "%";
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function readableMode(mode) {
    return {
      composite: "analogia composta",
      geoquimico: "analogia geoquímica",
      mineralogico: "analogia mineralógica",
      contextual: "analogia contextual",
      funcional: "analogia funcional",
    }[mode] || mode || "analogia composta";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderTagList(values) {
    if (!values || !values.length) return "<span>Nao informado</span>";
    return values.map(function (value) {
      return '<span class="argilo-geo-network__tag">' + escapeHtml(value) + "</span>";
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderPlainList(values) {
    if (!values || !values.length) return "Nao informado";
    return values.map(escapeHtml).join(", ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderOxides(oxides) {
    const entries = Object.entries(oxides || {}).filter(function (item) {
      return typeof item[1] === "number";
    });
    if (!entries.length) return "<p>Sem tabela composicional.</p>";
    const max = Math.max.apply(null, entries.map(function (item) { return item[1]; })) || 1;

    return '<div class="argilo-geo-network__oxide-list">' + entries.map(function (item) {
      const width = Math.max(2, Math.min(100, (item[1] / max) * 100));
      return [
        '<div class="argilo-geo-network__oxide-row">',
        "<strong>", escapeHtml(item[0]), "</strong>",
        '<div class="argilo-geo-network__oxide-track"><div class="argilo-geo-network__oxide-fill" style="width:', width, '%"></div></div>',
        "<span>", formatNumber(item[1], 2), "%</span>",
        "</div>",
      ].join("");
    }).join("") + "</div>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderEvidenceList(items, emptyText) {
    if (!items || !items.length) return "<p>" + escapeHtml(emptyText) + "</p>";
    return "<ul>" + items.map(function (item) {
      const value = typeof item.value === "number" ? " (" + formatNumber(item.value, 2) + ")" : "";
      const source = item.source ? " <small>" + escapeHtml(item.source) + "</small>" : "";
      const details = item.details && item.details.length
        ? "<br><small>" + escapeHtml(item.details.join(", ")) + "</small>"
        : "";
      return "<li><strong>" + escapeHtml(item.label || item) + "</strong>" + value + source + details + "</li>";
    }).join("") + "</ul>";
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderDifferences(items) {
    if (!items || !items.length) return "<p>Sem divergencias relevantes registradas.</p>";
    return "<ul>" + items.map(function (item) {
      return "<li>" + escapeHtml(item) + "</li>";
    }).join("") + "</ul>";
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function updateModeIndicator(network) {
    if (!modeIndicatorEl) return;
    const mode = network.meta && network.meta.analysis_mode;
    modeIndicatorEl.textContent = "Modo atual: " + readableMode(mode);
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function formParams() {
    const params = new URLSearchParams();
    new FormData(form).forEach(function (value, key) {
      if (String(value).trim() !== "") params.set(key, value);
    });
    return params;
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function networkEndpoint(params) {
    const query = (params || formParams()).toString();
    return query ? networkUrl + "?" + query : networkUrl;
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function paramsFromLocation() {
    return new URLSearchParams(window.location.search);
  }

  function syncUrl(params, mode) {
    const query = params.toString();
    const nextUrl = query ? window.location.pathname + "?" + query : window.location.pathname;
    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    const historyMethod = mode === "push" ? "pushState" : "replaceState";
    window.history[historyMethod]({}, "", nextUrl);
  }

  function fillSelect(select, values) {
    if (!select) return;
    const current = select.value;
    const firstOption = select.querySelector("option");
    select.innerHTML = "";
    if (firstOption) select.appendChild(firstOption.cloneNode(true));
    (values || []).forEach(function (value) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
    select.value = current && (values || []).indexOf(current) >= 0 ? current : "";
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function applyEffectiveParams(params) {
    Array.from(form.elements).forEach(function (field) {
      if (!field || !field.name) return;
      if (field.type === "reset" || field.type === "submit" || field.type === "button") return;
      field.value = "";
    });
    Object.keys(params || {}).forEach(function (key) {
      const field = form.elements[key];
      if (field) field.value = String(params[key]);
    });
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fillFilterOptions(filters, effectiveParams) {
    fillSelect(root.querySelector('[data-role="grupo-options"]'), filters.mineral_group || []);
    fillSelect(root.querySelector('[data-role="argilomineral-options"]'), filters.argilomineral || []);
    fillSelect(root.querySelector('[data-role="ambiente-options"]'), filters.ambiente_formacao || []);
    fillSelect(root.querySelector('[data-role="rocha-options"]'), filters.rocha_hospedeira || []);
    fillSelect(root.querySelector('[data-role="era-options"]'), filters.era_geologica || []);
    fillSelect(root.querySelector('[data-role="relation-type-options"]'), filters.relation_type || []);
    fillSelect(root.querySelector('[data-role="analogy-class-options"]'), filters.analogy_class || []);
    fillSelect(root.querySelector('[data-role="confidence-class-options"]'), filters.confidence_class || []);
    applyEffectiveParams(effectiveParams || {});
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function relationColor(type) {
    const meta = relationMeta[type] || relationMeta.analogia_composta;
    return meta.color;
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function hashText(value) {
    const text = String(value || "Nao informado");
    let hash = 0;
    for (let index = 0; index < text.length; index += 1) {
      hash = ((hash << 5) - hash) + text.charCodeAt(index);
      hash |= 0;
    }
    return Math.abs(hash);
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function groupColor(group) {
    if (!group) return token("--arg-color-relation", "#6a5d7b");
    return groupPalette[hashText(group) % groupPalette.length];
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function lightGroupColor(group) {
    const base = groupColor(group);
    return base + "22";
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function edgeLineStyle(edge) {
    return edge.data("analogy_class") === "exploratoria" ? "dashed" : "solid";
  }

  function toElements(network) {
    const nodes = (network.nodes || []).map(function (node) {
      return {
        data: Object.assign({}, node, {
          display_label: node.argilominerais && node.argilominerais.length
            ? node.argilominerais.slice(0, 2).join(", ")
            : (node.grupo_mineralogico_dominante || node.label),
          size: node.ui && node.ui.size ? node.ui.size : 24,
          node_color: groupColor(node.grupo_mineralogico_dominante),
          node_halo_color: lightGroupColor(node.grupo_mineralogico_dominante),
          border_color: groupColor(node.grupo_mineralogico_dominante),
        }),
      };
    });

    const edges = (network.edges || []).map(function (edge) {
      return {
        data: Object.assign({}, edge, {
          line_color: relationColor(edge.relation_type),
          line_opacity: confidenceOpacity[edge.confidence_class] || 0.6,
          line_width: 1 + ((edge.score_total || 0) * 7),
        }),
      };
    });

    return nodes.concat(edges);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderLegend() {
    if (!legendEl) return;
    const groupItems = groupLegendItems();
    const groupLegend = groupItems.length ? [
      '<div class="argilo-geo-network__legend-section">',
      '<h3>Cores dos nós</h3>',
      groupItems.map(function (item) {
        return [
          '<div class="argilo-geo-network__legend-item">',
          '<span class="argilo-geo-network__legend-dot" style="background:', item.color, '"></span>',
          '<div><strong>', escapeHtml(item.label), '</strong>',
          '<div class="argilo-geo-network__legend-caption">Grupo mineralógico dominante.</div></div>',
          "</div>",
        ].join("");
      }).join(""),
      "</div>",
    ].join("") : "";

    legendEl.innerHTML = groupLegend + [
      '<div class="argilo-geo-network__legend-section">',
      '<h3>Cores das arestas</h3>',
      Object.keys(relationMeta).map(function (key) {
      return [
        '<div class="argilo-geo-network__legend-item">',
        '<span class="argilo-geo-network__legend-line" style="background:', relationMeta[key].color, '"></span>',
        '<div><strong>', escapeHtml(relationMeta[key].label), '</strong>',
        '<div class="argilo-geo-network__legend-caption">Aresta principal nesta dimensão.</div></div>',
        "</div>",
      ].join("");
      }).join(""),
      '<div class="argilo-geo-network__legend-item">',
      '<span class="argilo-geo-network__legend-line is-dashed"></span>',
      '<div><strong>Analogia exploratória</strong><div class="argilo-geo-network__legend-caption">Relação parcial ou advertida por divergências.</div></div>',
      "</div>",
      '<div class="argilo-geo-network__legend-item">',
      '<span class="argilo-geo-network__legend-dot"></span>',
      '<div><strong>Espessura e opacidade</strong><div class="argilo-geo-network__legend-caption">Espessura = força da analogia; opacidade = confiança.</div></div>',
      "</div>",
      "</div>",
    ].join("");
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function groupLegendItems() {
    const nodes = (lastNetwork && lastNetwork.nodes) || [];
    const groups = [];
    nodes.forEach(function (node) {
      const label = node.grupo_mineralogico_dominante || "Nao informado";
      /**
       * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (groups.some(function (item) { return item.label === label; })) return;
      groups.push({
        label: label,
        color: groupColor(label),
      });
    });
    return groups.slice(0, 9);
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function nodeMap(network) {
    return new Map((network.nodes || []).map(function (node) {
      return [node.id, node];
    }));
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderNodeDetails(node, network) {
    detailsTitleEl.textContent = "Registro selecionado";
    detailsEl.innerHTML = [
      "<h3>", escapeHtml(node.label), "</h3>",
      '<div class="argilo-geo-network__detail-grid">',
      "<div><strong>Grupo mineralógico dominante:</strong> ", escapeHtml(node.grupo_mineralogico_dominante || "Nao informado"), "</div>",
      "<div><strong>Argilominerais:</strong> ", renderPlainList(node.argilominerais), "</div>",
      "<div><strong>Códigos das amostras:</strong> ", renderPlainList(node.sample_codes), "</div>",
      "<div><strong>Localidade da amostra:</strong> ", escapeHtml(node.sample_locality || node.sample_label || "Nao informada"), "</div>",
      "<div><strong>Ambiente de formação:</strong> ", escapeHtml(node.ambiente_formacao || "Nao informado"), "</div>",
      "<div><strong>Rocha hospedeira:</strong> ", escapeHtml(node.rocha_hospedeira || "Nao informada"), "</div>",
      "<div><strong>Era geológica:</strong> ", escapeHtml(node.era_geologica || "Nao informada"), "</div>",
      "<div><strong>Formação geológica:</strong> ", escapeHtml(node.formacao_geologica || "Nao informada"), "</div>",
      "<div><strong>Razão Si/Al:</strong> ", formatNumber(node.razao_si_al, 2), "</div>",
      "<div><strong>Fração argilosa estimada:</strong> ", formatNumber(node.fracao_argilosa_estimada, 2), "</div>",
      "</div>",
      "<h4>Resumo interpretativo</h4>",
      "<p>", escapeHtml(node.resumo_estruturado || node.resultado_analise || "Nao informado"), "</p>",
      "<h4>Métodos analíticos principais</h4>",
      '<div class="argilo-geo-network__tag-list">', renderTagList(node.metodos_principais), "</div>",
      "<h4>Assinaturas funcionais</h4>",
      '<div class="argilo-geo-network__tag-list">', renderTagList(node.uses_signatures), "</div>",
      "<h4>Composição química</h4>",
      renderOxides(node.oxidos),
      "<h4>Relações mais fortes</h4>",
      renderSimilar(node.id, network),
      '<p><a class="ui primary button" href="', escapeHtml(node.links.record_html), '">Abrir registro</a> ',
      '<a class="ui button" href="', escapeHtml(recordUrlTemplate.replace("__record_id__", encodeURIComponent(node.id))), '">Ver JSON</a></p>',
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderEdgeDetails(edge, network) {
    const nodes = nodeMap(network);
    const sourceNode = nodes.get(edge.source) || {};
    const targetNode = nodes.get(edge.target) || {};
    detailsTitleEl.textContent = "Analogia selecionada";
    detailsEl.innerHTML = [
      "<h3>", escapeHtml(edge.source_label), " ↔ ", escapeHtml(edge.target_label), "</h3>",
      '<div class="argilo-geo-network__detail-grid">',
      "<div><strong>Tipo principal:</strong> ", escapeHtml((relationMeta[edge.relation_type] || {}).label || edge.relation_type), "</div>",
      "<div><strong>Classe de analogia:</strong> ", escapeHtml(edge.analogy_class || "Nao informada"), "</div>",
      "<div><strong>Confiança:</strong> ", escapeHtml(edge.confidence_class || "Nao informada"), " (", formatNumber(edge.confidence, 2), ")</div>",
      "<div><strong>Score total:</strong> ", formatNumber(edge.score_total, 2), "</div>",
      "<div><strong>Score geoquímico:</strong> ", formatNumber(edge.score_geoquimico, 2), "</div>",
      "<div><strong>Score mineralógico:</strong> ", formatNumber(edge.score_mineralogico, 2), "</div>",
      "<div><strong>Score contextual:</strong> ", formatNumber(edge.score_contextual, 2), "</div>",
      "<div><strong>Score funcional:</strong> ", formatNumber(edge.score_funcional, 2), "</div>",
      "</div>",
      "<h4>Evidências</h4>",
      renderEvidenceList(edge.evidence, "Sem evidências estruturadas registradas."),
      "<h4>Divergências e advertências</h4>",
      renderDifferences(edge.differences),
      '<p><a class="ui primary button" href="', escapeHtml((sourceNode.links || {}).record_html || "#"), '">Abrir registro A</a> ',
      '<a class="ui button" href="', escapeHtml((targetNode.links || {}).record_html || "#"), '">Abrir registro B</a> ',
      '<a class="ui button" href="', escapeHtml(recordUrlTemplate.replace("__record_id__", encodeURIComponent(edge.source))), '">JSON A</a> ',
      '<a class="ui button" href="', escapeHtml(recordUrlTemplate.replace("__record_id__", encodeURIComponent(edge.target))), '">JSON B</a></p>',
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderSimilar(nodeId, network) {
    const nodeById = nodeMap(network);
    const edges = (network.edges || [])
      .filter(function (edge) { return edge.source === nodeId || edge.target === nodeId; })
      .sort(function (a, b) { return (b.score_total || 0) - (a.score_total || 0); })
      .slice(0, 6);

    if (!edges.length) return "<p>Nenhuma analogia encontrada para o filtro atual.</p>";

    return "<ul>" + edges.map(function (edge) {
      const otherId = edge.source === nodeId ? edge.target : edge.source;
      const other = nodeById.get(otherId) || { label: otherId };
      return "<li><strong>" + escapeHtml(other.label) + "</strong> | " +
        escapeHtml((relationMeta[edge.relation_type] || {}).label || edge.relation_type) +
        " | score " + formatNumber(edge.score_total, 2) +
        " | confiança " + escapeHtml(edge.confidence_class || "nao informada") + "</li>";
    }).join("") + "</ul>";
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function updateRecentSelection(nodeId) {
    recentNodeSelection = recentNodeSelection.filter(function (id) { return id !== nodeId; });
    recentNodeSelection.push(nodeId);
    if (recentNodeSelection.length > 2) recentNodeSelection = recentNodeSelection.slice(-2);
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function buildComparisonSummary(left, right, edge) {
    const relation = edge && relationMeta[edge.relation_type] ? relationMeta[edge.relation_type].label : "analogia composta";
    const differences = edge && edge.differences && edge.differences.length
      ? edge.differences.slice(0, 2).join(" ")
      : "Sem divergências críticas registradas.";
    return [
      "Esses registros são análogos principalmente por ",
      relation.toLowerCase(),
      " com score total ",
      formatNumber(edge ? edge.score_total : 0, 2),
      ". As principais diferenças estão em: ",
      differences,
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderComparisonByIds(leftId, rightId, edge) {
    if (!comparisonEl || !lastNetwork) return;
    const nodes = nodeMap(lastNetwork);
    const left = nodes.get(leftId);
    const right = nodes.get(rightId);
    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!left || !right) {
      comparisonEl.innerHTML = "<p>Nao foi possível montar a comparação selecionada.</p>";
      return;
    }

    comparisonEl.innerHTML = [
      '<div class="argilo-geo-network__comparison-summary">',
      escapeHtml(buildComparisonSummary(left, right, edge)),
      "</div>",
      '<div class="argilo-geo-network__comparison-grid">',
      renderComparisonCard(left, "Registro A"),
      renderComparisonCard(right, "Registro B"),
      "</div>",
      edge ? [
        '<div class="argilo-geo-network__comparison-diff">',
        "<h3>Semelhanças e divergências</h3>",
        "<p><strong>Semelhanças principais:</strong></p>",
        renderEvidenceList(edge.evidence, "Sem semelhanças estruturadas."),
        "<p><strong>Divergências principais:</strong></p>",
        renderDifferences(edge.differences),
        "</div>",
      ].join("") : "",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderComparisonCard(node, label) {
    return [
      '<article class="argilo-geo-network__comparison-card">',
      "<p class=\"argilo-geo-network__comparison-label\">", escapeHtml(label), "</p>",
      "<h3>", escapeHtml(node.label), "</h3>",
      "<dl>",
      "<dt>Códigos de amostra</dt><dd>", renderPlainList(node.sample_codes), "</dd>",
      "<dt>Grupo mineralógico</dt><dd>", escapeHtml(node.grupo_mineralogico_dominante || "Nao informado"), "</dd>",
      "<dt>Argilominerais</dt><dd>", renderPlainList(node.argilominerais), "</dd>",
      "<dt>Razão Si/Al</dt><dd>", formatNumber(node.razao_si_al, 2), "</dd>",
      "<dt>Fração argilosa</dt><dd>", formatNumber(node.fracao_argilosa_estimada, 2), "</dd>",
      "<dt>Ambiente de formação</dt><dd>", escapeHtml(node.ambiente_formacao || "Nao informado"), "</dd>",
      "<dt>Rocha hospedeira</dt><dd>", escapeHtml(node.rocha_hospedeira || "Nao informada"), "</dd>",
      "<dt>Era geológica</dt><dd>", escapeHtml(node.era_geologica || "Nao informada"), "</dd>",
      "<dt>Interpretação</dt><dd>", escapeHtml(node.resultado_analise || "Nao informada"), "</dd>",
      "<dt>Usos/aplicações</dt><dd>", renderPlainList(node.uses_signatures), "</dd>",
      "</dl>",
      renderOxides(node.oxidos),
      "</article>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderClusters(network) {
    if (!network.clusters || !network.clusters.length) {
      clusterEl.innerHTML = "<h2>Agrupamentos</h2><p>Nenhum agrupamento foi calculado para o filtro atual.</p>";
      return;
    }
    clusterEl.innerHTML = [
      "<h2>Agrupamentos</h2>",
      "<p>Os agrupamentos sintetizam conjuntos conectados pela rede de analogias atual.</p>",
      '<div class="argilo-geo-network__cluster-list">',
      network.clusters.map(function (cluster) {
        return '<span class="argilo-geo-network__cluster-pill">' +
          escapeHtml(cluster.label) + ": " + cluster.size + " registros</span>";
      }).join(""),
      "</div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderMineralMap(network) {
    if (!network.mineral_map || !network.mineral_map.length) {
      mineralMapEl.innerHTML = "<h2>Mapa de argilominerais da rede</h2><p>Nenhum argilomineral mapeado para o recorte atual.</p>";
      return;
    }
    mineralMapEl.innerHTML = [
      "<h2>Mapa de argilominerais da rede</h2>",
      "<p>Relações inferidas a partir de <code>subject</code> e dos registros conectados pela análise composta.</p>",
      '<div class="argilo-geo-network__cluster-list">',
      network.mineral_map.map(function (item) {
        const groups = item.groups && item.groups.length ? " | grupos: " + item.groups.map(escapeHtml).join(", ") : "";
        return '<span class="argilo-geo-network__cluster-pill">' +
          escapeHtml(item.mineral) + ": " + item.count_records + " registros" + groups + "</span>";
      }).join(""),
      "</div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderOverview(network) {
    if (!overviewEl) return;
    if (!network.nodes || !network.nodes.length) {
      overviewEl.innerHTML = "<p>Nenhum registro atende aos filtros atuais.</p>";
      return;
    }
    overviewEl.innerHTML = [
      '<div class="argilo-geo-network__overview-grid">',
      network.nodes.map(function (node) {
        return [
          '<article class="argilo-geo-network__overview-card">',
          "<h3>", escapeHtml(node.label), "</h3>",
          '<div class="argilo-geo-network__overview-meta">',
          "<div><strong>Grupo dominante:</strong> ", escapeHtml(node.grupo_mineralogico_dominante || "Nao informado"), "</div>",
          "<div><strong>Ambiente:</strong> ", escapeHtml(node.ambiente_formacao || "Nao informado"), "</div>",
          "<div><strong>Rocha hospedeira:</strong> ", escapeHtml(node.rocha_hospedeira || "Nao informada"), "</div>",
          "<div><strong>Era:</strong> ", escapeHtml(node.era_geologica || "Nao informada"), "</div>",
          "</div>",
          renderOxides(node.oxidos),
          '<div class="argilo-geo-network__overview-actions">',
          '<a class="ui small button" href="', escapeHtml(node.links.record_html), '">Abrir registro</a>',
          '<button class="ui small button" type="button" data-role="focus-record" data-record-id="', escapeHtml(node.id), '">Focar na rede</button>',
          "</div>",
          "</article>",
        ].join("");
      }).join(""),
      "</div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderGraph(network) {
    const elements = toElements(network);
    if (cy) cy.destroy();

    cy = cytoscape({
      container: graphEl,
      elements: elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(node_color)",
            "border-color": "data(border_color)",
            "border-width": 3,
            color: token("--arg-color-text", "#223039"),
            width: "data(size)",
            height: "data(size)",
            label: "data(display_label)",
            "font-size": 11,
            "text-wrap": "wrap",
            "text-max-width": 120,
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.9,
            "text-background-padding": 3,
            "text-margin-y": -8,
            "shadow-blur": 22,
            "shadow-color": "data(node_color)",
            "shadow-opacity": 0.24,
            "overlay-opacity": 0,
          },
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "line-color": "data(line_color)",
            opacity: "data(line_opacity)",
            width: "data(line_width)",
            "line-style": edgeLineStyle,
            "target-arrow-shape": "none",
            "overlay-opacity": 0,
          },
        },
        {
          selector: ".faded",
          style: {
            opacity: 0.12,
            "text-opacity": 0.08,
          },
        },
        {
          selector: ".selected-neighborhood",
          style: {
            opacity: 1,
            "border-width": 5,
            "text-background-opacity": 1,
          },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        fit: true,
        padding: 45,
      },
      wheelSensitivity: 0.25,
    });

    cy.on("tap", "node", function (event) {
      const node = event.target;
      highlightNeighborhood(node.closedNeighborhood());
      updateRecentSelection(node.id());
      renderNodeDetails(node.data(), network);
      // Two consecutive node selections act as a lightweight pairwise comparison mode.
      /**
       * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (recentNodeSelection.length === 2) {
        const pairEdge = findEdgeBetween(recentNodeSelection[0], recentNodeSelection[1], network);
        renderComparisonByIds(recentNodeSelection[0], recentNodeSelection[1], pairEdge);
      }
    });

    cy.on("tap", "edge", function (event) {
      const edge = event.target;
      highlightNeighborhood(edge.connectedNodes().union(edge));
      // Edge selection is the primary path for explainable analogy inspection.
      renderEdgeDetails(edge.data(), network);
      renderComparisonByIds(edge.data("source"), edge.data("target"), edge.data());
    });

    cy.on("tap", function (event) {
      if (event.target === cy) cy.elements().removeClass("faded selected-neighborhood");
    });
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function findEdgeBetween(leftId, rightId, network) {
    return (network.edges || []).find(function (edge) {
      return (edge.source === leftId && edge.target === rightId) || (edge.source === rightId && edge.target === leftId);
    }) || null;
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function highlightNeighborhood(elements) {
    cy.elements().addClass("faded").removeClass("selected-neighborhood");
    elements.removeClass("faded").addClass("selected-neighborhood");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderWarnings(network) {
    const warnings = (network.meta && network.meta.warnings) || [];
    const relationCounts = network.meta && network.meta.relation_counts ? network.meta.relation_counts : {};
    const relationSummary = Object.keys(relationCounts).length
      ? " | relações: " + Object.keys(relationCounts).map(function (key) {
        return key + " " + relationCounts[key];
      }).join(", ")
      : "";
    statusEl.textContent = (network.meta.total_registros || 0) + " registros, " + (network.meta.total_relacoes || 0) + " relações" + relationSummary;
    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (warnings.length) {
      statusEl.textContent += " | " + warnings.join(" ");
    }
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadNetwork(options) {
    options = options || {};
    const params = options.params || formParams();
    statusEl.textContent = "Carregando painel de analogias...";
    fetch(networkEndpoint(params), { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("Falha ao carregar rede: HTTP " + response.status);
        return response.json();
      })
      .then(function (network) {
        lastNetwork = network;
        fillFilterOptions(network.filters || {}, (network.meta || {}).effective_params || {});
        updateModeIndicator(network);
        renderLegend();
        syncUrl(formParams(), options.historyMode || "replace");
        renderGraph(network);
        renderClusters(network);
        renderMineralMap(network);
        renderOverview(network);
        renderWarnings(network);

        /**
         * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
         * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
         */
        if (network.nodes && network.nodes.length) {
          renderNodeDetails(network.nodes[0], network);
          recentNodeSelection = [network.nodes[0].id];
        } else {
          detailsTitleEl.textContent = "Registro selecionado";
          detailsEl.innerHTML = "<p>Nenhum registro científico atende aos filtros atuais.</p>";
          comparisonEl.innerHTML = "<p>Nenhuma comparação disponível para o recorte atual.</p>";
        }
      })
      .catch(function (error) {
        statusEl.textContent = error.message;
        detailsTitleEl.textContent = "Registro selecionado";
        detailsEl.innerHTML = "<p>Nao foi possivel carregar a rede.</p>";
        if (comparisonEl) comparisonEl.innerHTML = "<p>Comparação indisponível.</p>";
      });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    loadNetwork({ historyMode: "push" });
  });

  form.addEventListener("reset", function () {
    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    setTimeout(function () {
      loadNetwork({ historyMode: "push" });
    }, 0);
  });

  root.querySelector('[data-role="fit-graph"]').addEventListener("click", function () {
    if (cy) cy.fit(undefined, 45);
  });

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function updateFullscreenButton() {
    if (!fullscreenButtonEl) return;
    const active = document.fullscreenElement === graphAreaEl;
    fullscreenButtonEl.setAttribute("aria-pressed", active ? "true" : "false");
    fullscreenButtonEl.textContent = active ? "Sair da tela cheia" : "Tela cheia";
    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (cy) {
      setTimeout(function () {
        cy.resize();
        cy.fit(undefined, active ? 70 : 45);
      }, 120);
    }
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  if (fullscreenButtonEl && graphAreaEl) {
    fullscreenButtonEl.addEventListener("click", function () {
      if (document.fullscreenElement === graphAreaEl) {
        document.exitFullscreen();
        return;
      }
      /**
       * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (graphAreaEl.requestFullscreen) {
        graphAreaEl.requestFullscreen();
      }
    });
    document.addEventListener("fullscreenchange", updateFullscreenButton);
  }

  root.addEventListener("click", function (event) {
    const trigger = event.target.closest('[data-role="focus-record"]');
    if (!trigger || !cy) return;
    const node = cy.getElementById(trigger.dataset.recordId);
    if (!node || !node.length) return;
    highlightNeighborhood(node.closedNeighborhood());
    renderNodeDetails(node.data(), lastNetwork);
    cy.animate({
      center: { eles: node },
      zoom: Math.max(cy.zoom(), 1.05),
      duration: 300,
    });
  });

  window.addEventListener("popstate", function () {
    loadNetwork({ params: paramsFromLocation(), historyMode: "replace" });
  });

  renderLegend();
  loadNetwork({ params: initialQueryParams, historyMode: "replace" });
})();
