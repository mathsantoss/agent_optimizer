"""Módulo de Observabilidade OpenTelemetry (Traces, Métricas e Logs) para o Kraken IA.

Integra de forma modular e não invasiva:
- Google ADK (aproveitando spans nativos `gcp.vertex.agent` + callbacks de agente/modelo/ferramenta/guardrail).
- LiteLLM / Ollama (latência, contagem de tokens de entrada/saída/total e erros de conexão/timeout).
- Exportação OTLP gRPC para stack local Grafana OTel LGTM (Grafana + Tempo + Prometheus + Loki).
- Sanitização rigorosa de privacidade: nunca registra prompts completos, dados sensíveis, credenciais ou chain-of-thought.
"""
import atexit
from datetime import datetime
import json
import logging
import os
import time
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler, LogRecordProcessor
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

# Desativa captura de conteúdo bruto de mensagens nos spans nativos do ADK / GenAI
os.environ.setdefault("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", "false")
os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false")

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", os.getenv("KRAKEN_IA_SERVICE_NAME", "kraken-ia"))
SERVICE_VERSION = os.getenv("OTEL_SERVICE_VERSION", "0.1.0")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
OTEL_ENABLED = os.getenv("KRAKEN_IA_OTEL_ENABLED", "true").strip().lower() not in ("0", "false", "no")

# Atributos de spans que podem conter prompts, respostas completas, CoT, dados de datasets ou chaves
REDACTED_SPAN_ATTRIBUTES = {
    "gcp.vertex.agent.llm_request",
    "gcp.vertex.agent.llm_response",
    "gcp.vertex.agent.tool_call_args",
    "gcp.vertex.agent.tool_response",
    "gcp.vertex.agent.data",
    "gen_ai.prompt",
    "gen_ai.completion",
    "gen_ai.request.messages",
    "gen_ai.response.text",
    "llm.prompts",
    "llm.completions",
    "thinking",
    "reasoning_content",
    "api_key",
    "authorization",
}

_INITIALIZED = False
_INSTRUMENTED_AGENTS: set[int] = set()
_TRACER_PROVIDER: TracerProvider | None = None
_METER_PROVIDER: MeterProvider | None = None
_LOGGER_PROVIDER: LoggerProvider | None = None
_TELEMETRY_LOGGER: logging.Logger | None = None

# Instrumentos de métricas OpenTelemetry
_METRICS: dict[str, Any] = {}


def _extract_safe_metadata_from_adk_span(span: ReadableSpan) -> dict[str, str | int | float | bool]:
    """
    Extrai apenas metadados seguros (modelo, tokens, nome da ferramenta, delegação de agente)
    dos atributos brutos do ADK antes que sejam removidos por privacidade.
    """
    safe_meta: dict[str, str | int | float | bool] = {}
    attrs = getattr(span, "attributes", None) or {}

    # Extrai contagem de tokens ou nome do modelo de gcp.vertex.agent.llm_response se disponível
    raw_llm_resp = attrs.get("gcp.vertex.agent.llm_response")
    if isinstance(raw_llm_resp, str) and raw_llm_resp.startswith("{"):
        try:
            parsed_resp = json.loads(raw_llm_resp)
            usage = parsed_resp.get("usage_metadata") or parsed_resp.get("usageMetadata") or {}
            if isinstance(usage, dict):
                in_tok = usage.get("prompt_token_count") or usage.get("promptTokenCount")
                out_tok = usage.get("candidates_token_count") or usage.get("candidatesTokenCount")
                tot_tok = usage.get("total_token_count") or usage.get("totalTokenCount")
                if isinstance(in_tok, int):
                    safe_meta["gen_ai.usage.input_tokens"] = in_tok
                if isinstance(out_tok, int):
                    safe_meta["gen_ai.usage.output_tokens"] = out_tok
                if isinstance(tot_tok, int):
                    safe_meta["gen_ai.usage.total_tokens"] = tot_tok
            model_ver = parsed_resp.get("model_version") or parsed_resp.get("modelVersion")
            if isinstance(model_ver, str) and model_ver:
                safe_meta["gen_ai.response.model"] = model_ver
        except Exception:
            pass

    # Extrai apenas o nome do agente de destino em transfer_to_agent
    raw_tool_args = attrs.get("gcp.vertex.agent.tool_call_args")
    if isinstance(raw_tool_args, str) and "agent_name" in raw_tool_args:
        try:
            parsed_args = json.loads(raw_tool_args)
            if isinstance(parsed_args, dict) and isinstance(parsed_args.get("agent_name"), str):
                safe_meta["agent.delegated_to"] = parsed_args["agent_name"]
        except Exception:
            pass

    return safe_meta


