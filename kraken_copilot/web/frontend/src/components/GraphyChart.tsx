import React, { useState, useMemo } from 'react';
import {
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  ScatterChart as ScatterChartIcon,
  Table as TableIcon,
  TrendingUp,
  Percent,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type ChartType = 'bar' | 'line' | 'area' | 'pie' | 'donut' | 'scatter';

export interface GraphyChartProps {
  type?: ChartType;
  title?: string;
  subtitle?: string;
  data: Array<Record<string, any>>;
  x: string;
  y: string;
  className?: string;
  height?: number;
}

const PALETTE = [
  '#3b82f6', // blue
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ec4899', // pink
  '#6366f1', // indigo
  '#14b8a6', // teal
  '#f97316', // orange
  '#a855f7', // purple
];

export function GraphyChart({
  type: initialType = 'bar',
  title,
  subtitle,
  data = [],
  x,
  y,
  className,
  height = 290,
}: GraphyChartProps) {
  const [activeTab, setActiveTab] = useState<'chart' | 'data'>('chart');
  const [currentType, setCurrentType] = useState<ChartType>(initialType);
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

      // Se for scatter, também tenta parsear X como número
      if (currentType === 'scatter') {
        const rawX = copy[x];
        const parsedX =
          typeof rawX === 'number'
            ? rawX
            : parseFloat(String(rawX).replace(/[^\d.-]/g, ''));
        copy._numX = isNaN(parsedX) ? 0 : parsedX;
      }
      copy[x] = String(copy[x] ?? '');
      return copy;
    });
  }, [data, x, y, currentType]);

  // Estatísticas descritivas rápidas para o cabeçalho e cálculos
  const stats = useMemo(() => {
    if (sanitizedData.length === 0) return { max: 0, min: 0, avg: 0, total: 0, maxX: 0, minX: 0 };
    const valuesY = sanitizedData.map((d) => d[y]);
    const total = valuesY.reduce((acc, val) => acc + val, 0);
    const max = Math.max(...valuesY, 1);
    const min = Math.min(...valuesY);
    const avg = total / valuesY.length;

    let maxX = 1;
    let minX = 0;
    if (currentType === 'scatter') {
      const valuesX = sanitizedData.map((d) => d._numX ?? 0);
      maxX = Math.max(...valuesX, 1);
      minX = Math.min(...valuesX, 0);
    }

    return { max, min, avg, total, maxX, minX };
  }, [sanitizedData, y, currentType]);

  if (!sanitizedData || sanitizedData.length === 0 || !x || !y) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center text-xs text-slate-500">
        Nenhum dado numérico válido para renderizar gráfico.
      </div>
    );
  }

  // Formatação amigável para números grandes e moedas
  const formatValue = (val: number): string => {
    if (Math.abs(val) >= 1_000_000) {
      return `R$ ${(val / 1_000_000).toFixed(2)}M`;
    }
    if (Math.abs(val) >= 1_000) {
      return `R$ ${(val / 1_000).toFixed(1)}k`;
    }
    return val.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  };

  const chartHeight = Math.max(height, 250);
  const paddingX = 45;
  const paddingY = 40;
  const svgWidth = 800;
  const svgHeight = chartHeight;
  const innerWidth = svgWidth - paddingX * 2;
  const innerHeight = svgHeight - paddingY * 2;

  // 1. RENDERIZADOR BARRAS (BAR)
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

  // 2. RENDERIZADOR LINHAS E ÁREAS (LINE / AREA)
  const renderLines = (isArea = false) => {
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
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.35" />
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
        {isArea && <path d={areaD} fill="url(#areaGradient)" />}

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

  // 3. RENDERIZADOR PIE & DONUT (COMPOSIÇÃO / PROPORÇÃO)
  const renderPie = (isDonut = false) => {
    const total = stats.total || 1;
    const cx = 260;
    const cy = chartHeight / 2;
    const outerR = Math.min(105, chartHeight / 2 - 16);
    const innerR = isDonut ? outerR * 0.58 : 0;

    let currentAngle = -Math.PI / 2; // começa no topo (12h)

    const slices = sanitizedData.slice(0, 8).map((d, idx) => {
      const val = Math.max(0, d[y]);
      const angle = (val / total) * Math.PI * 2;
      const startAngle = currentAngle;
      const endAngle = currentAngle + angle;
      currentAngle = endAngle;

      const pct = ((val / total) * 100).toFixed(1);
      const color = PALETTE[idx % PALETTE.length];

      // Coordenadas externas
      const x1 = cx + outerR * Math.cos(startAngle);
      const y1 = cy + outerR * Math.sin(startAngle);
      const x2 = cx + outerR * Math.cos(endAngle);
      const y2 = cy + outerR * Math.sin(endAngle);

      const largeArc = angle > Math.PI ? 1 : 0;

      let pathD = '';
      if (isDonut) {
        const ix1 = cx + innerR * Math.cos(endAngle);
        const iy1 = cy + innerR * Math.sin(endAngle);
        const ix2 = cx + innerR * Math.cos(startAngle);
        const iy2 = cy + innerR * Math.sin(startAngle);
        pathD = `M ${x1} ${y1} A ${outerR} ${outerR} 0 ${largeArc} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${innerR} ${innerR} 0 ${largeArc} 0 ${ix2} ${iy2} Z`;
      } else {
        pathD = `M ${cx} ${cy} L ${x1} ${y1} A ${outerR} ${outerR} 0 ${largeArc} 1 ${x2} ${y2} Z`;
      }

      return {
        pathD,
        color,
        label: d[x],
        val,
        pct,
        idx,
      };
    });

    const activeSlice = hoveredIndex !== null ? slices[hoveredIndex] : null;

    return (
      <div className="flex h-full w-full flex-col md:flex-row items-center justify-between gap-4 px-2">
        <div className="relative flex-1 flex items-center justify-center">
          <svg viewBox={`0 0 520 ${chartHeight}`} className="h-full w-full max-w-[420px] overflow-visible">
            {slices.map((slice) => {
              const isHov = hoveredIndex === slice.idx;
              return (
                <path
                  key={slice.idx}
                  d={slice.pathD}
                  fill={slice.color}
                  stroke="#ffffff"
                  strokeWidth="2"
                  className="cursor-pointer transition-all duration-200 hover:opacity-90"
                  style={{
                    transformOrigin: `${cx}px ${cy}px`,
                    transform: isHov ? 'scale(1.04)' : 'scale(1)',
                  }}
                  onMouseEnter={() => setHoveredIndex(slice.idx)}
                  onMouseLeave={() => setHoveredIndex(null)}
                />
              );
            })}

            {isDonut && (
              <g className="pointer-events-none select-none">
                <text x={cx} y={cy - 4} textAnchor="middle" className="text-[11px] font-medium fill-slate-400">
                  {activeSlice ? activeSlice.label.slice(0, 10) : 'Total'}
                </text>
                <text x={cx} y={cy + 15} textAnchor="middle" className="text-[13px] font-bold font-mono fill-slate-800">
                  {activeSlice ? `${activeSlice.pct}%` : formatValue(stats.total)}
                </text>
              </g>
            )}
          </svg>
        </div>

        {/* Legenda Interativa Lateral */}
        <div className="w-full md:w-56 max-h-56 overflow-y-auto space-y-1.5 pr-2">
          {slices.map((slice) => {
            const isHov = hoveredIndex === slice.idx;
            return (
              <div
                key={slice.idx}
                onMouseEnter={() => setHoveredIndex(slice.idx)}
                onMouseLeave={() => setHoveredIndex(null)}
                className={cn(
                  'flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs transition-all cursor-pointer',
                  isHov ? 'bg-blue-50/80 shadow-2xs' : 'hover:bg-slate-50'
                )}
              >
                <div className="flex items-center gap-2 truncate">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: slice.color }}
                  />
                  <span className={cn('truncate font-medium text-[11px]', isHov ? 'text-blue-900 font-bold' : 'text-slate-700')}>
                    {slice.label}
                  </span>
                </div>
                <div className="text-right shrink-0 font-mono text-[11px]">
                  <span className="font-semibold text-slate-800">{slice.pct}%</span>
                  <span className="ml-1 text-[10px] text-slate-400">({formatValue(slice.val)})</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // 4. RENDERIZADOR SCATTER (DISPERSÃO E CORRELAÇÃO)
  const renderScatter = () => {
    const minX = stats.minX;
    const maxX = stats.maxX || 1;
    const rangeX = maxX - minX || 1;
    const minY = stats.min;
    const maxY = stats.max || 1;
    const rangeY = maxY - minY || 1;

    const points = sanitizedData.map((d, idx) => {
      const numX = d._numX ?? 0;
      const numY = d[y] ?? 0;
      const px = paddingX + ((numX - minX) / rangeX) * innerWidth;
      const py = paddingY + innerHeight - ((numY - minY) / rangeY) * innerHeight;
      return { px, py, xVal: numX, yVal: numY, label: d[x], idx };
    });

    return (
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="w-full h-full overflow-visible select-none"
      >
        {/* Linhas de Grade Verticais e Horizontais */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
          const lineY = paddingY + innerHeight * (1 - pct);
          const valY = minY + rangeY * pct;
          const lineX = paddingX + innerWidth * pct;
          const valX = minX + rangeX * pct;

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
                {formatValue(valY)}
              </text>

              <line
                x1={lineX}
                y1={paddingY}
                x2={lineX}
                y2={svgHeight - paddingY}
                stroke="#f1f5f9"
                strokeDasharray="3 3"
                strokeWidth="1"
              />
              <text
                x={lineX}
                y={svgHeight - 12}
                textAnchor="middle"
                className="text-[10px] font-mono fill-slate-400"
              >
                {formatValue(valX)}
              </text>
            </g>
          );
        })}

        {/* Pontos de Dispersão */}
        {points.map((p) => {
          const isHov = hoveredIndex === p.idx;
          return (
            <g
              key={p.idx}
              className="cursor-pointer"
              onMouseEnter={() => setHoveredIndex(p.idx)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <circle
                cx={p.px}
                cy={p.py}
                r={isHov ? 7 : 5}
                fill={isHov ? '#2563eb' : '#60a5fa'}
                stroke="#ffffff"
                strokeWidth="2"
                className="transition-all duration-150 shadow-xs"
              />

              {isHov && (
                <g>
                  <rect
                    x={p.px - 60}
                    y={p.py - 36}
                    width="120"
                    height="30"
                    rx="5"
                    fill="#0f172a"
                    className="shadow-lg"
                  />
                  <text
                    x={p.px}
                    y={p.py - 22}
                    textAnchor="middle"
                    className="text-[10px] font-semibold fill-slate-200"
                  >
                    {p.label.slice(0, 15)}
                  </text>
                  <text
                    x={p.px}
                    y={p.py - 10}
                    textAnchor="middle"
                    className="text-[9.5px] font-mono font-bold fill-blue-300"
                  >
                    X: {formatValue(p.xVal)} · Y: {formatValue(p.yVal)}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  const getHeaderIcon = () => {
    switch (currentType) {
      case 'line':
        return <LineChartIcon className="h-4 w-4" />;
      case 'area':
        return <TrendingUp className="h-4 w-4" />;
      case 'pie':
      case 'donut':
        return <PieChartIcon className="h-4 w-4" />;
      case 'scatter':
        return <ScatterChartIcon className="h-4 w-4" />;
      case 'bar':
      default:
        return <BarChart3 className="h-4 w-4" />;
    }
  };

  return (
    <div
      className={cn(
        'my-3.5 w-full overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xs transition-all',
        className
      )}
    >
      {/* Header do Card com Seletor Interativo de Tipo e Abas */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50/70 px-4 py-3 select-none">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600 shadow-2xs border border-blue-100/80">
            {getHeaderIcon()}
          </div>
          <div>
            <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
              <span>{title || `Visualização: ${x} vs ${y}`}</span>
              <span className="rounded-md bg-blue-100/70 px-1.5 py-0.5 text-[9.5px] font-mono font-semibold uppercase text-blue-800">
                {currentType}
              </span>
            </div>
            <div className="text-[11px] text-slate-500">
              {subtitle || `Total: ${formatValue(stats.total)} · Média: ${formatValue(stats.avg)}`}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Seletor Rápido de Tipo de Gráfico */}
          <div className="hidden sm:flex items-center gap-0.5 rounded-xl bg-slate-200/50 p-0.5 text-[10px]">
            <button
              type="button"
              title="Barras"
              onClick={() => setCurrentType('bar')}
              className={cn(
                'rounded-lg p-1 transition-all cursor-pointer',
                currentType === 'bar' ? 'bg-white text-blue-700 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
              )}
            >
              <BarChart3 className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              title="Linhas"
              onClick={() => setCurrentType('line')}
              className={cn(
                'rounded-lg p-1 transition-all cursor-pointer',
                currentType === 'line' ? 'bg-white text-blue-700 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
              )}
            >
              <LineChartIcon className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              title="Área"
              onClick={() => setCurrentType('area')}
              className={cn(
                'rounded-lg p-1 transition-all cursor-pointer',
                currentType === 'area' ? 'bg-white text-blue-700 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
              )}
            >
              <TrendingUp className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              title="Donut / Pizza"
              onClick={() => setCurrentType(currentType === 'donut' ? 'pie' : 'donut')}
              className={cn(
                'rounded-lg p-1 transition-all cursor-pointer',
                currentType === 'donut' || currentType === 'pie' ? 'bg-white text-blue-700 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
              )}
            >
              <PieChartIcon className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              title="Dispersão (Scatter)"
              onClick={() => setCurrentType('scatter')}
              className={cn(
                'rounded-lg p-1 transition-all cursor-pointer',
                currentType === 'scatter' ? 'bg-white text-blue-700 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
              )}
            >
              <ScatterChartIcon className="h-3.5 w-3.5" />
            </button>
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
              {getHeaderIcon()}
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
      </div>

      {/* Conteúdo: Gráfico Vetorial Interativo ou Tabela */}
      <div className="p-4" style={{ minHeight: chartHeight }}>
        {activeTab === 'chart' ? (
          <div className="h-full w-full flex items-center justify-center" style={{ height: chartHeight }}>
            {currentType === 'line' && renderLines(false)}
            {currentType === 'area' && renderLines(true)}
            {currentType === 'donut' && renderPie(true)}
            {currentType === 'pie' && renderPie(false)}
            {currentType === 'scatter' && renderScatter()}
            {currentType === 'bar' && renderBars()}
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

      {/* Footer com Metadados e Ações */}
      <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/50 px-4 py-2 text-[10px] text-slate-400 select-none font-mono">
        <span>Dimensão: {x} · Métrica: {y} · Amostra: {sanitizedData.length} pontos</span>
        <span className="font-semibold text-blue-600/80">Kraken Visuals · Multi-Chart SDK</span>
      </div>
    </div>
  );
}

export default GraphyChart;