import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Code2,
  Database,
  FileCode,
  Gauge,
  Play,
  Check,
  AlertCircle,
  FileDiff,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { CodeBlock } from './CodeBlock';

export interface DiffRowData {
  tipo: 'add' | 'del' | 'ctx' | 'hunk';
  texto: string;
}

export interface DiffInfo {
  arquivo: string;
  caminho?: string;
  adicoes: number;
  remocoes: number;
  linhas: DiffRowData[];
  raw_diff?: string;
  original_code?: string;
  proposed_code?: string;
}

export interface ToolCallItem {
  id?: string;
  ferramenta: string;
  argumentos?: Record<string, any>;
  resultado?: any;
  status?: 'sucesso' | 'executando' | 'erro';
  diff_info?: DiffInfo;
  codigo_proposto?: string;
}

export interface ToolChipsProps {
  tools: ToolCallItem[];
  className?: string;
}

export function ToolChips({ tools, className }: ToolChipsProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (!tools || tools.length === 0) return null;

  const getToolIcon = (name: string) => {
    if (name.includes('optimize') || name.includes('feature')) {
      return <Code2 className="h-3.5 w-3.5 text-blue-500" />;
    }
    if (name.includes('benchmark') || name.includes('profile')) {
      return <Gauge className="h-3.5 w-3.5 text-amber-500" />;
    }
    if (name.includes('sql') || name.includes('dataset') || name.includes('dado')) {
      return <Database className="h-3.5 w-3.5 text-purple-500" />;
    }
    return <Play className="h-3.5 w-3.5 text-slate-500" />;
  };

  const toggleExpand = (idx: number) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  return (
    <div className={cn('my-2.5 flex flex-col gap-1.5', className)}>
      <div className="flex items-center gap-1.5 text-[11px] font-medium text-slate-500">
        <span>Ferramentas Executadas ({tools.length})</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {tools.map((tool, idx) => {
          const isExpanded = expandedIndex === idx;
          const hasDiff = Boolean(tool.diff_info || tool.codigo_proposto);

          return (
            <div key={idx} className="flex flex-col">
              <button
                type="button"
                onClick={() => toggleExpand(idx)}
                className={cn(
                  'inline-flex items-center gap-2 rounded-lg border px-2.5 py-1 text-xs font-medium transition-all select-none',
                  isExpanded
                    ? 'border-blue-300 bg-blue-50/70 text-blue-900 shadow-2xs'
                    : 'border-slate-200/90 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50 shadow-2xs'
                )}
              >
                {getToolIcon(tool.ferramenta)}
                <span className="font-mono text-[11px]">{tool.ferramenta}</span>

                {tool.diff_info && (
                  <span className="flex items-center gap-1 text-[10px] font-mono">
                    <span className="rounded bg-emerald-100 px-1 py-0.2 text-emerald-700">
                      +{tool.diff_info.adicoes}
                    </span>
                    <span className="rounded bg-rose-100 px-1 py-0.2 text-rose-700">
                      -{tool.diff_info.remocoes}
                    </span>
                  </span>
                )}

                {tool.status === 'sucesso' && (
                  <Check className="h-3 w-3 text-emerald-500" />
                )}
                {tool.status === 'erro' && (
                  <AlertCircle className="h-3 w-3 text-rose-500" />
                )}

                {isExpanded ? (
                  <ChevronDown className="h-3 w-3 text-slate-400" />
                ) : (
                  <ChevronRight className="h-3 w-3 text-slate-400" />
                )}
              </button>

              {/* Expansão com detalhes e Diff inline */}
              {isExpanded && (
                <div className="mt-2 w-full max-w-2xl rounded-xl border border-slate-200 bg-slate-50/90 p-3 shadow-xs">
                  <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-700">
                    <span className="flex items-center gap-1.5">
                      <FileDiff className="h-4 w-4 text-blue-600" />
                      {tool.diff_info ? `Diff: ${tool.diff_info.arquivo}` : `Execução: ${tool.ferramenta}`}
                    </span>
                    {tool.diff_info && (
                      <span className="text-[11px] text-slate-500 font-mono">
                        +{tool.diff_info.adicoes} / -{tool.diff_info.remocoes} linhas
                      </span>
                    )}
                  </div>

                  {tool.diff_info ? (
                    <CodeBlock
                      code={tool.codigo_proposto}
                      rawDiff={tool.diff_info.raw_diff}
                      diffInfo={tool.diff_info}
                      filename={tool.diff_info.arquivo}
                      language="python"
                      isDiff={true}
                    />
                  ) : tool.codigo_proposto ? (
                    <CodeBlock
                      code={tool.codigo_proposto}
                      filename={tool.argumentos?.file_path || 'pipeline_prep_otimizado.py'}
                      language="python"
                    />
                  ) : (
                    <div className="text-xs text-slate-600">
                      <pre className="overflow-x-auto rounded bg-white p-2 text-[11px] border border-slate-200">
                        {JSON.stringify(tool.argumentos || tool.resultado || 'Executado com sucesso', null, 2)}
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
  );
}

export default ToolChips;

