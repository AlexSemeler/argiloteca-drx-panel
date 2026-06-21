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
  const root = document.querySelector(".argilo-geo-atlas");
  if (!root) return;

  const endpoint = root.dataset.endpoint;
  const form = root.querySelector('[data-role="filters-form"]');
  const statusEl = root.querySelector('[data-role="status"]');
  const statsEl = root.querySelector('[data-role="stats-cards"]');
  const barEl = root.querySelector('[data-role="bar-chart"]');
  const radarEl = root.querySelector('[data-role="radar-chart"]');
  const tableEl = root.querySelector('[data-role="table-wrap"]');
  const barDimensionEl = root.querySelector('[data-role="bar-dimension"]');
  const barOxideEl = root.querySelector('[data-role="bar-oxide"]');
  const radarDimensionEl = root.querySelector('[data-role="radar-dimension"]');
  const tableMineralControlEl = root.querySelector('[data-role="table-mineral-control"]');
  const tableMineralFilterEl = root.querySelector('[data-role="table-mineral-filter"]');
  let currentData = null;
  const css = getComputedStyle(document.documentElement);
  const token = function (name, fallback) {
    const value = css.getPropertyValue(name).trim();
    return value || fallback;
  };

  const RADAR_OXIDES = ["SiO2", "Al2O3", "Fe2O3", "MgO", "CaO", "K2O"];
  const SERIES_COLORS = [
    token("--arg-chart-magnesiana", "#2f6f73"),
    token("--arg-chart-ferruginosa", "#b65f3a"),
    token("--arg-chart-aluminosa", "#5c6f8c"),
    token("--arg-chart-silicosa", "#7a8f53"),
    token("--arg-color-relation", "#6a5d7b"),
    token("--arg-chart-calcica", "#c49a43"),
  ];

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
    if (typeof value !== "number" || !Number.isFinite(value)) return "—";
    return value.toLocaleString("pt-BR", {
      minimumFractionDigits: digits || 0,
      maximumFractionDigits: digits || 2,
    });
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function normalizeComparable(value) {
    return String(value || "")
      .trim()
      .toLocaleLowerCase("pt-BR")
      .replace(/\s+/g, " ");
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function sameText(first, second) {
    const normalizedFirst = normalizeComparable(first);
    const normalizedSecond = normalizeComparable(second);
    return Boolean(normalizedFirst && normalizedFirst === normalizedSecond);
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function firstDistinct(values) {
    const accepted = [];
    values.forEach(function (value) {
      const text = String(value || "").trim();
      if (!text) return;
      /**
       * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (accepted.some(function (item) { return sameText(item, text); })) return;
      accepted.push(text);
    });
    return accepted;
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function queryString() {
    const params = new URLSearchParams();
    new FormData(form).forEach(function (value, key) {
      if (String(value).trim() !== "") params.set(key, value);
    });
    const query = params.toString();
    return query ? endpoint + "?" + query : endpoint;
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fillSelect(select, values) {
    if (!select) return;
    const current = select.value;
    const firstOption = select.querySelector("option");
    select.innerHTML = "";
    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (firstOption) {
      select.appendChild(firstOption.cloneNode(true));
    }
    values.forEach(function (value) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
    if (current && values.indexOf(current) >= 0) {
      select.value = current;
    }
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderStats(data) {
    const summary = data.summary || {};
    const meta = data.meta || {};
    const oxideStats = summary.oxide_statistics || {};
    const sio2Mean = oxideStats.SiO2 ? oxideStats.SiO2.mean : null;
    const al2o3Mean = oxideStats.Al2O3 ? oxideStats.Al2O3.mean : null;
    statsEl.innerHTML = [
      statCard("Linhas científicas", meta.total_rows),
      statCard("Registros únicos", meta.total_records),
      statCard("Com amostra", summary.with_sample),
      statCard("Com era geológica", summary.with_era),
      statCard("SiO2 médio", sio2Mean !== null ? formatNumber(sio2Mean, 2) + "%" : "—"),
      statCard("Al2O3 médio", al2o3Mean !== null ? formatNumber(al2o3Mean, 2) + "%" : "—"),
    ].join("");
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function statCard(label, value) {
    return [
      '<article class="argilo-geo-atlas__stat-card">',
      '<div class="argilo-geo-atlas__stat-label">', escapeHtml(label), "</div>",
      '<div class="argilo-geo-atlas__stat-value">', escapeHtml(String(value || "0")), "</div>",
      "</article>",
    ].join("");
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function currentAggregation() {
    if (!currentData) return [];
    const key = barDimensionEl.value;
    return ((currentData.aggregations || {})[key] || []).filter(function (item) {
      return item.averages && typeof item.averages[barOxideEl.value] === "number";
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderBarChart() {
    const aggregation = currentAggregation();
    const dimension = barDimensionEl.value;
    const oxide = barOxideEl.value;
    if (!aggregation.length) {
      barEl.innerHTML = '<div class="argilo-geo-atlas__empty">Dados insuficientes para o agrupamento selecionado.</div>';
      return;
    }

    const max = Math.max.apply(null, aggregation.map(function (item) { return item.averages[oxide]; })) || 1;
    barEl.innerHTML = [
      '<div class="argilo-geo-atlas__bar-chart">',
      aggregation.map(function (item) {
        const width = Math.max(2, (item.averages[oxide] / max) * 100);
        return [
          '<div class="argilo-geo-atlas__bar-row" data-dimension="', escapeHtml(dimension), '" data-label="', escapeHtml(item.label), '">',
          '<div class="argilo-geo-atlas__bar-label">', escapeHtml(item.label), '<small>', item.count_records, ' registros</small></div>',
          '<div class="argilo-geo-atlas__bar-track"><div class="argilo-geo-atlas__bar-fill" style="width:', width, '%"></div></div>',
          '<div class="argilo-geo-atlas__bar-value">', formatNumber(item.averages[oxide], 2), '%</div>',
          "</div>",
        ].join("");
      }).join(""),
      "</div>",
    ].join("");
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function polygonPoints(values, radius, centerX, centerY) {
    return values.map(function (value, index) {
      const angle = (-Math.PI / 2) + (index * 2 * Math.PI / values.length);
      const scaled = radius * value;
      const x = centerX + Math.cos(angle) * scaled;
      const y = centerY + Math.sin(angle) * scaled;
      return [x, y].join(",");
    }).join(" ");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRadar() {
    if (!currentData) return;
    const aggregation = ((currentData.aggregations || {})[radarDimensionEl.value] || [])
      .filter(function (item) { return item.averages; })
      .slice(0, 4);

    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!aggregation.length) {
      radarEl.innerHTML = '<div class="argilo-geo-atlas__empty">Dados insuficientes para o radar comparativo.</div>';
      return;
    }

    const maxByOxide = {};
    RADAR_OXIDES.forEach(function (oxide) {
      const values = aggregation
        .map(function (item) { return item.averages[oxide]; })
        .filter(function (value) { return typeof value === "number"; });
      maxByOxide[oxide] = values.length ? Math.max.apply(null, values) : 1;
    });

    const centerX = 210;
    const centerY = 210;
    const radius = 140;
    const circles = [0.25, 0.5, 0.75, 1].map(function (ratio) {
      return '<circle cx="' + centerX + '" cy="' + centerY + '" r="' + (radius * ratio) + '" fill="none" stroke="' + token("--arg-chart-grid", "#d8dee2") + '" stroke-dasharray="4 4"></circle>';
    }).join("");
    const axes = RADAR_OXIDES.map(function (oxide, index) {
      const angle = (-Math.PI / 2) + (index * 2 * Math.PI / RADAR_OXIDES.length);
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;
      const lx = centerX + Math.cos(angle) * (radius + 22);
      const ly = centerY + Math.sin(angle) * (radius + 22);
      return [
        '<line x1="', centerX, '" y1="', centerY, '" x2="', x, '" y2="', y, '" stroke="', token("--arg-chart-grid", "#d8dee2"), '"></line>',
        '<text x="', lx, '" y="', ly, '" text-anchor="middle" font-size="12" fill="', token("--arg-color-text-muted", "#5f6b65"), '">', escapeHtml(oxide), "</text>",
      ].join("");
    }).join("");

    const seriesSvg = aggregation.map(function (item, index) {
      const color = SERIES_COLORS[index % SERIES_COLORS.length];
      const normalized = RADAR_OXIDES.map(function (oxide) {
        const value = item.averages[oxide];
        const max = maxByOxide[oxide] || 1;
        return typeof value === "number" ? Math.max(0.05, value / max) : 0.05;
      });
      return '<polygon points="' + polygonPoints(normalized, radius, centerX, centerY) + '" fill="' + color + '22" stroke="' + color + '" stroke-width="2"></polygon>';
    }).join("");

    const legend = aggregation.map(function (item, index) {
      const color = SERIES_COLORS[index % SERIES_COLORS.length];
      return [
        '<button class="argilo-geo-atlas__legend-item" type="button" data-role="radar-filter" data-dimension="', escapeHtml(radarDimensionEl.value), '" data-label="', escapeHtml(item.label), '">',
        '<span class="argilo-geo-atlas__legend-swatch" style="background:', color, '"></span>',
        '<span><strong>', escapeHtml(item.label), '</strong><br><small>', item.count_records, ' registros</small></span>',
        "</button>",
      ].join("");
    }).join("");

    radarEl.innerHTML = [
      '<div class="argilo-geo-atlas__radar-wrap">',
      '<svg viewBox="0 0 420 420" role="img" aria-label="Radar comparativo">',
      circles,
      axes,
      seriesSvg,
      "</svg>",
      '<div class="argilo-geo-atlas__radar-legend">', legend, "</div>",
      "</div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderTable() {
    const rows = (currentData && currentData.records) || [];
    if (!rows.length) {
      tableEl.innerHTML = '<div class="argilo-geo-atlas__empty">Nenhuma linha científica atende aos filtros atuais.</div>';
      return;
    }

    const selectedMineral = tableMineralFilterEl ? tableMineralFilterEl.value : "";
    const visibleRows = selectedMineral
      ? rows.filter(function (row) {
          return normalizeComparable(row.mineral_name) === normalizeComparable(selectedMineral);
        })
      : rows;

    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!visibleRows.length) {
      tableEl.innerHTML = '<div class="argilo-geo-atlas__empty">Nenhuma linha científica para o argilomineral selecionado.</div>';
      return;
    }

    const groupedRows = groupRowsByRecord(visibleRows);

    tableEl.innerHTML = [
      '<div class="argilo-geo-atlas__table-wrap">',
      '<table class="argilo-geo-atlas__table">',
      "<thead><tr>",
      "<th>Registro</th><th>Amostra</th><th>Era</th><th>Período</th><th>Grupo</th><th>Argilomineral</th>",
      "<th>SiO2</th><th>Al2O3</th><th>Fe2O3</th><th>MgO</th><th>CaO</th><th>K2O</th><th>Na2O</th><th>TiO2</th><th>LOI</th><th>PF</th>",
      "</tr></thead><tbody>",
      groupedRows.map(renderRecordGroup).join(""),
      "</tbody></table></div>",
    ].join("");
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function groupRowsByRecord(rows) {
    const groups = [];
    const byRecord = {};
    rows.forEach(function (row) {
      const key = row.record_id || row.record_title || row.row_id;
      /**
       * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (!byRecord[key]) {
        byRecord[key] = {
          record: row,
          rows: [],
        };
        groups.push(byRecord[key]);
      }
      byRecord[key].rows.push(row);
    });
    return groups;
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRecordGroup(group) {
    const rows = group.rows;
    return rows.map(function (row, index) {
      const firstRow = index === 0;
      const className = firstRow ? "argilo-geo-atlas__record-start" : "";
      return [
        '<tr class="', className, '">',
        firstRow ? renderRecordCell(group.record, rows.length) : "",
        firstRow ? renderSampleCell(group.record, rows.length) : "",
        "<td>", escapeHtml(row.era || "—"), "</td>",
        "<td>", escapeHtml(row.periodo || "—"), "</td>",
        "<td>", escapeHtml(row.mineral_group || "—"), "</td>",
        "<td>", renderMineralCell(row, rows), "</td>",
        numericCell(row.oxides.SiO2),
        numericCell(row.oxides.Al2O3),
        numericCell(row.oxides.Fe2O3),
        numericCell(row.oxides.MgO),
        numericCell(row.oxides.CaO),
        numericCell(row.oxides.K2O),
        numericCell(row.oxides.Na2O),
        numericCell(row.oxides.TiO2),
        numericCell(row.oxides.LOI),
        numericCell(row.oxides.PF),
        "</tr>",
      ].join("");
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderRecordCell(row, rowSpan) {
    const title = row.record_title || row.record_id || "Registro";
    const showRecordId = row.record_id && !sameText(row.record_id, title);
    return [
      '<td class="argilo-geo-atlas__record-cell" rowspan="', rowSpan || 1, '">',
      '<a href="', escapeHtml(row.links.record_html), '">', escapeHtml(title), "</a>",
      showRecordId ? '<small>' + escapeHtml(row.record_id) + "</small>" : "",
      "</td>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderSampleCell(row, rowSpan) {
    const distinctLabels = firstDistinct([
      row.sample_code,
      row.sample_label,
      row.sample_id,
    ]).filter(function (label) {
      return !sameText(label, row.record_title) && !sameText(label, row.record_id);
    });
    const locality = row.locality && !distinctLabels.some(function (label) {
      return sameText(label, row.locality);
    })
      ? String(row.locality).trim()
      : "";

    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!distinctLabels.length && !locality) {
      return '<td rowspan="' + (rowSpan || 1) + '">—</td>';
    }

    return [
      '<td rowspan="', rowSpan || 1, '">',
      distinctLabels.length ? escapeHtml(distinctLabels.join(" / ")) : "—",
      locality ? "<small>" + escapeHtml(locality) + "</small>" : "",
      "</td>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderMineralCell(row, siblingRows) {
    const mineral = row.mineral_name || "Não informado";
    const repeated = siblingRows.filter(function (item) {
      return sameText(item.mineral_name, row.mineral_name);
    }).length > 1;
    return [
      '<span class="argilo-geo-atlas__mineral-name">', escapeHtml(mineral), "</span>",
      repeated ? '<small>mesmo argilomineral em mais de uma linha analítica deste registro</small>' : "",
    ].join("");
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function numericCell(value) {
    return '<td class="is-numeric">' + (typeof value === "number" ? formatNumber(value, 2) : "—") + "</td>";
  }

  function renderFilters(data) {
    const filters = data.filters || {};
    fillSelect(root.querySelector('[data-role="eon-options"]'), filters.eon || []);
    fillSelect(root.querySelector('[data-role="era-options"]'), filters.era || []);
    fillSelect(root.querySelector('[data-role="periodo-options"]'), filters.periodo || []);
    fillSelect(root.querySelector('[data-role="epoca-options"]'), filters.epoca || []);
    fillSelect(root.querySelector('[data-role="group-options"]'), filters.mineral_group || []);
    fillSelect(root.querySelector('[data-role="mineral-options"]'), filters.argilomineral || []);
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderTableMineralFilter(data) {
    if (!tableMineralControlEl || !tableMineralFilterEl) return;
    const rows = (data && data.records) || [];
    const current = tableMineralFilterEl.value;
    const options = [];
    rows.forEach(function (row) {
      const value = row.mineral_name || "";
      /**
       * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      if (!value || options.some(function (item) { return sameText(item.value, value); })) return;
      options.push({
        value: value,
        label: value,
      });
    });

    options.sort(function (a, b) {
      return a.label.localeCompare(b.label, "pt-BR");
    });

    tableMineralFilterEl.innerHTML = '<option value="">Todos</option>';
    options.forEach(function (item) {
      const option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.label;
      tableMineralFilterEl.appendChild(option);
    });

    tableMineralControlEl.hidden = options.length <= 1;
    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (current && options.some(function (item) { return sameText(item.value, current); })) {
      tableMineralFilterEl.value = current;
    } else {
      tableMineralFilterEl.value = "";
    }
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function updateAll() {
    renderStats(currentData);
    renderBarChart();
    renderRadar();
    renderTableMineralFilter(currentData);
    renderTable();
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function loadData() {
    statusEl.textContent = "Carregando painel geoquímico...";
    fetch(queryString(), { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("Falha ao carregar painel: HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        currentData = data;
        renderFilters(data);
        updateAll();
        statusEl.textContent =
          (data.meta.total_rows || 0) +
          " linhas científicas filtradas em " +
          (data.meta.total_records || 0) +
          " registros.";
      })
      .catch(function (error) {
        statusEl.textContent = error.message;
        statsEl.innerHTML = '<div class="argilo-geo-atlas__empty">Não foi possível carregar o painel.</div>';
        barEl.innerHTML = "";
        radarEl.innerHTML = "";
        tableEl.innerHTML = "";
      });
  }

  /**
   * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function setFilterForDimension(dimension, label) {
    const mapping = {
      by_era: "era",
      by_periodo: "periodo",
      by_epoca: "epoca",
      by_mineral_group: "mineral_group",
      by_argilomineral: "argilomineral",
    };
    const fieldName = mapping[dimension];
    if (!fieldName) return;
    const field = form.elements[fieldName];
    if (!field) return;
    field.value = label === "Não informado" ? "" : label;
    loadData();
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    loadData();
  });

  root.querySelector('[data-role="clear-filters"]').addEventListener("click", function () {
    setTimeout(loadData, 0);
  });

  [barDimensionEl, barOxideEl, radarDimensionEl, tableMineralFilterEl].forEach(function (element) {
    if (!element) return;
    element.addEventListener("change", updateAll);
  });

  root.addEventListener("click", function (event) {
    const bar = event.target.closest(".argilo-geo-atlas__bar-row");
    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (bar) {
      setFilterForDimension(bar.dataset.dimension, bar.dataset.label);
      return;
    }

    const radarFilter = event.target.closest('[data-role="radar-filter"]');
    /**
     * Atualiza a visualização geoquímica da Argiloteca a partir dos dados recebidos do backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (radarFilter) {
      setFilterForDimension(radarFilter.dataset.dimension, radarFilter.dataset.label);
    }
  });

  loadData();
})();
