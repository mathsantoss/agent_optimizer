import React from 'react';
import { Timer, HardDrive, CheckCircle2, AlertTriangle, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface BenchmarkMetrics {
  tempo_antes?: number | string;
  tempo_depois?: number | string;
  tempo_variacao?: string;
  memoria_antes?: number | string;
  memoria_depois?: number | string;
  memoria_variacao?: string;
  linhas_antes?: number | string;
  linhas_depois?: number | string;
  equivalencia_status?: 'Aprovada' | 'Reprovada' | string;
  equivalencia_msg?: string;
}

export interface InsightCardsProps {
  metrics: BenchmarkMetrics;
  className?: string;
}

export function InsightCards({ metrics, className }: InsightCardsProps) {
  if (!metrics) return null;

  return (
    <div className={cn('my-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-xs', className)}>
      <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          📊 Benchmark Comparativo (Antes vs Depois)
        </h4>
        {metrics.equivalencia_status && (
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold',
              metrics.equivalencia_status.toLowerCase().includes('aprovad')
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-rose-100 text-rose-800'
            )}
          >
            {metrics.equivalencia_status.toLowerCase().includes('aprovad') ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            ) : (
              <AlertTriangle className="h-3.5 w-3.5 text-rose-600" />
            )}
            Equivalência: {metrics.equivalencia_status}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {/* Card 1: Tempo de Execução */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5 font-medium">
              <Timer className="h-3.5 w-3.5 text-blue-500" />
              Tempo de Execução
            </span>
            {metrics.tempo_variacao && (
              <span className="rounded bg-emerald-100 px-1.5 py-0.2 text-[11px] font-semibold text-emerald-700">
                {metrics.tempo_variacao}
              </span>
            )}
          </div>
          <div className="mt-2 flex items-baseline justify-between font-mono text-sm">
            <div className="text-slate-400 text-xs">
              Antes: <span className="text-slate-600 font-semibold">{metrics.tempo_antes ?? '—'}s</span>
            </div>
            <div className="text-slate-900 font-bold text-base">
              {metrics.tempo_depois ?? '—'}s
            </div>
          </div>
        </div>

        {/* Card 2: Pico de Memória */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5 font-medium">
              <HardDrive className="h-3.5 w-3.5 text-purple-500" />
              Pico de Memória
            </span>
            {metrics.memoria_variacao && (
              <span className="rounded bg-emerald-100 px-1.5 py-0.2 text-[11px] font-semibold text-emerald-700">
                {metrics.memoria_variacao}
              </span>
            )}
          </div>
          <div className="mt-2 flex items-baseline justify-between font-mono text-sm">
            <div className="text-slate-400 text-xs">
              Antes: <span className="text-slate-600 font-semibold">{metrics.memoria_antes ?? '—'}MB</span>
            </div>
            <div className="text-slate-900 font-bold text-base">
              {metrics.memoria_depois ?? '—'}MB
            </div>
          </div>
        </div>

        {/* Card 3: Linhas Processadas */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5 font-medium">
              <Layers className="h-3.5 w-3.5 text-amber-500" />
              Linhas Processadas
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between font-mono text-sm">
            <div className="text-slate-400 text-xs">
              Antes: <span className="text-slate-600 font-semibold">{metrics.linhas_antes ?? '—'}</span>
            </div>
            <div className="text-slate-900 font-bold text-base">
              {metrics.linhas_depois ?? metrics.linhas_antes ?? '—'}
            </div>
          </div>
        </div>
      </div>

      {metrics.equivalencia_msg && (
        <div className="mt-3 rounded-lg bg-slate-100/80 px-3 py-2 text-xs text-slate-600 leading-relaxed font-sans">
          <strong>Diagnóstico:</strong> {metrics.equivalencia_msg}
        </div>
      )}
    </div>
  );
}

export default InsightCards;

