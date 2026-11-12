import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  ScatterChart as ScatterChartIcon,
  Table as TableIcon,
  TrendingUp,
  Maximize2,
  Minimize2,
  Sun,
  Moon,
  CheckCircle2,
} from 'lucide-react';
import {
  GraphProvider,
  GraphRenderer,
  createSpec,
  pipe,
  geom,
  scale,
  coord,
  config,
} from '@graphysdk/react';
import type { Data } from '@graphysdk/react';
import { shiny } from '@graphysdk/theme-shiny';
import { botanical } from '@graphysdk/theme-botanical';
import { neoBrutalist } from '@graphysdk/theme-neo-brutalist';
import { spreadsheet } from '@graphysdk/theme-spreadsheet';
import { cn } from '@/lib/utils';

export type ChartType = 'bar' | 'line' | 'area' | 'pie' | 'donut' | 'scatter';
export type ColorSchemeType = 'light' | 'dark';
export type ThemeChoice = 'default' | 'shiny' | 'botanical' | 'neoBrutalist' | 'spreadsheet';

export interface GraphyChartProps {
  type?: ChartType;
  title?: string;
  subtitle?: string;
  data: Array<Record<string, any>>;
  x: string;
  y: string;
  className?: string;
  height?: number;
  sizing?: {
    mode?: 'responsive' | 'fixed';
    width?: number;
    height?: number;
  };
}

// Mapeamento dos temas oficiais do Graphy SDK
const THEMES: Record<ThemeChoice, { label: string; theme: any }> = {
  default: { label: 'Default', theme: undefined },
  shiny: { label: 'Shiny Glow', theme: shiny },
  botanical: { label: 'Botanical', theme: botanical },
  neoBrutalist: { label: 'Neo Brutalist', theme: neoBrutalist },
  spreadsheet: { label: 'Spreadsheet', theme: spreadsheet },
};

