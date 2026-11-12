import React from 'react';
import {
  Zap,
  TrendingUp,
  Cpu,
  Clock,
  HardDrive,
  CheckCircle2,
  XCircle,
  FileCode2,
  BarChart3,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface KrakenBenchmarkData {
  arquivo: string;
  baseline_arquivo?: string;
  status?: string;
  tempo_execucao_original: number;
  tempo_execucao_otimizado: number;
  speedup: number;
  memoria_pico_original_mb: number;
  memoria_pico_otimizada_mb: number;
  reducao_memoria_pct: number;
  linhas_baseline?: number;
  linhas_candidato?: number;
  equivalencia_preservada: boolean;
  detalhes_equivalencia?: string;
  tabela_markdown?: string;
  metricas_adicionais?: Record<string, any>;
}

export interface KrakenBenchmarkCardProps {
  benchmark: KrakenBenchmarkData;
  className?: string;
}

export function KrakenBenchmarkCard({ benchmark, className }: KrakenBenchmarkCardProps) {
  const isSpeedupPositive = benchmark.speedup > 0;
  const isMemoryReduced = benchmark.reducao_memoria_pct > 0;
  const speedupMultiplier =
    benchmark.tempo_execucao_otimizado > 0
      ? (benchmark.tempo_execucao_original / benchmark.tempo_execucao_otimizado).toFixed(1)
      : '1.0';

  return (
    <div
      className={cn(
        'my-3 overflow-hidden rounded-2xl border border-emerald-200/90 bg-gradient-to-b from-white to-emerald-50/20 shadow-xs transition-all',
        className
      )}
    >
      {/* Header do Benchmark */}
      <div className="flex flex-wrap items-center justify-between border-b border-emerald-100 bg-emerald-50/60 px-4 py-2.5 text-xs">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-2xs">
            <Zap className="h-3.5 w-3.5" />
          </div>
          <div>
            <span className="font-bold text-slate-900">Benchmark Comparativo (Antes vs Depois)</span>
            <span className="ml-2 font-mono text-[11px] text-slate-500">
              krakenlake/workspace/{benchmark.arquivo}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {benchmark.equivalencia_preservada ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 border border-emerald-200">
              <CheckCircle2 className="h-3 w-3 text-emerald-600" />
              <span>Equivalência Aprovada</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-800 border border-rose-200">
              <XCircle className="h-3 w-3 text-rose-600" />
              <span>Equivalência Reprovada</span>
            </span>
          )}
        </div>
      </div>

      {/* Grid de Métricas Principais (Hero KPI Cards) */}
      <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-3">
        {/* Card 1: Speedup / Tempo */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-3 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-[11px]">
            <span className="flex items-center gap-1 font-medium">
              <Clock className="h-3.5 w-3.5 text-blue-600" />
              <span>Tempo de Execução</span>
            </span>
            <span
              className={cn(
                'rounded px-1.5 py-0.2 text-[10px] font-mono font-bold',
                isSpeedupPositive ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
              )}
            >
              {isSpeedupPositive ? `+${benchmark.speedup.toFixed(1)}%` : `${benchmark.speedup.toFixed(1)}%`}
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-mono text-base font-bold text-slate-900">
              {benchmark.tempo_execucao_otimizado.toFixed(4)}s
            </span>
            <span className="font-mono text-xs text-slate-400 line-through">
              {benchmark.tempo_execucao_original.toFixed(4)}s
            </span>
          </div>
          <div className="mt-1 text-[10.5px] text-emerald-700 font-medium">
            {speedupMultiplier}x mais rápido na CPU
          </div>
        </div>

        {/* Card 2: Pico de Memória */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-3 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-[11px]">
            <span className="flex items-center gap-1 font-medium">
              <HardDrive className="h-3.5 w-3.5 text-purple-600" />
              <span>Pico de Memória RAM</span>
            </span>
            <span
              className={cn(
                'rounded px-1.5 py-0.2 text-[10px] font-mono font-bold',
                isMemoryReduced ? 'bg-purple-100 text-purple-800' : 'bg-slate-100 text-slate-600'
              )}
            >
              {isMemoryReduced
                ? `-${benchmark.reducao_memoria_pct.toFixed(1)}%`
                : `${benchmark.reducao_memoria_pct.toFixed(1)}%`}
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-mono text-base font-bold text-slate-900">
              {benchmark.memoria_pico_otimizada_mb.toFixed(2)} MB
            </span>
            <span className="font-mono text-xs text-slate-400 line-through">
              {benchmark.memoria_pico_original_mb.toFixed(2)} MB
            </span>
          </div>
          <div className="mt-1 text-[10.5px] text-slate-500">
            {benchmark.reducao_memoria_pct > 0
              ? 'Economia de footprint de memória'
              : 'Consumo estável de memória'}
          </div>
        </div>

        {/* Card 3: Linhas e Integridade */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-3 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-[11px]">
            <span className="flex items-center gap-1 font-medium">
              <BarChart3 className="h-3.5 w-3.5 text-emerald-600" />
              <span>Volume Processado</span>
            </span>
            <span className="rounded bg-slate-100 px-1.5 py-0.2 text-[10px] font-mono text-slate-600">
              {benchmark.status || 'OK'}
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-mono text-base font-bold text-slate-900">
              {benchmark.linhas_candidato?.toLocaleString() ?? '10.000'} linhas
            </span>
          </div>
          <div className="mt-1 text-[10.5px] text-slate-500 truncate" title={benchmark.detalhes_equivalencia}>
            {benchmark.detalhes_equivalencia || 'Contrato funcional preservado'}
          </div>
        </div>
      </div>
    </div>
  );
}

export default KrakenBenchmarkCard;

