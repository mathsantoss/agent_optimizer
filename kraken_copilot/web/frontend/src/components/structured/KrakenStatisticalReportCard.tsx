import React, { useState } from 'react';
import {
  BarChart2,
  Sigma,
  AlertCircle,
  TrendingDown,
  TrendingUp,
  Table,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface KrakenStatisticalMetricData {
  coluna: string;
  media: number;
  desvio_padrao: number;
  minimo: number;
  q25: number;
  mediana: number;
  q75: number;
  maximo: number;
  nulos?: number;
  outliers_iqr?: number;
  limite_inferior_iqr?: number;
  limite_superior_iqr?: number;
}

export interface KrakenStatisticalReportData {
  dataset_nome: string;
  total_linhas_analisadas: number;
  amostragem_ativa?: boolean;
  total_outliers_geral?: number;
  metricas_colunas: KrakenStatisticalMetricData[] | Record<string, any>;
  tabela_markdown?: string;
  insights_estatisticos?: string[];
}

export interface KrakenStatisticalReportCardProps {
  report: KrakenStatisticalReportData;
  className?: string;
}

export function KrakenStatisticalReportCard({
  report,
  className,
}: KrakenStatisticalReportCardProps) {
  const [showTable, setShowTable] = useState(false);

  // Normaliza lista de métricas por coluna
  const metricsList: KrakenStatisticalMetricData[] = Array.isArray(report.metricas_colunas)
    ? report.metricas_colunas
    : Object.entries(report.metricas_colunas || {}).map(([colName, row]: [string, any]) => ({
        coluna: colName,
        media: Number(row.media ?? row.mean ?? 0),
        desvio_padrao: Number(row.desvio_padrao ?? row.std ?? 0),
        minimo: Number(row.minimo ?? row.min ?? 0),
        q25: Number(row.q25 ?? row['25%'] ?? 0),
        mediana: Number(row.mediana ?? row['50%'] ?? 0),
        q75: Number(row.q75 ?? row['75%'] ?? 0),
        maximo: Number(row.maximo ?? row.max ?? 0),
        nulos: Number(row.nulos ?? 0),
        outliers_iqr: Number(row.outliers_iqr ?? 0),
        limite_inferior_iqr: row.limite_inferior_iqr,
        limite_superior_iqr: row.limite_superior_iqr,
      }));

  return (
    <div
      className={cn(
        'my-3 overflow-hidden rounded-2xl border border-purple-200/90 bg-gradient-to-b from-white to-purple-50/20 shadow-xs transition-all',
        className
      )}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between border-b border-purple-100 bg-purple-50/60 px-4 py-2.5 text-xs">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-purple-600 text-white shadow-2xs">
            <Sigma className="h-3.5 w-3.5" />
          </div>
          <div>
            <span className="font-bold text-slate-900">Relatório Estatístico &amp; Outliers (KrakenStatisticalReport)</span>
            <span className="ml-2 font-mono text-[11px] text-slate-500">
              {report.dataset_nome}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {report.total_outliers_geral !== undefined && report.total_outliers_geral > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800 border border-amber-200">
              <AlertCircle className="h-3 w-3 text-amber-600" />
              <span>{report.total_outliers_geral} outliers (IQR)</span>
            </span>
          ) : (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
              0 outliers
            </span>
          )}
          <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-mono font-bold text-purple-800">
            {report.total_linhas_analisadas.toLocaleString()} linhas
          </span>
        </div>
      </div>

      {/* Grid de Cards Estatísticos por Coluna */}
      <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3">
        {metricsList.map((m) => (
          <div
            key={m.coluna}
            className="rounded-xl border border-slate-200/90 bg-white p-3.5 shadow-2xs transition-all hover:border-purple-300"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-slate-900 truncate">
                {m.coluna}
              </span>
              {m.outliers_iqr !== undefined && m.outliers_iqr > 0 ? (
                <span className="rounded bg-rose-100 px-1.5 py-0.2 font-mono text-[10px] font-bold text-rose-700">
                  {m.outliers_iqr} outliers
                </span>
              ) : (
                <span className="rounded bg-slate-100 px-1.5 py-0.2 font-mono text-[10px] text-slate-500">
                  Normal
                </span>
              )}
            </div>

            {/* Métricas Principais */}
            <div className="mt-2.5 grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-[10px] text-slate-400">Média</div>
                <div className="font-mono font-bold text-slate-800">
                  {m.media.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Mediana (Q2)</div>
                <div className="font-mono font-bold text-slate-800">
                  {m.mediana.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Desvio Padrão</div>
                <div className="font-mono text-slate-600">
                  {m.desvio_padrao.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Amplitude [Min - Max]</div>
                <div className="font-mono text-slate-600 text-[10.5px]">
                  [{m.minimo.toFixed(1)}, {m.maximo.toFixed(1)}]
                </div>
              </div>
            </div>

            {/* Intervalo Interquartil (IQR) */}
            <div className="mt-2 pt-2 border-t border-slate-100 text-[10.5px] font-mono text-slate-500 flex justify-between">
              <span>Q1 (25%): {m.q25.toFixed(1)}</span>
              <span>Q3 (75%): {m.q75.toFixed(1)}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Accordion para Tabela Completa */}
      {report.tabela_markdown && (
        <div className="border-t border-slate-100 px-4 py-2 bg-white/70">
          <button
            type="button"
            onClick={() => setShowTable(!showTable)}
            className="flex w-full items-center justify-between py-1 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors cursor-pointer"
          >
            <span className="flex items-center gap-1.5">
              <Table className="h-3.5 w-3.5 text-purple-600" />
              <span>Ver Tabela Estatística Completa</span>
            </span>
            {showTable ? <ChevronUp className="h-3.5 w-3.5 text-slate-400" /> : <ChevronDown className="h-3.5 w-3.5 text-slate-400" />}
          </button>

          {showTable && (
            <div className="mt-2 overflow-x-auto rounded-xl border border-slate-200/80 bg-white p-3 font-mono text-xs">
              <pre className="overflow-x-auto whitespace-pre leading-relaxed text-slate-800">
                {report.tabela_markdown}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default KrakenStatisticalReportCard;

