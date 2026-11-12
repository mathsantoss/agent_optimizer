import React from 'react';
import {
  FileCode2,
  GitCompare,
  Check,
  X,
  Sparkles,
  ShieldAlert,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { CodeBlock } from '../CodeBlock';

export interface KrakenCodeDiffData {
  arquivo: string;
  arquivo_alvo?: string;
  original_code?: string;
  proposed_code: string;
  raw_diff?: string;
  adicoes: number;
  remocoes: number;
  has_approval_request?: boolean;
  tipo_transformacao?: string;
  explicacao?: string;
}

export interface KrakenCodeDiffCardProps {
  diff: KrakenCodeDiffData;
  onApprove?: (targetFile: string) => void;
  onReject?: (targetFile: string) => void;
  className?: string;
}

export function KrakenCodeDiffCard({
  diff,
  onApprove,
  onReject,
  className,
}: KrakenCodeDiffCardProps) {
  const targetFile = diff.arquivo_alvo || diff.arquivo;

  return (
    <div
      className={cn(
        'my-3 overflow-hidden rounded-2xl border border-indigo-200/90 bg-white shadow-xs transition-all',
        className
      )}
    >
      {/* Header do Diff */}
      <div className="flex flex-wrap items-center justify-between border-b border-indigo-100 bg-indigo-50/60 px-4 py-2.5 text-xs">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-2xs">
            <GitCompare className="h-3.5 w-3.5" />
          </div>
          <div>
            <span className="font-bold text-slate-900">Proposta de Alteração de Código (KrakenCodeDiff)</span>
            <span className="ml-2 font-mono text-[11px] text-slate-500">
              krakenlake/workspace/{diff.arquivo}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800">
            +{diff.adicoes}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-bold text-rose-800">
            -{diff.remocoes}
          </span>
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-sans font-semibold text-slate-600 uppercase">
            {diff.tipo_transformacao || 'Otimização'}
          </span>
        </div>
      </div>

      {/* Explicação da Mudança */}
      {diff.explicacao && (
        <div className="border-b border-slate-100 bg-slate-50/50 px-4 py-2 text-xs text-slate-600 leading-relaxed">
          <strong>Resumo da alteração:</strong> {diff.explicacao}
        </div>
      )}

      {/* Visualizador de Diff Shiki / Pierre Diffs */}
      <div className="p-3 bg-[#0c1222]">
        <CodeBlock
          code={diff.proposed_code}
          oldCode={diff.original_code}
          rawDiff={diff.raw_diff}
          language="python"
          filename={diff.arquivo}
          isDiff={true}
          variant="Diff"
          className="my-0 border-none shadow-none"
        />
      </div>

      {/* Barra de Aprovação / Decisão HITL */}
      {diff.has_approval_request && (
        <div className="flex flex-wrap items-center justify-between border-t border-slate-200 bg-amber-50/40 px-4 py-3 gap-2">
          <div className="flex items-center gap-2 text-xs text-amber-900 font-medium">
            <ShieldAlert className="h-4 w-4 text-amber-600 shrink-0" />
            <span>
              Autorização necessária para substituir definitivamente o script no workspace.
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onReject?.(targetFile)}
              className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs transition-colors cursor-pointer"
            >
              <X className="h-3.5 w-3.5 text-slate-500" />
              <span>Rejeitar</span>
            </button>

            <button
              type="button"
              onClick={() => onApprove?.(targetFile)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 shadow-2xs transition-colors cursor-pointer"
            >
              <Check className="h-3.5 w-3.5" />
              <span>Aprovar e Gravar</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default KrakenCodeDiffCard;