class SanitizingADKSpanProcessor(SpanProcessor):
    """
    Intercepta todos os spans (incluindo os spans nativos `gcp.vertex.agent` do Google ADK),
    extrai metadados operacionais seguros e remove prompts, respostas brutas, CoT e dados sensíveis
    antes de encaminhar ao exportador OTLP (Tempo).
    """

    def __init__(self, delegate_processor: SpanProcessor) -> None:
        self._delegate = delegate_processor

    def on_start(self, span: Span, parent_context: Any = None) -> None:
        try:
            if span.is_recording():
                span.set_attribute("service.name", SERVICE_NAME)
        except Exception:
            pass
        self._delegate.on_start(span, parent_context=parent_context)

    def on_end(self, span: ReadableSpan) -> None:
        try:
            internal_attrs = getattr(span, "_attributes", None)
            if internal_attrs is not None and hasattr(internal_attrs, "__setitem__"):
                safe_meta = _extract_safe_metadata_from_adk_span(span)
                for key, val in safe_meta.items():
                    internal_attrs[key] = val

                for sensitive_key in list(internal_attrs.keys()):
                    lower_key = str(sensitive_key).lower()
                    if (
                        sensitive_key in REDACTED_SPAN_ATTRIBUTES
                        or "prompt" in lower_key
                        or "completion" in lower_key
                        or "api_key" in lower_key
                        or "secret" in lower_key
                        or "password" in lower_key
                        or "thinking" in lower_key
                    ):
                        try:
                            del internal_attrs[sensitive_key]
                        except Exception:
                            internal_attrs[sensitive_key] = "[REDACTED]"
        except Exception:
            pass

        self._delegate.on_end(span)

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._delegate.force_flush(timeout_millis=timeout_millis)


class SanitizingBatchLogRecordProcessor(BatchLogRecordProcessor):
    """
    Processador de logs em lote que filtra chunks de streaming ruidosos
    emitidos com 'content': '<elided>' ou payloads vazios antes de exportar ao Loki.
    """

    def _should_drop_record(self, log_record: Any) -> bool:
        try:
            record = getattr(log_record, "log_record", None) or log_record
            if record is not None:
                body = getattr(record, "body", None)
                if isinstance(body, str):
                    if "<elided>" in body:
                        return True
                    if body.strip() in ("", "{}"):
                        return True
                elif isinstance(body, dict):
                    if body.get("content") == "<elided>":
                        return True
                    if not body:
                        return True
                attrs = getattr(record, "attributes", None) or {}
                if isinstance(attrs, dict) and attrs.get("content") == "<elided>":
                    return True
        except Exception:
            pass
        return False

    def on_emit(self, log_record: Any) -> None:
        if self._should_drop_record(log_record):
            return
        super().on_emit(log_record)

    def emit(self, log_data: Any) -> None:
        if self._should_drop_record(log_data):
            return
        if hasattr(super(), "emit"):
            super().emit(log_data)
        else:
            super().on_emit(log_data)


# Alias para retrocompatibilidade
class SanitizingLogRecordProcessor(LogRecordProcessor):
    """Encapsulador legado mantido para compatibilidade."""

    def __init__(self, delegate_processor: LogRecordProcessor) -> None:
        self._delegate = delegate_processor

    def emit(self, log_data: Any) -> None:
        try:
            record = getattr(log_data, "log_record", None) or log_data
            if record is not None:
                body = getattr(record, "body", None)
                if isinstance(body, str):
                    if "<elided>" in body:
                        return
                    if body.strip() in ("", "{}"):
                        return
                elif isinstance(body, dict):
                    if body.get("content") == "<elided>":
                        return
                    if not body:
                        return
                attrs = getattr(record, "attributes", None) or {}
                if isinstance(attrs, dict) and attrs.get("content") == "<elided>":
                    return
        except Exception:
            pass
        self._delegate.emit(log_data)

    def on_emit(self, log_record: Any) -> None:
        self.emit(log_record)

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._delegate.force_flush(timeout_millis=timeout_millis)


