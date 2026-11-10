import React, { useEffect, useState, useRef } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Cpu,
  Bot,
  ShieldCheck,
  FileCode,
  Terminal,
  Activity,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  Layers,
  Sparkles,
  UserCheck,
  Database,
  Lock,
  GitBranch,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { CodeBlock } from './CodeBlock';
import { ExecutionWorkflowFlow } from './ExecutionWorkflowFlow';
import { GuardrailsAuditPanel } from './GuardrailsAuditPanel';

// Helper recursivo para converter strings que contêm JSON em objetos reais
function deepParseJson(val: any): any {
  if (typeof val === 'string') {
    const trimmed = val.trim();
    if (
      (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))
    ) {
      try {
        return deepParseJson(JSON.parse(trimmed));
      } catch {
        return val;
      }
    }
    return val;
  }
  if (Array.isArray(val)) {
    return val.map(deepParseJson);
  }
  if (val && typeof val === 'object') {
    const copy: Record<string, any> = {};
    for (const [k, v] of Object.entries(val)) {
      copy[k] = deepParseJson(v);
    }
    return copy;
  }
  return val;
}

// Extrai código Python embutido em objetos de retorno de ferramentas caso exista
function extractPythonCode(obj: any): { code: string; filename?: string } | null {
  if (!obj || typeof obj !== 'object') return null;
  const parsed = deepParseJson(obj);

  // Procura campos conhecidos com código
  if (parsed.data) {
    if (typeof parsed.data.conteudo_atual === 'string' && parsed.data.conteudo_atual.trim().length > 0) {
      return { code: parsed.data.conteudo_atual, filename: parsed.data.file_path || 'codigo_original.py' };
    }
    if (typeof parsed.data.proposed_code === 'string' && parsed.data.proposed_code.trim().length > 0) {
      return { code: parsed.data.proposed_code, filename: parsed.data.file_path || 'codigo_proposto.py' };
    }
    if (typeof parsed.data.code === 'string' && parsed.data.code.trim().length > 0) {
      return { code: parsed.data.code, filename: parsed.data.file_path || 'pipeline.py' };
    }
  }

  if (typeof parsed.conteudo_atual === 'string' && parsed.conteudo_atual.trim().length > 0) {
    return { code: parsed.conteudo_atual, filename: parsed.file_path || 'codigo_original.py' };
  }
  if (typeof parsed.proposed_code === 'string' && parsed.proposed_code.trim().length > 0) {
    return { code: parsed.proposed_code, filename: parsed.file_path || 'codigo_proposto.py' };
  }
  if (typeof parsed.codigo_proposto === 'string' && parsed.codigo_proposto.trim().length > 0) {
    return { code: parsed.codigo_proposto, filename: 'codigo_proposto.py' };
  }

  return null;
}

export interface InvestigationViewProps {
  execucaoId: string;
  onBackToChat: () => void;
  className?: string;
}

