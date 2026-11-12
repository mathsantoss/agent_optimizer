import React, { useState } from 'react';
import {
  ShieldAlert,
  Check,
  X,
  FileCode,
  ChevronDown,
  ChevronUp,
  Sparkles,
  CheckCircle2,
  FileDiff,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DiffInfo } from './ToolChips';
import { CodeBlock } from './CodeBlock';

export interface ApprovalCardProps {
  execucaoId?: string;
  targetFile?: string;
  diffInfo?: DiffInfo;
  proposedCode?: string;
  onApprove: (execucaoId?: string, targetFile?: string) => void;
  onReject: (execucaoId?: string, targetFile?: string) => void;
  isProcessing?: boolean;
  className?: string;
}

export function ApprovalCard({
  execucaoId,
  targetFile = '',
  diffInfo,
  proposedCode,
  onApprove,
  onReject,
  isProcessing = false,
  className,
}: ApprovalCardProps) {
  const [showCode, setShowCode] = useState(false);
  const [decided, setDecided] = useState<'approved' | 'rejected' | null>(null);

  const effectiveTargetFile = diffInfo?.arquivo || targetFile || 'script.py';

  const handleApprove = () => {
    setDecided('approved');
    onApprove(execucaoId, effectiveTargetFile);
  };

  const handleReject = () => {
    setDecided('rejected');
    onReject(execucaoId, effectiveTargetFile);
  };

  if (decided === 'approved') {
    return (
      <div className="my-3 flex items-center gap-2.5 rounded-2xl border border-emerald-200 bg-emerald-50/90 px-4 py-3 text-xs font-medium text-emerald-900 shadow-2xs">
        <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
        <span>
          Proposta Aprovada e Autorizada. As alterações foram aplicadas em{' '}
          <code className="font-semibold text-emerald-950">{effectiveTargetFile}</code>.
        </span>
      </div>
    );
  }

  if (decided === 'rejected') {
    return (
      <div className="my-3 flex items-center gap-2.5 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs font-medium text-slate-700 shadow-2xs">
        <X className="h-4 w-4 text-rose-500 shrink-0" />
        <span>Proposta rejeitada. O código do pipeline foi mantido na versão original.</span>
      </div>
    );
  }

  const hasCodeContent = Boolean(proposedCode || diffInfo);

  return (
    <div
      className={cn(
        'my-3.5 overflow-hidden rounded-2xl border border-amber-300/90 bg-gradient-to-b from-amber-50/50 via-white to-amber-50/20 p-4 shadow-sm transition-all',
        className
      )}
    >
      {/* Header Estilo Beautiful UI */}
      <div className="flex items-center justify-between border-b border-amber-100/90 pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-amber-100 text-amber-800 shadow-2xs">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <div className="text-xs font-bold tracking-tight text-slate-900">
              Aprovação de Alterações no Pipeline
            </div>
            <div className="text-[10.5px] text-slate-500 font-mono">
              krakenlake/workspace/{effectiveTargetFile}
            </div>
          </div>
        </div>

        <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-bold text-amber-800 uppercase tracking-tight">
          Human-in-the-Loop
        </span>
      </div>

      <div className="mt-3 text-xs text-slate-700 leading-relaxed">
        <p>
          O assistente de IA gerou uma proposta otimizada para o script{' '}
          <code className="rounded bg-amber-100/80 px-1.5 py-0.5 font-mono text-[11px] font-bold text-amber-900">
            {effectiveTargetFile}
          </code>
          . A gravação definitiva no disco requer sua autorização explícita:
        </p>
      </div>

      {/* Estatísticas e Toggle do Código / Diff */}
      {hasCodeContent && (
        <div className="mt-3 rounded-xl border border-slate-200/90 bg-slate-50/70 p-2.5">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setShowCode(!showCode)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:text-blue-900 transition-colors cursor-pointer select-none"
            >
              <Eye className="h-3.5 w-3.5" />
              <span>{showCode ? 'Ocultar código / diff' : 'Inspecionar código otimizado antes de aprovar'}</span>
              {showCode ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>

            {diffInfo && (
              <span className="text-[11px] font-mono text-slate-500">
                <strong className="text-emerald-600">+{diffInfo.adicoes}</strong> /{' '}
                <strong className="text-rose-600">-{diffInfo.remocoes}</strong> linhas
              </span>
            )}
          </div>

          {showCode && (
            <div className="mt-2.5 overflow-hidden rounded-xl">
              <CodeBlock
                code={proposedCode}
                rawDiff={diffInfo?.raw_diff}
                diffInfo={diffInfo}
                language="python"
                filename={effectiveTargetFile}
                isDiff={Boolean(diffInfo)}
              />
            </div>
          )}
        </div>
      )}

      {/* Botões Personalizados e Estilizados para Aprovação ou Rejeição */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3.5">
        <span className="text-[11px] text-slate-500 font-medium">
          Escolha uma ação para prosseguir:
        </span>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={isProcessing}
            onClick={handleReject}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 hover:text-slate-900 shadow-2xs transition-all active:scale-98 cursor-pointer disabled:opacity-50"
          >
            <X className="h-3.5 w-3.5 text-slate-500" />
            <span>Rejeitar Proposta</span>
          </button>

          <button
            type="button"
            disabled={isProcessing}
            onClick={handleApprove}
            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 shadow-xs transition-all active:scale-98 cursor-pointer disabled:opacity-50"
          >
            <Check className="h-3.5 w-3.5" />
            <span>Aprovar e Aplicar Alterações ↵</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ApprovalCard;