def emit_telemetry_log(
    event_name: str,
    level: int = logging.INFO,
    **attributes: Any,
) -> None:
    """
    Emite um log estruturado OpenTelemetry (enviado via OTLP para o Loki) correlacionado
    com o `trace_id` e `span_id` ativos, garantindo ausência de prompts ou dados sensíveis.
    """
    if _TELEMETRY_LOGGER is None:
        return

    current_span = trace.get_current_span()
    span_ctx = current_span.get_span_context() if current_span else None
    trace_id_hex = f"{span_ctx.trace_id:032x}" if span_ctx and span_ctx.is_valid else ""
    span_id_hex = f"{span_ctx.span_id:016x}" if span_ctx and span_ctx.is_valid else ""

    safe_payload = {
        "event": event_name,
        "service": SERVICE_NAME,
        "trace_id": trace_id_hex,
        "span_id": span_id_hex,
    }
    for key, value in attributes.items():
        if key.lower() in REDACTED_SPAN_ATTRIBUTES or "prompt" in key.lower() or "key" in key.lower():
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe_payload[key] = value
        else:
            safe_payload[key] = str(value)[:160]

    try:
        _TELEMETRY_LOGGER.log(
            level,
            json.dumps(safe_payload, ensure_ascii=False),
            extra={"otel_event": event_name, **{f"attr_{k}": str(v) for k, v in safe_payload.items() if v is not None}},
        )
    except Exception:
        pass


def _init_metrics(meter: metrics.Meter) -> None:
    """Cria os contadores e histogramas OpenTelemetry exportados para o Prometheus."""
    _METRICS["agent_executions"] = meter.create_counter(
        name="kraken_ia_agent_executions",
        description="Total de execuções de cada agente (orquestrador e especialistas)",
        unit="1",
    )
    _METRICS["agent_duration_ms"] = meter.create_histogram(
        name="kraken_ia_agent_duration_ms",
        description="Duração das execuções de cada agente em milissegundos",
        unit="ms",
    )
    _METRICS["agent_delegations"] = meter.create_counter(
        name="kraken_ia_agent_delegations",
        description="Total de delegações (transfer_to_agent) entre agentes",
        unit="1",
    )
    _METRICS["llm_calls"] = meter.create_counter(
        name="kraken_ia_llm_calls",
        description="Total de chamadas ao modelo LLM via LiteLLM",
        unit="1",
    )
    _METRICS["llm_duration_ms"] = meter.create_histogram(
        name="kraken_ia_llm_duration_ms",
        description="Latência das chamadas ao modelo LLM via LiteLLM em milissegundos",
        unit="ms",
    )
    _METRICS["llm_tokens"] = meter.create_counter(
        name="kraken_ia_llm_tokens",
        description="Total de tokens consumidos nas chamadas LLM (input, output, total)",
        unit="1",
    )
    _METRICS["tool_calls"] = meter.create_counter(
        name="kraken_ia_tool_calls",
        description="Total de execuções de ferramentas pelos agentes",
        unit="1",
    )
    _METRICS["tool_duration_ms"] = meter.create_histogram(
        name="kraken_ia_tool_duration_ms",
        description="Duração de execução das ferramentas em milissegundos",
        unit="ms",
    )
    _METRICS["guardrail_executions"] = meter.create_counter(
        name="kraken_ia_guardrail_executions",
        description="Total de verificações de guardrails executadas por estágio e ação",
        unit="1",
    )
    _METRICS["guardrail_blocks"] = meter.create_counter(
        name="kraken_ia_guardrail_blocks",
        description="Total de bloqueios ou sanitizações acionados pelos guardrails",
        unit="1",
    )
    _METRICS["errors"] = meter.create_counter(
        name="kraken_ia_errors",
        description="Total de erros, exceções e timeouts por componente",
        unit="1",
    )


def _compute_duration_ms(start_time: Any, end_time: Any) -> tuple[float, int | None, int | None]:
    """Calcula a duração em ms e timestamps em nanosegundos a partir de objetos datetime ou float."""
    if isinstance(start_time, datetime) and isinstance(end_time, datetime):
        duration_ms = max(0.0, (end_time - start_time).total_seconds() * 1000.0)
        start_ns = int(start_time.timestamp() * 1_000_000_000)
        end_ns = int(end_time.timestamp() * 1_000_000_000)
        return round(duration_ms, 2), start_ns, end_ns
    if isinstance(start_time, (int, float)) and isinstance(end_time, (int, float)):
        duration_ms = max(0.0, (float(end_time) - float(start_time)) * 1000.0)
        return round(duration_ms, 2), int(float(start_time) * 1e9), int(float(end_time) * 1e9)
    return 0.0, None, None