// Formatação compacta de números para títulos e resumos estatísticos
export function formatCompactNumber(val: number): string {
  const abs = Math.abs(val);
  if (abs >= 1_000_000_000) {
    return `R$ ${(val / 1_000_000_000).toFixed(2).replace(/\.00$/, '')}B`;
  }
  if (abs >= 1_000_000) {
    return `R$ ${(val / 1_000_000).toFixed(2).replace(/\.00$/, '')}M`;
  }
  if (abs >= 1_000) {
    return `R$ ${(val / 1_000).toFixed(1).replace(/\.0$/, '')}k`;
  }
  return `R$ ${val.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

export function GraphyChart({
  type: initialType = 'bar',
  title,
  subtitle,
  data = [],
  x,
  y,
  className,
  height = 380,
}: GraphyChartProps) {
  const [activeTab, setActiveTab] = useState<'chart' | 'data'>('chart');
  const [currentType, setCurrentType] = useState<ChartType>(initialType);
  const [isExpanded, setIsExpanded] = useState(false);
  // Padrão light e tema simples (sem tema extra) conforme preferência visual
  const [colorScheme, setColorScheme] = useState<ColorSchemeType>('light');
  const [selectedTheme, setSelectedTheme] = useState<ThemeChoice>('default');

  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState<number>(0);

  // Medição reativa e contínua da largura do container para renderização imediata do Graphy
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;

    const measure = () => {
      const rect = el.getBoundingClientRect();
      const w = Math.floor(rect.width);
      if (w > 0) {
        setContainerWidth(w);
      }
    };

    measure();

    const ro = new ResizeObserver(() => {
      measure();
    });
    ro.observe(el);

    // Timeout de segurança para layout assíncrono do navegador
    const timer = setTimeout(measure, 100);

    return () => {
      clearTimeout(timer);
      ro.disconnect();
    };
  }, [isExpanded, activeTab]);

  // Fecha tela cheia com tecla ESC
  useEffect(() => {
    if (!isExpanded) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsExpanded(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isExpanded]);

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

  // Estatísticas descritivas básicas para o resumo
  const stats = useMemo(() => {
    if (sanitizedData.length === 0) {
      return { max: 1, min: 0, avg: 0, total: 0, count: 0 };
    }
    const valuesY = sanitizedData.map((d) => d[y]);
    const count = valuesY.length;
    const total = valuesY.reduce((acc, val) => acc + val, 0);
    const max = Math.max(...valuesY, 0);
    const min = Math.min(...valuesY);
    const avg = total / (count || 1);
    return { max, min, avg, total, count };
  }, [sanitizedData, y]);

  // Estrutura de dados exigida pelo Graphy SDK (colunas e linhas)
  const graphyData: Data = useMemo(() => {
    return {
      columns: [
        { key: x, label: x },
        { key: y, label: y },
      ],
      rows: sanitizedData.map((d) => ({
        [x]: d[x],
        [y]: d[y],
      })),
    };
  }, [sanitizedData, x, y]);

  // Geração do Spec declarativo do Graphy SDK conforme o tipo selecionado
  const graphySpec = useMemo(() => {
    try {
      const baseMapping = createSpec({ x, y });
      let specWithGeom: any = baseMapping;

      if (currentType === 'bar') {
        specWithGeom = pipe(
          baseMapping,
          geom.bar(),
          scale.x({ nice: true }),
          scale.y({ nice: true })
        );
      } else if (currentType === 'line') {
        specWithGeom = pipe(
          baseMapping,
          geom.line(),
          scale.x({ nice: true }),
          scale.y({ nice: true })
        );
      } else if (currentType === 'area') {
        specWithGeom = pipe(
          baseMapping,
          geom.area(),
          scale.x({ nice: true }),
          scale.y({ nice: true })
        );
      } else if (currentType === 'scatter') {
        specWithGeom = pipe(
          baseMapping,
          geom.point(),
          scale.x({ nice: true }),
          scale.y({ nice: true })
        );
      } else if (currentType === 'pie') {
        specWithGeom = pipe(
          createSpec({ x: '', y, color: x }),
          geom.bar({
            position: 'fill',
            dataLabels: { showDataLabels: true },
          }),
          coord.polar({ theta: 'y' }),
          scale.x(),
          scale.y(),
          scale.color.discrete(),
          config({
            legend: { position: 'right' },
          })
        );
      } else if (currentType === 'donut') {
        specWithGeom = pipe(
          createSpec({ x: '', y, color: x }),
          geom.bar({
            position: 'fill',
            dataLabels: { showDataLabels: true },
          }),
          coord.polar({ theta: 'y', innerRadius: 0.55 }),
          scale.x(),
          scale.y(),
          scale.color.discrete(),
          config({
            legend: { position: 'right' },
            headline: { show: 'total', position: 'center' },
          })
        );
      }

      return pipe(
        specWithGeom,
        config({
          content: {
            graphyBadge: { visible: false },
          },
        })
      );
    } catch (err) {
      console.error('Erro gerando spec do Graphy:', err);
      return null;
    }
  }, [x, y, currentType]);

  if (!sanitizedData || sanitizedData.length === 0 || !x || !y) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center text-xs text-slate-500">
        Nenhum dado numérico válido para renderizar gráfico.
      </div>
    );
  }

  const isDark = colorScheme === 'dark';
  const chartHeightPx = isExpanded ? 640 : Math.max(height, 380);
  const activeGraphyTheme = THEMES[selectedTheme]?.theme;

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

  const chartCard = (
    <div
      className={cn(
        'my-3 w-full overflow-hidden rounded-2xl border transition-all shadow-xs',
        isDark
          ? 'bg-slate-900 border-slate-800 text-slate-100'
          : 'bg-white border-slate-200 text-slate-800',
        isExpanded ? 'h-full flex flex-col my-0 border-0 shadow-none' : '',
        className
      )}
    >
      {/* Header do Card: Título + Botão Expandir alinhados no topo; Controles abaixo */}
      <div
        className={cn(
          'flex flex-col gap-2.5 border-b px-4 py-3 select-none',
          isDark ? 'bg-slate-950/70 border-slate-800' : 'bg-slate-50 border-slate-100'
        )}
      >
            <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div
                className={cn(
                  'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border shadow-2xs',
                  isDark
                    ? 'bg-slate-800 border-slate-700 text-cyan-400'
                    : 'bg-blue-50 border-blue-100 text-blue-600'
                )}
              >
                {getHeaderIcon()}
              </div>
              <div className="min-w-0">
                <div className="text-xs font-bold flex items-center gap-2 flex-wrap">
                  <span className={cn('truncate', isDark ? 'text-white' : 'text-slate-900')}>
                    {title || `${x} vs ${y}`}
                  </span>
                  <span
                    className={cn(
                      'rounded-md px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase shrink-0',
                      isDark ? 'bg-slate-800 text-cyan-300' : 'bg-blue-100 text-blue-800'
                    )}
                  >
                    {currentType}
                  </span>
                </div>
                <div className={cn('text-[11px] truncate', isDark ? 'text-slate-400' : 'text-slate-500')}>
                  {subtitle || `Total: ${formatCompactNumber(stats.total)} · Média: ${formatCompactNumber(stats.avg)}`}
                </div>
              </div>
            </div>

            {/* Botão de Expandir alinhado ao título no final da div */}
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              title={isExpanded ? 'Restaurar tamanho (ESC)' : 'Expandir gráfico em tela cheia'}
              className={cn(
                'shrink-0 rounded-xl border p-1.5 transition-colors cursor-pointer shadow-2xs',
                isDark
                    ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              )}
            >
          {isExpanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
        </button>
      </div>

        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-1.5">
            {/* Seletor de Temas Oficiais do Graphy SDK */}
            <select
              value={selectedTheme}
              onChange={(e) => setSelectedTheme(e.target.value as ThemeChoice)}
              className={cn(
                'rounded-xl border px-2.5 py-1 text-[11px] font-medium transition-colors cursor-pointer shadow-2xs focus:outline-hidden',
                isDark
                  ? 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
                  : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
              )}
              title="Escolher Tema oficial do Graphy SDK"
            >
              {Object.entries(THEMES).map(([key, item]) => (
                <option key={key} value={key} className={isDark ? 'bg-slate-900 text-slate-100' : 'bg-white text-slate-800'}>
                  {item.label}
                </option>
              ))}
            </select>

            {/* Alternador de Modo Claro e Escuro (ColorScheme) */}
            <button
              type="button"
              onClick={() => setColorScheme(colorScheme === 'light' ? 'dark' : 'light')}
              title={colorScheme === 'light' ? 'Alternar para Modo Escuro (Dark)' : 'Alternar para Modo Claro (Light)'}
              className={cn(
                'flex items-center gap-1.5 rounded-xl border px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer shadow-2xs',
                isDark
                  ? 'bg-slate-800 border-slate-700 text-yellow-400 hover:bg-slate-700'
                  : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-100'
              )}
            >
              { colorScheme === 'light' ? (
                  <>
                    <Moon className="h-3.5 w-3.5 text-slate-600" />
                    <span className="text-[11px] font-sans">Dark</span>
                  </>
                ) : (
                  <>
                    <Sun className="h-3.5 w-3.5 text-yellow-400" />
                    <span className="text-[11px] font-sans text-slate-200">Light</span>
                  </>
                )}
            </button>
          </div>

          <div className="flex items-center flex-wrap gap-2">
              {/* Seletor Rápido de Tipo de Gráfico */}
              <div
                className={cn(
                'hidden sm:flex items-center gap-0.5 rounded-xl p-0.5 border text-[10px]',
                  isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-200/50 border-slate-200'
                )}
              >
                {(
                  [
                    { id: 'bar', title: 'Barras (Bar)', icon: BarChart3, active: currentType === 'bar' },
                    { id: 'line', title: 'Linhas (Line)', icon: LineChartIcon, active: currentType === 'line' },
                    { id: 'area', title: 'Área (Area)', icon: TrendingUp, active: currentType === 'area' },
                    {
                      id: 'donut',
                      title: 'Donut / Pizza',
                      icon: PieChartIcon,
                      active: currentType === 'donut' || currentType === 'pie',
                      onClick: () => setCurrentType(currentType === 'donut' ? 'pie' : 'donut'),
                    },
                    { id: 'scatter', title: 'Dispersão (Scatter)', icon: ScatterChartIcon, active: currentType === 'scatter' },
                  ] as const
                ).map((btn) => {
                  const Icon = btn.icon;
                  return (
                    <button
                      key={btn.id}
                      type="button"
                      title={btn.title}
                      onClick={'onClick' in btn ? btn.onClick : () => setCurrentType(btn.id)}
                      className={cn(
                        'rounded-lg p-1.5 transition-all cursor-pointer',
                        btn.active
                          ? isDark
                            ? 'bg-slate-700 text-cyan-300 font-bold shadow-xs'
                            : 'bg-white text-blue-700 shadow-2xs font-bold'
                          : isDark
                            ? 'text-slate-400 hover:text-slate-200'
                            : 'text-slate-500 hover:text-slate-800'
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                    </button>
                  );
                })}
            </div>

            {/* Alternador Gráfico vs Dados */}
            <div
              className={cn(
                'flex items-center gap-1 rounded-xl p-0.5 border text-[11px] font-semibold',
                isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-200/60 border-slate-200'
              )}
            >
            <button
              type="button"
              onClick={() => setActiveTab('chart')}
              className={cn(
                'flex items-center gap-1.5 rounded-lg px-2.5 py-1 transition-all cursor-pointer',
                activeTab === 'chart'
                  ? isDark
                    ? 'bg-slate-700 text-cyan-300 shadow-xs'
                    : 'bg-white text-blue-700 shadow-2xs'
                  : isDark
                    ? 'text-slate-400 hover:text-white'
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
                  ? isDark
                    ? 'bg-slate-700 text-cyan-300 shadow-xs'
                    : 'bg-white text-blue-700 shadow-2xs'
                  : isDark
                    ? 'text-slate-400 hover:text-white'
                    : 'text-slate-600 hover:text-slate-900'
              )}
            >
              <TableIcon className="h-3 w-3" />
              <span>Dados ({sanitizedData.length})</span>
            </button>
          </div>
        </div>
      </div>
    </div>

      {/* Área do Gráfico: Renderizado Exclusivamente pelo Graphy SDK */ }
  <div
    className={cn(
      'p-3 sm:p-5 w-full flex-1 flex flex-col justify-center items-center',
      isExpanded ? 'min-h-[calc(90vh-140px)]' : ''
    )}
  >
    {activeTab === 'chart' ? (
      sanitizedData.length > 0 && sanitizedData.every((d) => d[y] === 0) ? (
        <div className="flex flex-col items-center justify-center p-8 text-center" style={{ height: chartHeightPx }}>
          <div
            className={cn(
              'flex h-12 w-12 items-center justify-center rounded-2xl border mb-3 shadow-2xs',
              isDark
                ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
                : 'bg-emerald-50 border-emerald-200 text-emerald-600'
            )}
          >
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <span className={cn('text-sm font-bold', isDark ? 'text-white' : 'text-slate-900')}>
            Nenhum registro diferente de zero identificado
          </span>
          <p className={cn('mt-1 max-w-md text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>
            Todos os {sanitizedData.length} registros avaliados na dimensão{' '}
            <span className="font-semibold font-mono">"{x}"</span> apresentam métrica{' '}
            <span className="font-semibold font-mono">"{y} = 0"</span>.
          </p>
          <button
            type="button"
            onClick={() => setActiveTab('data')}
            className={cn(
              'mt-4 inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold shadow-2xs cursor-pointer',
              isDark
                ? 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
            )}
          >
            <TableIcon className="h-3.5 w-3.5" />
            <span>Inspecionar Valores na Tabela</span>
          </button>
        </div>
      ) : graphySpec ? (
        /* Container com medição de largura e altura para pintura imediata pelo Graphy SDK */
        <div
          ref={containerRef}
          className="w-full relative flex-1 flex flex-col overflow-hidden"
          style={{
            width: '100%',
            height: isExpanded ? 'calc(90vh - 150px)' : `${chartHeightPx}px`,
            minHeight: isExpanded ? '450px' : `${chartHeightPx}px`,
          }}
        >
          <GraphProvider
            key={`${currentType}-${colorScheme}-${selectedTheme}-${isExpanded}`}
            data={graphyData}
            spec={graphySpec}
            colorScheme={colorScheme}
            theme={activeGraphyTheme}
            telemetry={false}
          >
            <GraphRenderer
              sizing={
                containerWidth > 0
                  ? { mode: 'fixed', width: containerWidth, height: isExpanded ? Math.max(window.innerHeight * 0.72, 450) : chartHeightPx }
                  : { mode: 'responsive' }
              }
            />
          </GraphProvider>
        </div>
      ) : (
        <div className="flex h-64 items-center justify-center text-xs text-slate-400">
          Não foi possível gerar a especificação do gráfico.
        </div>
      )
    ) : (
      <div
        className={cn(
          'overflow-auto rounded-xl border font-mono text-[11px] w-full',
          isDark ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-slate-50/50',
          isExpanded ? 'max-h-[calc(85vh-120px)]' : 'max-h-80'
        )}
      >
        <table className="w-full text-left">
          <thead
            className={cn(
              'sticky top-0 border-b',
              isDark ? 'bg-slate-900 border-slate-800 text-slate-300' : 'bg-slate-100 border-slate-200 text-slate-700'
            )}
          >
            <tr>
              <th className="px-4 py-2.5 font-semibold">#</th>
              <th className="px-4 py-2.5 font-semibold">{x}</th>
              <th className="px-4 py-2.5 font-semibold text-right">{y}</th>
            </tr>
          </thead>
          <tbody className={cn('divide-y', isDark ? 'divide-slate-800/80' : 'divide-slate-100')}>
            {sanitizedData.map((row, i) => (
              <tr
                key={i}
                className={cn(
                  'transition-colors',
                  isDark ? 'hover:bg-slate-800/50' : 'hover:bg-blue-50/40'
                )}
              >
                <td className={cn('px-4 py-2 text-[10px]', isDark ? 'text-slate-500' : 'text-slate-400')}>
                  {i + 1}
                </td>
                <td className={cn('px-4 py-2 font-medium', isDark ? 'text-slate-200' : 'text-slate-800')}>
                  {row[x]}
                </td>
                <td
                  className={cn(
                    'px-4 py-2 text-right font-semibold',
                    isDark ? 'text-cyan-400' : 'text-blue-700'
                  )}
                >
                  {formatCompactNumber(row[y])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </div>

  {/* Footer com Metadados Analíticos (sem menção desnecessária de marca no rodapé) */ }
  <div
    className={cn(
      'flex flex-wrap items-center justify-between border-t px-4 py-2 text-[11px] select-none font-mono',
      isDark ? 'bg-slate-950/70 border-slate-800 text-slate-400' : 'bg-slate-50 border-slate-100 text-slate-500'
    )}
  >
    <div className="flex items-center gap-3 flex-wrap">
      <span>Dimensão: <strong className={isDark ? 'text-slate-200' : 'text-slate-700'}>{x}</strong></span>
      <span>·</span>
      <span>Métrica: <strong className={isDark ? 'text-slate-200' : 'text-slate-700'}>{y}</strong></span>
      <span>·</span>
      <span>Amostra: <strong className={isDark ? 'text-slate-200' : 'text-slate-700'}>{sanitizedData.length} pontos</strong></span>
    </div>
  </div>
    </div >
  );

  // Modal Expandido em Tela Cheia
  if (isExpanded) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-2 sm:p-4 md:p-6 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={() => setIsExpanded(false)}
      >
        <div
          className={cn(
            'w-[96vw] max-w-7xl h-[92vh] flex flex-col rounded-2xl overflow-hidden shadow-2xl border transition-all',
            isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {chartCard}
        </div>
      </div>
    );
  }

  return chartCard;
}

export default GraphyChart;