export function InvestigationView({
  execucaoId,
  onBackToChat,
  className,
}: InvestigationViewProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});
  const [activeTab, setActiveTab] = useState<'all' | 'workflow' | 'guardrails' | 'timeline'>('all');

  const stepRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    carregarExecucao();
  }, [execucaoId]);

  const carregarExecucao = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`/api/execucoes/${execucaoId}`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
        // Expande primeira e última etapas por padrão
        setExpandedSteps({ 0: true, 1: true });
      } else {
        setError(`Execução ${execucaoId} não encontrada ou erro no servidor.`);
      }
    } catch (err: any) {
      setError(`Falha ao conectar com a API: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleStep = (idx: number) => {
    setExpandedSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const scrollToStep = (idx: number) => {
    setExpandedSteps((prev) => ({ ...prev, [idx]: true }));
    const el = stepRefs.current[idx];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const getStepIcon = (tipo: string) => {
    switch (tipo) {
      case 'guardrail_entrada':
      case 'guardrail_saida':
        return ShieldCheck;
      case 'transfer':
        return GitBranch;
      case 'tool_execution':
        return Terminal;
      case 'tool_response':
        return Activity;
      case 'decisao_humana':
        return UserCheck;
      case 'execution_error':
        return AlertTriangle;
      default:
        return Layers;
    }
  };

  return (
    <div className={cn('flex flex-col h-full overflow-hidden bg-[#fafbfd]', className)}>
      {/* Top Header com Botão de Voltar ao Chat */}
      <div className="flex items-center justify-between border-b border-slate-200/90 bg-white px-6 py-3.5 shadow-2xs select-none shrink-0">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBackToChat}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-blue-600 transition-all active:scale-98 cursor-pointer"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Voltar ao Chat</span>
          </button>

          <div className="h-4 w-[1px] bg-slate-200" />

          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-blue-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Trilha de Observabilidade, Workflow & Auditoria
            </h2>
            <span className="font-mono text-xs text-slate-400">#{execucaoId}</span>
          </div>
        </div>

        {data && (
          <div className="flex items-center gap-2">
            {data.has_approval_request && (
              <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                <UserCheck className="h-3 w-3" />
                <span>HITL Ativo</span>
              </span>
            )}
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold',
                data.status === 'sucesso'
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-rose-100 text-rose-800'
              )}
            >
              {data.status === 'sucesso' ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              ) : (
                <AlertTriangle className="h-3.5 w-3.5 text-rose-600" />
              )}
              {data.status === 'sucesso' ? 'Sucesso' : 'Falha'}
            </span>
          </div>
        )}
      </div>

      {/* Navegação Rápida entre Seções */}
      {data && (
        <div className="flex items-center gap-2 border-b border-slate-200/80 bg-slate-50/80 px-6 py-2 text-xs font-medium text-slate-600 select-none shrink-0">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
            Visualizar:
          </span>
          <button
            type="button"
            onClick={() => setActiveTab('all')}
            className={cn(
              'rounded-lg px-2.5 py-1 text-xs transition-colors cursor-pointer',
              activeTab === 'all'
                ? 'bg-blue-600 font-semibold text-white shadow-2xs'
                : 'hover:bg-slate-200/60 text-slate-600'
            )}
          >
            Visão Completa
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('workflow')}
            className={cn(
              'rounded-lg px-2.5 py-1 text-xs transition-colors cursor-pointer',
              activeTab === 'workflow'
                ? 'bg-blue-600 font-semibold text-white shadow-2xs'
                : 'hover:bg-slate-200/60 text-slate-600'
            )}
          >
            Workflow Interativo (@xyflow/react)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('guardrails')}
            className={cn(
              'rounded-lg px-2.5 py-1 text-xs transition-colors cursor-pointer',
              activeTab === 'guardrails'
                ? 'bg-blue-600 font-semibold text-white shadow-2xs'
                : 'hover:bg-slate-200/60 text-slate-600'
            )}
          >
            Guardrails & Governança (6 Camadas)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('timeline')}
            className={cn(
              'rounded-lg px-2.5 py-1 text-xs transition-colors cursor-pointer',
              activeTab === 'timeline'
                ? 'bg-blue-600 font-semibold text-white shadow-2xs'
                : 'hover:bg-slate-200/60 text-slate-600'
            )}
          >
            Trilha de Spans & Ferramentas
          </button>
        </div>
      )}

      {/* Conteúdo Principal Scrollável */}
      <div className="flex-1 overflow-y-auto p-6 sm:p-8">
        <div className="mx-auto max-w-5xl space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-24 text-slate-400">
              <Activity className="h-8 w-8 animate-pulse text-blue-600 mb-2" />
              <p className="text-xs">Carregando percurso da execução e grafo de governança...</p>
            </div>
          ) : error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center text-xs text-rose-800">
              <AlertTriangle className="mx-auto h-8 w-8 text-rose-600 mb-2" />
              <p className="font-semibold">{error}</p>
              <button
                type="button"
                onClick={onBackToChat}
                className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 cursor-pointer"
              >
                Voltar ao Chat
              </button>
            </div>
          ) : data ? (
            <>
              {/* Meta Cards com Detalhes da Execução */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
                <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                    <Clock className="h-3.5 w-3.5 text-blue-500" />
                    Latência Total
                  </div>
                  <div className="mt-1 font-mono text-base font-bold text-slate-900">
                    {data.latencia_segundos ?? data.latencia_s ?? '—'}s
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                    <Cpu className="h-3.5 w-3.5 text-purple-500" />
                    Modelo Gemini
                  </div>
                  <div className="mt-1 font-mono text-xs font-semibold text-slate-900 truncate">
                    {(data.modelo || 'gemini-2.5-flash').replace('vertex_ai/', '').replace('gemini/', '')}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                    <Bot className="h-3.5 w-3.5 text-emerald-500" />
                    Agente Especialista
                  </div>
                  <div className="mt-1 text-xs font-semibold text-slate-900 truncate">
                    {data.especialista || 'Kraken Copilot'}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                    <ShieldCheck className="h-3.5 w-3.5 text-amber-500" />
                    Governança & Spans
                  </div>
                  <div className="mt-1 font-mono text-xs font-bold text-slate-900">
                    {(data.etapas || data.steps || []).length} etapas · {data.total_ferramentas || (data.ferramentas_executadas || []).length} ferramentas
                  </div>
                </div>
              </div>

              {/* 1. SEÇÃO DO WORKFLOW INTERATIVO COM @XYFLOW/REACT */}
              {(activeTab === 'all' || activeTab === 'workflow') && (
                <ExecutionWorkflowFlow
                  execucao={data}
                  onSelectStep={scrollToStep}
                />
              )}

              {/* 2. SEÇÃO DA MATRIZ DE GUARDRAILS E GOVERNANÇA CORPORATIVA */}
              {(activeTab === 'all' || activeTab === 'guardrails') && (
                <GuardrailsAuditPanel
                  guardrails={data.guardrails_audit}
                  hasApprovalRequest={data.has_approval_request}
                  humanDecision={data.decisao_humana}
                />
              )}

              {/* 3. SEÇÃO DA TRILHA SEQUENCIAL DE ETAPAS / SPANS */}
              {(activeTab === 'all' || activeTab === 'timeline') && (
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                        Percurso Sequencial de Execução (Spans & Ferramentas)
                      </h3>
                      <p className="text-[11px] text-slate-500">
                        Auditoria atômica de cada entrada, chamada de especialista, retorno de ferramenta e guardrail
                      </p>
                    </div>

                    <span className="font-mono text-[11px] text-slate-400">
                      {(data.etapas || data.steps || []).length} eventos rastreados
                    </span>
                  </div>

                  <div className="space-y-3">
                    {(data.etapas || data.steps || []).map((etapa: any, idx: number) => {
                      const isExpanded = expandedSteps[idx] ?? false;
                      const StepIcon = getStepIcon(etapa.tipo);
                      const pythonCode = extractPythonCode(etapa.resultado) || extractPythonCode(etapa.payload);

                      return (
                        <div
                          key={idx}
                          ref={(el) => (stepRefs.current[idx] = el)}
                          className={cn(
                            'rounded-xl border overflow-hidden text-xs transition-all',
                            isExpanded ? 'border-blue-200 bg-white shadow-2xs' : 'border-slate-200/90 bg-slate-50/50 hover:bg-slate-50'
                          )}
                        >
                          <div
                            onClick={() => toggleStep(idx)}
                            className="flex cursor-pointer items-center justify-between p-3.5 select-none"
                          >
                            <div className="flex items-center gap-3 overflow-hidden">
                              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-blue-100 font-mono text-[10px] font-bold text-blue-700">
                                {idx + 1}
                              </span>

                              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
                                <StepIcon className="h-4 w-4 text-blue-600" />
                              </div>

                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-slate-900 truncate">
                                    {etapa.titulo || etapa.tipo || 'Etapa'}
                                  </span>
                                  {etapa.tipo && (
                                    <span className="rounded bg-slate-100 px-1.5 py-0.2 font-mono text-[9.5px] text-slate-500">
                                      {etapa.tipo}
                                    </span>
                                  )}
                                </div>
                                {etapa.descricao && (
                                  <p className="text-[11px] text-slate-500 truncate">{etapa.descricao}</p>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-3 shrink-0">
                              {etapa.duracao_ms && (
                                <span className="font-mono text-[10.5px] text-slate-500 font-semibold bg-slate-100 px-2 py-0.5 rounded-md">
                                  {etapa.duracao_ms}ms
                                </span>
                              )}
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4 text-slate-400" />
                              ) : (
                                <ChevronRight className="h-4 w-4 text-slate-400" />
                              )}
                            </div>
                          </div>

                          {isExpanded && (
                            <div className="border-t border-slate-100 bg-[#f8fafc] p-4 space-y-3.5">
                              {/* Se a ferramenta gerou código Python legível, exibe no CodeBlock */}
                              {pythonCode && (
                                <div>
                                  <div className="flex items-center justify-between mb-1.5">
                                    <span className="font-bold text-[11px] text-slate-800 flex items-center gap-1.5">
                                      <FileCode className="h-3.5 w-3.5 text-blue-600" />
                                      Código Python Processado / Inspecionado ({pythonCode.filename}):
                                    </span>
                                  </div>
                                  <div className="rounded-xl overflow-hidden border border-slate-800 shadow-sm">
                                    <CodeBlock
                                      code={pythonCode.code}
                                      filename={pythonCode.filename}
                                      language="python"
                                    />
                                  </div>
                                </div>
                              )}

                              {/* Payload / Entradas com visualizador */}
                              {etapa.payload && (
                                <div>
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-semibold text-[11px] text-slate-700 flex items-center gap-1">
                                      <Terminal className="h-3 w-3 text-slate-500" />
                                      Parâmetros & Entrada:
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        navigator.clipboard.writeText(
                                          JSON.stringify(deepParseJson(etapa.payload), null, 2)
                                        );
                                      }}
                                      className="inline-flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-700 cursor-pointer"
                                    >
                                      <Copy className="h-3 w-3" />
                                      <span>Copiar JSON</span>
                                    </button>
                                  </div>
                                  <pre className="max-h-52 overflow-auto rounded-xl bg-slate-900 p-3 font-mono text-[11px] text-slate-200 border border-slate-800 leading-relaxed">
                                    {JSON.stringify(deepParseJson(etapa.payload), null, 2)}
                                  </pre>
                                </div>
                              )}

                              {/* Resultado da Etapa */}
                              {etapa.resultado && (
                                <div>
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-semibold text-[11px] text-slate-700 flex items-center gap-1">
                                      <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                                      Retorno & Resultado Processado:
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        navigator.clipboard.writeText(
                                          JSON.stringify(deepParseJson(etapa.resultado), null, 2)
                                        );
                                      }}
                                      className="inline-flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-700 cursor-pointer"
                                    >
                                      <Copy className="h-3 w-3" />
                                      <span>Copiar JSON</span>
                                    </button>
                                  </div>
                                  <pre className="max-h-52 overflow-auto rounded-xl bg-slate-900 p-3 font-mono text-[11px] text-slate-200 border border-slate-800 leading-relaxed">
                                    {JSON.stringify(deepParseJson(etapa.resultado), null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default InvestigationView;