def _register_litellm_callbacks() -> None:
    """Registra um CustomLogger no LiteLLM para capturar latência, tokens e erros de chamadas ao Ollama/LLM."""
    try:
        import litellm
        from litellm.integrations.custom_logger import CustomLogger

        class LiteLLMOTelLogger(CustomLogger):
            """Callback LiteLLM que registra spans, métricas de tokens/latência e logs sem expor prompts."""

            def _record_success(self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any) -> None:
                try:
                    model_name = str(kwargs.get("model") or getattr(response_obj, "model", "unknown"))
                    provider = model_name.split("/")[0] if "/" in model_name else str(kwargs.get("custom_llm_provider") or "ollama")
                    duration_ms, start_ns, end_ns = _compute_duration_ms(start_time, end_time)

                    usage = getattr(response_obj, "usage", None)
                    if usage is None and isinstance(response_obj, dict):
                        usage = response_obj.get("usage")

                    input_tokens = int(getattr(usage, "prompt_tokens", 0) or (usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0) or 0)
                    output_tokens = int(getattr(usage, "completion_tokens", 0) or (usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0) or 0)
                    total_tokens = int(getattr(usage, "total_tokens", 0) or (usage.get("total_tokens", 0) if isinstance(usage, dict) else 0) or (input_tokens + output_tokens))

                    tracer = trace.get_tracer("kraken_ia.litellm")
                    span_kwargs = {"start_time": start_ns} if start_ns else {}
                    span = tracer.start_span(f"litellm.completion [{model_name}]", **span_kwargs)
                    span.set_attribute("gen_ai.system", provider)
                    span.set_attribute("gen_ai.request.model", model_name)
                    span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
                    span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
                    span.set_attribute("gen_ai.usage.total_tokens", total_tokens)
                    span.set_attribute("llm.duration_ms", duration_ms)
                    span.set_status(Status(StatusCode.OK))
                    if end_ns:
                        span.end(end_time=end_ns)
                    else:
                        span.end()

                    labels = {"model": model_name, "provider": provider, "status": "success"}
                    if "llm_calls" in _METRICS:
                        _METRICS["llm_calls"].add(1, labels)
                        _METRICS["llm_duration_ms"].record(duration_ms, labels)
                        if input_tokens > 0:
                            _METRICS["llm_tokens"].add(input_tokens, {"model": model_name, "token_type": "input"})
                        if output_tokens > 0:
                            _METRICS["llm_tokens"].add(output_tokens, {"model": model_name, "token_type": "output"})
                        if total_tokens > 0:
                            _METRICS["llm_tokens"].add(total_tokens, {"model": model_name, "token_type": "total"})

                    emit_telemetry_log(
                        "llm_call",
                        level=logging.INFO,
                        model=model_name,
                        provider=provider,
                        status="success",
                        duration_ms=duration_ms,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                    )
                except Exception:
                    pass

            def _record_failure(self, kwargs: dict[str, Any], start_time: Any, end_time: Any) -> None:
                try:
                    model_name = str(kwargs.get("model") or "unknown")
                    provider = model_name.split("/")[0] if "/" in model_name else str(kwargs.get("custom_llm_provider") or "ollama")
                    duration_ms, start_ns, end_ns = _compute_duration_ms(start_time, end_time)
                    exception = kwargs.get("exception")
                    exc_type = type(exception).__name__ if exception else "LLMError"
                    is_timeout = "timeout" in exc_type.lower() or "timeout" in str(exception or "").lower()
                    error_category = "timeout" if is_timeout else exc_type

                    tracer = trace.get_tracer("kraken_ia.litellm")
                    span_kwargs = {"start_time": start_ns} if start_ns else {}
                    span = tracer.start_span(f"litellm.completion [{model_name}]", **span_kwargs)
                    span.set_attribute("gen_ai.system", provider)
                    span.set_attribute("gen_ai.request.model", model_name)
                    span.set_attribute("llm.duration_ms", duration_ms)
                    span.set_attribute("error.type", error_category)
                    span.set_status(Status(StatusCode.ERROR, description=exc_type))
                    if end_ns:
                        span.end(end_time=end_ns)
                    else:
                        span.end()

                    labels = {"model": model_name, "provider": provider, "status": "error"}
                    if "llm_calls" in _METRICS:
                        _METRICS["llm_calls"].add(1, labels)
                        _METRICS["llm_duration_ms"].record(duration_ms, labels)
                        _METRICS["errors"].add(
                            1,
                            {"component": "llm", "name": model_name, "error_type": error_category},
                        )

                    emit_telemetry_log(
                        "llm_error",
                        level=logging.ERROR,
                        model=model_name,
                        provider=provider,
                        status="error",
                        error_type=error_category,
                        duration_ms=duration_ms,
                    )
                except Exception:
                    pass

            def log_success_event(self, kwargs: Any, response_obj: Any, start_time: Any, end_time: Any) -> None:
                self._record_success(kwargs, response_obj, start_time, end_time)

            async def async_log_success_event(self, kwargs: Any, response_obj: Any, start_time: Any, end_time: Any) -> None:
                self._record_success(kwargs, response_obj, start_time, end_time)

            def log_failure_event(self, kwargs: Any, response_obj: Any, start_time: Any, end_time: Any) -> None:
                self._record_failure(kwargs, start_time, end_time)

            async def async_log_failure_event(self, kwargs: Any, response_obj: Any, start_time: Any, end_time: Any) -> None:
                self._record_failure(kwargs, start_time, end_time)

        if not any(type(cb).__name__ == "LiteLLMOTelLogger" for cb in getattr(litellm, "callbacks", [])):
            litellm.callbacks.append(LiteLLMOTelLogger())
    except Exception:
        pass


