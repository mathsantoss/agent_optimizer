import React, { useState } from 'react';
import { Copy, Check, FileCode, Terminal } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  className?: string;
  isDiff?: boolean;
}

export function CodeBlock({
  code,
  language = 'python',
  filename,
  className,
  isDiff = false,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const lines = code.split('\n');

  return (
    <div
      className={cn(
        'my-3 overflow-hidden rounded-xl border border-slate-200 bg-[#0f172a] text-slate-100 shadow-sm font-mono text-xs',
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-slate-800 bg-[#090d16] px-3.5 py-2 text-[11px] text-slate-400 select-none">
        <div className="flex items-center gap-2">
          {isDiff ? (
            <Terminal className="h-3.5 w-3.5 text-blue-400" />
          ) : (
            <FileCode className="h-3.5 w-3.5 text-slate-400" />
          )}
          <span className="font-medium text-slate-300">
            {filename || (isDiff ? 'Unified Diff' : language)}
          </span>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] text-slate-300 transition-colors hover:bg-slate-800 hover:text-white"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400 font-sans">Copiado!</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span className="font-sans">Copiar</span>
            </>
          )}
        </button>
      </div>

      <div className="max-h-[460px] overflow-x-auto overflow-y-auto p-3 text-[11px] leading-relaxed">
        {lines.map((line, idx) => {
          let lineBg = '';
          let textStyle = 'text-slate-200';
          let prefix = '';

          if (isDiff || line.startsWith('+') || line.startsWith('-')) {
            if (line.startsWith('+')) {
              lineBg = 'bg-emerald-950/40 text-emerald-300';
              textStyle = 'text-emerald-300';
            } else if (line.startsWith('-')) {
              lineBg = 'bg-rose-950/40 text-rose-300';
              textStyle = 'text-rose-300';
            } else if (line.startsWith('@@')) {
              lineBg = 'bg-blue-950/30 text-blue-300';
              textStyle = 'text-blue-300';
            }
          }

          return (
            <div key={idx} className={cn('flex items-start gap-3 px-1 py-0.5 rounded-sm', lineBg)}>
              <span className="w-8 shrink-0 select-none text-right text-[10px] text-slate-600">
                {idx + 1}
              </span>
              <span className={cn('whitespace-pre font-mono flex-1', textStyle)}>{line}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default CodeBlock;

