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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DiffInfo } from './ToolChips';

export interface ApprovalCardProps {
  execucaoId?: string;
  targetFile?: string;
  diffInfo?: DiffInfo;
  onApprove: (execucaoId?: string) => void;
  onReject: (execucaoId?: string) => void;
  isProcessing?: boolean;
  className?: string;
}

export function ApprovalCard({
  execucaoId,
  targetFile = 'pipeline_prep.py',
  diffInfo,
  onApprove,
  onReject,
  isProcessing = false,
  className,
}: ApprovalCardProps) {
  const [selectedOption, setSelectedOption] = useState<number>(0);
  const [showDiff, setShowDiff] = useState(false);
  const [decided, setDecided] = useState<'approved' | 'rejected' | null>(null);

  const options = [
    {
      title: `Aprovar e aplicar alterações em ${targetFile}`,
      desc: 'Substitui o arquivo alvo de forma atômica e executa validação.',
      action: 'approve',
    },
    {
      title: 'Rejeitar proposta e manter versão original',
      desc: 'Mantém o script inalterado e descarta o código proposto.',
      action: 'reject',
    },
  ];

  const handleConfirm = () => {
    if (selectedOption === 0) {
      setDecided('approved');
      onApprove(execucaoId);
    } else {
      setDecided('rejected');
      onReject(execucaoId);
    }
  };

  if (decided === 'approved') {
    return (
      <div className="my-3 flex items-center gap-2.5 rounded-2xl border border-emerald-200 bg-emerald-50/80 px-4 py-3 text-xs font-medium text-emerald-900 shadow-2xs">
        <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
        <span>
          ✓ Proposta Aprovada e Autorizada para aplicação em{' '}
          <code className="font-semibold">{targetFile}</code>.
        </span>
      </div>
    );
  }

  if (decided === 'rejected') {
    return (
      <div className="my-3 flex items-center gap-2.5 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs font-medium text-slate-700 shadow-2xs">
        <X className="h-4 w-4 text-slate-500 shrink-0" />
        <span>✕ Proposta rejeitada. O código do pipeline foi mantido sem alterações.</span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'my-3 overflow-hidden rounded-2xl border border-amber-200/90 bg-gradient-to-b from-amber-50/40 to-white p-4 shadow-sm transition-all',
        className
      )}
    >
      {/* Header Estilo Beautiful UI */}
      <div className="flex items-center justify-between border-b border-amber-100/80 pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-amber-100 text-amber-800">
            <ShieldAlert className="h-3.5 w-3.5" />
          </div>
          <span className="text-xs font-bold tracking-tight text-slate-900">
            Aprovação de Alterações no Pipeline
          </span>
        </div>

        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
          Human-in-the-Loop
        </span>
      </div>

      <p className="mt-2.5 text-xs text-slate-600 leading-relaxed">
        O assistente gerou uma proposta de alteração ou otimização para o script{' '}
        <code className="rounded bg-amber-100/70 px-1.5 py-0.5 font-mono text-[11px] font-bold text-amber-900">
          {targetFile}
        </code>
        . Selecione sua decisão:
      </p>

      {/* Opções Interativas (Radio Cards) */}
      <div className="mt-3 space-y-2">
        {options.map((opt, idx) => {
          const isSelected = selectedOption === idx;
          return (
            <div
              key={idx}
              onClick={() => setSelectedOption(idx)}
              className={cn(
                'flex cursor-pointer items-start gap-3 rounded-xl border p-3 text-xs transition-all select-none',
                isSelected
                  ? 'border-blue-500 bg-blue-50/40 shadow-xs ring-1 ring-blue-500'
                  : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
              )}
            >
              <div className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-slate-300 bg-white">
                {isSelected && <div className="h-2 w-2 rounded-full bg-blue-600" />}
              </div>
              <div className="flex-1">
                <div className="font-semibold text-slate-900">{opt.title}</div>
                <div className="text-[11px] text-slate-500 mt-0.5">{opt.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Diff Toggle */}
      {diffInfo && (
        <div className="mt-3 border-t border-slate-100 pt-2.5">
          <button
            type="button"
            onClick={() => setShowDiff(!showDiff)}
            className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 hover:text-blue-600 transition-colors"
          >
            <FileCode className="h-3.5 w-3.5" />
            <span>
              {showDiff ? 'Ocultar diff da proposta' : 'Visualizar diff da proposta'} (
              <span className="text-emerald-600">+{diffInfo.adicoes}</span> /{' '}
              <span className="text-rose-600">-{diffInfo.remocoes}</span> linhas)
            </span>
            {showDiff ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>

          {showDiff && diffInfo.linhas && (
            <div className="mt-2 max-h-60 overflow-y-auto rounded-xl border border-slate-800 bg-[#0f172a] p-3 font-mono text-[11px]">
              {diffInfo.linhas.map((row, rIdx) => {
                let color = 'text-slate-300';
                if (row.tipo === 'add') color = 'bg-emerald-950/40 text-emerald-300 px-1 rounded-xs';
                if (row.tipo === 'del') color = 'bg-rose-950/40 text-rose-300 px-1 rounded-xs';
                if (row.tipo === 'hunk') color = 'text-blue-400 font-bold';
                return (
                  <div key={rIdx} className={cn('whitespace-pre py-0.5', color)}>
                    {row.texto}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Footer com Botão de Confirmação */}
      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
        <span className="text-[11px] text-slate-400">
          Decisão exigida antes da escrita definitiva
        </span>

        <button
          type="button"
          disabled={isProcessing}
          onClick={handleConfirm}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-bold text-white shadow-xs transition-all active:scale-98 cursor-pointer disabled:opacity-50',
            selectedOption === 0 ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-slate-700 hover:bg-slate-800'
          )}
        >
          {selectedOption === 0 ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
          <span>{selectedOption === 0 ? 'Aprovar e Aplicar ↵' : 'Rejeitar Proposta'}</span>
        </button>
      </div>
    </div>
  );
}

export default ApprovalCard;
