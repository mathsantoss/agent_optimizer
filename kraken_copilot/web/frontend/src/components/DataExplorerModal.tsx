import React, { useState, useEffect } from 'react';
import {
  X,
  Database,
  FileSpreadsheet,
  FileText,
  Search,
  Table as TableIcon,
  RefreshCw,
  Play,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { RecordsTable } from './RecordsTable';

export interface DataExplorerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSendSqlToChat?: (sql: string) => void;
}

export function DataExplorerModal({
  isOpen,
  onClose,
  onSendSqlToChat,
}: DataExplorerModalProps) {
  const [arquivos, setArquivos] = useState<string[]>([]);
  const [arquivoAtivo, setArquivoAtivo] = useState<string>('');
  const [conteudo, setConteudo] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [abaAtiva, setAbaAtiva] = useState<'preview' | 'schema' | 'sql' | 'pdf'>('preview');
  const [sqlQuery, setSqlQuery] = useState('SELECT * FROM telecom LIMIT 10;');

  useEffect(() => {
    if (isOpen) {
      carregarArquivos();
    }
  }, [isOpen]);

  const carregarArquivos = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/dados/arquivos');
      const data = await res.json();
      const list = data.arquivos || [];
      setArquivos(list);
      if (list.length > 0 && !arquivoAtivo) {
        selecionarArquivo(list[0]);
      }
    } catch (err) {
      console.error('Erro ao listar arquivos de dados:', err);
    } finally {
      setLoading(false);
    }
  };

  const selecionarArquivo = async (nomeArquivo: string) => {
    setArquivoAtivo(nomeArquivo);
    if (nomeArquivo.endsWith('.pdf')) {
      setAbaAtiva('pdf');
      return;
    }
    try {
      setLoading(true);
      const res = await fetch(`/api/dados/conteudo/${nomeArquivo}`);
      const data = await res.json();
      setConteudo(data);
    } catch (err) {
      console.error('Erro ao carregar conteúdo:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
      <div className="flex h-[88vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        {/* Header do Modal */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5 bg-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100 text-purple-700">
              <Database className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                Explorador de Dados e Documentos
              </h3>
              <p className="text-[11px] text-slate-500">
                Consulte schemas, tabelas e manuais de dados do Kraken Copilot
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Corpo: Lista Lateral de Arquivos + Conteúdo */}
        <div className="flex flex-1 overflow-hidden">
          {/* Coluna Lateral de Arquivos */}
          <div className="w-64 border-r border-slate-200 bg-slate-50/50 p-3 overflow-y-auto">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Conjuntos de Dados
            </div>
            <div className="space-y-1">
              {arquivos.map((arq) => {
                const isSelected = arq === arquivoAtivo;
                const isPdf = arq.endsWith('.pdf');
                return (
                  <button
                    key={arq}
                    type="button"
                    onClick={() => selecionarArquivo(arq)}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition-colors',
                      isSelected
                        ? 'bg-purple-50 font-semibold text-purple-900 shadow-2xs'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    )}
                  >
                    {isPdf ? (
                      <FileText className="h-3.5 w-3.5 text-rose-500 shrink-0" />
                    ) : (
                      <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    )}
                    <span className="truncate">{arq}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Área Principal de Abas & Visualização */}
          <div className="flex flex-1 flex-col overflow-hidden bg-white">
            {/* Barra de Abas */}
            <div className="flex items-center gap-1 border-b border-slate-200 px-4 pt-2 text-xs font-medium">
              <button
                type="button"
                onClick={() => setAbaAtiva('preview')}
                className={cn(
                  'rounded-t-lg border-b-2 px-3 py-2 transition-colors',
                  abaAtiva === 'preview'
                    ? 'border-purple-600 text-purple-900 font-semibold'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                )}
              >
                Tabela / Preview
              </button>
              <button
                type="button"
                onClick={() => setAbaAtiva('schema')}
                className={cn(
                  'rounded-t-lg border-b-2 px-3 py-2 transition-colors',
                  abaAtiva === 'schema'
                    ? 'border-purple-600 text-purple-900 font-semibold'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                )}
              >
                Esquema / Colunas
              </button>
              <button
                type="button"
                onClick={() => setAbaAtiva('sql')}
                className={cn(
                  'rounded-t-lg border-b-2 px-3 py-2 transition-colors',
                  abaAtiva === 'sql'
                    ? 'border-purple-600 text-purple-900 font-semibold'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                )}
              >
                Consulta SQL
              </button>
              {arquivoAtivo.endsWith('.pdf') && (
                <button
                  type="button"
                  onClick={() => setAbaAtiva('pdf')}
                  className={cn(
                    'rounded-t-lg border-b-2 px-3 py-2 transition-colors',
                    abaAtiva === 'pdf'
                      ? 'border-purple-600 text-purple-900 font-semibold'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  )}
                >
                  Visualizador PDF
                </button>
              )}
            </div>

            {/* Conteúdo da Aba */}
            <div className="flex-1 overflow-auto p-4">
              {loading ? (
                <div className="flex h-64 items-center justify-center text-xs text-slate-400 gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin text-purple-600" />
                  <span>Carregando dados...</span>
                </div>
              ) : abaAtiva === 'pdf' ? (
                <div className="h-full w-full rounded-xl border border-slate-200 overflow-hidden">
                  <iframe
                    src={`/api/dados/conteudo/${arquivoAtivo}`}
                    className="h-full w-full"
                    title="Documento PDF"
                  />
                </div>
              ) : abaAtiva === 'schema' && conteudo?.colunas ? (
                <div className="space-y-3">
                  <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
                    <p className="font-semibold">Resumo do Arquivo:</p>
                    <p className="mt-1 text-slate-600">
                      Total de linhas: <strong>{conteudo.total_linhas?.toLocaleString() || '—'}</strong> |
                      Total de colunas: <strong>{conteudo.colunas?.length || 0}</strong>
                    </p>
                  </div>
                  <RecordsTable
                    columns={['coluna', 'tipo', 'nulos']}
                    data={conteudo.colunas.map((col: any) => ({
                      coluna: col.nome || col,
                      tipo: col.tipo || 'unknown',
                      nulos: col.nulos ?? 0,
                    }))}
                    title={`Estrutura de Colunas (${arquivoAtivo})`}
                  />
                </div>
              ) : abaAtiva === 'sql' ? (
                <div className="space-y-3">
                  <p className="text-xs text-slate-600">
                    Escreva sua consulta SQL e envie diretamente para o Kraken Copilot executar no SQLite:
                  </p>
                  <textarea
                    value={sqlQuery}
                    onChange={(e) => setSqlQuery(e.target.value)}
                    rows={4}
                    className="w-full rounded-xl border border-slate-300 p-3 font-mono text-xs text-slate-800 focus:border-purple-500 focus:outline-hidden"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (onSendSqlToChat) {
                        onSendSqlToChat(`Execute a seguinte consulta SQL: ${sqlQuery}`);
                        onClose();
                      }
                    }}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-purple-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-700"
                  >
                    <Play className="h-3.5 w-3.5" />
                    <span>Executar Consulta no Chat</span>
                  </button>
                </div>
              ) : conteudo?.linhas ? (
                <RecordsTable
                  columns={conteudo.colunas?.map((c: any) => c.nome || c) || Object.keys(conteudo.linhas[0] || {})}
                  data={conteudo.linhas}
                  title={`Amostra de Registros (${arquivoAtivo})`}
                />
              ) : (
                <div className="flex h-64 items-center justify-center text-xs text-slate-400">
                  Selecione um arquivo de dados para visualizar.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DataExplorerModal;