def _classify_tool_response_status(tool_response: Any) -> tuple[str, str | None]:
    """
    Analisa de forma segura o retorno de uma ferramenta para identificar se houve:
    - Bloqueio de guardrail (`blocked`, tipo do guardrail)
    - Timeout (`timeout`, `"timeout"`)
    - Erro de execução (`error`, `"tool_error"`)
    - Sucesso (`success`, None)
    """
    text = ""
    if isinstance(tool_response, str):
        text = tool_response
        if tool_response.startswith("{") and "success" in tool_response:
            try:
                parsed = json.loads(tool_response)
                if isinstance(parsed, dict) and parsed.get("success") is False:
                    errs = " ".join(str(e) for e in parsed.get("errors", []))
                    text = errs or str(parsed.get("summary", text))
            except Exception:
                pass
    elif isinstance(tool_response, dict):
        if tool_response.get("success") is False:
            errs = " ".join(str(e) for e in tool_response.get("errors", []))
            text = errs or str(tool_response.get("summary", ""))
        else:
            text = str(tool_response.get("result") or tool_response.get("error") or "")

    lower_text = text.strip().lower()
    if not lower_text:
        return "success", None

    if (
        "erro de segurança" in lower_text
        or "erro de guardrail" in lower_text
        or "guardrail de circuit breaker" in lower_text
        or "guardrail de orquestração" in lower_text
        or "proibido" in lower_text
        or "proibida" in lower_text
    ):
        if "sql" in lower_text or "proibido" in lower_text:
            return "blocked", "sql_readonly_guardrail"
        if "contrato" in lower_text:
            return "blocked", "pipeline_contract_guardrail"
        if "integridade" in lower_text:
            return "blocked", "raw_data_integrity_guardrail"
        return "blocked", "ast_security_guardrail"

    if (
        "excedeu o tempo limite" in lower_text
        or "excedeu o limite de" in lower_text
        or "exceder o limite de tempo" in lower_text
    ):
        return "timeout", "timeout"

    if (
        lower_text.startswith("erro")
        or "erro na execução" in lower_text
        or "resultado dos testes [falha]" in lower_text
    ):
        return "error", "tool_execution_error"

    return "success", None


