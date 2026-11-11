import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { Eye, Code2, Copy, Check, GitFork, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

// Inicialização segura do Mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'loose',
  fontFamily: 'Inter, system-ui, sans-serif',
});

export interface MermaidBlockProps {
  chart: string;
  className?: string;
}

export function MermaidBlock({ chart, className }: MermaidBlockProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'chart' | 'code'>('chart');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const renderChart = async () => {
      try {
        let cleanCode = chart.trim();
        // Remove cercas markdown ou diretivas ::: mermaid se presentes
        cleanCode = cleanCode
          .replace(/^:::\s*mermaid/i, '')
          .replace(/:::\s*$/i, '')
          .replace(/^```(?:mermaid)?/i, '')
          .replace(/```$/i, '')
          .trim();
        // Ajusta sintaxe de pipes com espaços no mermaid (ex: --> |Sim| -> -->|Sim|)
        cleanCode = cleanCode.replace(/-->\s+\|/g, '-->|');

        const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(id, cleanCode);
        if (isMounted) {
          setSvgContent(svg);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err?.message || 'Falha ao renderizar diagrama Mermaid');
        }
      }
    };

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(chart);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <div
      className={cn(
        'my-4 overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xs transition-all',
        className
      )}
    >
      {/* Header com Controles do Diagrama */}
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/70 px-4 py-2 text-xs select-none">
        <div className="flex items-center gap-2">
          <GitFork className="h-3.5 w-3.5 text-blue-600" />
          <span className="font-semibold text-slate-800">Diagrama Visual (Mermaid)</span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setViewMode(viewMode === 'chart' ? 'code' : 'chart')}
            className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors cursor-pointer"
            title={viewMode === 'chart' ? 'Ver código Mermaid' : 'Ver gráfico SVG'}
          >
            {viewMode === 'chart' ? <Code2 className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            <span>{viewMode === 'chart' ? 'Código' : 'Diagrama'}</span>
          </button>

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors cursor-pointer"
            title="Copiar código do diagrama"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 text-emerald-500" />
                <span className="text-emerald-600">Copiado</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                <span>Copiar</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Renderizador do Diagrama ou Código */}
      <div className="p-4 overflow-x-auto flex justify-center bg-white min-h-[140px]">
        {viewMode === 'code' || error ? (
          <div className="w-full">
            {error && (
              <div className="mb-2 flex items-center gap-1.5 text-[11px] text-amber-800 bg-amber-50 p-2 rounded-lg border border-amber-200">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                <span>Exibindo código fonte do diagrama ({error})</span>
              </div>
            )}
            <pre className="w-full rounded-xl bg-[#0f172a] p-3 font-mono text-[11px] text-slate-200 overflow-x-auto">
              {chart}
            </pre>
          </div>
        ) : (
          <div
            ref={containerRef}
            className="w-full flex justify-center items-center py-2 [&_svg]:max-w-full [&_svg]:h-auto [&_svg]:rounded-lg"
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        )}
      </div>
    </div>
  );
}

export default MermaidBlock;

