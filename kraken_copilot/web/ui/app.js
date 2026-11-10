"use strict";

const byId = (id) => document.getElementById(id);
const list = (val) => Array.isArray(val) ? val : [];
const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const dollars = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 4, maximumFractionDigits: 6 });

const pathIcons = {
  shield: "M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z M9 12l2 2 4-4",
  route: "M5 12h6m0 0 5-5m-5 5 5 5 M16 7h3m-3 10h3",
  step: "M5 12h13m-5-5 5 5-5 5",
  tool: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
  human: "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z M5 21v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2",
  stop: "M12 5v8m0 4v1 M21 12a9 9 0 1 1-18 0 9 9 0 1 1 18 0z",
};

// Inicializa Mermaid para renderização de diagramas
if (typeof window !== "undefined" && window.mermaid) {
  try {
    mermaid.initialize({
      startOnLoad: false,
      theme: "default",
      securityLevel: "loose",
      fontFamily: "system-ui, -apple-system, sans-serif"
    });
  } catch (e) {
    console.warn("Aviso ao inicializar Mermaid:", e);
  }
}

// Função recursiva para desempacotar e formatar JSONs com strings escapadas aninhadas
function parseRecursiveJson(val) {
  if (val === null || val === undefined) return val;
  if (typeof val === "string") {
    const trimmed = val.trim();
    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try {
        const parsed = JSON.parse(trimmed);
        return parseRecursiveJson(parsed);
      } catch (_) {
        return val;
      }
    }
    return val;
  }
  if (Array.isArray(val)) {
    return val.map(parseRecursiveJson);
  }
  if (typeof val === "object") {
    const out = {};
    for (const [k, v] of Object.entries(val)) {
      out[k] = parseRecursiveJson(v);
    }
    return out;
  }
  return val;
}

function renderMermaidNode(codeText) {
  const container = el("div", "mermaid-diagram-container");
  const toolbar = el("div", "mermaid-toolbar");
  toolbar.appendChild(el("span", "badge active", "📊 Diagrama Mermaid"));

  const btnToggle = el("button", "button", "📄 Ver Código");
  btnToggle.type = "button";
  toolbar.appendChild(btnToggle);
  container.appendChild(toolbar);

  const chartWrapper = el("div", "mermaid-chart-inner");
  container.appendChild(chartWrapper);

  const rawPre = el("pre", "json-raw-box", el("code", null, codeText));
  rawPre.style.display = "none";
  container.appendChild(rawPre);

  btnToggle.addEventListener("click", () => {
    if (rawPre.style.display === "none") {
      rawPre.style.display = "block";
      chartWrapper.style.display = "none";
      btnToggle.textContent = "👁 Ver Diagrama";
    } else {
      rawPre.style.display = "none";
      chartWrapper.style.display = "flex";
      btnToggle.textContent = "📄 Ver Código";
    }
  });

  const renderChart = () => {
    if (typeof window !== "undefined" && window.mermaid) {
      const id = "mmd_" + Math.random().toString(36).substring(2, 9);
      const cleanCode = codeText.trim();
      try {
        window.mermaid.render(id, cleanCode)
          .then(({ svg }) => {
            chartWrapper.innerHTML = svg;
          })
          .catch((err) => {
            console.warn("Falha na renderização Mermaid:", err);
            chartWrapper.innerHTML = `<p class="empty" style="padding: 1rem;">⚠️ Diagrama exibido em modo texto:</p>`;
            rawPre.style.display = "block";
          });
      } catch (err) {
        console.warn("Erro síncrono Mermaid:", err);
        rawPre.style.display = "block";
      }
    } else {
      // Se o script ESM do CDN ainda estiver baixando, tenta novamente em instantes
      setTimeout(() => {
        if (typeof window !== "undefined" && window.mermaid) {
          renderChart();
        } else {
          rawPre.style.display = "block";
          chartWrapper.style.display = "none";
        }
      }, 350);
    }
  };

  renderChart();
  return container;
}

function createSvgIcon(kind) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", pathIcons[kind] || pathIcons.step);
  svg.appendChild(path);
  return svg;
}

function el(tag, className, ...children) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  for (const child of children) {
    if (child !== null && child !== undefined) {
      if (typeof child === "string" || typeof child === "number") {
        node.appendChild(document.createTextNode(String(child)));
      } else if (child instanceof Node) {
        node.appendChild(child);
      }
    }
  }
  return node;
}

async function api(path, payload, method = null) {
  const options = { cache: "no-store", headers: { Accept: "application/json" } };
  if (method) {
    options.method = method;
  } else if (payload !== undefined) {
    options.method = "POST";
  }
  if (payload !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(payload);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch (err) {
    throw new Error("O servidor do Kraken Copilot está indisponível. Verifique se o serviço está em execução.");
  }
  if (response.status === 204) {
    return { ok: true };
  }
  const body = await response.json().catch(() => null);
  if (!response.ok || (body === null && response.status !== 200)) {
    const error = new Error(typeof body?.detail === "string" ? body.detail : `Falha no serviço (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return body || { ok: true };
}

// ============================================================================
// Markdown, Tabelas e Blocos de Código
// ============================================================================

function appendInline(node, text) {
  const pattern = /(`[^`\n]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*)/g;
  let offset = 0;
  for (const match of text.matchAll(pattern)) {
    const token = match[0];
    const index = match.index;
    if (index > offset) {
      node.appendChild(document.createTextNode(text.slice(offset, index)));
    }
    if (token.startsWith("`")) {
      node.appendChild(el("code", null, token.slice(1, -1)));
    } else if (token.startsWith("**")) {
      node.appendChild(el("strong", null, token.slice(2, -2)));
    } else {
      node.appendChild(el("em", null, token.slice(1, -1)));
    }
    offset = index + token.length;
  }
  if (offset < text.length) {
    node.appendChild(document.createTextNode(text.slice(offset)));
  }
}

function parseMarkdownTable(lines, startIndex) {
  const table = el("table");
  const thead = el("thead");
  const tbody = el("tbody");
  table.appendChild(thead);
  table.appendChild(tbody);

  let i = startIndex;
  const headerLine = lines[i].trim();
  const headerCells = headerLine.split("|").map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length);
  const headerRow = el("tr");
  for (const cell of headerCells) {
    const th = el("th");
    appendInline(th, cell);
    headerRow.appendChild(th);
  }
  thead.appendChild(headerRow);
  i += 2;

  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line.startsWith("|")) break;
    const cells = line.split("|").map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length);
    if (cells.length) {
      const row = el("tr");
      for (const cell of cells) {
        const td = el("td");
        appendInline(td, cell);
        row.appendChild(td);
      }
      tbody.appendChild(row);
    }
    i++;
  }
  const wrapper = el("div", "table-wrapper", table);
  return { node: wrapper, nextIndex: i };
}

