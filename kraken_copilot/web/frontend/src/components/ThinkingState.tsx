import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Check, Loader2, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ThinkingStep {
  id?: string;
  text: string;
  done?: boolean;
  duration?: string;
  secondary?: string;
}

export interface ThinkingStateProps {
  isThinking: boolean;
  agentName?: string;
  steps?: ThinkingStep[];
  className?: string;
}

export function ThinkingState({
  isThinking,
  agentName = 'Kraken Copilot',
  steps = [],
  className,
}: ThinkingStateProps) {
  const [expanded, setExpanded] = useState(true);

  if (!isThinking && steps.length === 0) return null;

  return (
    <div
      className={cn(
        'my-2 rounded-xl border border-slate-200/90 bg-white/90 p-3 text-xs shadow-xs transition-all backdrop-blur-xs',
        className
      )}
    >
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex cursor-pointer items-center justify-between gap-2 text-slate-700 select-none hover:text-slate-900"
      >
        <div className="flex items-center gap-2">
          {isThinking ? (
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-50 text-blue-600">
              <Loader2 className="h-3 w-3 animate-spin" />
            </div>
          ) : (
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <Check className="h-3 w-3" />
            </div>
          )}
          <span className="font-medium text-slate-800">
            {isThinking ? (
              <span className="flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-blue-500 animate-pulse" />
                {agentName} está raciocinando...
              </span>
            ) : (
              `${agentName} concluiu o percurso de raciocínio`
            )}
          </span>
          {steps.length > 0 && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
              {steps.filter((s) => s.done).length}/{steps.length} etapas
            </span>
          )}
        </div>

        <button
          type="button"
          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          aria-label={expanded ? 'Recolher' : 'Expandir'}
        >
          {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </button>
      </div>

      {expanded && steps.length > 0 && (
        <div className="mt-2.5 space-y-1.5 border-t border-slate-100 pt-2 font-mono text-[11px]">
          {steps.map((step, idx) => (
            <div key={idx} className="flex items-start gap-2 text-slate-600">
              {step.done ? (
                <Check className="mt-0.5 h-3 w-3 shrink-0 text-emerald-500" />
              ) : (
                <Loader2 className="mt-0.5 h-3 w-3 shrink-0 animate-spin text-blue-500" />
              )}
              <span className="flex-1 leading-snug">{step.text}</span>
              {step.duration && (
                <span className="text-[10px] text-slate-400 shrink-0">{step.duration}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
export default ThinkingState;

