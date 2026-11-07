"""Testes automatizados da infraestrutura de Observabilidade OpenTelemetry do Kraken IA."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace

from opentelemetry import trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from kraken_ia.agent import kraken_analyst_agent, kraken_optimizer_agent, root_agent
import kraken_ia.observability as obs


def test_observability_files_and_dashboard_valid():
    """Garante que o Docker Compose, provisioning e dashboard do Grafana existem e são válidos."""
    project_root = Path(__file__).resolve().parents[1]
    compose_file = project_root / "docker-compose.observability.yml"
    provisioning_file = project_root / "observability" / "grafana" / "provisioning" / "dashboards" / "kraken-ia-dashboards.yaml"
    dashboard_file = project_root / "observability" / "grafana" / "dashboards" / "kraken-ia-observability.json"
    readme_file = project_root / "observability" / "README.md"

    assert compose_file.exists(), "docker-compose.observability.yml deve existir"
    assert "grafana/otel-lgtm" in compose_file.read_text(encoding="utf-8")
    assert provisioning_file.exists(), "Configuração de provisioning do Grafana deve existir"
    assert dashboard_file.exists(), "Dashboard JSON do Grafana deve existir"
    assert readme_file.exists(), "README da observabilidade deve existir"

    dashboard_data = json.loads(dashboard_file.read_text(encoding="utf-8"))
    assert dashboard_data["uid"] == "kraken-ia-observability"
    assert len(dashboard_data.get("panels", [])) >= 12


def test_sanitizing_log_record_processor_drops_elided_and_empty_chunks():
    """Garante que logs internos com '<elided>' ou vazios são descartados antes de ir para o Loki."""
    class MockDelegate:
        def __init__(self):
            self.emitted = []

        def emit(self, log_data):
            self.emitted.append(log_data)

        def shutdown(self):
            pass

        def force_flush(self, timeout_millis=30000):
            return True

    mock_delegate = MockDelegate()
    processor = obs.SanitizingLogRecordProcessor(mock_delegate)

    # 1. Log com content: <elided> em string ou dict deve ser descartado
    elided_record_1 = SimpleNamespace(log_record=SimpleNamespace(body='{"content": "<elided>"}', attributes={}))
    elided_record_2 = SimpleNamespace(log_record=SimpleNamespace(body={"content": "<elided>"}, attributes={}))
    processor.emit(elided_record_1)
    processor.emit(elided_record_2)
    assert len(mock_delegate.emitted) == 0

    # 2. Log estruturado válido deve passar normalmente
    valid_record = SimpleNamespace(log_record=SimpleNamespace(body='{"event": "tool_execution", "tool_name": "run_pipeline"}', attributes={}))
    processor.emit(valid_record)
    assert len(mock_delegate.emitted) == 1


def test_sanitizing_span_processor_redacts_prompts_and_extracts_safe_metadata():
    """Verifica que prompts, respostas brutas, CoT e chaves são removidos e tokens/delegações são preservados."""
    memory_exporter = InMemorySpanExporter()
    sanitizing_proc = obs.SanitizingADKSpanProcessor(SimpleSpanProcessor(memory_exporter))

    provider = TracerProvider()
    provider.add_span_processor(sanitizing_proc)
    tracer = provider.get_tracer("gcp.vertex.agent")

    with tracer.start_as_current_span("call_llm") as span:
        span.set_attribute("gcp.vertex.agent.llm_request", '{"prompt": "SEGREDO CONFIDENCIAL DO USUARIO"}')
        span.set_attribute(
            "gcp.vertex.agent.llm_response",
            json.dumps(
                {
                    "model_version": "ollama_chat/qwen3.6:35b-a3b",
                    "usage_metadata": {
                        "prompt_token_count": 120,
                        "candidates_token_count": 45,
                        "total_token_count": 165,
                    },
                    "text": "RESPOSTA COMPLETA DO LLM QUE NAO DEVE IR PARA O TEMPO",
                }
            ),
        )
        span.set_attribute("gcp.vertex.agent.tool_call_args", '{"agent_name": "kraken_analyst", "secret": "123"}')
        span.set_attribute("thinking", "cadeia de pensamento confidencial")
        span.set_attribute("api_key", "sk-secret-key")

    finished = memory_exporter.get_finished_spans()
    assert len(finished) == 1
    exported_attrs = dict(finished[0].attributes or {})

    # Nenhum atributo sensível pode permanecer no span exportado
    assert "gcp.vertex.agent.llm_request" not in exported_attrs
    assert "gcp.vertex.agent.llm_response" not in exported_attrs
    assert "gcp.vertex.agent.tool_call_args" not in exported_attrs
    assert "thinking" not in exported_attrs
    assert "api_key" not in exported_attrs

    # Metadados seguros extraídos devem estar presentes
    assert exported_attrs.get("gen_ai.usage.input_tokens") == 120
    assert exported_attrs.get("gen_ai.usage.output_tokens") == 45
    assert exported_attrs.get("gen_ai.usage.total_tokens") == 165
    assert exported_attrs.get("gen_ai.response.model") == "ollama_chat/qwen3.6:35b-a3b"
    assert exported_attrs.get("agent.delegated_to") == "kraken_analyst"
    assert exported_attrs.get("service.name") == "kraken-ia"


def test_agent_callbacks_delegation_tools_guardrails_and_metrics():
    """Valida a coleta de métricas e spans em execuções de agentes, delegações, ferramentas e guardrails."""
    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    meter = meter_provider.get_meter("test.kraken_ia")
    obs._init_metrics(meter)

    # Garante que os agentes foram instrumentados
    obs.setup_observability(root_agent)
    assert id(root_agent) in obs._INSTRUMENTED_AGENTS
    assert id(kraken_analyst_agent) in obs._INSTRUMENTED_AGENTS
    assert id(kraken_optimizer_agent) in obs._INSTRUMENTED_AGENTS

    # 1. Simula ciclo de execução do agente principal e delegação para kraken_analyst
    dummy_ctx = SimpleNamespace(agent_name="kraken_ia")
    root_agent.before_agent_callback(callback_context=dummy_ctx)

    transfer_tool = SimpleNamespace(name="transfer_to_agent")
    root_agent.before_tool_callback(
        tool=transfer_tool,
        args={"agent_name": "kraken_analyst"},
        tool_context=None,
    )
    root_agent.after_tool_callback(
        tool=transfer_tool,
        args={"agent_name": "kraken_analyst"},
        tool_context=None,
        tool_response={"result": "ok"},
    )
    root_agent.after_agent_callback(callback_context=dummy_ctx)

    # 2. Simula bloqueio de guardrail de SQL proibido no kraken_analyst_agent
    sql_tool = SimpleNamespace(name="query_dataset")
    kraken_analyst_agent.before_tool_callback(
        tool=sql_tool,
        args={"query": "DROP TABLE pedidos"},
        tool_context=None,
    )
    kraken_analyst_agent.after_tool_callback(
        tool=sql_tool,
        args={"query": "DROP TABLE pedidos"},
        tool_context=None,
        tool_response="Erro de segurança: Comando SQL proibido detectado ('DROP').",
    )

    # 3. Simula chamada LiteLLM (Ollama) via callback registrado
    import litellm

    litellm_loggers = [cb for cb in litellm.callbacks if type(cb).__name__ == "LiteLLMOTelLogger"]
    assert len(litellm_loggers) == 1
    otel_logger = litellm_loggers[0]

    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(milliseconds=420)
    otel_logger.log_success_event(
        kwargs={"model": "ollama_chat/qwen3.6:35b-a3b"},
        response_obj=SimpleNamespace(
            model="ollama_chat/qwen3.6:35b-a3b",
            usage=SimpleNamespace(prompt_tokens=200, completion_tokens=80, total_tokens=280),
        ),
        start_time=t0,
        end_time=t1,
    )

    metrics_data = metric_reader.get_metrics_data()
    metric_names = {
        m.name
        for rm in metrics_data.resource_metrics
        for sm in rm.scope_metrics
        for m in sm.metrics
    }

    assert "kraken_ia_agent_executions" in metric_names
    assert "kraken_ia_agent_duration_ms" in metric_names
    assert "kraken_ia_agent_delegations" in metric_names
    assert "kraken_ia_tool_calls" in metric_names
    assert "kraken_ia_tool_duration_ms" in metric_names
    assert "kraken_ia_guardrail_executions" in metric_names
    assert "kraken_ia_guardrail_blocks" in metric_names
    assert "kraken_ia_llm_calls" in metric_names
    assert "kraken_ia_llm_duration_ms" in metric_names
    assert "kraken_ia_llm_tokens" in metric_names

