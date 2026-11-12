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
  ExternalLink,
  Globe,
  Code2,
  Eye,
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
  filename = '',
  code = '',
  isOptimizing = false,
  diffInfo,
  className,
}: SideCodePanelProps) {
  const [copied, setCopied] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [fetchedDiff, setFetchedDiff] = useState<DiffInfo | undefined>(undefined);
  const isHtml = filename.toLowerCase().endsWith('.html');
  const [htmlViewMode, setHtmlViewMode] = useState<'preview' | 'code'>('preview');

  // Limpa diff cacheado ao alternar de arquivo
  useEffect(() => {
    setFetchedDiff(undefined);
    if (isHtml) setHtmlViewMode('preview');
  }, [filename, isHtml]);

  // Busca diff sob demanda se não tiver sido injetado via prop
  useEffect(() => {
    if (!isOpen || !filename || diffInfo) {
      if (diffInfo) setFetchedDiff(undefined);
      return;
    }
    fetch(`/api/dados/diff?caminho=${encodeURIComponent(filename)}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && (data.adicoes > 0 || data.remocoes > 0) && (data.linhas?.length > 0 || (data.raw_diff && data.raw_diff.trim().length > 0))) {
          setFetchedDiff(data);
        } else {
          setFetchedDiff(undefined);
        }
      })
      .catch(() => {
        setFetchedDiff(undefined);
      });
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
          <div className={cn(
            'flex h-7 w-7 items-center justify-center rounded-lg shadow-2xs',
            isHtml ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
          )}>
            {isHtml ? <Globe className="h-4 w-4" /> : <FileCode2 className="h-4 w-4" />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 truncate">
              <span className="font-bold text-slate-900 truncate">{filename}</span>
              {isOptimizing ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 animate-pulse">
                  <RefreshCw className="h-2.5 w-2.5 animate-spin" /> Otimizando...
                </span>
              ) : isHtml ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-semibold text-purple-800">
                  Relatório HTML
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
          {/* Alternador de visualização para arquivos HTML (Dashboard vs Código) */}
          {isHtml && (
            <div className="flex items-center rounded-lg border border-slate-200 bg-white p-0.5 mr-1 shadow-2xs">
              <button
                type="button"
                onClick={() => setHtmlViewMode('preview')}
                className={cn(
                  'flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer',
                  htmlViewMode === 'preview'
                    ? 'bg-purple-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                )}
                title="Visualizar Dashboard Interativo"
              >
                <Eye className="h-3 w-3" />
                <span>Dashboard</span>
              </button>
              <button
                type="button"
                onClick={() => setHtmlViewMode('code')}
                className={cn(
                  'flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer',
                  htmlViewMode === 'code'
                    ? 'bg-purple-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                )}
                title="Ver Código HTML"
              >
                <Code2 className="h-3 w-3" />
                <span>Código</span>
              </button>
            </div>
          )}

          {/* Abrir em nova aba caso seja HTML */}
          {isHtml && (
            <a
              href={`/api/dados/documento?caminho=krakenlake/workspace/${filename}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex h-7 w-7 items-center justify-center rounded-lg hover:bg-slate-200/60 hover:text-slate-800 transition-colors cursor-pointer"
              title="Abrir Dashboard em Nova Aba"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}

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

      {/* Code / Diff / HTML Body */}
      <div className="flex-1 overflow-hidden bg-[#0c1222] flex flex-col min-h-0">
        {isHtml && htmlViewMode === 'preview' ? (
          <div className="flex-1 w-full h-full bg-white relative flex flex-col min-h-0">
            <iframe
              srcDoc={code && code.trim().length > 0 ? code : undefined}
              src={!code || code.trim().length === 0 ? `/api/dados/documento?caminho=${encodeURIComponent(filename.startsWith('krakenlake/') ? filename : 'krakenlake/workspace/' + filename)}` : undefined}
              title={filename}
              className="w-full h-full flex-1 border-none bg-white"
              sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
            />
          </div>
        ) : code.trim().length > 0 || (effectiveDiff && (effectiveDiff.adicoes > 0 || effectiveDiff.remocoes > 0 || (effectiveDiff.raw_diff && effectiveDiff.raw_diff.trim().length > 0))) ? (
          <CodeBlock
            code={code || effectiveDiff?.proposed_code}
            oldCode={effectiveDiff?.original_code}
            rawDiff={effectiveDiff?.raw_diff}
            diffInfo={effectiveDiff}
            language={isHtml ? 'html' : 'python'}
            filename={filename}
            isDiff={Boolean(effectiveDiff && (effectiveDiff.adicoes > 0 || effectiveDiff.remocoes > 0 || (effectiveDiff.raw_diff && effectiveDiff.raw_diff.trim().length > 0)))}
            fullHeight={true}
            className="h-full flex flex-col my-0 rounded-none border-none shadow-none flex-1"
          />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center text-center text-xs text-slate-400 gap-2 p-6">
            <FileCode2 className="h-8 w-8 text-slate-600" />
            <p className="font-semibold text-slate-300">
              {filename ? `${filename} está vazio (0 linhas)` : 'Nenhum script selecionado'}
            </p>
            <p className="max-w-xs text-slate-500">
              {filename
                ? 'Este arquivo no workspace ainda não possui código. Solicite ao Kraken Copilot para gerar ou otimizar seu pipeline aqui.'
                : 'Selecione um script do workspace para acompanhar em tempo real.'}
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}

export default SideCodePanel;
