import React from 'react';
import { Hash, Type, Percent, Calendar, Table as TableIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ColumnDef {
  key: string;
  label?: string;
  type?: 'number' | 'string' | 'percent' | 'date' | 'boolean';
}

export interface RecordsTableProps {
  columns: (string | ColumnDef)[];
  data: Record<string, any>[];
  title?: string;
  maxHeight?: string;
  className?: string;
}

export function RecordsTable({
  columns,
  data,
  title,
  maxHeight = '380px',
  className,
}: RecordsTableProps) {
  if (!data || data.length === 0) {
    return (
      <div className={cn('rounded-xl border border-slate-200 bg-white p-6 text-center text-xs text-slate-500', className)}>
        Nenhum registro para exibir.
      </div>
    );
  }

  // Normaliza colunas
  const normalizedCols: ColumnDef[] = columns.map((col) => {
    if (typeof col === 'string') {
      const sampleVal = data[0]?.[col];
      let colType: ColumnDef['type'] = 'string';
      if (typeof sampleVal === 'number') colType = 'number';
      if (typeof sampleVal === 'boolean') colType = 'boolean';
      if (col.toLowerCase().includes('taxa') || col.toLowerCase().includes('pct')) colType = 'percent';
      if (col.toLowerCase().includes('data') || col.toLowerCase().includes('time')) colType = 'date';
      return { key: col, label: col, type: colType };
    }
    return col;
  });

  const getTypeBadge = (type?: ColumnDef['type']) => {
    switch (type) {
      case 'number':
        return (
          <span className="flex items-center gap-0.5 rounded bg-blue-50 px-1 py-0.2 text-[9px] font-mono font-semibold text-blue-600">
            <Hash className="h-2.5 w-2.5" /> NUM
          </span>
        );
      case 'percent':
        return (
          <span className="flex items-center gap-0.5 rounded bg-emerald-50 px-1 py-0.2 text-[9px] font-mono font-semibold text-emerald-600">
            <Percent className="h-2.5 w-2.5" /> PCT
          </span>
        );
      case 'date':
        return (
          <span className="flex items-center gap-0.5 rounded bg-amber-50 px-1 py-0.2 text-[9px] font-mono font-semibold text-amber-600">
            <Calendar className="h-2.5 w-2.5" /> DATA
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-0.5 rounded bg-slate-100 px-1 py-0.2 text-[9px] font-mono font-semibold text-slate-500">
            <Type className="h-2.5 w-2.5" /> STR
          </span>
        );
    }
  };

  return (
    <div className={cn('my-3 overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-xs', className)}>
      {title && (
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/70 px-4 py-2 text-xs font-semibold text-slate-700">
          <span className="flex items-center gap-1.5">
            <TableIcon className="h-4 w-4 text-slate-500" />
            {title}
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            {data.length} {data.length === 1 ? 'linha' : 'linhas'}
          </span>
        </div>
      )}

      <div className="overflow-x-auto overflow-y-auto" style={{ maxHeight }}>
        <table className="w-full border-collapse text-left text-xs">
          <thead className="sticky top-0 bg-slate-100/90 backdrop-blur-xs z-10 select-none">
            <tr className="border-b border-slate-200">
              <th className="w-10 px-3 py-2 text-center text-[10px] font-mono text-slate-400">#</th>
              {normalizedCols.map((c) => (
                <th key={c.key} className="px-3 py-2 text-[11px] font-semibold text-slate-700 whitespace-nowrap">
                  <div className="flex items-center gap-1.5">
                    <span>{c.label || c.key}</span>
                    {getTypeBadge(c.type)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
            {data.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-blue-50/40 transition-colors">
                <td className="px-3 py-1.5 text-center text-[10px] text-slate-400 select-none">
                  {rIdx + 1}
                </td>
                {normalizedCols.map((c) => {
                  const val = row[c.key];
                  const display = val === null || val === undefined ? '—' : String(val);
                  return (
                    <td key={c.key} className="px-3 py-1.5 text-slate-700 whitespace-nowrap">
                      {display}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default RecordsTable;

