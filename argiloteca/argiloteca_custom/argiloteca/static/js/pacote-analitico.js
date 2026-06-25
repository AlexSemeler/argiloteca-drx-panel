/**
 * Projeto: Painel DRX Argiloteca
 * Descrição:
 * Controla comportamento de interface do painel Argiloteca, consumindo APIs backend e renderizando resultados para o usuário.
 * Autor:
 * Alexandre Ribas Semeler
 * E-mail: alexandre.semeler@ufrgs.br
 * Projeto:
 * Argiloteca / CPAA
 * Última revisão:
 * 2026-06-21
 * Este arquivo integra o sistema de análise,
 * comparação e interpretação de difratogramas
 * de raios X para argilominerais.
 */

(function () {
  // Controla a pagina de pacote analitico DRX: lista arquivos, exporta revisao
  // e carrega curvas sem alterar o manifesto recebido do backend.
  const root = document.querySelector(".argilo-package");
  if (!root) return;

  const apiUrl = root.dataset.apiUrl;
  const recordId = root.dataset.recordId || "";
  const recordTitle = root.dataset.recordTitle || recordId || "Pacote analitico";
  const curveUrl = root.dataset.curveUrl || (function () {
    const parts = window.location.pathname.split("/").filter(Boolean);
    const recordId = parts[parts.length - 1] || "";
    return "/argiloteca/analises/" + encodeURIComponent(recordId) + "/drx/curva";
  })();
  // Fallback local para quando o template ainda nao injeta o catalogo
  // autorizado de argilominerais.
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
    clorita: "chlorite",
    "clorita-esmectita": "chlorite-smectite",
    "clorita-vermiculita": "chlorite-vermiculite",
    ilita: "illite",
    "ilita-esmectita": "illite-smectite",
  };
  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
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
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function parseAuthorizedMineralAliases() {
    try {
      const parsed = JSON.parse(root.dataset.authorizedMineralAliases || "{}");
      return parsed && Object.keys(parsed).length ? parsed : defaultAuthorizedMineralAliases;
    } catch (error) {
      return defaultAuthorizedMineralAliases;
    }
  }
  const authorizedMineralSlugs = new Set(parseAuthorizedMineralSlugs());
  const authorizedMineralAliases = parseAuthorizedMineralAliases();
  const summaryEl = root.querySelector('[data-role="summary"]');
  const filtersEl = root.querySelector('[data-role="filters"]');
  const itemsEl = root.querySelector('[data-role="items"]');
  const statusEl = root.querySelector('[data-role="status"]');
  const pageInfoEl = root.querySelector('[data-role="page-info"]');
  const prevBtn = root.querySelector('[data-role="prev"]');
  const nextBtn = root.querySelector('[data-role="next"]');
  const exportCsvBtn = root.querySelector('[data-role="export-csv"]');
  const exportPdfBtn = root.querySelector('[data-role="export-pdf"]');
  const compareSelectedBtn = root.querySelector('[data-role="compare-selected"]');
  const fullscreenBtn = root.querySelector('[data-role="package-fullscreen"]');
  const viewerEl = root.querySelector('[data-role="viewer"]');
  const viewerTitleEl = root.querySelector('[data-role="viewer-title"]');
  const viewerMetaEl = root.querySelector('[data-role="viewer-meta"]');
  const viewerCloseBtn = root.querySelector('[data-role="viewer-close"]');
  const chartEl = root.querySelector('[data-role="chart"]');
  const state = { offset: 0, limit: 100, total: 0 };
  const compareSelection = new Map();
  let staticManifest = null;

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function isFullscreen() {
    return document.fullscreenElement === root || root.classList.contains("argilo-package--fullscreen");
  }

  function syncFullscreenButton() {
    if (!fullscreenBtn) return;
    fullscreenBtn.textContent = isFullscreen() ? "Sair da tela cheia" : "Tela cheia";
    fullscreenBtn.setAttribute("aria-pressed", isFullscreen() ? "true" : "false");
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function toggleFullscreen() {
    if (document.fullscreenElement === root && document.exitFullscreen) {
      document.exitFullscreen();
      return;
    }
    /**
     * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (root.requestFullscreen) {
      root.requestFullscreen();
      return;
    }
    root.classList.toggle("argilo-package--fullscreen");
    syncFullscreenButton();
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function formatBytes(value) {
    const bytes = Number(value || 0);
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
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
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
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
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function mineralLink(name) {
    const slug = resolveMineralSlug(name);
    if (!slug) return escapeHtml(name || "Mineral candidato");
    return '<a href="/argilominerais/' + encodeURIComponent(slug) + '">' + escapeHtml(name) + "</a>";
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function recordUrl(item) {
    const id = String((item && item.record_id) || recordId || "").trim();
    return /^[a-z0-9]{5}-[a-z0-9]{5}$/i.test(id) ? "/records/" + encodeURIComponent(id) : "";
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function recordButton(item) {
    const url = recordUrl(item);
    return url ? '<a class="ui tiny button" href="' + escapeHtml(url) + '">Registro</a>' : "";
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function params() {
    return paramsFor(state.offset, state.limit);
  }

  function paramsFor(offset, limit) {
    const data = new FormData(filtersEl);
    const query = new URLSearchParams();
    query.set("limit", limit == null ? state.limit : limit);
    query.set("offset", offset == null ? state.offset : offset);
    ["q", "preparation", "mineral"].forEach(function (name) {
      const value = (data.get(name) || "").trim();
      if (value) query.set(name, value);
    });
    return query.toString();
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function staticManifestUrl() {
    const parts = window.location.pathname.split("/").filter(Boolean);
    const recordId = parts[parts.length - 1] || "";
    return "/argiloteca/static/data/analytical_packages/" + encodeURIComponent(recordId) + "/drx_manifest.json";
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function itemMatchesText(item, query) {
    if (!query) return true;
    const normalized = query.toLowerCase();
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
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function itemMatchesMineral(item, mineral) {
    if (!mineral) return true;
    const normalized = mineral.toLowerCase();
    return (item.mineral_candidates || []).some(function (candidate) {
      return String(candidate.mineral || "").toLowerCase().indexOf(normalized) !== -1;
    });
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function payloadFromStaticManifest(manifest) {
    return payloadFromStaticManifestRange(manifest, state.offset, state.limit);
  }

  function payloadFromStaticManifestRange(manifest, offset, limit) {
    const data = new FormData(filtersEl);
    const q = (data.get("q") || "").trim();
    const preparation = (data.get("preparation") || "").trim();
    const mineral = (data.get("mineral") || "").trim();
    let rows = manifest.items || [];
    /**
     * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (preparation) {
      rows = rows.filter(function (item) { return item.preparation === preparation; });
    }
    if (mineral) {
      rows = rows.filter(function (item) { return itemMatchesMineral(item, mineral); });
    }
    /**
     * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (q) {
      rows = rows.filter(function (item) { return itemMatchesText(item, q); });
    }
    const total = rows.length;
    const page = rows.slice(offset, offset + limit);
    return {
      success: true,
      exists: true,
      record_id: manifest.record_id,
      analysis_type: manifest.analysis_type || "drx",
      summary: manifest.summary || {},
      source: manifest.source || {},
      generated_at: manifest.generated_at,
      items: page,
      pagination: { total: total, limit: limit, offset: offset, returned: page.length },
    };
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fetchStaticPayload() {
    // Mantem a pagina funcional em deploys estaticos ou antes da API paginada.
    if (staticManifest) {
      return Promise.resolve(payloadFromStaticManifest(staticManifest));
    }
    return fetch(staticManifestUrl(), { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("Falha ao carregar manifesto analitico. API e manifesto estatico indisponiveis.");
        return response.json();
      })
      .then(function (manifest) {
        staticManifest = manifest;
        statusEl.textContent = "Usando manifesto estatico ate o servidor registrar a API paginada.";
        return payloadFromStaticManifest(staticManifest);
      });
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fetchPayload() {
    return fetch(apiUrl + "?" + params(), { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (response.ok) return response.json();
        if (response.status === 404) return fetchStaticPayload();
        throw new Error("Falha ao carregar manifesto analitico. HTTP " + response.status + ".");
      });
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fetchPayloadPage(offset, limit) {
    return fetch(apiUrl + "?" + paramsFor(offset, limit), { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (response.ok) return response.json();
        if (response.status === 404) {
          if (staticManifest) return payloadFromStaticManifestRange(staticManifest, offset, limit);
          return fetch(staticManifestUrl(), { headers: { Accept: "application/json" } })
            .then(function (staticResponse) {
              if (!staticResponse.ok) throw new Error("Falha ao carregar manifesto analitico para exportacao.");
              return staticResponse.json();
            })
            .then(function (manifest) {
              staticManifest = manifest;
              return payloadFromStaticManifestRange(staticManifest, offset, limit);
            });
        }
        throw new Error("Falha ao carregar dados para exportacao. HTTP " + response.status + ".");
      });
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function fetchAllFilteredItems() {
    // Exportacoes precisam varrer todas as paginas filtradas, nao apenas a
    // pagina atualmente visivel na tabela.
    const limit = 500;
    return fetchPayloadPage(0, limit).then(function (first) {
      const total = Number((first.pagination || {}).total || (first.items || []).length || 0);
      const items = (first.items || []).slice();
      const requests = [];
      /**
       * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
       * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
       */
      for (let offset = limit; offset < total; offset += limit) {
        requests.push(fetchPayloadPage(offset, limit));
      }
      return requests.reduce(function (promise, requestPromise) {
        return promise.then(function () {
          return requestPromise.then(function (payload) {
            items.push.apply(items, payload.items || []);
          });
        });
      }, Promise.resolve()).then(function () {
        return { payload: first, items: items, total: total };
      });
    });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderSummary(payload) {
    if (!payload.exists) {
      summaryEl.innerHTML = '<div class="argilo-package__empty">' + escapeHtml(payload.message || "Manifesto nao encontrado.") + "</div>";
      return;
    }
    const summary = payload.summary || {};
    const prep = summary.by_preparation || {};
    const topMinerals = (summary.top_minerals || []).slice(0, 5).map(function (item) {
      return escapeHtml(item.mineral) + " (" + escapeHtml(item.count) + ")";
    }).join(", ");
    summaryEl.innerHTML = [
      '<div class="argilo-package__metric"><span>Arquivos brutos</span><strong>', escapeHtml(summary.total_files || 0), "</strong></div>",
      '<div class="argilo-package__metric"><span>Amostras/base</span><strong>', escapeHtml(summary.samples_count || 0), "</strong></div>",
      '<div class="argilo-package__metric"><span>Tamanho referenciado</span><strong>', escapeHtml(formatBytes(summary.total_size_bytes)), "</strong></div>",
      '<div class="argilo-package__metric"><span>Preparações</span><strong>', escapeHtml(Object.keys(prep).length), "</strong><small>",
      escapeHtml(Object.entries(prep).map(function (entry) { return entry[0] + ": " + entry[1]; }).join(" · ") || "Nao informado"),
      "</small></div>",
      '<div class="argilo-package__metric"><span>Minerais candidatos frequentes</span><small>', topMinerals || "Sem candidatos", "</small></div>",
    ].join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderCandidates(item) {
    const candidates = item.mineral_candidates || [];
    if (!candidates.length) return "Sem candidato mineralogico registrado.";
    return candidates.slice(0, 3).map(function (candidate) {
      const matches = candidate.matches || [];
      const evidence = matches.length
        ? matches.slice(0, 2).map(function (match) {
            return "d ref. " + escapeHtml(match.reference_d || "") + " / obs. " + escapeHtml(match.observed_d || "");
          }).join("; ")
        : escapeHtml(candidate.evidence || "sem evidência detalhada");
      return '<span class="argilo-package__candidate"><strong>' + mineralLink(candidate.mineral || "Mineral candidato")
        + '</strong> · score ' + escapeHtml(candidate.score || "n/d") + '<br><small>' + evidence + "</small></span>";
    }).join("");
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderPeakValues(item, field) {
    const peaks = item.detected_peaks || item.peaks || [];
    const values = peaks.slice(0, 8).map(function (peak) {
      const value = field === "d"
        ? (peak.d || peak.d_spacing || peak.d_angstrom)
        : (peak[field] || peak.twoTheta);
      return value == null ? "" : Number(value).toFixed(field === "d" ? 3 : 2);
    }).filter(Boolean);
    return values.length ? values.join(", ") : "Sem pico detectado";
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function candidateText(item) {
    const candidates = item.mineral_candidates || [];
    if (!candidates.length) return "";
    return candidates.map(function (candidate) {
      const matches = candidate.matches || [];
      const evidence = matches.slice(0, 3).map(function (match) {
        return "d_ref=" + (match.reference_d || "") + " d_obs=" + (match.observed_d || "");
      }).join("; ");
      return [
        candidate.mineral || "Mineral candidato",
        candidate.score != null ? "score=" + candidate.score : "",
        candidate.confidence ? "conf=" + candidate.confidence : "",
        evidence,
      ].filter(Boolean).join(" | ");
    }).join(" ; ");
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function csvValue(value) {
    const text = String(value == null ? "" : value).replace(/\r?\n/g, " ").trim();
    return '"' + text.replace(/"/g, '""') + '"';
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function exportRows(items) {
    // CSV/PDF carregam campos cientificos e de rastreabilidade sem expandir RAW.
    return items.map(function (item) {
      const metadata = item.metadata || {};
      const advanced = item.advanced_summary || {};
      return {
        record_id: item.record_id || recordId,
        record_title: recordTitle,
        sample_code: item.sample_code || "",
        sample_base: item.sample_base || "",
        filename: item.filename || "",
        preparation: item.preparation_label || item.preparation || "",
        status: item.status || "",
        size_bytes: item.size_bytes || "",
        sha256: item.sha256 || "",
        parser: metadata.parser || "",
        detected_format: metadata.detected_format || "",
        points: metadata.points || advanced.points || "",
        peaks_two_theta: renderPeakValues(item, "two_theta"),
        peaks_d: renderPeakValues(item, "d"),
        candidates: candidateText(item),
        advanced_result_path: item.advanced_result_path || "",
        fit_results: advanced.fit_results || (item.fit_results || []).length || "",
        mineral_evidence: advanced.mineral_evidence || (item.mineral_evidence || []).length || "",
        mineral_characterization: advanced.mineral_characterization || (item.mineral_characterization || []).length || "",
        qc_flags: advanced.qc_flags || (item.qc_flags || []).length || "",
      };
    });
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function downloadText(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 500);
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function exportCsv() {
    if (exportCsvBtn) exportCsvBtn.classList.add("loading");
    fetchAllFilteredItems()
      .then(function (result) {
        const rows = exportRows(result.items);
        const headers = [
          "record_id", "record_title", "sample_code", "sample_base", "filename", "preparation",
          "status", "size_bytes", "sha256", "parser", "detected_format", "points",
          "peaks_two_theta", "peaks_d", "candidates", "advanced_result_path",
          "fit_results", "mineral_evidence", "mineral_characterization", "qc_flags",
        ];
        const csv = [headers.map(csvValue).join(",")].concat(rows.map(function (row) {
          return headers.map(function (header) { return csvValue(row[header]); }).join(",");
        })).join("\n");
        downloadText("pacote-analitico-" + (recordId || "registro") + ".csv", csv + "\n", "text/csv;charset=utf-8");
        statusEl.textContent = "CSV exportado com " + rows.length + " item(ns).";
      })
      .catch(function (error) {
        statusEl.textContent = error.message;
      })
      .finally(function () {
        if (exportCsvBtn) exportCsvBtn.classList.remove("loading");
      });
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function shortText(value, maxLength) {
    const text = String(value == null ? "" : value);
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength - 1) + "...";
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function exportPdf() {
    if (exportPdfBtn) exportPdfBtn.classList.add("loading");
    fetchAllFilteredItems()
      .then(function (result) {
        const rows = exportRows(result.items);
        const opened = window.open("", "_blank");
        if (!opened) throw new Error("O navegador bloqueou a janela de PDF. Permita pop-ups para exportar.");
        const generatedAt = new Date().toLocaleString();
        const tableRows = rows.map(function (row) {
          return [
            "<tr>",
            "<td>", escapeHtml(row.sample_code), "<br><small>", escapeHtml(row.sample_base), "</small></td>",
            "<td>", escapeHtml(row.filename), "<br><small>", escapeHtml(row.preparation), "</small></td>",
            "<td>", escapeHtml(row.peaks_two_theta), "</td>",
            "<td>", escapeHtml(row.peaks_d), "</td>",
            "<td>", escapeHtml(shortText(row.candidates, 420)), "</td>",
            "<td>", escapeHtml(row.parser || row.detected_format || ""), "</td>",
            "</tr>",
          ].join("");
        }).join("");
        opened.document.open();
        opened.document.write([
          "<!doctype html><html><head><meta charset=\"utf-8\"><title>Pacote analítico DRX</title>",
          "<style>",
          "body{font-family:Arial,sans-serif;color:#1f2f35;margin:24px;} h1{font-size:22px;margin:0 0 6px;} h2{font-size:15px;margin-top:18px;} .meta{color:#53666d;margin-bottom:18px;} table{width:100%;border-collapse:collapse;font-size:10.5px;} th,td{border:1px solid #cfdadd;padding:6px;vertical-align:top;} th{background:#eef5f5;text-align:left;} small{color:#617177;} .actions{margin:0 0 16px;} .actions button{padding:8px 12px;} @media print{.actions{display:none;} body{margin:12mm;} table{font-size:9px;} tr{break-inside:avoid;}}",
          "</style></head><body>",
          "<div class=\"actions\"><button onclick=\"window.print()\">Imprimir / salvar PDF</button></div>",
          "<h1>Pacote analítico DRX</h1>",
          "<div class=\"meta\"><strong>", escapeHtml(recordTitle), "</strong><br>Registro: ", escapeHtml(recordId),
          "<br>Gerado em: ", escapeHtml(generatedAt), "<br>Itens exportados: ", escapeHtml(rows.length), "</div>",
          "<h2>Dados analíticos exportados</h2>",
          "<table><thead><tr><th>Amostra</th><th>Arquivo / preparação</th><th>Picos 2θ</th><th>Espaçamentos d</th><th>Candidatos e evidências</th><th>Parser</th></tr></thead><tbody>",
          tableRows || "<tr><td colspan=\"6\">Nenhum item encontrado para os filtros atuais.</td></tr>",
          "</tbody></table>",
          "</body></html>",
        ].join(""));
        opened.document.close();
        opened.focus();
        statusEl.textContent = "PDF preparado com " + rows.length + " item(ns). Use imprimir/salvar PDF na nova janela.";
      })
      .catch(function (error) {
        statusEl.textContent = error.message;
      })
      .finally(function () {
        if (exportPdfBtn) exportPdfBtn.classList.remove("loading");
      });
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderAdvancedSummary(item) {
    const summary = item.advanced_summary || {};
    const parts = [];
    if (item.advanced_result_path) {
      parts.push("resultado avançado");
    }
    if (summary.fit_results || (item.fit_results || []).length) {
      parts.push((summary.fit_results || (item.fit_results || []).length) + " ajuste(s)");
    }
    if (summary.mineral_evidence || (item.mineral_evidence || []).length) {
      parts.push((summary.mineral_evidence || (item.mineral_evidence || []).length) + " evidência(s)");
    }
    if (summary.mineral_characterization || (item.mineral_characterization || []).length) {
      parts.push((summary.mineral_characterization || (item.mineral_characterization || []).length) + " caracterização(ões)");
    }
    if (summary.qc_flags || (item.qc_flags || []).length) {
      parts.push((summary.qc_flags || (item.qc_flags || []).length) + " flag(s) QC");
    }
    if (!parts.length) return "";
    return '<br><small class="argilo-package__advanced">Avançado: ' + escapeHtml(parts.join(" · ")) + "</small>";
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function comparisonUrl(item) {
    // Abre o mesmo item no comparador DRX, preservando amostra e arquivo.
    const query = new URLSearchParams();
    query.set("record_id", item.record_id || "");
    query.set("sample_code", item.sample_code || "");
    query.set("filename", item.filename || "");
    query.set("source", "package");
    return "/drx/comparacao?" + query.toString();
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function comparisonKey(item) {
    return [
      item.record_id || recordId,
      item.sample_code || "",
      item.filename || "",
    ].join("||");
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function updateCompareSelectedButton() {
    if (!compareSelectedBtn) return;
    const count = compareSelection.size;
    compareSelectedBtn.disabled = count < 1;
    compareSelectedBtn.textContent = count > 0 ? "Comparar selecionados (" + count + ")" : "Comparar selecionados";
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function selectedComparisonUrl() {
    // Envia uma selecao manual de curvas para o comparador sem reformatar nomes.
    const query = new URLSearchParams();
    query.set("record_id", recordId || "");
    query.set("source", "package");
    query.set("samples", JSON.stringify(Array.from(compareSelection.values()).map(function (item) {
      return {
        sample_code: item.sample_code || "",
        filename: item.filename || "",
      };
    })));
    return "/drx/comparacao?" + query.toString();
  }

  /**
   * Executa etapa de interface do painel DRX, exibindo dados de difratogramas, evidências auxiliares ou controles de análise para o usuário.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function renderItems(payload) {
    const rows = payload.items || [];
    const pagination = payload.pagination || {};
    state.total = pagination.total || 0;
    statusEl.textContent = state.total + " arquivo(s) encontrados para os filtros atuais.";
    pageInfoEl.textContent = "Exibindo " + (pagination.offset + 1) + "-" + (pagination.offset + rows.length) + " de " + state.total;
    prevBtn.disabled = state.offset <= 0;
    nextBtn.disabled = state.offset + state.limit >= state.total;
    /**
     * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!rows.length) {
      itemsEl.innerHTML = '<tr><td colspan="8">Nenhum arquivo encontrado para os filtros atuais.</td></tr>';
      return;
    }
    itemsEl.innerHTML = rows.map(function (item) {
      const key = comparisonKey(item);
      const checked = compareSelection.has(key) ? " checked" : "";
      return [
        "<tr>",
        '<td><input type="checkbox" data-role="compare-check" data-key="', escapeHtml(key), '" data-sample-code="', escapeHtml(item.sample_code || ""), '" data-filename="', escapeHtml(item.filename || ""), '"', checked, ' aria-label="Selecionar ', escapeHtml(item.sample_code || item.filename || "amostra"), '"></td>',
        "<td><strong>", escapeHtml(item.sample_code), "</strong><br><small>base: ", escapeHtml(item.sample_base || ""), "</small></td>",
        "<td>", escapeHtml(item.filename), "<br><small>", escapeHtml(formatBytes(item.size_bytes)), "</small></td>",
        "<td>", escapeHtml(item.preparation_label || item.preparation || "Nao informado"), "<br><small>", escapeHtml(item.preparation_evidence || ""), "</small></td>",
        '<td class="argilo-package__peaks">', escapeHtml(renderPeakValues(item, "two_theta")), "</td>",
        '<td class="argilo-package__peaks">', escapeHtml(renderPeakValues(item, "d")), "</td>",
        "<td>", renderCandidates(item), renderAdvancedSummary(item), "</td>",
        '<td><div class="argilo-package__row-actions"><a class="ui tiny button" href="', escapeHtml(comparisonUrl(item)), '">Ver difratograma</a>', recordButton(item), "</div></td>",
        "</tr>",
      ].join("");
    }).join("");
    updateCompareSelectedButton();
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function scale(value, domainMin, domainMax, rangeMin, rangeMax) {
    if (domainMax === domainMin) return rangeMin;
    return rangeMin + ((value - domainMin) / (domainMax - domainMin)) * (rangeMax - rangeMin);
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function drawCurve(payload) {
    // Visualizador SVG simples para inspecao rapida de uma curva do pacote.
    const x = payload.two_theta || [];
    const y = payload.intensity || [];
    const width = 920;
    const height = 420;
    const margin = { top: 24, right: 24, bottom: 48, left: 62 };
    /**
     * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (!x.length || !y.length) {
      chartEl.innerHTML = '<text x="40" y="60">Sem dados de curva.</text>';
      return;
    }
    const xMin = Math.min.apply(null, x);
    const xMax = Math.max.apply(null, x);
    const yMin = Math.min.apply(null, y);
    const yMax = Math.max.apply(null, y);
    const points = x.map(function (value, index) {
      const px = scale(value, xMin, xMax, margin.left, width - margin.right);
      const py = scale(y[index], yMin, yMax, height - margin.bottom, margin.top);
      return px.toFixed(1) + "," + py.toFixed(1);
    }).join(" ");
    const nodes = [];
    /**
     * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    for (let i = 0; i <= 5; i += 1) {
      const gx = scale(i, 0, 5, margin.left, width - margin.right);
      const gy = scale(i, 0, 5, height - margin.bottom, margin.top);
      nodes.push('<line class="argilo-package__grid" x1="' + gx + '" y1="' + margin.top + '" x2="' + gx + '" y2="' + (height - margin.bottom) + '"></line>');
      nodes.push('<line class="argilo-package__grid" x1="' + margin.left + '" y1="' + gy + '" x2="' + (width - margin.right) + '" y2="' + gy + '"></line>');
    }
    nodes.push('<line class="argilo-package__axis" x1="' + margin.left + '" y1="' + (height - margin.bottom) + '" x2="' + (width - margin.right) + '" y2="' + (height - margin.bottom) + '"></line>');
    nodes.push('<line class="argilo-package__axis" x1="' + margin.left + '" y1="' + margin.top + '" x2="' + margin.left + '" y2="' + (height - margin.bottom) + '"></line>');
    nodes.push('<polyline class="argilo-package__curve" points="' + points + '"></polyline>');
    nodes.push('<text class="argilo-package__axis-label" x="' + (width / 2) + '" y="' + (height - 12) + '" text-anchor="middle">2θ</text>');
    nodes.push('<text class="argilo-package__axis-label" x="18" y="' + (height / 2) + '" transform="rotate(-90 18 ' + (height / 2) + ')" text-anchor="middle">Intensidade</text>');
    nodes.push('<text class="argilo-package__axis-label" x="' + margin.left + '" y="' + (height - 30) + '">' + xMin.toFixed(2) + '</text>');
    nodes.push('<text class="argilo-package__axis-label" x="' + (width - margin.right) + '" y="' + (height - 30) + '" text-anchor="end">' + xMax.toFixed(2) + '</text>');
    chartEl.innerHTML = nodes.join("");
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function showCurve(sampleCode, filename) {
    viewerEl.hidden = false;
    viewerTitleEl.textContent = "Difratograma " + sampleCode;
    viewerMetaEl.textContent = "Carregando " + filename + "...";
    chartEl.innerHTML = '<text x="40" y="60">Carregando curva...</text>';
    const query = new URLSearchParams();
    query.set("sample_code", sampleCode);
    query.set("filename", filename);
    query.set("max_points", "2500");
    fetch(curveUrl + "?" + query.toString(), { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("Nao foi possivel carregar a curva. Reinicie o servidor se a rota ainda estiver antiga.");
        return response.json();
      })
      .then(function (payload) {
        viewerMetaEl.textContent = [
          payload.filename,
          (payload.metadata && payload.metadata.points ? payload.metadata.points + " pontos" : ""),
          (payload.metadata && payload.metadata.detected_format ? payload.metadata.detected_format : ""),
        ].filter(Boolean).join(" · ");
        drawCurve(payload);
        viewerEl.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function (error) {
        viewerMetaEl.textContent = error.message;
        chartEl.innerHTML = '<text x="40" y="60">' + escapeHtml(error.message) + "</text>";
      });
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function load() {
    // Fluxo principal de recarga: busca payload, resumo e linhas da tabela.
    statusEl.textContent = "Carregando pacote analitico...";
    fetchPayload()
      .then(function (payload) {
        renderSummary(payload);
        renderItems(payload);
      })
      .catch(function (error) {
        statusEl.textContent = error.message;
        itemsEl.innerHTML = '<tr><td colspan="7">' + escapeHtml(error.message) + "</td></tr>";
      });
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function handleCompareSelectionChange(event) {
    const input = event.target.closest('[data-role="compare-check"]');
    if (!input) return;
    const key = input.dataset.key || "";
    if (!key) return;
    /**
     * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
     * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
     */
    if (input.checked) {
      compareSelection.set(key, {
        record_id: recordId,
        sample_code: input.dataset.sampleCode || "",
        filename: input.dataset.filename || "",
      });
    } else {
      compareSelection.delete(key);
    }
    updateCompareSelectedButton();
  }

  /**
   * Executa uma ação de interface da Argiloteca mantendo o contrato esperado pelo HTML e pelas APIs backend.
   * @returns {void} Resultado aplicado diretamente ao estado visual ou ao fluxo chamador.
   */
  function compareSelected() {
    if (!compareSelection.size) return;
    window.location.href = selectedComparisonUrl();
  }

  // Eventos de UI ficam no final para deixar claro onde o estado e conectado.
  filtersEl.addEventListener("submit", function (event) {
    event.preventDefault();
    state.offset = 0;
    load();
  });
  prevBtn.addEventListener("click", function () {
    state.offset = Math.max(0, state.offset - state.limit);
    load();
  });
  nextBtn.addEventListener("click", function () {
    state.offset += state.limit;
    load();
  });
  viewerCloseBtn.addEventListener("click", function () {
    viewerEl.hidden = true;
  });
  if (exportCsvBtn) exportCsvBtn.addEventListener("click", exportCsv);
  if (exportPdfBtn) exportPdfBtn.addEventListener("click", exportPdf);
  if (compareSelectedBtn) compareSelectedBtn.addEventListener("click", compareSelected);
  if (fullscreenBtn) fullscreenBtn.addEventListener("click", toggleFullscreen);
  document.addEventListener("fullscreenchange", syncFullscreenButton);
  itemsEl.addEventListener("change", handleCompareSelectionChange);

  syncFullscreenButton();
  load();
})();
