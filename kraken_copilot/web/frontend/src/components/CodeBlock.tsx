import React, { useState, useEffect, useCallback, useMemo, type ReactNode } from 'react';
import { File, PatchDiff, MultiFileDiff } from '@pierre/diffs/react';
import { cn } from '@/lib/utils';
import { Copy, Check, FileCode, GitCompare, Columns, AlignJustify } from 'lucide-react';
import { MermaidBlock } from './MermaidBlock';
import { type DiffInfo } from './ToolChips';

/* ─────────────────────────────────────────────────────────
 * CODE BLOCK (POWERED BY @PIERRE/DIFFS)
 * Visualizador moderno de código e diffs com Shiki engine:
 *   · Code — arquivo com syntax highlighting profissional e gutter
 *   · Diff — unified ou split (lado a lado) diff com detecção
 *     a nível de palavras/caracteres, estatísticas +added / -removed
 * ───────────────────────────────────────────────────────── */

export type CodePiece = { text: string; change?: 'add' | 'del' };

export type DiffRow = {
  old: number | null;
  cur: number | null;
  type: 'ctx' | 'add' | 'del';
  pieces: CodePiece[];
};

export interface CodeBlockProps {
  code?: string;
  oldCode?: string;
  patch?: string;
  rawDiff?: string;
  diffInfo?: DiffInfo;
  lines?: string[];
  diff?: DiffRow[];
  language?: string;
  filename?: string;
  className?: string;
  isDiff?: boolean;
  variant?: 'Code' | 'Diff';
  diffStyle?: 'unified' | 'split';
  fullHeight?: boolean;
  onCopy?: (text: string) => void;
}

// Garante que o patch possua cabeçalhos válidos '--- a/...' e '+++ b/...' para o parser Pierre
function normalizePatchString(raw: string, filename: string = 'pipeline.py'): string {
  let trimmed = raw.trim();
  if (!trimmed) return '';
  if (!trimmed.startsWith('---') && !trimmed.startsWith('diff --git')) {
    trimmed = `--- a/${filename}\n+++ b/${filename}\n` + trimmed;
  }
  return trimmed.endsWith('\n') ? trimmed : trimmed + '\n';
}

