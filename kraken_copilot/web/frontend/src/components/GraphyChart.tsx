import React, { useState, useMemo } from 'react';
import { BarChart3, LineChart as LineChartIcon, Table as TableIcon, ArrowUpRight } from 'lucide-react';
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

export function GraphyChart({
  type = 'bar',
  title,
  subtitle,
  data = [],
  x,
  y,
  className,
  height = 280,
}: GraphyChartProps) {
  const [activeTab, setActiveTab] = useState<'chart' | 'data'>('chart');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Sanitização e formatação dos dados
  const sanitizedData = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return data.map((item) => {
      const copy = { ...item };
      const rawY = copy[y];
      const parsedY =
        typeof rawY === 'number'
          ? rawY
          : parseFloat(String(rawY).replace(/[^\d.-]/g, ''));
      copy[y] = isNaN(parsedY) ? 0 : parsedY;
      copy[x] = String(copy[x] ?? '');
      return copy;
    });
  }, [data, x, y]);

  // Estatísticas descritivas rápidas para o cabeçalho
  const stats = useMemo(() => {
    if (sanitizedData.length === 0) return { max: 0, min: 0, avg: 0, total: 0 };
    const values = sanitizedData.map((d) => d[y]);
    const total = values.reduce((acc, val) => acc + val, 0);
    const max = Math.max(...values, 1);
    const min = Math.min(...values);
    const avg = total / values.length;
    return { max, min, avg, total };
  }, [sanitizedData, y]);

  if (!sanitizedData || sanitizedData.length === 0 || !x || !y) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center text-xs text-slate-500">
        Nenhum dado numérico válido para renderizar gráfico.
      </div>
    );
  }

  // Formatação amigável para números grandes e moedas
  const formatValue = (val: number): string => {
    if (val >= 1_000_000) {
      return `R$ ${(val / 1_000_000).toFixed(2)}M`;
    }
    if (val >= 1_000) {
      return `R$ ${(val / 1_000).toFixed(1)}k`;
    }
    return val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const chartHeight = Math.max(height, 240);
  const paddingX = 40;
  const paddingY = 40;
  const svgWidth = 800;
  const svgHeight = chartHeight;
  const innerWidth = svgWidth - paddingX * 2;
  const innerHeight = svgHeight - paddingY * 2;

  // Renderizador SVG Vetorial Nativo e Fluido (Barras)
  const renderBars = () => {
    const barCount = sanitizedData.length;
    const barWidth = Math.max(16, Math.min(48, innerWidth / (barCount * 1.5)));
    const gap = (innerWidth - barWidth * barCount) / (barCount + 1);

    return (
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="w-full h-full overflow-visible select-none"
      >
        <defs>
          <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#1d4ed8" />
          </linearGradient>
          <linearGradient id="barGradientHover" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#60a5fa" />
            <stop offset="100%" stopColor="#2563eb" />
          </linearGradient>
        </defs>

        {/* Linhas de Grade Horizontais */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
          const lineY = paddingY + innerHeight * (1 - pct);
          const val = stats.max * pct;
          return (
            <g key={idx}>
              <line
                x1={paddingX}
                y1={lineY}
                x2={svgWidth - paddingX}
                y2={lineY}
                stroke="#e2e8f0"
                strokeDasharray="4 4"
                strokeWidth="1"
              />
              <text
                x={paddingX - 8}
                y={lineY + 3}
                textAnchor="end"
                className="text-[10px] font-mono fill-slate-400"
              >
                {formatValue(val)}
              </text>
            </g>
          );
        })}

        {/* Barras e Rótulos */}
        {sanitizedData.map((d, idx) => {
          const barHeight = Math.max(4, (d[y] / stats.max) * innerHeight);
          const posX = paddingX + gap + idx * (barWidth + gap);
          const posY = paddingY + innerHeight - barHeight;
          const isHovered = hoveredIndex === idx;

          return (
            <g
              key={idx}
              className="cursor-pointer transition-all duration-150"
              onMouseEnter={() => setHoveredIndex(idx)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <rect
                x={posX}
                y={posY}
                width={barWidth}
                height={barHeight}
                rx="6"
                ry="6"
                fill={isHovered ? 'url(#barGradientHover)' : 'url(#barGradient)'}
                className="transition-all duration-200"
              />

              {/* Rótulo do Eixo X */}
              <text
                x={posX + barWidth / 2}
                y={svgHeight - 12}
                textAnchor="middle"
                className={cn(
                  'text-[10px] font-mono transition-colors',
                  isHovered ? 'fill-blue-700 font-bold' : 'fill-slate-500'
                )}
              >
                {d[x].length > 12 ? `${d[x].slice(0, 10)}…` : d[x]}
              </text>

              {/* Tooltip inline de Valor ao passar o mouse */}
              {isHovered && (
                <g>
                  <rect
                    x={posX + barWidth / 2 - 45}
                    y={posY - 26}
                    width="90"
                    height="20"
                    rx="4"
                    fill="#0f172a"
                    className="shadow-md"
                  />
                  <text
                    x={posX + barWidth / 2}
                    y={posY - 12}
                    textAnchor="middle"
                    className="text-[10px] font-mono font-bold fill-white"
                  >
                    {formatValue(d[y])}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  // Renderizador SVG para Linhas e Áreas
  const renderLines = () => {
    const points = sanitizedData.map((d, idx) => {
      const px = paddingX + (idx / Math.max(sanitizedData.length - 1, 1)) * innerWidth;
      const py = paddingY + innerHeight - (d[y] / stats.max) * innerHeight;
      return { x: px, y: py, data: d };
    });

    const pathD = points.reduce(
      (acc, p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`),
      ''
    );
    const areaD = `${pathD} L ${points[points.length - 1].x} ${paddingY + innerHeight} L ${points[0].x} ${paddingY + innerHeight} Z`;

    return (
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="w-full h-full overflow-visible select-none"
      >
        <defs>
          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Linhas de Grade Horizontais */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
          const lineY = paddingY + innerHeight * (1 - pct);
          const val = stats.max * pct;
          return (
            <g key={idx}>
              <line
                x1={paddingX}
                y1={lineY}
                x2={svgWidth - paddingX}
                y2={lineY}
                stroke="#e2e8f0"
                strokeDasharray="4 4"
                strokeWidth="1"
              />
              <text
                x={paddingX - 8}
                y={lineY + 3}
                textAnchor="end"
                className="text-[10px] font-mono fill-slate-400"
              >
                {formatValue(val)}
              </text>
            </g>
          );
        })}

        {/* Área preenchida */}
        <path d={areaD} fill="url(#areaGradient)" />

        {/* Linha principal */}
        <path
          d={pathD}
          fill="none"
          stroke="#2563eb"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Pontos de dados */}
        {points.map((p, idx) => {
          const isHovered = hoveredIndex === idx;
          return (
            <g
              key={idx}
              className="cursor-pointer"
              onMouseEnter={() => setHoveredIndex(idx)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <circle
                cx={p.x}
                cy={p.y}
                r={isHovered ? 6 : 4}
                className={cn(
                  'transition-all duration-150',
                  isHovered ? 'fill-blue-600 stroke-white stroke-2' : 'fill-white stroke-blue-600 stroke-2'
                )}
              />
              <text
                x={p.x}
                y={svgHeight - 12}
                textAnchor="middle"
                className={cn(
                  'text-[10px] font-mono transition-colors',
                  isHovered ? 'fill-blue-700 font-bold' : 'fill-slate-500'
                )}
              >
                {p.data[x].length > 12 ? `${p.data[x].slice(0, 10)}…` : p.data[x]}
              </text>

              {isHovered && (
                <g>
                  <rect
                    x={p.x - 45}
                    y={p.y - 28}
                    width="90"
                    height="20"
                    rx="4"
                    fill="#0f172a"
                    className="shadow-md"
                  />
                  <text
                    x={p.x}
                    y={p.y - 14}
                    textAnchor="middle"
                    className="text-[10px] font-mono font-bold fill-white"
                  >
                    {formatValue(p.data[y])}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  return (
    <div
      className={cn(
        'my-3.5 w-full overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xs transition-all',
        className
      )}
    >
      {/* Header do Card com Visual Beautiful UI */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50/70 px-4 py-3 select-none">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600 shadow-2xs border border-blue-100/80">
            {type === 'line' ? (
              <LineChartIcon className="h-4 w-4" />
            ) : (
              <BarChart3 className="h-4 w-4" />
            )}
          </div>
          <div>
            <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
              <span>{title || `Visualização: ${x} vs ${y}`}</span>
            </div>
            <div className="text-[11px] text-slate-500">
              {subtitle || `Total: ${formatValue(stats.total)} · Média: ${formatValue(stats.avg)}`}
            </div>
          </div>
        </div>

        {/* Alternador de Visualização (Gráfico vs Tabela) */}
        <div className="flex items-center gap-1 rounded-xl bg-slate-200/60 p-0.5 text-[11px] font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab('chart')}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-2.5 py-1 transition-all cursor-pointer',
              activeTab === 'chart'
                ? 'bg-white text-blue-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            )}
          >
            {type === 'line' ? <LineChartIcon className="h-3 w-3" /> : <BarChart3 className="h-3 w-3" />}
            <span>Gráfico</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('data')}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-2.5 py-1 transition-all cursor-pointer',
              activeTab === 'data'
                ? 'bg-white text-blue-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            )}
          >
            <TableIcon className="h-3 w-3" />
            <span>Dados ({sanitizedData.length})</span>
          </button>
        </div>
      </div>

      {/* Conteúdo: Gráfico Vetorial Interativo ou Tabela */}
      <div className="p-4" style={{ minHeight: chartHeight }}>
        {activeTab === 'chart' ? (
          <div className="h-full w-full flex items-center justify-center" style={{ height: chartHeight }}>
            {type === 'line' || type === 'area' ? renderLines() : renderBars()}
          </div>
        ) : (
          <div className="max-h-72 overflow-auto rounded-xl border border-slate-100 font-mono text-[11px]">
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-700">
                <tr>
                  <th className="px-3 py-2 font-semibold">{x}</th>
                  <th className="px-3 py-2 font-semibold text-right">{y}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sanitizedData.map((row, i) => (
                  <tr key={i} className="hover:bg-blue-50/30 transition-colors">
                    <td className="px-3 py-1.5 text-slate-800">{row[x]}</td>
                    <td className="px-3 py-1.5 text-right font-semibold text-blue-700">
                      {formatValue(row[y])}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer com Metadados */}
      <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/50 px-4 py-2 text-[10px] text-slate-400 select-none font-mono">
        <span>Dimensão: {x} · Métrica: {y}</span>
        <span className="font-semibold text-blue-600/80">Kraken Visuals · Beautiful UI</span>
      </div>
    </div>
  );
}

export default GraphyChart;