def _instrument_single_agent(agent: Any) -> None:
    """
    Envolve de forma transparente os callbacks de um agente ADK para registrar métricas,
    traces e logs de:
    - Execução do agente (`before_agent_callback` / `after_agent_callback`)
    - Execução e bloqueio de guardrails (`before_model_callback`, `after_model_callback`, `before_tool_callback`, `after_tool_callback`)
    - Execução, duração, delegação (`transfer_to_agent`) e erros de ferramentas.
    """
    agent_id = id(agent)
    if agent_id in _INSTRUMENTED_AGENTS:
        return
    _INSTRUMENTED_AGENTS.add(agent_id)

    agent_name = getattr(agent, "name", "unknown_agent")
    tracer = trace.get_tracer("kraken_ia.adk")

    orig_before_agent = getattr(agent, "before_agent_callback", None)
    orig_after_agent = getattr(agent, "after_agent_callback", None)
    orig_before_model = getattr(agent, "before_model_callback", None)
    orig_after_model = getattr(agent, "after_model_callback", None)
    orig_before_tool = getattr(agent, "before_tool_callback", None)
    orig_after_tool = getattr(agent, "after_tool_callback", None)

    agent_start_times: dict[int, float] = {}
    tool_start_times: dict[str, float] = {}

    def wrapped_before_agent(callback_context: Any = None, **kwargs: Any) -> Any:
        ctx_key = id(callback_context) if callback_context is not None else 0
        agent_start_times[ctx_key] = time.perf_counter()

        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute("agent.name", agent_name)

        emit_telemetry_log("agent_start", level=logging.INFO, agent_name=agent_name)
        if callable(orig_before_agent):
            return orig_before_agent(callback_context=callback_context, **kwargs)
        return None

    def wrapped_after_agent(callback_context: Any = None, **kwargs: Any) -> Any:
        ctx_key = id(callback_context) if callback_context is not None else 0
        start_ts = agent_start_times.pop(ctx_key, None)
        duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2) if start_ts else 0.0

        result = None
        status = "success"
        try:
            if callable(orig_after_agent):
                result = orig_after_agent(callback_context=callback_context, **kwargs)
        except Exception as exc:
            status = "error"
            if "errors" in _METRICS:
                _METRICS["errors"].add(
                    1,
                    {"component": "agent", "name": agent_name, "error_type": type(exc).__name__},
                )
            raise
        finally:
            if "agent_executions" in _METRICS:
                _METRICS["agent_executions"].add(1, {"agent_name": agent_name, "status": status})
                _METRICS["agent_duration_ms"].record(duration_ms, {"agent_name": agent_name, "status": status})
            emit_telemetry_log(
                "agent_execution",
                level=logging.INFO,
                agent_name=agent_name,
                status=status,
                duration_ms=duration_ms,
            )
        return result

    def wrapped_before_model(callback_context: Any = None, llm_request: Any = None, **kwargs: Any) -> Any:
        start_ts = time.perf_counter()
        with tracer.start_as_current_span("guardrail.before_model") as span:
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("guardrail.stage", "before_model")
            result = None
            if callable(orig_before_model):
                result = orig_before_model(
                    callback_context=callback_context,
                    llm_request=llm_request,
                    **kwargs,
                )
            duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
            blocked = result is not None
            action = "blocked" if blocked else "passed"
            span.set_attribute("guardrail.action", action)
            span.set_attribute("guardrail.duration_ms", duration_ms)

            if "guardrail_executions" in _METRICS:
                _METRICS["guardrail_executions"].add(
                    1,
                    {"guardrail_stage": "before_model", "agent_name": agent_name, "action": action},
                )
            if blocked:
                if "guardrail_blocks" in _METRICS:
                    _METRICS["guardrail_blocks"].add(
                        1,
                        {"guardrail_type": "prompt_injection", "agent_name": agent_name},
                    )
                emit_telemetry_log(
                    "guardrail_block",
                    level=logging.WARNING,
                    agent_name=agent_name,
                    guardrail_stage="before_model",
                    guardrail_type="prompt_injection",
                    action="blocked",
                    duration_ms=duration_ms,
                )
            return result

    def wrapped_after_model(callback_context: Any = None, llm_response: Any = None, **kwargs: Any) -> Any:
        start_ts = time.perf_counter()
        with tracer.start_as_current_span("guardrail.after_model") as span:
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("guardrail.stage", "after_model")
            result = None
            if callable(orig_after_model):
                result = orig_after_model(
                    callback_context=callback_context,
                    llm_response=llm_response,
                    **kwargs,
                )
            duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
            sanitized = result is not None
            action = "sanitized" if sanitized else "passed"
            span.set_attribute("guardrail.action", action)
            span.set_attribute("guardrail.duration_ms", duration_ms)

            if "guardrail_executions" in _METRICS:
                _METRICS["guardrail_executions"].add(
                    1,
                    {"guardrail_stage": "after_model", "agent_name": agent_name, "action": action},
                )
            if sanitized:
                if "guardrail_blocks" in _METRICS:
                    _METRICS["guardrail_blocks"].add(
                        1,
                        {"guardrail_type": "output_sanitization", "agent_name": agent_name},
                    )
                emit_telemetry_log(
                    "guardrail_sanitized",
                    level=logging.WARNING,
                    agent_name=agent_name,
                    guardrail_stage="after_model",
                    guardrail_type="output_sanitization",
                    action="sanitized",
                    duration_ms=duration_ms,
                )
            return result

    def wrapped_before_tool(
        tool: Any = None,
        args: dict[str, Any] | None = None,
        tool_context: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        target_tool = tool or kwargs.get("tool")
        tool_name = getattr(target_tool, "name", getattr(target_tool, "__name__", "unknown_tool"))
        tool_start_times[f"{agent_name}::{tool_name}"] = time.perf_counter()

        # Registra delegação entre agentes quando transfer_to_agent é invocado
        if tool_name == "transfer_to_agent" and isinstance(args, dict):
            target_agent = str(args.get("agent_name") or "unknown")
            with tracer.start_as_current_span(f"agent.delegation [{agent_name} -> {target_agent}]") as del_span:
                del_span.set_attribute("agent.from", agent_name)
                del_span.set_attribute("agent.to", target_agent)
            if "agent_delegations" in _METRICS:
                _METRICS["agent_delegations"].add(
                    1,
                    {"from_agent": agent_name, "to_agent": target_agent},
                )
            emit_telemetry_log(
                "agent_delegation",
                level=logging.INFO,
                from_agent=agent_name,
                to_agent=target_agent,
            )

        start_ts = time.perf_counter()
        result = None
        if callable(orig_before_tool):
            result = orig_before_tool(tool=tool, args=args, tool_context=tool_context, **kwargs)
        guardrail_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)

        blocked = result is not None
        action = "blocked" if blocked else "passed"
        if "guardrail_executions" in _METRICS:
            _METRICS["guardrail_executions"].add(
                1,
                {"guardrail_stage": "before_tool", "agent_name": agent_name, "action": action},
            )
        if blocked:
            if "guardrail_blocks" in _METRICS:
                _METRICS["guardrail_blocks"].add(
                    1,
                    {"guardrail_type": f"circuit_breaker_{tool_name}", "agent_name": agent_name},
                )
            if "tool_calls" in _METRICS:
                _METRICS["tool_calls"].add(
                    1,
                    {"tool_name": tool_name, "agent_name": agent_name, "status": "blocked"},
                )
            emit_telemetry_log(
                "guardrail_block",
                level=logging.WARNING,
                agent_name=agent_name,
                tool_name=tool_name,
                guardrail_stage="before_tool",
                guardrail_type="circuit_breaker",
                action="blocked",
                duration_ms=guardrail_ms,
            )
        return result

    def wrapped_after_tool(
        tool: Any = None,
        args: dict[str, Any] | None = None,
        tool_context: Any = None,
        tool_response: Any = None,
        **kwargs: Any,
    ) -> Any:
        target_tool = tool or kwargs.get("tool")
        tool_name = getattr(target_tool, "name", getattr(target_tool, "__name__", "unknown_tool"))
        start_ts = tool_start_times.pop(f"{agent_name}::{tool_name}", None)
        tool_duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2) if start_ts else 0.0

        modified_response = None
        if callable(orig_after_tool):
            modified_response = orig_after_tool(
                tool=tool,
                args=args,
                tool_context=tool_context,
                tool_response=tool_response,
                **kwargs,
            )

        effective_response = modified_response if modified_response is not None else tool_response
        status, error_or_guardrail_type = _classify_tool_response_status(effective_response)

        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute("agent.name", agent_name)
            current_span.set_attribute("tool.name", tool_name)
            current_span.set_attribute("tool.status", status)
            current_span.set_attribute("tool.duration_ms", tool_duration_ms)
            if status in ("error", "timeout"):
                current_span.set_status(Status(StatusCode.ERROR, description=error_or_guardrail_type))

        if "tool_calls" in _METRICS:
            _METRICS["tool_calls"].add(
                1,
                {"tool_name": tool_name, "agent_name": agent_name, "status": status},
            )
            _METRICS["tool_duration_ms"].record(
                tool_duration_ms,
                {"tool_name": tool_name, "agent_name": agent_name, "status": status},
            )

        if status == "blocked" and error_or_guardrail_type:
            if "guardrail_blocks" in _METRICS:
                _METRICS["guardrail_blocks"].add(
                    1,
                    {"guardrail_type": error_or_guardrail_type, "agent_name": agent_name},
                )
            emit_telemetry_log(
                "guardrail_block",
                level=logging.WARNING,
                agent_name=agent_name,
                tool_name=tool_name,
                guardrail_stage="tool_validation",
                guardrail_type=error_or_guardrail_type,
                action="blocked",
                duration_ms=tool_duration_ms,
            )
        elif status in ("error", "timeout") and error_or_guardrail_type:
            if "errors" in _METRICS:
                _METRICS["errors"].add(
                    1,
                    {"component": "tool", "name": tool_name, "error_type": error_or_guardrail_type},
                )
            emit_telemetry_log(
                "tool_error",
                level=logging.ERROR,
                agent_name=agent_name,
                tool_name=tool_name,
                status=status,
                error_type=error_or_guardrail_type,
                duration_ms=tool_duration_ms,
            )
        else:
            emit_telemetry_log(
                "tool_execution",
                level=logging.INFO,
                agent_name=agent_name,
                tool_name=tool_name,
                status=status,
                duration_ms=tool_duration_ms,
            )

        return modified_response

    agent.before_agent_callback = wrapped_before_agent
    agent.after_agent_callback = wrapped_after_agent
    if hasattr(agent, "before_model_callback"):
        agent.before_model_callback = wrapped_before_model
    if hasattr(agent, "after_model_callback"):
        agent.after_model_callback = wrapped_after_model
    if hasattr(agent, "before_tool_callback"):
        agent.before_tool_callback = wrapped_before_tool
    if hasattr(agent, "after_tool_callback"):
        agent.after_tool_callback = wrapped_after_tool


