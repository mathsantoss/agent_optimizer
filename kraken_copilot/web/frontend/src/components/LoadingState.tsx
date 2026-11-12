import React, { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

/* ─────────────────────────────────────────────────────────
 * LOADING STATE (BEAUTIFUL UI)
 * Pixel-grid loader para operações de agentes e telemetria:
 *   · Drive — células quadradas, chevron wavefront animado
 *   · Dots  — células circulares, mesmo wavefront
 *   · Orbit — cometa contornando o perímetro do grid 3x3
 *
 * Combinado com label com animação shimmer e cronômetro decorrido.
 * ───────────────────────────────────────────────────────── */

const chevron = Array.from({ length: 9 }, (_, i) => {
  const r = Math.floor(i / 3);
  const c = i % 3;
  return (c + Math.abs(r - 1)) * 90;
});

const ORBIT_ORDER = [0, 1, 2, 5, 8, 7, 6, 3];
const orbit = Array.from({ length: 9 }, (_, i) => {
  const k = ORBIT_ORDER.indexOf(i);
  return k === -1 ? null : k * 110;
});

const PATTERNS: Record<string, { delays: (number | null)[]; dur: number; round: boolean }> = {
  Drive: { delays: chevron, dur: 650, round: false },
  Dots: { delays: chevron, dur: 650, round: true },
  Orbit: { delays: orbit, dur: 950, round: false },
};

function LoaderGrid({
  delays,
  dur,
  round,
}: {
  delays: (number | null)[];
  dur: number;
  round: boolean;
}) {
  return (
    <span aria-hidden className="grid shrink-0 grid-cols-[repeat(3,4px)] gap-[2px]">
      {delays.map((delay, index) => (
        <span
          key={index}
          className={cn(
            'size-[4px] bg-blue-600 transition-opacity',
            round ? 'rounded-full' : 'rounded-[1px]'
          )}
          style={{
            opacity: delay === null ? 0.12 : 0.25,
            animation: delay === null ? 'none' : `pixel-on ${dur}ms ease-in-out ${delay}ms infinite`,
          }}
        />
      ))}
    </span>
  );
}

function useElapsed() {
  const [ds, setDs] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setDs((d) => d + 1), 100);
    return () => clearInterval(t);
  }, []);
  const total = ds / 10;
  if (total < 60) return `${total.toFixed(1)}s`;
  return `${Math.floor(total / 60)}m ${(total % 60).toFixed(1)}s`;
}

export interface LoadingStateProps {
  label?: string;
  variant?: 'Drive' | 'Dots' | 'Orbit';
  className?: string;
}

export function LoadingState({
  label = 'Processando pipeline e raciocínio...',
  variant = 'Drive',
  className,
}: LoadingStateProps) {
  const elapsed = useElapsed();
  const { delays, dur, round } = PATTERNS[variant] ?? PATTERNS.Drive;

  return (
    <div
      role="status"
      className={cn(
        'inline-flex items-center gap-2.5 rounded-full border border-slate-200/90 bg-white/95 px-3.5 py-1.5 shadow-2xs select-none backdrop-blur-xs',
        className
      )}
    >
      <LoaderGrid delays={delays} dur={dur} round={round} />

      <span
        className="bg-clip-text text-[12px] font-semibold text-transparent"
        style={{
          backgroundImage:
            'linear-gradient(90deg, #64748b 25%, #0f172a 50%, #64748b 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer-text 1.6s linear infinite',
        }}
      >
        {label}
      </span>

      <span className="font-mono text-[11px] text-slate-400 tabular-nums font-medium">
        {elapsed}
      </span>
    </div>
  );
}

export default LoadingState;

