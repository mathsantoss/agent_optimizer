import React, { useMemo, useState } from 'react';
import {
  GraphProvider,
  GraphRenderer,
  createSpec,
  pipe,
  geom,
  scale,
  config,
} from '@graphysdk/react';
import { BarChart3, LineChart as LineChartIcon, AreaChart as AreaChartIcon, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface GraphyChartProps {
  type?: 'bar' | 'line' | 'area';
  title?: string;
  subtitle?: string;
  data: Array<Record<string, any>>;
  x: string;
  y: string;
  className?: string;
  height?: number;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class ChartErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: any) {
    console.warn('Erro ao renderizar gráfico Graphy SDK:', error);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export function GraphyChart({
  type = 'bar',
  title,
  subtitle,
  data,
  x,
  y,
  className,
  height = 320,
}: GraphyChartProps) {
  const [activeTab, setActiveTab] = useState<'chart' | 'data'>('chart');

  // Sanitiza os dados para garantir que campos y sejam numéricos
  const sanitizedData = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return data.map((item) => {
      const copy = { ...item };
      const rawY = copy[y];
      const parsedY = typeof rawY === 'number' ? rawY : parseFloat(String(rawY).replace(/[^\d.-]/g, ''));
      copy[y] = isNaN(parsedY) ? 0 : parsedY;
      copy[x] = String(copy[x] ?? '');
      return copy;
    });
  }, [data, x, y]);

  // Cria a especificação compilável do Graphy SDK
  const chartSpec = useMemo(() => {
    try {
      let selectedGeom = geom.bar();
      if (type === 'line') {
        selectedGeom = geom.line();
      } else if (type === 'area') {
        selectedGeom = geom.area();
      }

      return pipe(
        createSpec({ x, y }),
        selectedGeom,
        scale.x(),
        scale.y(),
        config({
          content: {
            graphyBadge: { visible: false },
          },
        })
      );
    } catch (e) {
      console.warn('Falha ao compilar especificação Graphy:', e);
      return null;
    }
  }, [type, x, y]);

  if (!sanitizedData || sanitizedData.length === 0 || !x || !y) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center text-xs text-slate-500">
        Dados insuficientes para renderizar gráfico.
      </div>
    );
  }

  const icon =
    type === 'line' ? (
      <LineChartIcon className="h-4 w-4 text-blue-600" />
    ) : type === 'area' ? (
      <AreaChartIcon className="h-4 w-4 text-emerald-600" />
    ) : (
      <BarChart3 className="h-4 w-4 text-purple-600" />
    );

  // Fallback visual limpo em SVG caso o canvas/webgl do browser falhe
  const renderFallbackBars = () => {
    const maxY = Math.max(...sanitizedData.map((d) => d[y]), 1);
    return (
      <div className="flex h-48 items-end gap-2 px-4 pb-4 pt-8">
        {sanitizedData.slice(0, 15).map((d, idx) => {
          const pct = Math.max(8, Math.round((d[y] / maxY) * 100));
          return (
            <div key={idx} className="flex-1 flex flex-col items-center gap-1 group">
              <span className="text-[9px] font-mono text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
                {d[y]}
              </span>
              <div
                style={{ height: `${pct}%` }}
                className="w-full rounded-t-sm bg-gradient-to-t from-purple-600 to-indigo-500 transition-all hover:brightness-110"
              />
              <span className="w-full truncate text-center text-[10px] font-mono text-slate-500" title={d[x]}>
                {d[x]}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div
      className={cn(
        'my-4 w-full overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xs transition-all',
        className
      )}
    >
      {/* Header do Gráfico */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50/70 px-4 py-3 select-none">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white shadow-2xs border border-slate-200/60">
            {icon}
          </div>
          <div>
            <div className="text-xs font-bold text-slate-800">
              {title || `Visualização: ${x} vs ${y}`}
            </div>
            {subtitle && (
              <div className="text-[11px] text-slate-500">{subtitle}</div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 rounded-lg bg-slate-200/60 p-0.5 text-[11px] font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab('chart')}
            className={cn(
              'rounded-md px-2.5 py-1 transition-all cursor-pointer',
              activeTab === 'chart'
                ? 'bg-white text-slate-900 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            )}
          >
            Gráfico Interativo
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('data')}
            className={cn(
              'rounded-md px-2.5 py-1 transition-all cursor-pointer',
              activeTab === 'data'
                ? 'bg-white text-slate-900 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            )}
          >
            Tabela ({sanitizedData.length})
          </button>
        </div>
      </div>

      {/* Conteúdo do Gráfico / Tabela */}
      <div className="p-4" style={{ minHeight: height }}>
        {activeTab === 'chart' ? (
          <ChartErrorBoundary fallback={renderFallbackBars()}>
            {chartSpec ? (
              <div className="h-full w-full" style={{ height }}>
                <GraphProvider data={sanitizedData} spec={chartSpec} telemetry={false}>
                  <GraphRenderer />
                </GraphProvider>
              </div>
            ) : (
              renderFallbackBars()
            )}
          </ChartErrorBoundary>
        ) : (
          <div className="max-h-64 overflow-auto rounded-xl border border-slate-100">
            <table className="w-full text-left font-mono text-[11px]">
              <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-700">
                <tr>
                  <th className="px-3 py-1.5">{x}</th>
                  <th className="px-3 py-1.5 text-right">{y}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sanitizedData.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50/60">
                    <td className="px-3 py-1 text-slate-800">{row[x]}</td>
                    <td className="px-3 py-1 text-right font-semibold text-purple-700">{row[y]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer com Metadados da Visualização */}
      <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/40 px-4 py-2 text-[10px] text-slate-400 select-none font-mono">
        <span>Eixo X: {x} · Eixo Y: {y}</span>
        <span className="font-semibold text-purple-600/80">Powered by Graphy SDK</span>
      </div>
    </div>
  );
}

export default GraphyChart;

