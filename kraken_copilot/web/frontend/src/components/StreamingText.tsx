import React from 'react';
import { cn } from '@/lib/utils';
import { CodeBlock } from './CodeBlock';
import { RecordsTable } from './RecordsTable';
import { MermaidBlock } from './MermaidBlock';
import { GraphyChart } from './GraphyChart';

export interface StreamingTextProps {
  content: string;
  isStreaming?: boolean;
  className?: string;
}

export function StreamingText({ content, isStreaming = false, className }: StreamingTextProps) {
  if (!content) {
    if (isStreaming) {
      return (
        <span className="inline-flex items-center gap-1 text-slate-400">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.3s]"></span>
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.15s]"></span>
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-500"></span>
        </span>
      );
    }
    return null;
  }

  // Parse markdown code blocks, tables, and paragraphs
  const renderFormattedMarkdown = (rawText: string) => {
    // 1. Quebra blocos de código ```
    const codeParts = rawText.split(/(```[\s\S]*?```)/g);

    return codeParts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const firstLineEnd = part.indexOf('\n');
        const lang = part.slice(3, firstLineEnd).trim().toLowerCase() || 'python';
        const code = part.slice(firstLineEnd + 1, -3);

        if (lang === 'mermaid') {
          return <MermaidBlock key={index} chart={code} />;
        }

        if (lang === 'chart' || lang === 'graphy') {
          try {
            const chartData = JSON.parse(code.trim());
            if (chartData && Array.isArray(chartData.data) && chartData.x && chartData.y) {
              return (
                <GraphyChart
                  key={index}
                  type={chartData.type || 'bar'}
                  title={chartData.title}
                  subtitle={chartData.subtitle}
                  data={chartData.data}
                  x={chartData.x}
                  y={chartData.y}
                />
              );
            }
          } catch (e) {
            // Se ainda está em streaming ou json incompleto, mostra como código json
          }
        }

        const isDiff = lang === 'diff' || code.includes('---') || code.includes('+++');
        return <CodeBlock key={index} code={code} language={lang} isDiff={isDiff} />;
      }

      // 2. Procura e converte tabelas markdown no texto comum
      const lines = part.split('\n');
      const renderedElements: React.ReactNode[] = [];
      let i = 0;

      while (i < lines.length) {
        const line = lines[i];

        // Detecta início de tabela markdown (| col1 | col2 | ...)
        if (
          line.trim().startsWith('|') &&
          line.trim().endsWith('|') &&
          i + 1 < lines.length &&
          /^\|[\s:\-|]+\|$/.test(lines[i + 1].trim())
        ) {
          const headerCells = line
            .split('|')
            .map((c) => c.trim())
            .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

          i += 2; // pula header e separador
          const tableRows: Record<string, any>[] = [];

          while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
            const cells = lines[i]
              .split('|')
              .map((c) => c.trim())
              .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

            const rowObj: Record<string, any> = {};
            headerCells.forEach((h, hIdx) => {
              rowObj[h] = cells[hIdx] ?? '';
            });
            tableRows.push(rowObj);
            i++;
          }

          renderedElements.push(
            <div key={`tbl-${index}-${i}`} className="my-3 overflow-hidden">
              <RecordsTable columns={headerCells} data={tableRows} maxHeight="340px" />
            </div>
          );
          continue;
        }

        // Renderiza linha padrão
        if (!line.trim()) {
          renderedElements.push(<div key={`empty-${index}-${i}`} className="h-2" />);
        } else if (line.startsWith('### ')) {
          renderedElements.push(
            <h4 key={`h4-${index}-${i}`} className="mt-3 text-sm font-bold text-slate-900">
              {formatInline(line.slice(4))}
            </h4>
          );
        } else if (line.startsWith('## ')) {
          renderedElements.push(
            <h3 key={`h3-${index}-${i}`} className="mt-3.5 text-base font-bold text-slate-900">
              {formatInline(line.slice(3))}
            </h3>
          );
        } else if (line.startsWith('# ')) {
          renderedElements.push(
            <h2 key={`h2-${index}-${i}`} className="mt-4 text-lg font-bold text-slate-900">
              {formatInline(line.slice(2))}
            </h2>
          );
        } else if (/^!\[(.*?)\]\((.*?)\)$/.test(line.trim())) {
          const match = line.trim().match(/^!\[(.*?)\]\((.*?)\)$/);
          if (match) {
            const alt = match[1];
            let src = match[2];
            if (!src.startsWith('http') && !src.startsWith('/')) {
              src = `/docs/${src}`;
            }
            renderedElements.push(
              <figure key={`img-${index}-${i}`} className="my-2.5">
                <img
                  src={src}
                  alt={alt}
                  className="max-w-full rounded-xl border border-slate-200 shadow-xs"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
                {alt && <figcaption className="mt-1 text-[11px] text-slate-400 text-center">{alt}</figcaption>}
              </figure>
            );
          }
        } else if (line.startsWith('- ') || line.startsWith('* ')) {
          renderedElements.push(
            <li key={`li-${index}-${i}`} className="ml-4 list-disc text-xs text-slate-700 leading-relaxed">
              {formatInline(line.slice(2))}
            </li>
          );
        } else {
          renderedElements.push(
            <p key={`p-${index}-${i}`} className="text-xs text-slate-700 leading-relaxed">
              {formatInline(line)}
            </p>
          );
        }

        i++;
      }

      return <div key={index} className="space-y-1.5">{renderedElements}</div>;
    });
  };

  // Helper para formatar negrito **, inline code ` e links [texto](url)
  const formatInline = (str: string): React.ReactNode => {
    const tokens = str.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g);
    return tokens.map((token, i) => {
      if (token.startsWith('`') && token.endsWith('`')) {
        return (
          <code
            key={i}
            className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px] font-semibold text-slate-800"
          >
            {token.slice(1, -1)}
          </code>
        );
      }
      if (token.startsWith('**') && token.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-slate-900">
            {token.slice(2, -2)}
          </strong>
        );
      }
      const linkMatch = token.match(/^\[(.*?)\]\((.*?)\)$/);
      if (linkMatch) {
        const linkText = linkMatch[1];
        const linkHref = linkMatch[2];
        return (
          <a
            key={i}
            href={linkHref}
            className="font-medium text-blue-600 underline hover:text-blue-800 transition-colors"
          >
            {linkText}
          </a>
        );
      }
      return token;
    });
  };

  return (
    <div className={cn('relative leading-relaxed', className)}>
      {renderFormattedMarkdown(content)}
      {isStreaming && (
        <span className="inline-block h-3.5 w-1.5 animate-pulse rounded-xs bg-blue-600 align-middle ml-1" />
      )}
    </div>
  );
}

export default StreamingText;