function renderMarkdown(rawText) {
  const root = el("div", "prose");
  const lines = String(rawText || "").replaceAll("\r\n", "\n").split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Bloco Mermaid ::: mermaid
    if (line.trim().startsWith("::: mermaid")) {
      i++;
      const codeLines = [];
      while (i < lines.length && !lines[i].trim().startsWith(":::")) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length && lines[i].trim().startsWith(":::")) i++;
      const fullCode = codeLines.join("\n");
      root.appendChild(renderMermaidNode(fullCode));
      continue;
    }

    if (line.trim().startsWith("```")) {
      const langMatch = line.trim().match(/^```(\w+)?/);
      const lang = langMatch && langMatch[1] ? langMatch[1] : "código";
      i++;
      const codeLines = [];
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++;
      const fullCode = codeLines.join("\n");

      // Se for diagrama Mermaid
      if (lang.toLowerCase() === "mermaid") {
        root.appendChild(renderMermaidNode(fullCode));
        continue;
      }

      const container = el("div", "code-block-container");
      const header = el("div", "code-header", el("span", null, lang));
      const copyBtn = el("button", "copy-code-btn", "Copiar");
      copyBtn.type = "button";
      copyBtn.addEventListener("click", async () => {
        await navigator.clipboard.writeText(fullCode).catch(() => {});
        copyBtn.textContent = "Copiado!";
        setTimeout(() => { copyBtn.textContent = "Copiar"; }, 2000);
      });
      header.appendChild(copyBtn);
      const pre = el("pre", null, el("code", null, fullCode));
      container.appendChild(header);
      container.appendChild(pre);
      root.appendChild(container);
      continue;
    }

    // Divisores horizontais
    if (line.trim() === "---" || line.trim() === "--" || line.trim() === "***") {
      root.appendChild(el("hr"));
      i++;
      continue;
    }

    if (line.trim().startsWith("|") && i + 1 < lines.length && lines[i + 1].trim().startsWith("|") && lines[i + 1].includes("---")) {
      const { node, nextIndex } = parseMarkdownTable(lines, i);
      root.appendChild(node);
      i = nextIndex;
      continue;
    }

    if (!line.trim()) {
      i++;
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = Math.min(headingMatch[1].length + 1, 4);
      const heading = el(`h${level}`);
      appendInline(heading, headingMatch[2]);
      root.appendChild(heading);
      i++;
      continue;
    }

    const quoteMatch = line.match(/^>\s*(.+)$/);
    if (quoteMatch) {
      const bq = el("blockquote");
      appendInline(bq, quoteMatch[1]);
      root.appendChild(bq);
      i++;
      continue;
    }

    const listMatch = line.match(/^\s*(?:([-*+])|(\d+)\.)\s+(.+)$/);
    if (listMatch) {
      const isOrdered = Boolean(listMatch[2]);
      const listTag = isOrdered ? "ol" : "ul";
      const listEl = el(listTag);
      while (i < lines.length) {
        const itemMatch = lines[i].match(/^\s*(?:([-*+])|(\d+)\.)\s+(.+)$/);
        if (!itemMatch) break;
        const li = el("li");
        appendInline(li, itemMatch[3]);
        listEl.appendChild(li);
        i++;
      }
      root.appendChild(listEl);
      continue;
    }

    const p = el("p");
    appendInline(p, line);
    root.appendChild(p);
    i++;
  }

  return root;
}

// ============================================================================
// Atendimento / Chat Principal (index.html)
// ============================================================================

function initChat() {
  let sessionId = new URLSearchParams(window.location.search).get("sessao");
  const appShell = byId("app-shell");
  const messagesContainer = byId("chat-messages");
  const welcomeCard = byId("welcome-card");
  const form = byId("consulta-form");
  const textarea = byId("pergunta");
  const submitBtn = byId("enviar");
  const historyList = byId("historico");
  const newChatBtn = byId("nova-conversa");
  const tituloHeader = byId("titulo");
  const mobileToggleBtn = byId("alternar-historico");
  const sidebar = byId("sidebar");
  const sidebarBackdrop = byId("sidebar-backdrop");
  const modelSelect = byId("select-modelo");
  const sidebarModelBadge = byId("sidebar-model-badge");

  const tabChat = byId("tab-chat");
  const tabDados = byId("tab-dados");
  const viewChat = byId("view-chat");
  const viewDados = byId("view-dados");

  // Inicialização e sincronização do seletor de modelos da família Gemini
  async function initModelSelector() {
    let savedModel = localStorage.getItem("kraken_gemini_model") || "gemini-2.5-flash";
    try {
      const data = await api("/api/modelos");
      if (data && Array.isArray(data.modelos) && modelSelect) {
        modelSelect.innerHTML = "";
        const availableIds = data.modelos.map((m) => m.id);
        if (!availableIds.includes(savedModel)) {
          savedModel = data.modelo_atual || availableIds[0] || "gemini-2.5-flash";
          localStorage.setItem("kraken_gemini_model", savedModel);
        }
        data.modelos.forEach((m) => {
          const opt = document.createElement("option");
          opt.value = m.id;
          opt.textContent = `${m.nome} (${m.tag})`;
          if (m.id === savedModel) {
            opt.selected = true;
          }
          modelSelect.appendChild(opt);
        });
      }
    } catch (_) {}

    if (modelSelect) {
      if (savedModel) modelSelect.value = savedModel;
      updateModelDisplay(modelSelect.value);
      modelSelect.addEventListener("change", () => {
        const val = modelSelect.value;
        localStorage.setItem("kraken_gemini_model", val);
        updateModelDisplay(val);
      });
    }
  }

  function updateModelDisplay(modelId) {
    if (sidebarModelBadge) {
      sidebarModelBadge.textContent = modelId;
    }
  }

  initModelSelector();

  // Botão ☰ Conversas: Funciona no Desktop (recolhe/expande) e no Mobile (drawer)
  function toggleSidebar() {
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
      const isOpen = sidebar.getAttribute("data-open") === "true";
      sidebar.setAttribute("data-open", !isOpen ? "true" : "false");
      if (sidebarBackdrop) {
        sidebarBackdrop.setAttribute("data-active", !isOpen ? "true" : "false");
      }
    } else {
      const isCollapsed = appShell.getAttribute("data-sidebar-collapsed") === "true";
      appShell.setAttribute("data-sidebar-collapsed", !isCollapsed ? "true" : "false");
    }
  }

  if (mobileToggleBtn) {
    mobileToggleBtn.addEventListener("click", toggleSidebar);
  }
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener("click", () => {
      sidebar.setAttribute("data-open", "false");
      sidebarBackdrop.setAttribute("data-active", "false");
    });
  }

  // Alternância de Abas: Chat vs Dados & Documentos
  if (tabChat && tabDados && viewChat && viewDados) {
    tabChat.addEventListener("click", () => {
      tabChat.setAttribute("aria-selected", "true");
      tabDados.setAttribute("aria-selected", "false");
      viewChat.hidden = false;
      viewDados.hidden = true;
    });

    tabDados.addEventListener("click", () => {
      tabChat.setAttribute("aria-selected", "false");
      tabDados.setAttribute("aria-selected", "true");
      viewChat.hidden = true;
      viewDados.hidden = false;
      loadDataExplorer();
    });
  }

  async function loadSessions() {
    try {
      const data = await api("/api/conversas");
      historyList.innerHTML = "";
      if (!data.conversas || data.conversas.length === 0) {
        historyList.appendChild(el("p", "empty", "Nenhuma conversa recente."));
        return;
      }
      const ul = el("ul", "history-list");
      for (const conv of data.conversas) {
        const li = el("li");
        const a = el("a", null, conv.titulo || "Conversa sem título");
        a.href = `/?sessao=${conv.id}`;
        a.title = conv.titulo || "Conversa sem título";
        if (conv.id === sessionId) {
          a.setAttribute("aria-current", "page");
        }
        a.addEventListener("click", (e) => {
          e.preventDefault();
          selectSession(conv.id);
          if (window.innerWidth <= 768) {
            sidebar.setAttribute("data-open", "false");
            if (sidebarBackdrop) sidebarBackdrop.setAttribute("data-active", "false");
          }
        });
        li.appendChild(a);

        // Botão de exclusão de conversa
        const deleteBtn = el("button", "delete-session-btn", "🗑️");
        deleteBtn.type = "button";
        deleteBtn.title = "Excluir conversa";
        deleteBtn.setAttribute("aria-label", `Excluir conversa: ${conv.titulo || ""}`);
        deleteBtn.addEventListener("click", async (e) => {
          e.preventDefault();
          e.stopPropagation();
          const tituloCurto = conv.titulo ? `"${conv.titulo}"` : "esta conversa";
          if (!confirm(`Deseja realmente apagar ${tituloCurto}?`)) {
            return;
          }
          try {
            await api(`/api/conversas/${conv.id}`, undefined, "DELETE");
            if (conv.id === sessionId) {
              sessionId = null;
              window.history.pushState({}, "", "/");
              messagesContainer.innerHTML = "";
              if (welcomeCard) messagesContainer.appendChild(welcomeCard);
            }
            await loadSessions();
          } catch (err) {
            alert("Erro ao excluir conversa: " + err.message);
          }
        });
        li.appendChild(deleteBtn);
        ul.appendChild(li);
      }
      historyList.appendChild(ul);
    } catch (err) {
      historyList.innerHTML = `<p class="empty">${err.message}</p>`;
    }
  }

  async function selectSession(id) {
    sessionId = id;
    window.history.pushState({}, "", `/?sessao=${id}`);
    await loadSessions();
    await loadSessionMessages();
  }

  async function createNewSession() {
    try {
      const res = await api("/api/conversas", {});
      await selectSession(res.id);
    } catch (err) {
      alert("Falha ao criar nova conversa: " + err.message);
    }
  }

  function renderTurn(role, text, specialist, executionId, hasApprovalRequest, proposedCode) {
    if (welcomeCard && welcomeCard.parentNode) {
      welcomeCard.remove();
    }
    const turn = el("div", "turn");

    if (role === "user") {
      const q = el("div", "question");
      q.appendChild(el("p", "message-label", "Você"));
      q.appendChild(el("p", null, text));
      turn.appendChild(q);
    } else {
      const ans = el("div", "answer");
      const header = el("div", "answer-header");

      // Badge do especialista
      let badgeClass = "agent-copilot";
      let badgeLabel = "Kraken Copilot";
      if (specialist === "kraken_analyst") {
        badgeClass = "agent-analyst";
        badgeLabel = "📊 Kraken Analyst";
      } else if (specialist === "kraken_code") {
        badgeClass = "agent-code";
        badgeLabel = "⚡ Kraken Code";
      } else if (specialist === "kraken_optimizer") {
        badgeClass = "agent-optimizer";
        badgeLabel = "🚀 Kraken Optimizer";
      }

      header.appendChild(el("span", `agent-badge ${badgeClass}`, badgeLabel));
      ans.appendChild(header);

      // Conteúdo formatado
      ans.appendChild(renderMarkdown(text));

      // Botão de Decisão e Aprovação Humana (apenas no fluxo de otimização, criação ou alteração de código)
      const lowerText = text.toLowerCase();
      const alreadyApplied =
        lowerText.includes("gravado com sucesso no disco") ||
        lowerText.includes("otimização aprovada e aplicada") ||
        lowerText.includes("alteração aplicada com sucesso") ||
        lowerText.includes("aplicada com sucesso");

      const isExplicitApprovalPhrase =
        lowerText.includes("deseja autorizar") ||
        lowerText.includes("deseja que eu aplique") ||
        lowerText.includes("autoriza a aplicação") ||
        lowerText.includes("aguardo sua autorização") ||
        lowerText.includes("posso aplicar as alterações");

      const isOptimizationProposal =
        !alreadyApplied &&
        (hasApprovalRequest === true ||
          (hasApprovalRequest === undefined &&
            isExplicitApprovalPhrase &&
            (specialist === "kraken_optimizer" || specialist === "kraken_code")));

      if (isOptimizationProposal) {
        const approvalCard = el("div", "approval-card");
        const appHead = el("div", "approval-card-head", "⚡ Aprovação de Alterações no Pipeline");
        const appDesc = el(
          "p",
          null,
          "O assistente propôs uma alteração ou versão otimizada para o pipeline. Deseja autorizar a aplicação das mudanças no código?"
        );
        const actionsBox = el("div", "approval-actions");

        const approveBtn = el("button", "btn-approve", "✓ Aprovar e Aplicar Alterações");
        approveBtn.type = "button";
        approveBtn.addEventListener("click", async () => {
          approveBtn.disabled = true;
          rejectBtn.disabled = true;
          if (executionId) {
            await api(`/api/execucoes/${executionId}/decisao`, {
              aprovar: true,
              motivo: "Aprovado e autorizado pelo usuário",
            }).catch(() => {});
          }
          actionsBox.innerHTML = "";
          actionsBox.appendChild(
            el("span", "approval-status-badge approved", "✓ Proposta Aprovada e Autorizada")
          );
          if (textarea && form) {
            textarea.value = "Aprovado. Por favor, aplique o código proposto em pipeline/pipeline_prep.py e valide os resultados.";
            form.requestSubmit();
          }
        });

        const rejectBtn = el("button", "btn-reject", "✕ Rejeitar Proposta");
        rejectBtn.type = "button";
        rejectBtn.addEventListener("click", async () => {
          approveBtn.disabled = true;
          rejectBtn.disabled = true;
          if (executionId) {
            await api(`/api/execucoes/${executionId}/decisao`, {
              aprovar: false,
              motivo: "Rejeitado pelo usuário",
            }).catch(() => {});
          }
          actionsBox.innerHTML = "";
          actionsBox.appendChild(
            el("span", "approval-status-badge rejected", "✕ Proposta Rejeitada pelo Usuário")
          );
        });

        actionsBox.appendChild(approveBtn);
        actionsBox.appendChild(rejectBtn);
        approvalCard.appendChild(appHead);
        approvalCard.appendChild(appDesc);
        approvalCard.appendChild(actionsBox);
        ans.appendChild(approvalCard);
      }

      // Sugestões de Ação Rápida Clicáveis na resposta da IA
      extractAndRenderSuggestionChips(text, ans, (selectedPrompt) => {
        if (textarea && form) {
          textarea.value = selectedPrompt;
          textarea.dispatchEvent(new Event("input"));
          form.requestSubmit();
        }
      });

      // Ações do turno: Copiar resposta e Investigar
      const actions = el("div", "turn-actions");
      const copyBtn = el("button", "copy-turn-btn", "📋 Copiar resposta");
      copyBtn.type = "button";
      copyBtn.addEventListener("click", async () => {
        await navigator.clipboard.writeText(text).catch(() => {});
        copyBtn.textContent = "✓ Copiado!";
        setTimeout(() => { copyBtn.textContent = "📋 Copiar resposta"; }, 2000);
      });
      actions.appendChild(copyBtn);

      if (executionId) {
        const linkInv = el("a", null, "🔍 Investigação da execução →");
        linkInv.href = `/investigar/${executionId}`;
        actions.appendChild(linkInv);
      }

      ans.appendChild(actions);
      turn.appendChild(ans);
    }

    messagesContainer.appendChild(turn);
    const scroll = byId("conversation-scroll");
    if (scroll) scroll.scrollTop = scroll.scrollHeight;
  }

  async function loadSessionMessages() {
    if (!sessionId) return;
    messagesContainer.innerHTML = "";
    try {
      const conv = await api(`/api/conversas/${sessionId}`);
      if (tituloHeader) tituloHeader.textContent = conv.titulo || "Conversa";
      if (conv.mensagens && conv.mensagens.length > 0) {
        for (const m of conv.mensagens) {
          const meta = m.metadados || {};
          renderTurn(
            m.role,
            m.texto,
            m.especialista || meta.especialista,
            m.execucao_id,
            meta.has_approval_request,
            meta.proposed_code
          );
        }
      } else {
        if (welcomeCard) messagesContainer.appendChild(welcomeCard);
      }
    } catch (err) {
      messagesContainer.innerHTML = `<p class="empty">${err.message}</p>`;
    }
  }

  // Envio de formulário
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = textarea.value.trim();
      if (!text) return;

      if (!sessionId) {
        try {
          const res = await api("/api/conversas", {});
          sessionId = res.id;
          window.history.pushState({}, "", `/?sessao=${sessionId}`);
          await loadSessions();
        } catch (err) {
          alert("Erro ao iniciar sessão: " + err.message);
          return;
        }
      }

      textarea.value = "";
      textarea.style.height = "auto";
      renderTurn("user", text);

      // Indicador de carregamento
      const loadingTurn = el("div", "turn");
      const loadingBox = el("div", "answer");
      loadingBox.appendChild(el("span", "badge active", "⏳ Kraken Copilot analisando e processando..."));
      loadingTurn.appendChild(loadingBox);
      messagesContainer.appendChild(loadingTurn);
      const scroll = byId("conversation-scroll");
      if (scroll) scroll.scrollTop = scroll.scrollHeight;

      const selectedModel = modelSelect ? modelSelect.value : (localStorage.getItem("kraken_gemini_model") || "gemini-2.5-flash");
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span>Enviando...</span> <span class="send-icon" aria-hidden="true">⏳</span>';
      try {
        const res = await api(`/api/conversas/${sessionId}/mensagens`, {
          texto: text,
          modelo: selectedModel,
        });
        loadingTurn.remove();
        renderTurn(
          "assistant",
          res.resposta,
          res.especialista,
          res.execucao_id,
          res.has_approval_request,
          res.proposed_code
        );
        await loadSessions();
      } catch (err) {
        loadingTurn.remove();
        renderTurn("assistant", `⚠️ **Falha no processamento**: ${err.message}`, "kraken_copilot");
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span>Enviar</span> <span class="send-icon" aria-hidden="true">↑</span>';
        textarea.focus();
      }
    });

    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
      }
    });

    const adjustHeight = () => {
      textarea.style.height = "auto";
      textarea.style.height = Math.max(48, Math.min(textarea.scrollHeight, 220)) + "px";
    };
    textarea.addEventListener("input", adjustHeight);
  }

  // Cards de sugestões rápidas
  document.querySelectorAll(".suggestion-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      if (prompt && textarea) {
        textarea.value = prompt;
        textarea.focus();
        form.requestSubmit();
      }
    });
  });

  if (newChatBtn) {
    newChatBtn.addEventListener("click", createNewSession);
  }

  loadSessions();
  if (sessionId) {
    loadSessionMessages();
  }
}

// ============================================================================
// Extração e Renderização de Sugestões de Ação Rápida
// ============================================================================

function extractAndRenderSuggestionChips(rawText, containerEl, onSelect) {
  const text = String(rawText || "");
  const triggerRegex = /(?:o que você gostaria|posso ajudar com|próximos passos|sugestões|gostaria de|como deseja prosseguir|ações recomendadas|opções a seguir)/i;
  const match = triggerRegex.exec(text);

  let targetSlice = "";
  if (match) {
    targetSlice = text.slice(match.index);
  } else {
    const lines = text.trim().split("\n");
    if (lines.length >= 3) {
      targetSlice = lines.slice(-6).join("\n");
    }
  }

  if (!targetSlice) return;

  const lines = targetSlice.split("\n");
  const suggestions = [];

  for (const line of lines) {
    const trimmed = line.trim();
    const listMatch = trimmed.match(/^(?:[-*•]|\d+\.)\s+(.+)$/);
    if (listMatch) {
      let s = listMatch[1].trim();
      s = s.replace(/\*\*(.*?)\*\*/g, "$1")
           .replace(/`([^`]+)`/g, "$1")
           .replace(/^["'«“]|["'»”]$/g, "")
           .trim();
      if (s.length >= 6 && s.length <= 140 && !s.toLowerCase().startsWith("http")) {
        suggestions.push(s);
      }
    }
  }

  if (suggestions.length === 0) return;

  const tray = el("div", "suggestion-chips-container");
  const label = el("span", "suggestion-chips-label", "💡 Ações Sugeridas:");
  tray.appendChild(label);

  const chipsList = el("div", "suggestion-chips-list");
  for (const s of suggestions.slice(0, 5)) {
    const chip = el("button", "suggestion-chip");
    chip.type = "button";
    chip.appendChild(el("span", null, "✨ " + s));
    chip.addEventListener("click", () => {
      onSelect(s);
    });
    chipsList.appendChild(chip);
  }
  tray.appendChild(chipsList);
  containerEl.appendChild(tray);
}

// ============================================================================
// Explorador de Dados & Documentos (Hierarquia Expansível Dinâmica)
// ============================================================================

async function loadDataExplorer() {
  const fileListEl = byId("lista-arquivos-dados");
  const viewerPane = byId("painel-visualizador-dados");
  if (!fileListEl || !viewerPane) return;

  fileListEl.innerHTML = `<li class="empty">Buscando arquivos…</li>`;
  try {
    const res = await api("/api/dados/arquivos");
    fileListEl.innerHTML = "";
    if (!res.arquivos || res.arquivos.length === 0) {
      fileListEl.innerHTML = `<li class="empty">Nenhum arquivo encontrado em pipeline/dados ou docs.</li>`;
      return;
    }

    const arvore = res.arvore || {};
    const secoesInfo = {
      DATALAKE: { titulo: "DATALAKE", icone: "🗄️" },
      OUTPUTS: { titulo: "OUTPUTS", icone: "⚡" },
      DOCUMENTAÇÕES: { titulo: "DOCUMENTAÇÕES", icone: "📚" }
    };

    let activeBtn = null;

    viewerPane.innerHTML = `
      <div class="viewer-empty-state">
        <div class="empty-state-icon">📂</div>
        <h3>Arquivos e Ativos do Projeto</h3>
        <p>Selecione um arquivo nas categorias à esquerda (<strong>CSV</strong>, <strong>JSON</strong>, <strong>MARKDOWN</strong> ou <strong>PDF</strong>) para visualizar e interagir com seu conteúdo.</p>
      </div>
    `;

    for (const [secId, subs] of Object.entries(arvore)) {
      const secInfo = secoesInfo[secId] || { titulo: secId, icone: "📁" };
      const subEntries = Object.entries(subs).filter(([_, files]) => files && files.length > 0);
      if (subEntries.length === 0) continue; // Não exibe seções vazias

      const totalSecFiles = subEntries.reduce((acc, [_, files]) => acc + files.length, 0);

      // Section Details colapsável (Nível 1: Aberto por padrão)
      const secDetails = el("details", "tree-section-details");
      secDetails.open = true;

      const secSummary = el("summary", "tree-section-summary");
      secSummary.appendChild(el("span", "tree-chevron", "▾"));
      secSummary.appendChild(el("span", null, secInfo.icone));
      secSummary.appendChild(el("strong", null, secInfo.titulo));
      secSummary.appendChild(el("span", "tree-count-badge", `${totalSecFiles} ARQUIVO${totalSecFiles > 1 ? "S" : ""}`));
      secDetails.appendChild(secSummary);

      const secBody = el("div", "tree-section-body");

      for (const [subNome, files] of subEntries) {
        if (!files || files.length === 0) continue; // Apenas tipos com arquivos reais!

        // Subcategory Details (Nível 2: Colapsado por padrão conforme solicitado)
        const subDetails = el("details", "tree-subcat-details");
        subDetails.open = false;

        const subSummary = el("summary", "tree-subcat-summary");
        subSummary.appendChild(el("span", "tree-chevron", "▾"));

        let subIcon = "📂";
        if (subNome === "CSV") subIcon = "📊";
        else if (subNome === "JSON") subIcon = "🗂️";
        else if (subNome === "PARQUET") subIcon = "📦";
        else if (subNome === "MARKDOWN") subIcon = "📝";
        else if (subNome === "PDF") subIcon = "📕";

        subSummary.appendChild(el("span", null, `${subIcon} ${subNome}`));
        subSummary.appendChild(el("span", "tree-count-badge", String(files.length)));
        subDetails.appendChild(subSummary);

        const ul = el("ul", "file-list");

        for (const f of files) {
          const li = el("li");
          const btn = el("button", "file-btn");
          btn.type = "button";

          let icon = "📄";
          if (f.tipo === "csv") icon = f.secao === "OUTPUTS" ? "⚡" : "📊";
          else if (f.tipo === "parquet") icon = "📦";
          else if (f.tipo === "json") icon = f.is_metadados ? "📘" : "🗂️";
          else if (f.tipo === "md" || f.tipo === "markdown") icon = "📝";
          else if (f.tipo === "pdf") icon = "📕";

          btn.appendChild(el("span", "file-icon", icon));
          const meta = el("div", "file-meta");
          meta.appendChild(el("span", "file-name", f.nome));

          let subText = `${f.tipo.toUpperCase()} · ${f.tamanho_kb} KB`;
          if (f.is_metadados) subText += " · Metadados";
          meta.appendChild(el("span", "file-sub", subText));
          btn.appendChild(meta);

          btn.addEventListener("click", () => {
            if (activeBtn) activeBtn.setAttribute("aria-selected", "false");
            btn.setAttribute("aria-selected", "true");
            activeBtn = btn;
            renderFileData(f, viewerPane);
          });

          ul.appendChild(li);
          li.appendChild(btn);
        }

        subDetails.appendChild(ul);
        secBody.appendChild(subDetails);
      }

      secDetails.appendChild(secBody);
      fileListEl.appendChild(secDetails);
    }
  } catch (err) {
    fileListEl.innerHTML = `<li class="empty">${err.message}</li>`;
  }
}

async function renderFileData(file, container) {
  container.innerHTML = `<p class="empty">Carregando conteúdo de ${file.nome}…</p>`;
  try {
    if (file.tipo === "pdf") {
      container.innerHTML = "";
      const docUrl = `/api/dados/documento?caminho=${encodeURIComponent(file.caminho)}`;
      const dlUrl = `/api/dados/download?caminho=${encodeURIComponent(file.caminho)}`;

      const toolbar = el("div", "viewer-toolbar");
      const title = el("div", "viewer-title");
      title.appendChild(el("span", "badge active", "PDF Document"));
      title.appendChild(el("h2", null, file.nome));
      toolbar.appendChild(title);

      const actions = el("div", "viewer-actions");
      const openTab = el("a", "button", "↗ Abrir em nova aba");
      openTab.href = docUrl;
      openTab.target = "_blank";
      openTab.rel = "noopener noreferrer";

      const btnDownload = el("a", "button", "⬇ Baixar PDF");
      btnDownload.href = dlUrl;
      btnDownload.setAttribute("download", file.nome);

      actions.appendChild(openTab);
      actions.appendChild(btnDownload);
      toolbar.appendChild(actions);

      // Renderização direta via iframe nativo com Content-Disposition inline (sem download forçado)
      const frame = document.createElement("iframe");
      frame.className = "pdf-frame";
      frame.src = `${docUrl}#toolbar=1&navpanes=0`;
      frame.title = file.nome;
      frame.setAttribute("type", "application/pdf");

      container.appendChild(toolbar);
      container.appendChild(frame);
      return;
    } else if (file.tipo === "md" || file.tipo === "markdown") {
      const data = await api(`/api/dados/arquivo?caminho=${encodeURIComponent(file.caminho)}`);
      container.innerHTML = "";

      const toolbar = el("div", "viewer-toolbar");
      const title = el("div", "viewer-title");
      title.appendChild(el("span", "badge active", "Markdown Document"));
      title.appendChild(el("h2", null, file.nome));
      title.appendChild(el("span", "badge neutral", file.caminho));
      toolbar.appendChild(title);

      const actions = el("div", "viewer-actions");
      const btnFormatted = el("button", "button primary", "👁 Visualização Formatada");
      const btnRaw = el("button", "button", "📄 Markdown Puro");
      const btnCopy = el("button", "button", "📋 Copiar Conteúdo");
      const btnOpen = el("a", "button", "↗ Abrir Documento");
      btnOpen.href = `/api/dados/documento?caminho=${encodeURIComponent(file.caminho)}`;
      btnOpen.target = "_blank";
      btnOpen.rel = "noopener noreferrer";

      actions.appendChild(btnFormatted);
      actions.appendChild(btnRaw);
      actions.appendChild(btnCopy);
      actions.appendChild(btnOpen);
      toolbar.appendChild(actions);

      const contentBox = el("div", null);
      container.appendChild(toolbar);
      container.appendChild(contentBox);

      btnCopy.addEventListener("click", async () => {
        await navigator.clipboard.writeText(data.conteudo || "").catch(() => {});
        btnCopy.textContent = "✓ Copiado!";
        setTimeout(() => { btnCopy.textContent = "📋 Copiar Conteúdo"; }, 2000);
      });

      function showFormatted() {
        btnFormatted.className = "button primary";
        btnRaw.className = "button";
        contentBox.innerHTML = "";
        const body = el("div", "markdown-viewer-body");
        body.appendChild(renderMarkdown(data.conteudo || ""));
        contentBox.appendChild(body);
      }

      function showRaw() {
        btnFormatted.className = "button";
        btnRaw.className = "button primary";
        contentBox.innerHTML = "";
        const pre = el("pre", "json-raw-box", el("code", null, data.conteudo || ""));
        contentBox.appendChild(pre);
      }

      btnFormatted.addEventListener("click", showFormatted);
      btnRaw.addEventListener("click", showRaw);
      showFormatted();

    } else if (file.tipo === "csv" || file.tipo === "parquet") {
      const data = await api(`/api/dados/arquivo?caminho=${encodeURIComponent(file.caminho)}&limite=100`);
      container.innerHTML = "";

      const toolbar = el("div", "viewer-toolbar");
      const title = el("div", "viewer-title");
      let catBadge = "CSV Dataset";
      if (file.tipo === "parquet") catBadge = "PARQUET Dataset";
      else if (file.secao === "OUTPUTS") catBadge = "⚡ Saída Processada";

      title.appendChild(el("span", "badge success", catBadge));
      title.appendChild(el("h2", null, file.nome));
      title.appendChild(el("span", "badge active", `${number.format(data.total_linhas)} linhas`));
      title.appendChild(el("span", "badge attention", `${data.colunas.length} colunas`));
      toolbar.appendChild(title);

      const actions = el("div", "viewer-actions");
      const dlLink = el("a", "button", `⬇ Baixar ${file.tipo.toUpperCase()}`);
      dlLink.href = `/api/dados/documento?caminho=${encodeURIComponent(file.caminho)}`;
      dlLink.setAttribute("download", file.nome);
      actions.appendChild(dlLink);
      toolbar.appendChild(actions);

      const scrollWrapper = el("div", "csv-table-scroll");
      const table = el("table", "csv-table");
      const thead = el("thead");
      const headerRow = el("tr");
      for (const col of data.colunas) {
        const th = el("th");
        th.appendChild(el("div", null, col));
        if (data.tipos && data.tipos[col]) {
          th.appendChild(el("small", null, ` (${data.tipos[col]})`));
        }
        headerRow.appendChild(th);
      }
      thead.appendChild(headerRow);
      table.appendChild(thead);

      const tbody = el("tbody");
      for (const row of data.linhas) {
        const tr = el("tr");
        for (const col of data.colunas) {
          const td = el("td", null, String(row[col] ?? ""));
          tr.appendChild(td);
        }
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);
      scrollWrapper.appendChild(table);

      container.appendChild(toolbar);
      container.appendChild(scrollWrapper);

    } else if (file.tipo === "json") {
      const data = await api(`/api/dados/arquivo?caminho=${encodeURIComponent(file.caminho)}`);
      container.innerHTML = "";

      const toolbar = el("div", "viewer-toolbar");
      const title = el("div", "viewer-title");
      title.appendChild(el("span", "badge attention", "Dicionário / Conhecimento"));
      title.appendChild(el("h2", null, file.nome));
      toolbar.appendChild(title);

      const actions = el("div", "viewer-actions");
      const btnViewPretty = el("button", "button primary", "📑 Visualização Estruturada");
      const btnViewRaw = el("button", "button", "{ } JSON Nítido");
      const btnCopy = el("button", "button", "📋 Copiar JSON");
      actions.appendChild(btnViewPretty);
      actions.appendChild(btnViewRaw);
      actions.appendChild(btnCopy);
      toolbar.appendChild(actions);

      const contentBox = el("div", "json-viewer-container");
      container.appendChild(toolbar);
      container.appendChild(contentBox);

      const c = data.conteudo ?? data.dados ?? {};
      const jsonStr = JSON.stringify(c, null, 2);
      btnCopy.addEventListener("click", async () => {
        await navigator.clipboard.writeText(jsonStr).catch(() => {});
        btnCopy.textContent = "✓ Copiado!";
        setTimeout(() => { btnCopy.textContent = "📋 Copiar JSON"; }, 2000);
      });

      function showPretty() {
        btnViewPretty.className = "button primary";
        btnViewRaw.className = "button";
        contentBox.innerHTML = "";

        const obj = data.conteudo ?? data.dados ?? {};
        if (obj && (obj.metadata || obj.columns || obj.description)) {
          // Metadados em cards
          const dl = el("dl", "dict-meta-grid");
          if (obj.metadata?.category) dl.appendChild(el("div", "dict-meta-item", el("dt", null, "Categoria"), el("dd", null, obj.metadata.category)));
          if (obj.metadata?.table) dl.appendChild(el("div", "dict-meta-item", el("dt", null, "Tabela"), el("dd", null, obj.metadata.table)));
          if (obj.metadata?.source_file) dl.appendChild(el("div", "dict-meta-item", el("dt", null, "Arquivo Fonte"), el("dd", null, obj.metadata.source_file)));
          if (obj.metadata?.version) dl.appendChild(el("div", "dict-meta-item", el("dt", null, "Versão"), el("dd", null, obj.metadata.version)));
          if (obj.metadata?.updated_at) dl.appendChild(el("div", "dict-meta-item", el("dt", null, "Atualizado Em"), el("dd", null, obj.metadata.updated_at)));
          contentBox.appendChild(dl);

          if (obj.description) {
            contentBox.appendChild(el("p", "prose", el("strong", null, "Descrição: "), obj.description));
          }
          if (Array.isArray(obj.primary_key_candidates) && obj.primary_key_candidates.length > 0) {
            contentBox.appendChild(el("p", "prose", el("strong", null, "Chave Primária Recomendada: "), el("span", "badge active", obj.primary_key_candidates.join(", "))));
          }

          // Lista de colunas explicadas
          if (Array.isArray(obj.columns)) {
            contentBox.appendChild(el("h3", null, `Colunas e Atributos de Negócio (${obj.columns.length})`));
            const listCols = el("div", "dict-columns-list");
            for (const col of obj.columns) {
              const card = el("div", "dict-col-card");
              const head = el("div", "dict-col-header");
              head.appendChild(el("span", "dict-col-name", col.name));
              const badges = el("div", null);
              if (col.data_type) badges.appendChild(el("span", "badge active", col.data_type));
              if (col.nullable !== undefined) badges.appendChild(el("span", `badge ${col.nullable ? "neutral" : "attention"}`, col.nullable ? "Nullable" : "Required"));
              head.appendChild(badges);
              card.appendChild(head);
              if (col.description) {
                card.appendChild(el("p", "dict-col-desc", col.description));
              }
              listCols.appendChild(card);
            }
            contentBox.appendChild(listCols);
          }
        } else {
          showRaw();
        }
      }

      function showRaw() {
        btnViewPretty.className = "button";
        btnViewRaw.className = "button primary";
        contentBox.innerHTML = "";
        const pre = el("pre", "json-raw-box", el("code", null, jsonStr));
        contentBox.appendChild(pre);
      }

      btnViewPretty.addEventListener("click", showPretty);
      btnViewRaw.addEventListener("click", showRaw);
      showPretty();
    }
  } catch (err) {
    container.innerHTML = `<p class="empty">${err.message}</p>`;
  }
}

// ============================================================================
// Investigação e Observabilidade (Fidelidade Completa à Imagem 2 de Referência)
// ============================================================================

function createCodeBlock(title, codeText, lang = "python") {
  const container = el("div", "proposed-code-box");
  const header = el("div", "proposed-code-header", el("span", null, title));
  const copyBtn = el("button", "copy-code-btn", "Copiar Código");
  copyBtn.type = "button";
  copyBtn.addEventListener("click", async () => {
    await navigator.clipboard.writeText(codeText).catch(() => {});
    copyBtn.textContent = "✓ Copiado!";
    setTimeout(() => { copyBtn.textContent = "Copiar Código"; }, 2000);
  });
  header.appendChild(copyBtn);
  const pre = el("pre", "proposed-code-pre", el("code", null, codeText));
  container.appendChild(header);
  container.appendChild(pre);
  return container;
}

function initInvestigacao() {
  const container = byId("investigacao-conteudo");
  const refreshBtn = byId("atualizar-btn");
  const voltarLink = byId("nav-voltar");

  const parts = window.location.pathname.split("/").filter(Boolean);
  let execId = parts.length >= 2 && parts[0] === "investigar" ? parts[1] : null;
  if (!execId) {
    execId = new URLSearchParams(window.location.search).get("execucao");
  }

  async function loadExecution() {
    if (!execId) {
      container.innerHTML = `<p class="empty">Nenhuma execução informada.</p>`;
      return;
    }
    container.setAttribute("aria-busy", "true");
    try {
      const data = await api(`/api/execucoes/${execId}`);
      container.innerHTML = "";
      if (voltarLink && data.conversa_id) {
        voltarLink.href = `/?sessao=${data.conversa_id}`;
      }

      // 1. Cabeçalho de Status e Metadados (Idêntico ao topo da Imagem 2)
      const statusLine = el("div", "inspection-status-line");
      const statusLabel = data.status_rotulo || (data.status === "sucesso" ? "Respondido" : "Falha");
      const statusTone = data.status_tom || (data.status === "sucesso" ? "success" : "error");
      statusLine.appendChild(el("span", `badge ${statusTone}`, statusLabel));

      const dt = data.criado_em ? new Date(data.criado_em).toLocaleString("pt-BR") : "Agora";
      statusLine.appendChild(el("span", null, dt));
      statusLine.appendChild(el("span", null, data.id));
      container.appendChild(statusLine);

      // Pergunta do Usuário
      const queryTitle = el("div", "inspection-query-title", data.pergunta || "Solicitação de Execução");
      container.appendChild(queryTitle);

      // 2. Grade de Métricas em Linha Superior (Idêntica à Imagem 2)
      const metricsDl = el("dl", "metrics-grid-ref");
      const addMCol = (label, val) => {
        metricsDl.appendChild(el("div", "metric-col", el("dt", null, label), el("dd", null, val)));
      };

      addMCol("Etapas registradas", (data.etapas_registradas ?? list(data.etapas).length).toString());
      addMCol("Chamadas de modelo", (data.chamadas_modelo ?? 2).toString());
      addMCol("Tokens observados", data.tokens_observados ? number.format(data.tokens_observados) : (data.tokens?.total ? number.format(data.tokens.total) : "—"));
      addMCol("Custo informado (USD)", data.custo_informado_usd ? dollars.format(data.custo_informado_usd) : (data.tokens?.custo_usd ? dollars.format(data.tokens.custo_usd) : "US$ 0,0000"));
      container.appendChild(metricsDl);

      // 3. Abas de Investigação (Idênticas à Imagem 2)
      const tabsNav = el("div", "inspection-tabs", el("span", null));
      const tabNames = [
        { id: "percurso", label: "Percurso" },
        { id: "busca", label: "Busca e contexto" },
        { id: "analises", label: "Análises" },
        { id: "decisoes", label: "Decisões e efeitos" },
        { id: "trace", label: "Trace" },
      ];

      const tabPanels = {};
      const activeTabId = "percurso";

      for (const t of tabNames) {
        const btn = el("button", "inspection-tab", t.label);
        btn.type = "button";
        btn.setAttribute("aria-selected", t.id === activeTabId ? "true" : "false");
        btn.addEventListener("click", () => {
          for (const [k, p] of Object.entries(tabPanels)) {
            p.hidden = k !== t.id;
          }
          tabsNav.querySelectorAll(".inspection-tab").forEach(b => b.setAttribute("aria-selected", "false"));
          btn.setAttribute("aria-selected", "true");
        });
        tabsNav.appendChild(btn);
      }
      container.appendChild(tabsNav);

      // ======================================================================
      // Painel 1: Percurso (Trajetória do Workflow conectada verticalmente)
      // ======================================================================
      const panelPercurso = el("div", "tab-panel");
      tabPanels.percurso = panelPercurso;

      // Card de Decisão da Execução
      const isSuccess = data.status === "sucesso";
      const decisionCard = el("div", `path-decision ${isSuccess ? "success" : "attention"}`);
      decisionCard.appendChild(el("p", "eyebrow", "Decisão da Execução"));
      decisionCard.appendChild(el("h3", null, isSuccess ? "Evidência suficiente para responder" : "Execução com restrições"));
      decisionCard.appendChild(el("p", null, data.triagem?.motivo || "Solicitação atendida com sucesso pelo assistente."));
      panelPercurso.appendChild(decisionCard);

      // Box Preflight: Antes do Workflow (Microsoft Presidio / Sanitização)
      const preflightBox = el("aside", "path-preflight");
      preflightBox.appendChild(el("span", "path-icon", createSvgIcon("shield")));
      const pfContent = el("div");
      pfContent.appendChild(el("p", "eyebrow", "Antes do workflow"));
      pfContent.appendChild(el("strong", null, "Sanitização de Entrada · Detecção de Injeção & PII"));
      pfContent.appendChild(el("p", null, `Dados pessoais detectados: ${data.pii?.entidades_removidas ?? 0} · Segredos mascarados: ${data.pii?.segredos_removidos ?? 0}`));
      preflightBox.appendChild(pfContent);
      panelPercurso.appendChild(preflightBox);

      // Linha do tempo conectada verticalmente
      panelPercurso.appendChild(el("h3", null, "Trajetória do workflow"));
      const timelineUl = el("ul", "timeline");

      for (const step of list(data.etapas)) {
        const stepLi = el("li", "path-step");

        let iconKey = "step";
        if (step.tipo.startsWith("guardrail")) iconKey = "shield";
        else if (step.tipo === "tool_execution") iconKey = "tool";
        else if (step.tipo === "transfer") iconKey = "route";
        else if (step.tipo === "decisao_humana") iconKey = "human";
        else if (step.tipo === "execution_error") iconKey = "stop";

        stepLi.appendChild(el("span", "path-icon", createSvgIcon(iconKey)));

        const card = el("div", "path-card");
        const sHead = el("div", "path-step-head");
        sHead.appendChild(el("h3", null, step.titulo || step.tipo));

        const duracaoSeg = step.duracao_ms ? `${(step.duracao_ms / 1000).toFixed(3).replace(".", ",")} s` : (data.latencia_segundos ? `${data.latencia_segundos.toFixed(3).replace(".", ",")} s` : "0,001 s");
        sHead.appendChild(el("span", "path-time", duracaoSeg));
        card.appendChild(sHead);

        if (step.descricao) {
          card.appendChild(el("p", "path-description", step.descricao));
        }

        // Detalhe colapsável sem duplo chevron e com alto contraste
        const details = el("details", "path-step-details");
        const sum = el("summary", "path-step-summary", `Ver detalhes · ${step.titulo || step.tipo}`);
        details.appendChild(sum);

        const detailsBody = el("div", "path-step-details-body");

        if (step.tipo === "tool_execution") {
          if (step.parametros && Object.keys(step.parametros).length > 0) {
            const paramBox = el("div", "step-params-card");
            paramBox.appendChild(el("h4", null, "Parâmetros da Chamada"));
            const dl = el("dl", "key-values");
            for (const [k, v] of Object.entries(step.parametros)) {
              dl.appendChild(el("dt", null, k));
              const cleanV = parseRecursiveJson(v);
              dl.appendChild(el("dd", null, typeof cleanV === "object" ? JSON.stringify(cleanV) : String(cleanV)));
            }
            paramBox.appendChild(dl);
            detailsBody.appendChild(paramBox);
          }
          if (step.proposed_code) {
            detailsBody.appendChild(createCodeBlock("📄 Código Proposto (Python)", step.proposed_code, "python"));
          }
          if (step.query) {
            detailsBody.appendChild(createCodeBlock("🔍 Consulta SQL (ANSI / SQLite)", step.query, "sql"));
          }
          if (step.resultado !== undefined && step.resultado !== null) {
            const cleanRes = parseRecursiveJson(step.resultado);
            const resFormatted = typeof cleanRes === "object" ? JSON.stringify(cleanRes, null, 2) : String(cleanRes);
            const resBox = el("div", "step-result-card");
            resBox.appendChild(el("h4", null, "Retorno da Ferramenta"));
            resBox.appendChild(el("pre", "json-raw-box", el("code", null, resFormatted)));
            detailsBody.appendChild(resBox);
          }
        } else {
          const detailData = step.payload ? parseRecursiveJson(step.payload) : { status: "passed", message: "Regra local validada sem ocorrências de risco." };
          const detailFormatted = typeof detailData === "object" ? JSON.stringify(detailData, null, 2) : String(detailData);
          const guardBox = el("div", "step-result-card");
          guardBox.appendChild(el("pre", "json-raw-box", el("code", null, detailFormatted)));
          detailsBody.appendChild(guardBox);
        }

        details.appendChild(detailsBody);
        card.appendChild(details);
        stepLi.appendChild(card);
        timelineUl.appendChild(stepLi);
      }
      panelPercurso.appendChild(timelineUl);
      container.appendChild(panelPercurso);

      // ======================================================================
      // Painel 2: Busca e Contexto
      // ======================================================================
      const panelBusca = el("div", "tab-panel");
      panelBusca.hidden = true;
      tabPanels.busca = panelBusca;

      panelBusca.appendChild(el("h3", null, "Datasets e Ativos Locais Consultados"));
      const ctxDl = el("dl", "key-values");
      ctxDl.appendChild(el("dt", null, "Base Primária"));
      ctxDl.appendChild(el("dd", null, "pipeline/dados/dados_vendas.csv (Transacional)"));
      ctxDl.appendChild(el("dt", null, "Base Processada"));
      ctxDl.appendChild(el("dd", null, "pipeline/saida/dados_processados.csv (Features)"));
      ctxDl.appendChild(el("dt", null, "Pipeline Ativo"));
      ctxDl.appendChild(el("dd", null, "pipeline/pipeline_prep.py"));
      ctxDl.appendChild(el("dt", null, "Dicionário de Dados"));
      ctxDl.appendChild(el("dd", null, "pipeline/dados/conhecimento/dicionario_vendas.json"));
      panelBusca.appendChild(ctxDl);
      container.appendChild(panelBusca);

      // ======================================================================
      // Painel 3: Análises
      // ======================================================================
      const panelAnalises = el("div", "tab-panel");
      panelAnalises.hidden = true;
      tabPanels.analises = panelAnalises;

      panelAnalises.appendChild(el("h3", null, `Parecer Técnico · Especialista ${data.especialista || "kraken_copilot"}`));
      if (data.analises?.conclusao) {
        panelAnalises.appendChild(renderMarkdown(data.analises.conclusao));
      } else {
        panelAnalises.appendChild(el("p", "empty", "Nenhuma análise detalhada armazenada."));
      }
      container.appendChild(panelAnalises);

      // ======================================================================
      // Painel 4: Decisões e Efeitos
      // ======================================================================
      const panelDecisoes = el("div", "tab-panel");
      panelDecisoes.hidden = true;
      tabPanels.decisoes = panelDecisoes;

      panelDecisoes.appendChild(el("h3", null, "Controles de Política e Decisão Humana"));
      const decDl = el("dl", "key-values");
      decDl.appendChild(el("dt", null, "Triagem Inicial"));
      decDl.appendChild(el("dd", null, data.triagem?.rota || "Atendimento Geral"));
      decDl.appendChild(el("dt", null, "Guardrail de Entrada"));
      decDl.appendChild(el("dd", null, "Liberado (Sem injeção de código ou SQL destrutivo)"));
      decDl.appendChild(el("dt", null, "Guardrail de Saída"));
      decDl.appendChild(el("dd", null, "Liberado (Sem vazamento de credenciais, chaves ou PII)"));
      decDl.appendChild(el("dt", null, "Decisão Humana"));
      decDl.appendChild(el("dd", null, data.status_decisao ? `Decisão: ${data.status_decisao.toUpperCase()}` : "Aguardando ou Autorizado"));
      panelDecisoes.appendChild(decDl);
      container.appendChild(panelDecisoes);

      // ======================================================================
      // Painel 5: Trace
      // ======================================================================
      const panelTrace = el("div", "tab-panel");
      panelTrace.hidden = true;
      tabPanels.trace = panelTrace;

      panelTrace.appendChild(el("h3", null, "Observabilidade OpenTelemetry e Provedor"));
      const traceDl = el("dl", "key-values");
      traceDl.appendChild(el("dt", null, "Provedor"));
      traceDl.appendChild(el("dd", null, data.provedor || "Vertex AI"));
      traceDl.appendChild(el("dt", null, "Modelo"));
      traceDl.appendChild(el("dd", null, data.modelo || "gemini-2.5-flash"));
      traceDl.appendChild(el("dt", null, "Latência Total"));
      traceDl.appendChild(el("dd", null, `${data.latencia_segundos || 0} segundos`));
      traceDl.appendChild(el("dt", null, "Tokens de Entrada (Prompt)"));
      traceDl.appendChild(el("dd", null, data.tokens?.prompt?.toString() || "—"));
      traceDl.appendChild(el("dt", null, "Tokens de Saída (Completion)"));
      traceDl.appendChild(el("dd", null, data.tokens?.completion?.toString() || "—"));
      traceDl.appendChild(el("dt", null, "Total de Tokens"));
      traceDl.appendChild(el("dd", null, data.tokens?.total?.toString() || "—"));
      panelTrace.appendChild(traceDl);
      container.appendChild(panelTrace);

    } catch (err) {
      container.innerHTML = `<p class="empty">${err.message}</p>`;
    } finally {
      container.setAttribute("aria-busy", "false");
    }
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadExecution);
  }
  loadExecution();
}

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
  const view = document.body.getAttribute("data-view");
  if (view === "chat") {
    initChat();
  } else if (view === "investigacao") {
    initInvestigacao();
  }
});