// Fallback de ErrorBoundary para proteger contra qualquer anomalia de parsing externo
class PierreErrorBoundary extends React.Component<
  { children: ReactNode; fallback: ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: ReactNode; fallback: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(err: any) {
    console.warn('Pierre Diff rendering fallback triggered:', err);
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export function CodeBlock({
  code = '',
  oldCode,
  patch,
  rawDiff,
  diffInfo,
  lines: customLines,
  diff: customDiff,
  language = 'python',
  filename = 'pipeline.py',
  className,
  isDiff = false,
  variant: initialVariant,
  diffStyle: initialDiffStyle = 'unified',
  fullHeight = false,
  onCopy,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [diffLayout, setDiffLayout] = useState<'unified' | 'split'>(initialDiffStyle);

  const rawCode = code || (customLines ? customLines.join('\n') : '');

  // Renderização de diagramas Mermaid
  if (
    language === 'mermaid' ||
    rawCode.trim().startsWith('flowchart') ||
    rawCode.trim().startsWith('sequenceDiagram') ||
    rawCode.trim().startsWith('classDiagram') ||
    rawCode.trim().startsWith('stateDiagram') ||
    rawCode.trim().startsWith('graph ')
  ) {
    return <MermaidBlock chart={rawCode} className={className} />;
  }

  // Identificação inteligente do patch unificado
  const unifiedPatch = useMemo(() => {
    if (patch) return normalizePatchString(patch, filename);
    if (rawDiff) return normalizePatchString(rawDiff, filename);
    if (diffInfo?.raw_diff) return normalizePatchString(diffInfo.raw_diff, filename);
    if (
      rawCode.includes('--- ') ||
      rawCode.includes('+++ ') ||
      (rawCode.includes('@@ ') && (rawCode.includes('\n+') || rawCode.includes('\n-')))
    ) {
      return normalizePatchString(rawCode, filename);
    }
    if (diffInfo?.linhas && diffInfo.linhas.length > 0) {
      const reconstructed = diffInfo.linhas.map((l) => l.texto).join('\n');
      return normalizePatchString(reconstructed, filename);
    }
    return '';
  }, [patch, rawDiff, diffInfo, rawCode, filename]);

  const effectiveOldCode = oldCode || diffInfo?.original_code;
  const effectiveNewCode = code || diffInfo?.proposed_code || (rawCode.startsWith('---') ? '' : rawCode);

  // Estatísticas de adições e remoções
  const { added, removed } = useMemo(() => {
    if (diffInfo && (diffInfo.adicoes > 0 || diffInfo.remocoes > 0)) {
      return { added: diffInfo.adicoes, removed: diffInfo.remocoes };
    }
    if (unifiedPatch) {
      const lines = unifiedPatch.split('\n');
      let a = 0;
      let r = 0;
      for (const l of lines) {
        if (l.startsWith('+') && !l.startsWith('+++')) a++;
        else if (l.startsWith('-') && !l.startsWith('---')) r++;
      }
      return { added: a, removed: r };
    }
    if (customDiff) {
      return {
        added: customDiff.filter((r) => r.type === 'add').length,
        removed: customDiff.filter((r) => r.type === 'del').length,
      };
    }
    return { added: 0, removed: 0 };
  }, [diffInfo, unifiedPatch, customDiff]);

  const hasDiffContent = useMemo(() => {
    if (unifiedPatch.length > 0) return true;
    if (effectiveOldCode && effectiveNewCode && effectiveOldCode.trim() !== effectiveNewCode.trim()) return true;
    if (diffInfo && (diffInfo.adicoes > 0 || diffInfo.remocoes > 0 || (diffInfo.raw_diff && diffInfo.raw_diff.trim().length > 0))) return true;
    if (customDiff && customDiff.length > 0) return true;
    if (isDiff && (added > 0 || removed > 0)) return true;
    return false;
  }, [isDiff, unifiedPatch, effectiveOldCode, effectiveNewCode, diffInfo, customDiff, added, removed]);

  const [activeVariant, setActiveVariant] = useState<'Code' | 'Diff'>(
    initialVariant || (hasDiffContent ? 'Diff' : 'Code')
  );

  useEffect(() => {
    if (initialVariant) {
      setActiveVariant(initialVariant);
    } else if (!hasDiffContent) {
      setActiveVariant('Code');
    } else {
      setActiveVariant('Diff');
    }
  }, [initialVariant, hasDiffContent, filename]);

  const copy = useCallback(() => {
    const textToCopy =
      activeVariant === 'Diff' && unifiedPatch
        ? unifiedPatch
        : effectiveNewCode || rawCode;
    navigator.clipboard.writeText(textToCopy).then(() => {
      setCopied(true);
      onCopy?.(textToCopy);
      setTimeout(() => setCopied(false), 1800);
    });
  }, [activeVariant, unifiedPatch, effectiveNewCode, rawCode, onCopy]);

  // Conteúdo de código simples caso necessário
  const displayCode = effectiveNewCode || rawCode || (unifiedPatch ? '# Selecione a aba Diff para visualizar as alterações' : '');

  // Se não houver diff e o arquivo estiver vazio
  if (!hasDiffContent && displayCode.trim().length === 0) {
    return (
      <div
        className={cn(
          fullHeight
            ? 'h-full flex-1 min-h-0 my-0 rounded-none border-none shadow-none font-mono text-xs select-text flex flex-col bg-[#0c1222]'
            : 'my-3 w-full overflow-hidden rounded-2xl border border-slate-800 bg-[#0c1222] shadow-md font-mono text-xs select-text flex flex-col',
          className
        )}
      >
        <div className="flex h-11 items-center justify-between border-b border-slate-800/80 bg-[#080d1a] px-4 text-[12px] select-none shrink-0">
          <div className="flex items-center gap-2 overflow-hidden">
            <FileCode className="h-4 w-4 text-slate-500 shrink-0" />
            <span className="truncate font-semibold text-slate-400">
              {filename || `${language}.py`}
            </span>
          </div>
          <span className="text-[11px] text-slate-500 font-sans">0 linhas (Vazio)</span>
        </div>
        <div className="flex flex-1 flex-col items-center justify-center p-8 text-center text-slate-500 gap-2 font-sans min-h-[160px]">
          <FileCode className="h-8 w-8 text-slate-700" />
          <p className="font-semibold text-slate-300 font-mono text-xs">{filename || 'Arquivo'} está vazio (0 bytes)</p>
          <p className="text-xs text-slate-500 max-w-sm">
            Nenhum conteúdo ou alteração para exibir neste script.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        fullHeight
          ? 'h-full flex-1 min-h-0 my-0 rounded-none border-none shadow-none font-mono text-xs select-text flex flex-col bg-[#0c1222]'
          : 'my-3 w-full overflow-hidden rounded-2xl border border-slate-800 bg-[#0c1222] shadow-md font-mono text-xs select-text flex flex-col',
        className
      )}
    >
      {/* Header — filename · (diff stats | switcher | layout split/unified | copy) */}
      <div className="flex h-11 items-center justify-between border-b border-slate-800/80 bg-[#080d1a] px-4 text-[12px] select-none shrink-0">
        <div className="flex items-center gap-2 overflow-hidden">
          {hasDiffContent ? (
            <GitCompare className="h-4 w-4 text-emerald-400 shrink-0" />
          ) : (
            <FileCode className="h-4 w-4 text-indigo-400 shrink-0" />
          )}
          <span className="truncate font-semibold text-slate-200">
            {filename || (hasDiffContent ? 'Proposta de Alteração (Diff)' : `${language}.py`)}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {hasDiffContent && (added > 0 || removed > 0) && (
            <div className="flex items-center gap-1.5 rounded-lg bg-slate-900/80 px-2 py-0.5 border border-slate-800 text-[11px] font-mono tabular-nums">
              <span className="text-emerald-400 font-semibold">+{added}</span>
              <span className="text-rose-400 font-semibold">-{removed}</span>
            </div>
          )}

          {/* Seletor Diff / Código */}
          {hasDiffContent && (
            <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5 text-[11px]">
              <button
                type="button"
                onClick={() => setActiveVariant('Diff')}
                className={cn(
                  'rounded px-2 py-0.5 transition-colors cursor-pointer',
                  activeVariant === 'Diff'
                    ? 'bg-emerald-500/20 text-emerald-300 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                Diff
              </button>
              <button
                type="button"
                onClick={() => setActiveVariant('Code')}
                className={cn(
                  'rounded px-2 py-0.5 transition-colors cursor-pointer',
                  activeVariant === 'Code'
                    ? 'bg-blue-500/20 text-blue-300 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                Código
              </button>
            </div>
          )}

          {/* Toggle Unificado vs Lado a Lado (Split) quando visualizando Diff */}
          {hasDiffContent && activeVariant === 'Diff' && (
            <div className="hidden sm:flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5 text-[11px]">
              <button
                type="button"
                title="Visualização Unificada"
                onClick={() => setDiffLayout('unified')}
                className={cn(
                  'flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors cursor-pointer',
                  diffLayout === 'unified'
                    ? 'bg-slate-700/60 text-slate-100 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                <AlignJustify className="h-3 w-3" />
                <span className="hidden md:inline">Unificado</span>
              </button>
              <button
                type="button"
                title="Visualização Lado a Lado (Split)"
                onClick={() => setDiffLayout('split')}
                className={cn(
                  'flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors cursor-pointer',
                  diffLayout === 'split'
                    ? 'bg-slate-700/60 text-slate-100 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                <Columns className="h-3 w-3" />
                <span className="hidden md:inline">Split</span>
              </button>
            </div>
          )}

          {/* Botão Copiar */}
          <button
            type="button"
            aria-label="Copiar código ou diff"
            onClick={copy}
            className={cn(
              'flex h-7 items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 text-[11px] font-sans font-medium transition-all hover:bg-slate-800 cursor-pointer',
              copied ? 'text-emerald-400 border-emerald-500/40' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span>Copiado!</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copiar</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Body — Pierre Diffs Container com Shiki Highlighting e Virtualização */}
      <div
        className={cn(
          'overflow-auto font-mono text-[12px] leading-[1.65] text-slate-300 w-full min-w-0 bg-[#0c1222]',
          fullHeight ? 'flex-1 h-full min-h-0 max-h-none py-0' : 'max-h-[520px] py-1'
        )}
      >
        <PierreErrorBoundary
          fallback={
            <div className="p-4 font-mono text-xs text-slate-400">
              <pre className="overflow-x-auto whitespace-pre-wrap">{displayCode || unifiedPatch}</pre>
            </div>
          }
        >
          {activeVariant === 'Diff' && (unifiedPatch || (effectiveOldCode && effectiveNewCode)) ? (
            effectiveOldCode && effectiveNewCode && effectiveOldCode.trim() !== effectiveNewCode.trim() ? (
              <MultiFileDiff
                oldFile={{ name: filename, contents: effectiveOldCode }}
                newFile={{ name: filename, contents: effectiveNewCode }}
                className={fullHeight ? 'h-full flex-1' : undefined}
                style={fullHeight ? { height: '100%' } : undefined}
                options={{
                  theme: 'pierre-dark',
                  diffStyle: diffLayout,
                  overflow: 'scroll',
                  disableFileHeader: true,
                }}
              />
            ) : (
              <PatchDiff
                patch={unifiedPatch}
                className={fullHeight ? 'h-full flex-1' : undefined}
                style={fullHeight ? { height: '100%' } : undefined}
                options={{
                  theme: 'pierre-dark',
                  diffStyle: diffLayout,
                  overflow: 'scroll',
                  disableFileHeader: true,
                }}
              />
            )
          ) : (
            <File
              file={{ name: filename, contents: displayCode }}
              className={fullHeight ? 'h-full flex-1' : undefined}
              style={fullHeight ? { height: '100%' } : undefined}
              options={{
                theme: 'pierre-dark',
                overflow: 'scroll',
                disableFileHeader: true,
              }}
            />
          )}
        </PierreErrorBoundary>
      </div>
    </div>
  );
}

export default CodeBlock;