def _instrument_agent_tree(agent: Any) -> None:
    """Instrumenta recursivamente um agente e toda a sua sub-árvore de `sub_agents`."""
    if agent is None:
        return
    _instrument_single_agent(agent)
    for sub_agent in getattr(agent, "sub_agents", []) or []:
        _instrument_agent_tree(sub_agent)


def setup_observability(root_agent: Any = None) -> None:
    """
    Inicializa os provedores OpenTelemetry (Traces -> Tempo, Métricas -> Prometheus, Logs -> Loki)
    via OTLP gRPC e instrumenta de forma não invasiva a hierarquia de agentes do Google ADK e o LiteLLM.
    """
    global _INITIALIZED, _TRACER_PROVIDER, _METER_PROVIDER, _LOGGER_PROVIDER, _TELEMETRY_LOGGER

    if not _INITIALIZED and OTEL_ENABLED:
        resource = Resource.create(
            {
                "service.name": SERVICE_NAME,
                "service.version": SERVICE_VERSION,
                "deployment.environment": os.getenv("KRAKEN_IA_ENV", "local"),
            }
        )

        # 1. Configuração de Traces (OTLP gRPC -> Tempo)
        try:
            span_exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
            batch_span_processor = BatchSpanProcessor(
                span_exporter,
                schedule_delay_millis=1000,
            )
            sanitizing_processor = SanitizingADKSpanProcessor(batch_span_processor)

            existing_provider = trace.get_tracer_provider()
            if isinstance(existing_provider, TracerProvider):
                try:
                    if hasattr(existing_provider, "_resource") and existing_provider._resource is not None:
                        existing_provider._resource = existing_provider._resource.merge(resource)
                except Exception:
                    pass
                existing_provider.add_span_processor(sanitizing_processor)
                _TRACER_PROVIDER = existing_provider
            else:
                tracer_provider = TracerProvider(resource=resource)
                tracer_provider.add_span_processor(sanitizing_processor)
                trace.set_tracer_provider(tracer_provider)
                _TRACER_PROVIDER = tracer_provider
        except Exception:
            pass

        # 2. Configuração de Métricas (OTLP gRPC -> Prometheus)
        try:
            metric_exporter = OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True)
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=2000,
            )
            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
            metrics.set_meter_provider(meter_provider)
            _METER_PROVIDER = meter_provider
            meter = metrics.get_meter("kraken_ia.observability", SERVICE_VERSION)
            _init_metrics(meter)
        except Exception:
            pass

        # 3. Configuração de Logs Estruturados (OTLP gRPC -> Loki)
        try:
            log_exporter = OTLPLogExporter(endpoint=OTLP_ENDPOINT, insecure=True)
            logger_provider = LoggerProvider(resource=resource)
            batch_log_processor = SanitizingBatchLogRecordProcessor(log_exporter, schedule_delay_millis=1000)
            logger_provider.add_log_record_processor(batch_log_processor)
            set_logger_provider(logger_provider)
            _LOGGER_PROVIDER = logger_provider

            otel_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
            telemetry_logger = logging.getLogger("kraken_ia.telemetry")
            telemetry_logger.setLevel(logging.INFO)
            telemetry_logger.propagate = False
            if not any(isinstance(h, LoggingHandler) for h in telemetry_logger.handlers):
                telemetry_logger.addHandler(otel_handler)
            _TELEMETRY_LOGGER = telemetry_logger
        except Exception:
            pass

        # 4. Instrumentação de callbacks do LiteLLM (Ollama / Modelos)
        _register_litellm_callbacks()
        atexit.register(flush_observability)
        _INITIALIZED = True

    # 5. Instrumenta de forma modular e recursiva o root_agent e toda a árvore de sub-agentes
    if root_agent is not None:
        _instrument_agent_tree(root_agent)


def flush_observability(timeout_millis: int = 5000) -> None:
    """Força o envio imediato de todos os spans, métricas e logs pendentes para o coletor OTLP."""
    try:
        if _TRACER_PROVIDER is not None:
            _TRACER_PROVIDER.force_flush(timeout_millis=timeout_millis)
    except Exception:
        pass
    try:
        if _METER_PROVIDER is not None:
            _METER_PROVIDER.force_flush(timeout_millis=timeout_millis)
    except Exception:
        pass
    try:
        if _LOGGER_PROVIDER is not None:
            _LOGGER_PROVIDER.force_flush(timeout_millis=timeout_millis)
    except Exception:
        pass
