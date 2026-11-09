"use strict";

const byId = (id) => document.getElementById(id);
const list = (val) => Array.isArray(val) ? val : [];
const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

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

async function api(path, payload) {
  const options = { cache: "no-store", headers: { Accept: "application/json" } };
  if (payload !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(payload);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch (err) {
    throw new Error("O servidor do Kraken Copilot está indisponível. Verifique se o serviço está em execução.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok || !body) {
    const error = new Error(typeof body?.detail === "string" ? body.detail : `Falha no serviço (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return body;
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
  i += 2; // pula header e divisor (|---|---|)

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

    // Bloco de código
    if (line.trim().startsWith("```")) {
      const langMatch = line.trim().match(/^```(\w+)?/);
      const lang = langMatch && langMatch[1] ? langMatch[1] : "código";
      i++;
      const codeLines = [];
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++; // pula fechamento ```
      const fullCode = codeLines.join("\n");

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

    // Tabela Markdown
    if (line.trim().startsWith("|") && i + 1 < lines.length && lines[i + 1].trim().startsWith("|") && lines[i + 1].includes("---")) {
      const { node, nextIndex } = parseMarkdownTable(lines, i);
      root.appendChild(node);
      i = nextIndex;
      continue;
    }

    // Linha vazia
    if (!line.trim()) {
      i++;
      continue;
    }

    // Títulos
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = Math.min(headingMatch[1].length + 1, 4); // h2 a h4
      const heading = el(`h${level}`);
      appendInline(heading, headingMatch[2]);
      root.appendChild(heading);
      i++;
      continue;
    }

    // Citações / Blockquote
    const quoteMatch = line.match(/^>\s*(.+)$/);
    if (quoteMatch) {
      const bq = el("blockquote");
      appendInline(bq, quoteMatch[1]);
      root.appendChild(bq);
      i++;
      continue;
    }

    // Listas com marcadores ou números
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

    // Parágrafo simples
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
  const messagesContainer = byId("chat-messages");
  const welcomeCard = byId("welcome-card");
  const form = byId("consulta-form");
  const textarea = byId("pergunta");
  const submitBtn = byId("enviar");
  const historyList = byId("historico");
  const newChatBtn = byId("nova-conversa");
  const tituloHeader = byId("titulo");

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
        if (conv.id === sessionId) {
          a.setAttribute("aria-current", "page");
        }
        a.addEventListener("click", (e) => {
          e.preventDefault();
          selectSession(conv.id);
        });
        li.appendChild(a);
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

  function renderTurn(role, text, specialist, executionId) {
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

      // Link para a página de investigação/observabilidade
      if (executionId) {
        const actions = el("div", "turn-actions");
        const linkInv = el("a", null, "🔍 Investigação da execução →");
        linkInv.href = `/investigar/${executionId}`;
        actions.appendChild(linkInv);
        ans.appendChild(actions);
      }

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
          renderTurn(m.role, m.texto, m.especialista, m.execucao_id);
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

      submitBtn.disabled = true;
      try {
        const res = await api(`/api/conversas/${sessionId}/mensagens`, { texto: text });
        loadingTurn.remove();
        renderTurn("assistant", res.resposta, res.especialista, res.execucao_id);
        await loadSessions();
      } catch (err) {
        loadingTurn.remove();
        renderTurn("assistant", `⚠️ **Falha no processamento**: ${err.message}`, "kraken_copilot");
      } finally {
        submitBtn.disabled = false;
        textarea.focus();
      }
    });

    // Submissão com tecla Enter (sem Shift)
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
      }
    });

    // Auto-resize do textarea
    textarea.addEventListener("input", () => {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 180) + "px";
    });
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

  // Inicialização
  loadSessions();
  if (sessionId) {
    loadSessionMessages();
  }
}

// ============================================================================
// Investigação e Observabilidade (investigacao.html)
// ============================================================================

function initInvestigacao() {
  const container = byId("investigacao-conteudo");
  const refreshBtn = byId("atualizar-btn");
  const voltarLink = byId("nav-voltar");

  // Obtém ID da execução da rota (/investigar/{id}) ou query param
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

      // 1. Resumo da Execução
      const summaryCard = el("div", "exec-summary-card");
      const summaryHeader = el("div", "step-header");
      summaryHeader.appendChild(el("h2", null, `Execução: ${data.id}`));
      const statusBadge = el("span", `badge ${data.status === "sucesso" ? "success" : "error"}`, data.status === "sucesso" ? "✓ Concluída com Sucesso" : "⚠️ Falha");
      summaryHeader.appendChild(statusBadge);
      summaryCard.appendChild(summaryHeader);

      const metricsGrid = el("div", "exec-metrics-grid");
      const addMetric = (label, val) => {
        metricsGrid.appendChild(el("div", "metric-box", el("span", "metric-label", label), el("span", "metric-val", val)));
      };

      addMetric("Latência", data.latencia_segundos ? `${number.format(data.latencia_segundos)} s` : "—");
      addMetric("Provedor", data.provedor || "Vertex AI");
      addMetric("Modelo", data.modelo || "gemini-2.5-flash");
      addMetric("Especialista", data.especialista || "kraken_copilot");
      addMetric("Ferramentas", list(data.ferramentas_executadas).length.toString());
      summaryCard.appendChild(metricsGrid);
      container.appendChild(summaryCard);

      // 2. Timeline de Etapas e Guardrails
      const headingEtapas = el("h2", null, "Linha do Tempo de Observabilidade (OpenTelemetry & Guardrails)");
      container.appendChild(headingEtapas);

      const timeline = el("div", "timeline");
      for (const step of list(data.etapas)) {
        const card = el("div", "step-card");
        const sHeader = el("div", "step-header");
        sHeader.appendChild(el("span", "step-title", step.titulo || step.tipo));
        if (step.duracao_ms) {
          sHeader.appendChild(el("span", "badge active", `${step.duracao_ms} ms`));
        }
        card.appendChild(sHeader);

        const details = el("div", "step-details");
        if (step.descricao) {
          details.appendChild(el("p", null, step.descricao));
        }
        if (step.payload) {
          const pre = el("pre", null, el("code", null, JSON.stringify(step.payload, null, 2)));
          details.appendChild(pre);
        }
        card.appendChild(details);
        timeline.appendChild(card);
      }
      container.appendChild(timeline);
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

// Inicializa a visão de acordo com o body
document.addEventListener("DOMContentLoaded", () => {
  const view = document.body.getAttribute("data-view");
  if (view === "chat") {
    initChat();
  } else if (view === "investigacao") {
    initInvestigacao();
  }
});

