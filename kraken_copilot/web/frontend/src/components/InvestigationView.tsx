import React, { useEffect, useState } from 'react';
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
  ExternalLink,
  Copy,
  Check,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { CodeBlock } from './CodeBlock';

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

  return (
    <div className={cn('flex flex-col h-full overflow-hidden bg-[#fafbfd]', className)}>
      {/* Top Header com Botão de Voltar ao Chat */}
      <div className="flex items-center justify-between border-b border-slate-200/90 bg-white px-6 py-3.5 shadow-2xs select-none">
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
              Trilha de Observabilidade e Auditoria
            </h2>
            <span className="font-mono text-xs text-slate-400">#{execucaoId}</span>
          </div>
        </div>

        {data && (
          <div className="flex items-center gap-2">
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

      {/* Conteúdo Principal */}
      <div className="flex-1 overflow-y-auto p-6 sm:p-8">
        <div className="mx-auto max-w-4xl space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <Activity className="h-8 w-8 animate-pulse text-blue-600 mb-2" />
              <p className="text-xs">Carregando percurso da execução...</p>
            </div>
          ) : error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center text-xs text-rose-800">
              <AlertTriangle className="mx-auto h-8 w-8 text-rose-600 mb-2" />
              <p className="font-semibold">{error}</p>
              <button
                type="button"
                onClick={onBackToChat}
                className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700"
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
                    {data.modelo || 'gemini-2.5-flash'}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                    <Bot className="h-3.5 w-3.5 text-emerald-500" />
                    Agente Ativo
                  </div>
                  <div className="mt-1 text-xs font-semibold text-slate-900 truncate">
                    {data.especialista || 'Kraken Copilot'}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                    <ShieldCheck className="h-3.5 w-3.5 text-amber-500" />
                    Total de Etapas
                  </div>
                  <div className="mt-1 font-mono text-base font-bold text-slate-900">
                    {(data.etapas || data.steps || []).length} etapas
                  </div>
                </div>
              </div>

              {/* Linha do Tempo das Etapas */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
                <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Percurso Sequencial de Execução (Spans & Ferramentas)
                </h3>

                <div className="space-y-3">
                  {(data.etapas || data.steps || []).map((etapa: any, idx: number) => {
                    const isExpanded = expandedSteps[idx] ?? false;
                    return (
                      <div
                        key={idx}
                        className="rounded-xl border border-slate-200/90 bg-slate-50/50 overflow-hidden text-xs transition-all"
                      >
                        <div
                          onClick={() => toggleStep(idx)}
                          className="flex cursor-pointer items-center justify-between p-3 select-none hover:bg-slate-100/70"
                        >
                          <div className="flex items-center gap-2.5">
                            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 font-mono text-[10px] font-bold text-blue-700">
                              {idx + 1}
                            </span>
                            <div>
                              <span className="font-semibold text-slate-800">
                                {etapa.titulo || etapa.tipo || 'Etapa'}
                              </span>
                              {etapa.descricao && (
                                <p className="text-[11px] text-slate-500">{etapa.descricao}</p>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {etapa.duracao_ms && (
                              <span className="font-mono text-[10px] text-slate-400">
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
                          <div className="border-t border-slate-200/70 bg-white p-3.5 space-y-3">
                            {etapa.payload && (
                              <div>
                                <div className="flex items-center justify-between mb-1">
                                  <span className="font-semibold text-[11px] text-slate-700">Payload / Entradas:</span>
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
                                    <span>Copiar</span>
                                  </button>
                                </div>
                                <pre className="max-h-60 overflow-auto rounded-xl bg-slate-900 p-3 font-mono text-[11px] text-slate-200 border border-slate-800 leading-relaxed">
                                  {JSON.stringify(deepParseJson(etapa.payload), null, 2)}
                                </pre>
                              </div>
                            )}

                            {etapa.resultado && (
                              <div>
                                <div className="flex items-center justify-between mb-1">
                                  <span className="font-semibold text-[11px] text-slate-700">Resultado:</span>
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
                                    <span>Copiar</span>
                                  </button>
                                </div>
                                <pre className="max-h-60 overflow-auto rounded-xl bg-slate-900 p-3 font-mono text-[11px] text-slate-200 border border-slate-800 leading-relaxed">
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
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default InvestigationView;

