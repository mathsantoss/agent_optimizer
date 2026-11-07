# Observabilidade Local — Kraken IA (Grafana OTel LGTM)

Stack open source local baseada em `grafana/otel-lgtm` (Grafana OSS + OpenTelemetry Collector + Prometheus + Tempo + Loki) integrada ao **Google ADK** e **LiteLLM / Ollama**.

## 1. Iniciar a stack de observabilidade

```bash
docker compose -f docker-compose.observability.yml up -d
```

## 2. Acessar interfaces locais e Dashboards

- **Grafana OSS**: http://localhost:3000 (acesso anônimo habilitado como Admin ou `admin` / `admin`)
- No menu lateral, clique em **Dashboards** → pasta **Kraken IA**:
  1. **Google ADK — Kraken IA Observability**: Visão geral da saúde da aplicação, contadores, latência média LLM, tokens, durações de ferramentas, guardrails, waterfall de traces e logs.
  2. **Kraken IA — Ferramentas, Benchmarks & Auditoria**: Visão detalhada de engenharia de código e dados:
     - Tabela comparativa de **Benchmarks** (Antes vs Depois, Speedup %, Redução de memória %, Equivalência).
     - Tabela de **Profiling** (`profile_pipeline`: tempo, memória MB, linhas, colunas, hash determinístico).
     - Tabela de **Validações e Testes de Código** (`analyze_pipeline_code`, `run_tests`, `save_file`, `rollback_pipeline`).
     - Tabela de **Análise de Dados e SQL** (`explore_dataset`, `generate_statistical_summary`, `execute_sql_query`, `list_datasets`).
     - Tabela de **Auditoria de Guardrails** (`CIRCUIT_BREAKER`, `AST_SECURITY`, `SQL_GUARDRAIL`, `PROMPT_INJECTION`, etc.).
     - Stream limpo de logs do Loki (sem ruídos internos).

## 3. Como Consultar Traces no Grafana (Tempo)

Os traces distribuídos do Google ADK e LiteLLM são exportados para o Tempo via OTLP gRPC. Você pode consultá-los de três formas:

1. **Pelo Dashboard Principal**: Na tabela inferior *"Traces Distribuídos Recentes"*, basta clicar em qualquer `Trace ID` para abrir a cascata completa com a árvore hierárquica de spans da interação.
2. **Menu Explore → Tempo (Modo Search)**:
   - **Service Name**: `kraken-ia`
   - **Span Name**: `execute_tool`, `call_llm`, `agent_run`, `guardrail.*`
   - **Tags**: filtre por `status = error`, `tool.name = profile_pipeline`, `agent.name = code_optimizer_agent`, etc.
3. **Menu Explore → Tempo (Modo TraceQL)**:
   - Traces com erro ou timeout: `{ span.status = error }`
   - Traces de uma ferramenta específica: `{ span.tool.name = "profile_pipeline" }`
   - Traces com latência superior a 2 segundos: `{ duration > 2s }`
   - Traces de delegação: `{ span.agent.delegated_to = "data_analyst_agent" }`
4. **Correlação Trace ↔ Logs**: Ao inspecionar qualquer span no Tempo, clique no botão **"Related logs"** para ver imediatamente os logs do Loki correspondentes àquela exata execução.

## 4. Executar o Kraken IA com telemetria ativa

```bash
# Interface Web do Google ADK
adk web src
```

Variáveis opcionais de ambiente (já possuem valores padrão locais):

```env
KRAKEN_IA_OTEL_ENABLED=true
OTEL_SERVICE_NAME=kraken-ia
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## 5. Parar a stack de observabilidade

```bash
# Parar os containers mantendo os dados nos volumes
docker compose -f docker-compose.observability.yml down

# Parar e remover os volumes de telemetria
docker compose -f docker-compose.observability.yml down -v
```

## 6. Privacidade e Sanitização

1. **Spans (Tempo)**: O `SanitizingADKSpanProcessor` remove automaticamente atributos brutos (`gcp.vertex.agent.llm_request`, `gcp.vertex.agent.llm_response`, `gcp.vertex.agent.tool_call_args`, `gcp.vertex.agent.tool_response`, prompts, respostas completas, *chain-of-thought* e chaves de API) antes da exportação OTLP, preservando metadados operacionais (agentes, ferramentas, durações, tokens, guardrails e erros).
2. **Logs (Loki)**: O `SanitizingLogRecordProcessor` intercepta e descarta chunks de streaming internos emitidos pelo Google ADK (como `{"content": "<elided>"}`), mantendo o Loki limpo com logs estruturados de eventos de negócio e auditoria.

## 7. Solução de Problemas Comuns no Grafana

### Painel de Logs com Ícone de Alerta (`⚠ Logs` / Erro de Sintaxe 400)
- **Causa**: O LogQL do Loki **não aceita** o operador `or` entre seletores de stream (ex: `{service_name="a"} or {job="b"}` é inválido). A sintaxe correta é usar um único seletor com regex: `{service_name=~".*kraken-ia.*"}`.
- **Resolução**: O dashboard JSON foi atualizado para a versão 6 com a query corrigida. No navegador Grafana, recarregue a página com `Ctrl+F5` (ou clique no ícone de atualização no canto superior direito) para limpar a consulta antiga em cache.

### Painel de Traces Distribuídos Vazio ("No data")
- **Causa**: O Tempo pesquisa spans dentro da janela de tempo selecionada no topo direito (ex.: `Last 30 minutes`). Se nenhuma mensagem foi enviada ao Agent nesse intervalo, o resultado será vazio.
- **Resolução**: 
  1. No topo direito, altere o seletor de tempo para `Last 1 hour` ou `Last 6 hours`.
  2. Envie uma mensagem para o agente no terminal do ADK (`adk web src`) para gerar spans recentes.
  3. Você também pode acessar o menu lateral **Explore → Tempo** e pesquisar por Service Name `kraken-ia`.

