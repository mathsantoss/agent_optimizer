import React, { useState, useEffect, useMemo } from 'react';
import {
  FileCode2,
  X,
  Maximize2,
  Minimize2,
  Sparkles,
  Check,
  RefreshCw,
  Copy,
  GitCompare,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { CodeBlock, DiffRow } from './CodeBlock';
import { DiffInfo } from './ToolChips';

export interface SideCodePanelProps {
  isOpen: boolean;
  onClose: () => void;
  filename?: string;
  code?: string;
  isOptimizing?: boolean;
  diffInfo?: DiffInfo;
  className?: string;
}

export function SideCodePanel({
  isOpen,
  onClose,
  filename = 'pipeline_prep.py',
  code = '',
  isOptimizing = false,
  diffInfo,
  className,
}: SideCodePanelProps) {
  const [copied, setCopied] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [fetchedDiff, setFetchedDiff] = useState<DiffInfo | undefined>(undefined);

  // Busca diff sob demanda se não tiver sido injetado via prop
  useEffect(() => {
    if (isOpen && filename && !diffInfo) {
      fetch(`/api/dados/diff?caminho=${encodeURIComponent(filename)}`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data && (data.linhas?.length > 0 || data.raw_diff)) {
            setFetchedDiff(data);
          }
        })
        .catch(() => {});
    }
  }, [isOpen, filename, diffInfo, code]);

  const effectiveDiff = diffInfo || fetchedDiff;

  // Converte linhas de diff da API em DiffRow[] compatível com o CodeBlock
  const convertedDiffRows: DiffRow[] = useMemo(() => {
    if (!effectiveDiff || !effectiveDiff.linhas) return [];
    let oldCounter = 1;
    let curCounter = 1;

    return effectiveDiff.linhas.map((row) => {
      const type = row.tipo === 'add' ? 'add' : row.tipo === 'del' ? 'del' : 'ctx';
      const cleanText = row.texto.replace(/^[+-]/, '');
      const oldNum = type === 'add' ? null : oldCounter++;
      const curNum = type === 'del' ? null : curCounter++;

      return {
        old: oldNum,
        cur: curNum,
        type,
        pieces: [
          {
            text: cleanText,
            change: type === 'add' ? 'add' : type === 'del' ? 'del' : undefined,
          },
        ],
      };
    });
  }, [effectiveDiff]);

  if (!isOpen) return null;

  const handleCopy = () => {
    if (code) {
      navigator.clipboard.writeText(code).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  return (
    <aside
      aria-label="Side Bar Code Inspector"
      className={cn(
        'flex flex-col border-l border-slate-200/90 bg-white transition-all duration-200 z-30 shadow-xl select-none',
        isMaximized
          ? 'fixed inset-0 z-50 w-screen h-screen'
          : 'w-full md:w-[48vw] lg:w-[50vw] xl:w-[52vw] min-w-[360px] max-w-[960px] h-full',
        className
      )}
    >
      {/* Top Header */}
      <div className="flex h-14 items-center justify-between border-b border-slate-100 bg-slate-50/80 px-4 text-xs select-none shrink-0">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-100 text-blue-700 shadow-2xs">
            <FileCode2 className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 truncate">
              <span className="font-bold text-slate-900 truncate">{filename}</span>
              {isOptimizing ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 animate-pulse">
                  <RefreshCw className="h-2.5 w-2.5 animate-spin" /> Otimizando...
                </span>
              ) : effectiveDiff && (effectiveDiff.adicoes > 0 || effectiveDiff.remocoes > 0) ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
                  <GitCompare className="h-2.5 w-2.5" /> +{effectiveDiff.adicoes} / -{effectiveDiff.remocoes}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                  Workspace
                </span>
              )}
            </div>
            <div className="truncate text-[10.5px] text-slate-400 font-mono">
              krakenlake/workspace/{filename}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 text-slate-500">
          <button
            type="button"
            onClick={handleCopy}
            className="flex h-7 w-7 items-center justify-center rounded-lg hover:bg-slate-200/60 hover:text-slate-800 transition-colors cursor-pointer"
            title="Copiar código"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
          </button>

          <button
            type="button"
            onClick={() => setIsMaximized(!isMaximized)}
            className="hidden md:flex h-7 w-7 items-center justify-center rounded-lg hover:bg-slate-200/60 hover:text-slate-800 transition-colors cursor-pointer"
            title={isMaximized ? 'Restaurar tamanho' : 'Maximizar tela inteira'}
          >
            {isMaximized ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>

          <button
            type="button"
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-lg hover:bg-slate-200/60 hover:text-slate-800 transition-colors cursor-pointer"
            title="Fechar painel de código"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Live Stream / Progress Banner */}
      {isOptimizing && (
        <div className="flex items-center gap-2 border-b border-blue-100 bg-blue-50/80 px-4 py-2 text-[11px] text-blue-800 shrink-0">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600"></span>
          </span>
          <span className="font-medium">
            Agente Otimizador processando transformações vetorizadas...
          </span>
        </div>
      )}

      {/* Code / Diff Body — Ocupa 100% da altura e largura sem margens inúteis */}
      <div className="flex-1 overflow-hidden bg-[#0c1222] flex flex-col min-h-0">
        {code || effectiveDiff ? (
          <CodeBlock
            code={code || effectiveDiff?.proposed_code}
            oldCode={effectiveDiff?.original_code}
            rawDiff={effectiveDiff?.raw_diff}
            diffInfo={effectiveDiff}
            language="python"
            filename={filename}
            isDiff={Boolean(effectiveDiff && (effectiveDiff.adicoes > 0 || effectiveDiff.remocoes > 0 || effectiveDiff.raw_diff))}
            fullHeight={true}
            className="h-full flex flex-col my-0 rounded-none border-none shadow-none flex-1"
          />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center text-center text-xs text-slate-400 gap-2 p-6">
            <FileCode2 className="h-8 w-8 text-slate-600" />
            <p className="font-semibold text-slate-300">Nenhum código para inspecionar no momento</p>
            <p className="max-w-xs text-slate-500">
              Inicie uma otimização ou selecione um script do workspace para acompanhar em tempo real.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}

export default SideCodePanel;
