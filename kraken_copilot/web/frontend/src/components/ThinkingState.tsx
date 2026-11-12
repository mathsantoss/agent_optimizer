import React, { useState, useRef, useLayoutEffect, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Sparkles, ChevronDown, Check, Loader2, Globe, FileCode, Cpu, Terminal } from 'lucide-react';

/* ─────────────────────────────────────────────────────────
 * THINKING STATE (BEAUTIFUL UI)
 * Trace expansível de raciocínio de agentes com 4 variantes:
 *   · Steps     — lista de passos com spinner → checkmarks verdes
 *   · Reasoning — raciocínio analítico estruturado
 *   · Search    — buscas no catálogo, metadados e datalake
 *   · Coding    — chamadas de ferramentas, leitura e diff de arquivos
 * ───────────────────────────────────────────────────────── */

export type ThinkingStep = {
  id?: string;
  text?: string;
  primary?: string;
  secondary?: string;
  done?: boolean;
  duration?: string;
  mono?: boolean;
  add?: number;
  del?: number;
  href?: string;
};

export interface ThinkingStateProps {
  isThinking: boolean;
  agentName?: string;
  steps?: ThinkingStep[];
  variant?: 'Steps' | 'Reasoning' | 'Search' | 'Coding';
  query?: string;
  className?: string;
}

export function ThinkingState({
  isThinking,
  agentName = 'Kraken Copilot',
  steps = [],
  variant = 'Steps',
  query,
  className,
}: ThinkingStateProps) {
  const [expanded, setExpanded] = useState<boolean>(true);
  const traceRef = useRef<HTMLDivElement>(null);
  const [lineHeight, setLineHeight] = useState(0);

  useLayoutEffect(() => {
    if (traceRef.current) {
      setLineHeight(traceRef.current.offsetHeight);
    }
  }, [steps, expanded]);

  if (!isThinking && steps.length === 0) return null;

  const totalSteps = steps.length;
  const completedSteps = steps.filter((s) => s.done).length;

  return (
    <div
      className={cn(
        'my-3 w-full max-w-2xl flex flex-col rounded-2xl border border-slate-200/90 bg-white/95 p-3 shadow-xs select-none backdrop-blur-xs transition-all',
        className
      )}
    >
      {/* Header — shared across variants */}
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between rounded-xl px-2 py-1 transition-colors hover:bg-slate-50 cursor-pointer"
      >
        <div className="flex items-center gap-2">
          {isThinking ? (
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-blue-50 text-blue-600 shadow-2xs">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" />
            </div>
          ) : (
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 shadow-2xs">
              <Check className="h-3.5 w-3.5 text-emerald-600" />
            </div>
          )}

          <div className="flex items-center gap-2 text-left">
            {isThinking ? (
              <span
                className="bg-clip-text text-[13px] font-semibold text-transparent"
                style={{
                  backgroundImage:
                    'linear-gradient(90deg, #64748b 25%, #2563eb 50%, #64748b 75%)',
                  backgroundSize: '200% 100%',
                  animation: 'shimmer-text 1.5s linear infinite',
                }}
              >
                {agentName} está raciocinando...
              </span>
            ) : (
              <span className="text-[13px] font-semibold text-slate-800">
                {agentName} concluiu o percurso ({totalSteps} etapas)
              </span>
            )}

            {totalSteps > 0 && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-mono font-semibold text-slate-500">
                {completedSteps}/{totalSteps}
              </span>
            )}
          </div>
        </div>

        <ChevronDown
          className={cn(
            'h-4 w-4 text-slate-400 transition-transform duration-200',
            expanded ? 'rotate-180' : 'rotate-0'
          )}
        />
      </button>

      {/* Expandable Trace com Conector Vertical */}
      {expanded && (
        <div className="relative mt-2 ml-3.5 pl-4 pb-1">
          {/* Linha vertical conectora */}
          <span
            aria-hidden
            className="absolute left-0 top-1 w-px bg-slate-200"
            style={{ height: Math.max(0, lineHeight - 8) }}
          />

          <div ref={traceRef} className="flex flex-col gap-1.5 py-1">
            {query && (
              <div className="flex items-center gap-2 px-1 text-xs text-slate-600 font-mono">
                <Globe className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                <span className="truncate">{query}</span>
              </div>
            )}

            {steps.map((step, i) => {
              const label = step.text || step.primary || `Etapa ${i + 1}`;
              const isDone = step.done ?? !isThinking;

              return (
                <div
                  key={step.id || i}
                  className="flex min-h-6 items-center justify-between gap-2 rounded-lg px-2 py-1 text-xs transition-colors hover:bg-slate-50"
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    {isDone ? (
                      <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                    ) : (
                      <span className="size-2.5 shrink-0 rounded-full border border-blue-500 border-t-transparent animate-spin" />
                    )}

                    <span
                      className={cn(
                        'truncate text-[12px] font-medium leading-tight',
                        isDone ? 'text-slate-700' : 'text-blue-700 font-semibold'
                      )}
                    >
                      {label}
                    </span>

                    {step.secondary && (
                      <span className="truncate text-[11px] text-slate-400 font-mono">
                        {step.secondary}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    {step.add !== undefined && (
                      <span className="font-mono text-[10px] text-emerald-600 font-semibold">
                        +{step.add}
                      </span>
                    )}
                    {step.del !== undefined && (
                      <span className="font-mono text-[10px] text-rose-500 font-semibold">
                        -{step.del}
                      </span>
                    )}
                    {step.duration && (
                      <span className="rounded bg-slate-100 px-1.5 py-0.2 font-mono text-[10px] text-slate-500">
                        {step.duration}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default ThinkingState;
