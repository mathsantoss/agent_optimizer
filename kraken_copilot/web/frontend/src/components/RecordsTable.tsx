import React, { useMemo, useState } from 'react';
import {
  Hash,
  Type,
  Calendar,
  Table as TableIcon,
  Tag as TagIcon,
  Code2,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  Check,
  Copy,
  SlidersHorizontal,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ColumnDef {
  key: string;
  label?: string;
  type?: 'number' | 'string' | 'percent' | 'date' | 'boolean' | 'formula' | 'tag' | 'status';
}

export interface RecordsTableProps {
  columns: (string | ColumnDef)[];
  data: Record<string, any>[];
  title?: string;
  maxHeight?: string;
  className?: string;
  showFilters?: boolean;
}

// Paleta de cores vibrantes para tags no tema escuro (Records Table / Glide / Notion style)
const TAG_PALETTE: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  amber: {
    bg: 'bg-amber-950/70',
    text: 'text-amber-300',
    border: 'border-amber-800/60',
    dot: 'bg-amber-400',
  },
  purple: {
    bg: 'bg-purple-950/70',
    text: 'text-purple-300',
    border: 'border-purple-800/60',
    dot: 'bg-purple-400',
  },
  stone: {
    bg: 'bg-stone-800/80',
    text: 'text-stone-300',
    border: 'border-stone-700/60',
    dot: 'bg-stone-400',
  },
  rose: {
    bg: 'bg-rose-950/70',
    text: 'text-rose-300',
    border: 'border-rose-800/60',
    dot: 'bg-rose-400',
  },
  yellow: {
    bg: 'bg-yellow-950/70',
    text: 'text-yellow-300',
    border: 'border-yellow-800/60',
    dot: 'bg-yellow-400',
  },
  cyan: {
    bg: 'bg-cyan-950/70',
    text: 'text-cyan-300',
    border: 'border-cyan-800/60',
    dot: 'bg-cyan-400',
  },
  emerald: {
    bg: 'bg-emerald-950/70',
    text: 'text-emerald-300',
    border: 'border-emerald-800/60',
    dot: 'bg-emerald-400',
  },
  teal: {
    bg: 'bg-teal-950/70',
    text: 'text-teal-300',
    border: 'border-teal-800/60',
    dot: 'bg-teal-400',
  },
  blue: {
    bg: 'bg-blue-950/70',
    text: 'text-blue-300',
    border: 'border-blue-800/60',
    dot: 'bg-blue-400',
  },
};

const PALETTE_KEYS = Object.keys(TAG_PALETTE);

function getTagColor(text: string) {
  const lower = text.toLowerCase().trim();
  if (lower.includes('b2b') || lower.includes('todo') || lower.includes('to do') || lower.includes('pendent')) {
    return TAG_PALETTE.amber;
  }
  if (lower.includes('gelato') || lower.includes('cater') || lower.includes('agreg') || lower.includes('group')) {
    return TAG_PALETTE.purple;
  }
  if (lower.includes('wholesale') || lower.includes('import') || lower.includes('lote')) {
    return TAG_PALETTE.stone;
  }
  if (lower.includes('sorbet') || lower.includes('cafe') || lower.includes('erro') || lower.includes('outlier')) {
    return TAG_PALETTE.rose;
  }
  if (lower.includes('season') || lower.includes('tempor') || lower.includes('trimestr') || lower.includes('dia')) {
    return TAG_PALETTE.yellow;
  }
  if (lower.includes('dairy') || lower.includes('progress') || lower.includes('andamento') || lower.includes('execu')) {
    return TAG_PALETTE.cyan;
  }
  if (lower.includes('vegan') || lower.includes('b2c') || lower.includes('complet') || lower.includes('aprov') || lower.includes('sucess')) {
    return TAG_PALETTE.emerald;
  }
  if (lower.includes('local') || lower.includes('nacional') || lower.includes('regi')) {
    return TAG_PALETTE.teal;
  }
  if (lower.includes('financ') || lower.includes('receit') || lower.includes('inter')) {
    return TAG_PALETTE.blue;
  }

  // Hash determinístico para palavras não mapeadas
  let hash = 0;
  for (let i = 0; i < lower.length; i++) {
    hash = (hash << 5) - hash + lower.charCodeAt(i);
    hash |= 0;
  }
  const idx = Math.abs(hash) % PALETTE_KEYS.length;
  return TAG_PALETTE[PALETTE_KEYS[idx]];
}

