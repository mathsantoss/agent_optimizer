import React from 'react';
import { BarChart3, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { CodeBlock } from './CodeBlock';
import { RecordsTable } from './RecordsTable';
import { MermaidBlock } from './MermaidBlock';
import { GraphyChart } from './GraphyChart';
import { StructuredResultCard } from './structured/StructuredResultCard';

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

  // Normaliza quebras de linha e converte blocos ::: mermaid em ```mermaid
  const normalizedContent = content
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/:::\s*mermaid([\s\S]*?):::/gi, '```mermaid$1```');

  // Parse markdown code blocks, tables, and paragraphs
  const renderFormattedMarkdown = (rawText: string) => {
    // 1. Quebra blocos de código ```
    const codeParts = rawText.split(/(```[\s\S]*?```)/g);

    return codeParts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const firstLineEnd = part.indexOf('\n');
        const lang = (firstLineEnd !== -1 ? part.slice(3, firstLineEnd) : '').trim().toLowerCase() || 'python';
        const code = firstLineEnd !== -1 ? part.slice(firstLineEnd + 1, -3) : part.slice(3, -3);

        if (lang === 'mermaid' || code.trim().startsWith('flowchart') || code.trim().startsWith('sequenceDiagram') || code.trim().startsWith('graph ')) {
          return <MermaidBlock key={index} chart={code} />;
        }

        if (lang === 'chart' || lang === 'graphy') {
          try {
            const parsed = JSON.parse(code.trim());
            // Suporte a multi-chart dashboard: array de gráficos ou { charts: [...] }
            const chartList = Array.isArray(parsed)
              ? parsed
              : Array.isArray(parsed.charts)
              ? parsed.charts
              : [parsed];

            const validCharts = chartList.filter(
              (c: any) => c && Array.isArray(c.data) && c.x && c.y
            );

            if (validCharts.length > 1) {
              return (
                <div key={index} className="my-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                  {validCharts.map((chartItem: any, cIdx: number) => (
                    <GraphyChart
                      key={cIdx}
                      type={chartItem.type || 'bar'}
                      title={chartItem.title}
                      subtitle={chartItem.subtitle}
                      data={chartItem.data}
                      x={chartItem.x}
                      y={chartItem.y}
                      height={270}
                    />
                  ))}
                </div>
              );
            } else if (validCharts.length === 1) {
              const chartData = validCharts[0];
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
            // Em caso de streaming incompleto ou JSON malformado, segue como CodeBlock
          }
        }

        if (lang === 'json') {
          try {
            const parsed = JSON.parse(code.trim());
            if (
              parsed.kraken_benchmark ||
              parsed.kraken_data_profile ||
              parsed.kraken_code_diff ||
              parsed.kraken_statistical_report ||
              (parsed.tempo_execucao_otimizado !== undefined && parsed.speedup !== undefined) ||
              (parsed.dataset_nome && parsed.colunas && parsed.tamanho_kb !== undefined) ||
              (parsed.total_linhas_analisadas && parsed.metricas_colunas)
            ) {
              return <StructuredResultCard key={index} data={parsed} />;
            }
          } catch (e) {
            // fallback
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
        const trimmed = line.trim();

        // Detecta início de tabela separada por tabs (\t)
        const isTabLine = trimmed.includes('\t') && trimmed.split('\t').filter(Boolean).length >= 3;
        if (isTabLine) {
          const tabLines: string[][] = [];
          while (i < lines.length && lines[i].trim().includes('\t')) {
            const cols = lines[i].trim().split('\t').map((c) => c.trim()).filter(Boolean);
            if (cols.length >= 2) {
              tabLines.push(cols);
            }
            i++;
          }
          if (tabLines.length > 0) {
            const maxCols = Math.max(...tabLines.map((r) => r.length));
            let headerCells: string[] = [];
            let dataRows = tabLines;

            // Se o primeiro item da linha 0 é um nome de coluna e o segundo é número, cria cabeçalho estatístico padrão
            const isStatRow = tabLines[0].length >= 5 && !isNaN(parseFloat(tabLines[0][1]));
            if (isStatRow) {
              headerCells = ['Variável / Coluna', 'Média', 'Desvio', 'Mínimo', '25%', 'Mediana', '75%', 'Máximo', 'Nulos', 'Outliers'].slice(0, maxCols);
            } else {
              headerCells = tabLines[0];
              dataRows = tabLines.slice(1);
            }

            renderedElements.push(
              <div key={`tabtbl-${index}-${i}`} className="my-3.5 overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-2xs">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50/80 border-b border-slate-200/80">
                        {headerCells.map((h, hIdx) => (
                          <th key={hIdx} className="px-4 py-2.5 text-[11px] font-bold text-slate-700 tracking-tight">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {dataRows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-slate-50/50 transition-colors">
                          {headerCells.map((_, cIdx) => (
                            <td key={cIdx} className={cn('px-4 py-2 text-xs leading-normal', cIdx === 0 ? 'font-medium text-slate-900' : 'font-mono text-[11.5px]')}>
                              {row[cIdx] ?? '—'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
            continue;
          }
        }

        // Detecta início de tabela markdown (| col1 | col2 | ...)
        const isPipeLine = trimmed.startsWith('|') && trimmed.endsWith('|');
        const nextTrimmed = i + 1 < lines.length ? lines[i + 1].trim() : '';
        const hasSepNext = nextTrimmed.startsWith('|') && /^\|[\s:\-|]+\|$/.test(nextTrimmed);
        const nextIsPipe = nextTrimmed.startsWith('|') && nextTrimmed.endsWith('|');

        if (isPipeLine && (hasSepNext || nextIsPipe)) {
          const headerCells = trimmed
            .split('|')
            .map((c) => c.trim())
            .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

          i += hasSepNext ? 2 : 1; // pula header e separador se presente
          const tableRows: Record<string, any>[] = [];

          while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
            const rowTrim = lines[i].trim();
            // Pula separador intermediário se existir
            if (/^\|[\s:\-|]+\|$/.test(rowTrim)) {
              i++;
              continue;
            }

            const cells = rowTrim
              .split('|')
              .map((c) => c.trim())
              .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

            const rowObj: Record<string, any> = {};
            headerCells.forEach((h, hIdx) => {
              rowObj[h || `col_${hIdx + 1}`] = cells[hIdx] ?? '';
            });
            tableRows.push(rowObj);
            i++;
          }

          if (headerCells.length > 0) {
            const isBenchmark =
              headerCells.some((h) => /métrica|baseline|depois|variação|speedup/i.test(h)) ||
              tableRows.some((r) =>
                Object.values(r).some((v) =>
                  /tempo de execução|pico de memória|equivalência/i.test(String(v))
                )
              );

            renderedElements.push(
              <div
                key={`tbl-${index}-${i}`}
                className={cn(
                  'my-3.5 overflow-hidden rounded-2xl border shadow-2xs',
                  isBenchmark ? 'border-blue-200/90 bg-white' : 'border-slate-200/90 bg-white'
                )}
              >
                {isBenchmark && (
                  <div className="flex items-center justify-between border-b border-blue-100 bg-gradient-to-r from-blue-50/80 via-white to-blue-50/40 px-4 py-2.5 text-xs font-bold text-blue-950">
                    <span className="flex items-center gap-1.5">
                      <BarChart3 className="h-4 w-4 text-blue-600 shrink-0" />
                      <span>Benchmark Comparativo de Performance (Antes vs Depois)</span>
                    </span>
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-800">
                      Vetorizado
                    </span>
                  </div>
                )}

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className={isBenchmark ? 'bg-slate-50/80 border-b border-slate-100' : 'bg-slate-50/70 border-b border-slate-200/80'}>
                        {headerCells.map((h, hIdx) => (
                          <th
                            key={hIdx}
                            className="px-4 py-2.5 text-[11px] font-bold text-slate-700 tracking-tight select-none"
                          >
                            {formatInline(h)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {tableRows.map((row, rIdx) => (
                        <tr
                          key={rIdx}
                          className="hover:bg-slate-50/50 transition-colors"
                        >
                          {headerCells.map((h, cIdx) => {
                            const val = String(row[h] ?? '');
                            const isSpeedup =
                              val.includes('%') ||
                              val.toLowerCase().includes('aprovada') ||
                              val.toLowerCase().includes('aprovado');
                            const isPositiveGain =
                              val.includes('+') || val.toLowerCase().includes('aprovad');

                            return (
                              <td
                                key={cIdx}
                                className={cn(
                                  'px-4 py-2.5 text-xs leading-normal',
                                  cIdx === 0 && headerCells.length > 3
                                    ? 'font-medium text-slate-900'
                                    : '',
                                  cIdx >= 1 && cIdx <= 3 && isBenchmark
                                    ? 'font-mono text-[11.5px]'
                                    : ''
                                )}
                              >
                                {isBenchmark && isSpeedup ? (
                                  <span
                                    className={cn(
                                      'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-bold font-mono',
                                      isPositiveGain
                                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                        : 'bg-slate-100 text-slate-700'
                                    )}
                                  >
                                    {isPositiveGain && <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0 inline" />}
                                    {val.replace(/\*\*/g, '')}
                                  </span>
                                ) : (
                                  formatInline(val)
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          }
          continue;
        }

        // Renderiza linha padrão
        if (!trimmed) {
          renderedElements.push(<div key={`empty-${index}-${i}`} className="h-2" />);
        } else if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
          renderedElements.push(
            <hr key={`hr-${index}-${i}`} className="my-4 border-t border-slate-200/80" />
          );
        } else if (trimmed.startsWith('#### ')) {
          renderedElements.push(
            <h5 key={`h5-${index}-${i}`} className="mt-3 text-xs font-bold text-slate-900 tracking-tight">
              {formatInline(trimmed.slice(5))}
            </h5>
          );
        } else if (trimmed.startsWith('### ')) {
          renderedElements.push(
            <h4 key={`h4-${index}-${i}`} className="mt-3.5 text-sm font-bold text-slate-900 tracking-tight">
              {formatInline(trimmed.slice(4))}
            </h4>
          );
        } else if (trimmed.startsWith('## ')) {
          renderedElements.push(
            <h3 key={`h3-${index}-${i}`} className="mt-4 text-base font-bold text-slate-900 tracking-tight flex items-center gap-1.5">
              {formatInline(trimmed.slice(3))}
            </h3>
          );
        } else if (trimmed.startsWith('# ')) {
          renderedElements.push(
            <h2 key={`h2-${index}-${i}`} className="mt-4.5 text-lg font-bold text-slate-900 tracking-tight">
              {formatInline(trimmed.slice(2))}
            </h2>
          );
        } else if (trimmed.startsWith('> ')) {
          renderedElements.push(
            <blockquote
              key={`quote-${index}-${i}`}
              className="my-3 border-l-3 border-blue-500 bg-blue-50/40 pl-3.5 py-2 text-xs text-slate-700 leading-relaxed rounded-r-xl"
            >
              {formatInline(trimmed.slice(2))}
            </blockquote>
          );
        } else if (/^!\[(.*?)\]\((.*?)\)$/.test(trimmed)) {
          const match = trimmed.match(/^!\[(.*?)\]\((.*?)\)$/);
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
        } else if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          const bulletText = trimmed.replace(/^[•\-*]\s+/, '');
          renderedElements.push(
            <div key={`li-${index}-${i}`} className="flex items-start gap-2 text-xs text-slate-800 leading-relaxed pl-1 py-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
              <div className="flex-1 min-w-0">{formatInline(bulletText)}</div>
            </div>
          );
        } else if (/^\d+\.\s+/.test(trimmed)) {
          const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
          const num = numMatch ? numMatch[1] : '1';
          const numText = numMatch ? numMatch[2] : trimmed;
          renderedElements.push(
            <div key={`ol-${index}-${i}`} className="flex items-start gap-2 text-xs text-slate-800 leading-relaxed pl-1 py-0.5">
              <span className="font-mono text-[11px] font-semibold text-slate-500 shrink-0 w-4 text-right">{num}.</span>
              <div className="flex-1 min-w-0">{formatInline(numText)}</div>
            </div>
          );
        } else {
          renderedElements.push(
            <p key={`p-${index}-${i}`} className="text-xs text-slate-800 leading-relaxed">
              {formatInline(trimmed)}
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
            className="rounded-md bg-slate-100 border border-slate-200/80 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-slate-800"
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
      {renderFormattedMarkdown(normalizedContent)}
      {isStreaming && (
        <span className="inline-block h-3.5 w-1.5 animate-pulse rounded-xs bg-blue-600 align-middle ml-1" />
      )}
    </div>
  );
}

export default StreamingText;