// Limpa e normaliza timestamps ISO poluídos (ex: 1997-09-17 21:50:14+00:00 -> 17/09/1997 21:50)
function formatCleanDate(val: string): string {
  if (typeof val !== 'string') return String(val);
  const match = val.match(/^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})(?::\d{2})?(?:\+\d{2}:\d{2}|Z)?$/);
  if (match) {
    const [, year, month, day, hours, minutes] = match;
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  }
  return val;
}

// Verifica se uma string parece fórmula matemática ou expressão de código
function isFormulaExpression(val: string): boolean {
  if (typeof val !== 'string') return false;
  const trimmed = val.trim();
  if (trimmed.length < 3 || trimmed.length > 80) return false;
  return /[\*\+\-\/]|\.dt\.|\.apply|\.transform|groupby\(|lambda\b|mean\(\)|sum\(\)/i.test(trimmed);
}

export function RecordsTable({
  columns,
  data,
  title,
  maxHeight = '420px',
  className,
  showFilters = true,
}: RecordsTableProps) {
  const [copiedCell, setCopiedCell] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('ALL');
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className={cn('my-3 rounded-2xl border border-zinc-800 bg-[#16171a] p-6 text-center text-xs text-zinc-500 shadow-xl', className)}>
        Nenhum registro para exibir.
      </div>
    );
  }

  // Normaliza colunas e infere tipos enriquecidos
  const normalizedCols: ColumnDef[] = useMemo(() => {
    return columns.map((col) => {
      if (typeof col === 'string') {
        const lowerCol = col.toLowerCase();
        let colType: ColumnDef['type'] = 'string';

        // Análise de amostras para inferência
        const sampleVals = data.slice(0, 5).map((d) => d[col]).filter((v) => v !== null && v !== undefined);
        const hasFormulas = sampleVals.some((v) => isFormulaExpression(String(v)));
        const allNumbers = sampleVals.length > 0 && sampleVals.every((v) => typeof v === 'number' || (!isNaN(Number(v)) && !String(v).includes('-') && String(v).trim() !== ''));

        if (hasFormulas || lowerCol.includes('fórmula') || lowerCol.includes('formula') || lowerCol.includes('express')) {
          colType = 'formula';
        } else if (lowerCol.includes('status') || lowerCol.includes('estado')) {
          colType = 'status';
        } else if (lowerCol.includes('categor') || lowerCol.includes('tag') || lowerCol.includes('tipo')) {
          colType = 'tag';
        } else if (lowerCol.includes('data') || lowerCol.includes('time') || lowerCol.includes('created') || lowerCol.includes('updated')) {
          colType = 'date';
        } else if (lowerCol.includes('taxa') || lowerCol.includes('pct') || lowerCol.includes('%')) {
          colType = 'percent';
        } else if (allNumbers || lowerCol.includes('preco') || lowerCol.includes('price') || lowerCol.includes('quantidade') || lowerCol.includes('quantity') || lowerCol.includes('total')) {
          colType = 'number';
        }

        return { key: col, label: col, type: colType };
      }
      return col;
    });
  }, [columns, data]);

  // Identifica se há uma coluna categórica/status para gerar a Filter Table Bar (imagem 13 de referência)
  const filterColumn = useMemo(() => {
    const col = normalizedCols.find(
      (c) => c.type === 'status' || c.type === 'tag' || c.key.toLowerCase().includes('status') || c.key.toLowerCase().includes('categoria')
    );
    if (!col) return null;
    const values = data.map((d) => String(d[col.key] || '').trim()).filter(Boolean);
    const unique = Array.from(new Set(values));
    if (unique.length >= 2 && unique.length <= 8) {
      return { col, unique };
    }
    return null;
  }, [normalizedCols, data]);

  // Filtros de status/categoria
  const statusCounts = useMemo(() => {
    if (!filterColumn) return {};
    const counts: Record<string, number> = {};
    data.forEach((row) => {
      const val = String(row[filterColumn.col.key] || '').trim();
      if (val) counts[val] = (counts[val] || 0) + 1;
    });
    return counts;
  }, [filterColumn, data]);

  // Filtra dados com base em busca e status ativo
  const filteredData = useMemo(() => {
    let result = [...data];

    if (filterColumn && selectedStatusFilter !== 'ALL') {
      result = result.filter(
        (row) => String(row[filterColumn.col.key] || '').trim().toLowerCase() === selectedStatusFilter.toLowerCase()
      );
    }

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      result = result.filter((row) =>
        Object.values(row).some((val) => String(val ?? '').toLowerCase().includes(q))
      );
    }

    if (sortConfig) {
      result.sort((a, b) => {
        const valA = a[sortConfig.key];
        const valB = b[sortConfig.key];
        if (valA === valB) return 0;
        if (valA === null || valA === undefined) return 1;
        if (valB === null || valB === undefined) return -1;

        const numA = Number(valA);
        const numB = Number(valB);
        if (!isNaN(numA) && !isNaN(numB)) {
          return sortConfig.direction === 'asc' ? numA - numB : numB - numA;
        }

        const comp = String(valA).localeCompare(String(valB));
        return sortConfig.direction === 'asc' ? comp : -comp;
      });
    }

    return result;
  }, [data, filterColumn, selectedStatusFilter, searchTerm, sortConfig]);

  // Alterna ordenação
  const handleSort = (key: string) => {
    setSortConfig((prev) => {
      if (!prev || prev.key !== key) return { key, direction: 'asc' };
      if (prev.direction === 'asc') return { key, direction: 'desc' };
      return null;
    });
  };

  // Cópia rápida de valor de célula
  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCell(id);
    setTimeout(() => setCopiedCell(null), 1500);
  };

  // Ícone de cabeçalho por tipo de propriedade
  const renderHeaderIcon = (type?: ColumnDef['type']) => {
    switch (type) {
      case 'number':
      case 'percent':
        return <Hash className="h-3 w-3 text-zinc-500 shrink-0" />;
      case 'date':
        return <Calendar className="h-3 w-3 text-zinc-500 shrink-0" />;
      case 'tag':
      case 'status':
        return <TagIcon className="h-3 w-3 text-zinc-500 shrink-0" />;
      case 'formula':
        return <Code2 className="h-3 w-3 text-zinc-500 shrink-0" />;
      default:
        return <Type className="h-3 w-3 text-zinc-500 shrink-0" />;
    }
  };

  // Renderizador rico de cada célula
  const renderCellContent = (col: ColumnDef, val: any, rIdx: number, cIdx: number) => {
    if (val === null || val === undefined || val === '') {
      return <span className="text-zinc-600">—</span>;
    }

    const strVal = String(val);

    // 1. Primeira coluna: entidade ou métrica estatística
    if (cIdx === 0 && strVal.length > 0) {
      const lower = strVal.toLowerCase().trim();
      const isStatMetric = /^(count|mean|std|min|max|\d{1,2}%|nulos|outliers|unique|top|freq|iqr|assimetria)/i.test(lower);

      if (isStatMetric) {
        return (
          <span className="inline-flex items-center rounded-md bg-zinc-800/80 px-2 py-0.5 font-mono text-[11px] font-semibold text-purple-300 border border-zinc-700/60 shadow-2xs">
            {strVal}
          </span>
        );
      }

      if (!isFormulaExpression(strVal)) {
        const initial = strVal.trim().charAt(0).toUpperCase();
        return (
          <div className="flex items-center gap-2.5">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-zinc-800 text-[10px] font-bold text-zinc-300 border border-zinc-700/60 shadow-2xs select-none">
              {initial}
            </span>
            <span className="font-medium text-zinc-100 truncate max-w-[240px]" title={strVal}>
              {strVal}
            </span>
          </div>
        );
      }
    }

    // 2. Coluna de Tags ou Categorias
    if (col.type === 'tag' || (typeof strVal === 'string' && (col.key.toLowerCase().includes('tag') || col.key.toLowerCase().includes('categor')))) {
      // Suporta múltiplas tags separadas por vírgula
      const tags = strVal.split(',').map((t) => t.trim()).filter(Boolean);
      return (
        <div className="flex flex-wrap gap-1.5 py-0.5">
          {tags.map((t, idx) => {
            const palette = getTagColor(t);
            return (
              <span
                key={idx}
                className={cn(
                  'inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium border shadow-2xs',
                  palette.bg,
                  palette.text,
                  palette.border
                )}
              >
                {t}
              </span>
            );
          })}
        </div>
      );
    }

    // 3. Status Chip (ex: "To do", "In Progress", "Completed", "Aprovada")
    if (col.type === 'status' || col.key.toLowerCase().includes('status')) {
      const palette = getTagColor(strVal);
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold border shadow-2xs',
            palette.bg,
            palette.text,
            palette.border
          )}
        >
          <span className={cn('h-1.5 w-1.5 rounded-full', palette.dot)} />
          {strVal}
        </span>
      );
    }

    // 4. Expressão / Fórmula de Feature Engineering
    if (col.type === 'formula' || isFormulaExpression(strVal)) {
      return (
        <span className="inline-block rounded-md bg-zinc-800/90 px-2 py-0.5 font-mono text-[11px] text-cyan-300 border border-zinc-700/60 shadow-2xs">
          {strVal}
        </span>
      );
    }

    // 5. Data / Timestamp
    if (col.type === 'date' || /^\d{4}-\d{2}-\d{2}/.test(strVal)) {
      return (
        <span className="font-mono text-[11.5px] text-zinc-300">
          {formatCleanDate(strVal)}
        </span>
      );
    }

    // 6. UUID / Hash Longo (ex: 442bc2f0-22d3-3c8a-9f71-0f9c16cee0b2)
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(strVal);
    if (isUuid) {
      const shortUuid = `${strVal.substring(0, 8)}...${strVal.substring(strVal.length - 4)}`;
      const cellId = `cell-${rIdx}-${cIdx}`;
      return (
        <button
          onClick={() => handleCopy(strVal, cellId)}
          title="Clique para copiar UUID"
          className="group inline-flex items-center gap-1 font-mono text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <span>{shortUuid}</span>
          {copiedCell === cellId ? (
            <Check className="h-3 w-3 text-emerald-400" />
          ) : (
            <Copy className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
          )}
        </button>
      );
    }

    // 7. Número Float
    const num = Number(strVal);
    if (!isNaN(num) && typeof val === 'number') {
      const formatted = Number.isInteger(num)
        ? num.toLocaleString()
        : num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 3 });
      return <span className="font-mono text-zinc-200">{formatted}</span>;
    }

    // Padrão de texto
    return <span className="text-zinc-300">{strVal}</span>;
  };

  return (
    <div
      className={cn(
        'my-3.5 flex flex-col overflow-hidden rounded-2xl border border-zinc-800/90 bg-[#16171a] text-zinc-200 shadow-2xl transition-all',
        className
      )}
    >
      {/* Top Header / Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-zinc-800/80 bg-zinc-900/60 px-4 py-2.5 text-xs">
        <div className="flex items-center gap-2">
          <TableIcon className="h-4 w-4 text-purple-400" />
          <span className="font-semibold text-zinc-100">{title || 'Records Table'}</span>
          <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-mono text-zinc-400">
            {filteredData.length} {filteredData.length === 1 ? 'linha' : 'linhas'}
          </span>
        </div>

        {/* Busca e Ações Rápidas */}
        {data.length > 4 && (
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                placeholder="Filtrar dados..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-7 w-36 sm:w-48 rounded-lg border border-zinc-700/70 bg-zinc-800/70 pl-8 pr-2 text-[11px] text-zinc-200 placeholder:text-zinc-500 focus:border-purple-500 focus:outline-none transition-colors"
              />
            </div>
          </div>
        )}
      </div>

      {/* Filter Table Bar (Imagem 13: Status chips that reorganize live data) */}
      {showFilters && filterColumn && (
        <div className="flex flex-wrap items-center gap-1.5 border-b border-zinc-800/60 bg-zinc-900/40 px-4 py-2">
          <button
            onClick={() => setSelectedStatusFilter('ALL')}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold transition-all cursor-pointer',
              selectedStatusFilter === 'ALL'
                ? 'bg-zinc-800 text-zinc-100 border border-zinc-700 shadow-2xs'
                : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
            )}
          >
            <span>All</span>
            <span className="rounded-full bg-zinc-700/60 px-1.5 py-0.2 text-[10px] text-zinc-300">
              {data.length}
            </span>
          </button>

          {filterColumn.unique.map((statusVal) => {
            const isSelected = selectedStatusFilter.toLowerCase() === statusVal.toLowerCase();
            const palette = getTagColor(statusVal);
            const count = statusCounts[statusVal] || 0;

            return (
              <button
                key={statusVal}
                onClick={() => setSelectedStatusFilter(isSelected ? 'ALL' : statusVal)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium transition-all cursor-pointer border',
                  isSelected
                    ? cn(palette.bg, palette.text, palette.border, 'shadow-2xs font-semibold')
                    : 'border-transparent text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
                )}
              >
                <span className={cn('h-1.5 w-1.5 rounded-full', palette.dot)} />
                <span>{statusVal}</span>
                <span className="text-[10px] opacity-70">({count})</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Grid Table Container */}
      <div className="overflow-x-auto overflow-y-auto" style={{ maxHeight }}>
        <table className="w-full border-collapse text-left text-xs">
          <thead className="sticky top-0 z-10 select-none bg-zinc-900/95 backdrop-blur-md">
            <tr className="border-b border-zinc-800 text-zinc-400">
              {/* Coluna de Numeração de Linha */}
              <th className="w-10 px-3 py-2.5 text-center font-mono text-[11px] text-zinc-500 font-normal">
                #
              </th>

              {normalizedCols.map((c) => {
                const isSorted = sortConfig?.key === c.key;
                return (
                  <th
                    key={c.key}
                    onClick={() => handleSort(c.key)}
                    className="group px-3 py-2.5 font-medium whitespace-nowrap cursor-pointer hover:bg-zinc-800/50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      {renderHeaderIcon(c.type)}
                      <span className="text-zinc-300 group-hover:text-zinc-100 transition-colors">
                        {c.label || c.key}
                      </span>
                      <span className="text-zinc-600 group-hover:text-zinc-400">
                        {isSorted ? (
                          sortConfig?.direction === 'asc' ? (
                            <ArrowUp className="h-3 w-3 text-purple-400" />
                          ) : (
                            <ArrowDown className="h-3 w-3 text-purple-400" />
                          )
                        ) : (
                          <ArrowUpDown className="h-2.5 w-2.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        )}
                      </span>
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>

          <tbody className="divide-y divide-zinc-800/70 font-sans text-xs">
            {filteredData.map((row, rIdx) => (
              <tr
                key={rIdx}
                className="hover:bg-zinc-800/40 transition-colors group"
              >
                {/* Linha Numérica (1, 2, 3...) */}
                <td className="px-3 py-2 text-center font-mono text-[11px] text-zinc-500 select-none group-hover:text-zinc-400">
                  {rIdx + 1}
                </td>

                {normalizedCols.map((col, cIdx) => (
                  <td
                    key={col.key}
                    className="px-3 py-2 whitespace-nowrap align-middle"
                  >
                    {renderCellContent(col, row[col.key], rIdx, cIdx)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer Row: contagem limpa de registros */}
      <div className="flex items-center justify-between border-t border-zinc-800/80 bg-zinc-900/70 px-4 py-2 text-xs text-zinc-400 select-none">
        <div className="flex items-center gap-3 font-mono text-[11px]">
          <span className="text-zinc-300 font-semibold">
            {filteredData.length} {filteredData.length === 1 ? 'registro' : 'registros'}
          </span>
          {searchTerm && (
            <span className="text-zinc-500 text-[10px]">
              (filtrado de {data.length})
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default RecordsTable;
