import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  Search,
  Sparkles,
  RefreshCw,
  ExternalLink,
  Download,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  FileText,
  FileSpreadsheet,
  FileCode,
  FileJson,
  LayoutGrid,
  Code2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { RecordsTable } from './RecordsTable';
import { StreamingText } from './StreamingText';
import { CodeBlock } from './CodeBlock';

export interface DataExplorerViewProps {
  onBackToChat: () => void;
  onSendToChat: (prompt: string) => void;
  className?: string;
}

const SECTIONS_CONFIG: Record<string, { label: string; icon: string }> = {
  DATALAKE: { label: 'DATALAKE', icon: '🗄️' },
  METADADOS: { label: 'METADADOS', icon: '🏷️' },
  OUTPUTS: { label: 'OUTPUTS', icon: '⚡' },
  DOCUMENTAÇÕES: { label: 'DOCUMENTAÇÕES', icon: '📚' },
  WORKSPACE: { label: 'WORKSPACE', icon: '💻' },
};

const SUBCAT_ICONS: Record<string, string> = {
  CSV: '📊',
  JSON: '🗂️',
  PARQUET: '📦',
  MARKDOWN: '📝',
  MD: '📝',
  PDF: '📕',
  PYTHON: '🐍',
  PY: '🐍',
};

// Helper para parsear JSON profundo (evita JSONs escapados com \n e \")
function deepParseJson(val: any): any {
  if (typeof val === 'string') {
    const trimmed = val.trim();
    if (
      (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))
    ) {
      try {
        return deepParseJson(JSON.parse(trimmed));
      } catch {
        return val;
      }
    }
    return val;
  }
  if (Array.isArray(val)) {
    return val.map(deepParseJson);
  }
  if (val && typeof val === 'object') {
    const copy: Record<string, any> = {};
    for (const [k, v] of Object.entries(val)) {
      copy[k] = deepParseJson(v);
    }
    return copy;
  }
  return val;
}

export function DataExplorerView({
  onBackToChat,
  onSendToChat,
  className,
}: DataExplorerViewProps) {
  const [arvore, setArvore] = useState<Record<string, Record<string, any[]>>>({});
  const [arquivos, setArquivos] = useState<any[]>([]);
  const [arquivoAtivo, setArquivoAtivo] = useState<any>(null);
  const [conteudo, setConteudo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadingConteudo, setLoadingConteudo] = useState(false);
  const [buscaArquivo, setBuscaArquivo] = useState('');
  const [copiedJson, setCopiedJson] = useState(false);

  // Modo de visualização de JSON: 'estruturada' ou 'raw' (JSON Nítido)
  const [jsonViewMode, setJsonViewMode] = useState<'estruturada' | 'raw'>('estruturada');

  // Nível 1 (Seções): Aberto por padrão
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    DATALAKE: true,
    METADADOS: true,
    OUTPUTS: true,
    DOCUMENTAÇÕES: true,
    WORKSPACE: true,
  });

  // Nível 2 (Subcategorias): Colapsado por padrão conforme Imagem 1
  const [openSubcats, setOpenSubcats] = useState<Record<string, boolean>>({});

  useEffect(() => {
    carregarArquivos();
  }, []);

  const carregarArquivos = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/dados/arquivos');
      if (res.ok) {
        const json = await res.json();
        const tree = json.arvore || {};
        setArvore(tree);
        const lista = json.arquivos || [];
        setArquivos(lista);

        if (lista.length > 0 && !arquivoAtivo) {
          selecionarArquivo(lista[0]);
        }
      }
    } catch (err) {
      console.error('Erro ao listar arquivos:', err);
    } finally {
      setLoading(false);
    }
  };

  const selecionarArquivo = async (arq: any) => {
    setArquivoAtivo(arq);
    if (arq.tipo === 'pdf') {
      setConteudo({ tipo: 'pdf', caminho: arq.caminho, nome: arq.nome });
      return;
    }
    try {
      setLoadingConteudo(true);
      const res = await fetch(`/api/dados/arquivo?caminho=${encodeURIComponent(arq.caminho)}`);
      if (res.ok) {
        const json = await res.json();
        setConteudo(json);
      }
    } catch (err) {
      console.error('Erro ao ler conteúdo do arquivo:', err);
    } finally {
      setLoadingConteudo(false);
    }
  };

  const toggleSection = (secName: string) => {
    setOpenSections((prev) => ({ ...prev, [secName]: !prev[secName] }));
  };

  const toggleSubcat = (key: string) => {
    setOpenSubcats((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const copyJsonContent = (text: string) => {
    try {
      navigator.clipboard.writeText(text);
      setCopiedJson(true);
      setTimeout(() => setCopiedJson(false), 2000);
    } catch {
      // fallback
    }
  };

  const jsonParsed = deepParseJson(conteudo?.conteudo || conteudo?.dados || conteudo || {});

  return (
    <div className={cn('flex flex-col h-full overflow-hidden bg-[#fafbfd]', className)}>
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-slate-200/90 bg-white px-6 py-3 shadow-2xs select-none">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBackToChat}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-blue-600 transition-all active:scale-98 cursor-pointer"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Voltar ao Chat</span>
          </button>

          <div className="h-4 w-[1px] bg-slate-200" />

          <div className="flex items-center gap-2">
            <span className="text-base">🗂️</span>
            <h2 className="text-sm font-bold text-slate-900">
              Explorador de Dados e Documentos
            </h2>
            <span className="hidden sm:inline-block text-xs text-slate-400">
              (Datalake, Metadados, Workspace e Documentações)
            </span>
          </div>
        </div>

        {arquivoAtivo && (
          <div className="flex items-center gap-2.5">
            {/* Opção de Baixar Arquivo */}
            <a
              href={`/api/dados/download?caminho=${encodeURIComponent(arquivoAtivo.caminho)}`}
              download
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-blue-600 transition-all cursor-pointer"
              title={`Baixar ${arquivoAtivo.nome}`}
            >
              <Download className="h-3.5 w-3.5" />
              <span>Baixar Arquivo</span>
            </a>

            {/* Ação de Perguntar sobre o arquivo */}
            <button
              type="button"
              onClick={() => {
                onSendToChat(`Analise a estrutura e conteúdo do arquivo ${arquivoAtivo.caminho}`);
                onBackToChat();
              }}
              className="inline-flex items-center gap-1.5 rounded-xl bg-purple-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-purple-700 transition-all cursor-pointer"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>Perguntar sobre este arquivo</span>
            </button>
          </div>
        )}
      </div>

      {/* Main Split Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Painel Esquerdo: Arquivos do Projeto (Nível 2 Colapsado por Padrão) */}
        <aside className="w-80 border-r border-slate-200/90 bg-[#f8fafc] p-3.5 flex flex-col overflow-hidden select-none">
          {/* Header da Sidebar */}
          <div className="mb-2.5 flex items-center justify-between px-1">
            <h3 className="text-sm font-bold tracking-tight text-slate-900">
              Arquivos do Projeto
            </h3>
            <button
              type="button"
              onClick={carregarArquivos}
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-200/60 hover:text-slate-700 transition-colors cursor-pointer"
              title="Recarregar arquivos"
            >
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
            </button>
          </div>

          {/* Campo de Busca */}
          <div className="relative mb-3">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              value={buscaArquivo}
              onChange={(e) => setBuscaArquivo(e.target.value)}
              placeholder="Filtrar arquivos..."
              className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-800 placeholder:text-slate-400 focus:border-purple-500 focus:outline-hidden"
            />
          </div>

          {/* Árvore de Arquivos em Níveis */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-12 text-xs text-slate-400 gap-2">
                <RefreshCw className="h-4 w-4 animate-spin text-purple-600" />
                <span>Carregando catálogo de arquivos...</span>
              </div>
            ) : Object.keys(arvore).length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-400">
                Nenhum arquivo encontrado.
              </div>
            ) : (
              Object.entries(arvore).map(([secaoNome, subcategorias]) => {
                const conf = SECTIONS_CONFIG[secaoNome] || { label: secaoNome, icon: '📁' };
                const isSecOpen = openSections[secaoNome] ?? true;

                // Coleta e filtra arquivos da seção
                const subEntries = Object.entries(subcategorias || {});
                let totalSecArquivos = 0;
                subEntries.forEach(([_, items]) => {
                  totalSecArquivos += (items || []).length;
                });

                if (totalSecArquivos === 0) return null;

                return (
                  <div
                    key={secaoNome}
                    className="rounded-xl border border-slate-200/80 bg-white overflow-hidden shadow-2xs"
                  >
                    {/* Nível 1: Cabeçalho da Seção */}
                    <div
                      onClick={() => toggleSection(secaoNome)}
                      className="flex items-center justify-between px-3 py-2 cursor-pointer bg-slate-50/70 hover:bg-slate-100/60 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        {isSecOpen ? (
                          <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
                        )}
                        <span className="text-sm">{conf.icon}</span>
                        <strong className="text-xs font-bold tracking-tight text-slate-800 uppercase">
                          {conf.label}
                        </strong>
                      </div>
                      <span className="rounded-full bg-slate-200/70 px-2 py-0.5 text-[10px] font-bold text-slate-600 uppercase tracking-tight">
                        {totalSecArquivos} {totalSecArquivos === 1 ? 'ARQUIVO' : 'ARQUIVOS'}
                      </span>
                    </div>

                    {/* Nível 2 & 3: Subcategorias e Arquivos */}
                    {isSecOpen && (
                      <div className="p-1 space-y-1 bg-white">
                        {subEntries.map(([subNome, rawItems]) => {
                          const items = (rawItems || []).filter((item: any) =>
                            item.nome.toLowerCase().includes(buscaArquivo.toLowerCase())
                          );
                          if (items.length === 0) return null;

                          const subcatKey = `${secaoNome}/${subNome}`;
                          // Nível 2 colapsado por padrão: false se não definido
                          const isSubOpen = openSubcats[subcatKey] ?? false;
                          const subIcon = SUBCAT_ICONS[subNome.toUpperCase()] || '📁';

                          return (
                            <div key={subNome} className="space-y-0.5">
                              {/* Nível 2: Cabeçalho da Subcategoria */}
                              <div
                                onClick={() => toggleSubcat(subcatKey)}
                                className="flex items-center justify-between rounded-lg px-2.5 py-1.5 cursor-pointer hover:bg-slate-100/70 text-xs transition-colors"
                              >
                                <div className="flex items-center gap-1.5">
                                  {isSubOpen ? (
                                    <ChevronDown className="h-3 w-3 text-slate-400" />
                                  ) : (
                                    <ChevronRight className="h-3 w-3 text-slate-400" />
                                  )}
                                  <span>{subIcon}</span>
                                  <span className="font-semibold text-slate-700 text-[11px]">
                                    {subNome}
                                  </span>
                                </div>
                                <span className="rounded-full bg-slate-100 px-1.5 py-0.2 text-[10px] font-bold text-slate-500">
                                  {items.length}
                                </span>
                              </div>

                              {/* Nível 3: Lista de Arquivos */}
                              {isSubOpen && (
                                <div className="pl-5 space-y-0.5">
                                  {items.map((item: any) => {
                                    const isSelected = arquivoAtivo?.caminho === item.caminho;
                                    let itemIcon = <FileText className="h-3.5 w-3.5 text-blue-500 shrink-0" />;
                                    if (item.tipo === 'csv' || item.tipo === 'parquet') {
                                      itemIcon = <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600 shrink-0" />;
                                    } else if (item.tipo === 'json') {
                                      itemIcon = <FileJson className="h-3.5 w-3.5 text-amber-500 shrink-0" />;
                                    } else if (item.tipo === 'pdf') {
                                      itemIcon = <FileText className="h-3.5 w-3.5 text-rose-500 shrink-0" />;
                                    } else if (item.tipo === 'py') {
                                      itemIcon = <FileCode className="h-3.5 w-3.5 text-indigo-500 shrink-0" />;
                                    }

                                    return (
                                      <button
                                        key={item.caminho}
                                        type="button"
                                        onClick={() => selecionarArquivo(item)}
                                        className={cn(
                                          'flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs transition-colors cursor-pointer',
                                          isSelected
                                            ? 'bg-purple-100 font-semibold text-purple-950 shadow-2xs border border-purple-200/70'
                                            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                                        )}
                                      >
                                        <div className="flex items-center gap-2 overflow-hidden">
                                          {itemIcon}
                                          <div className="truncate">
                                            <div className="truncate text-[11.5px] leading-tight">
                                              {item.nome}
                                            </div>
                                            <div className="text-[10px] text-slate-400 font-mono">
                                              {item.tipo.toUpperCase()} · {item.tamanho_kb} KB
                                              {item.is_metadados ? ' · Metadados' : ''}
                                            </div>
                                          </div>
                                        </div>
                                      </button>
                                    );
                                  })}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Painel Direito: Conteúdo e Visualização Interativa */}
        <main className="flex-1 flex flex-col overflow-hidden bg-white">
          {arquivoAtivo && (
            <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-6 py-2.5 text-xs text-slate-600 select-none">
              <div className="flex items-center gap-2 font-mono text-[11px]">
                <span className="font-semibold text-slate-800">{arquivoAtivo.caminho}</span>
                <span>·</span>
                <span>{arquivoAtivo.tamanho_kb} KB</span>
                {arquivoAtivo.modificado_em && (
                  <>
                    <span>·</span>
                    <span className="text-slate-400">
                      Atualizado em {new Date(arquivoAtivo.modificado_em).toLocaleDateString()}
                    </span>
                  </>
                )}
              </div>
            </div>
          )}

          <div className="flex-1 overflow-auto p-6">
            {loadingConteudo ? (
              <div className="flex h-full items-center justify-center text-xs text-slate-400 gap-2">
                <RefreshCw className="h-4 w-4 animate-spin text-purple-600" />
                <span>Carregando visualização...</span>
              </div>
            ) : !arquivoAtivo ? (
              <div className="flex h-full flex-col items-center justify-center text-xs text-slate-400 gap-2">
                <span className="text-3xl">📂</span>
                <p className="font-semibold text-slate-700">Nenhum arquivo selecionado</p>
                <p className="text-slate-400 max-w-sm text-center">
                  Selecione um arquivo nas categorias à esquerda para inspecionar seu conteúdo.
                </p>
              </div>
            ) : conteudo?.tipo === 'pdf' ? (
              <div className="flex flex-col h-full rounded-2xl border border-slate-200 overflow-hidden shadow-xs bg-slate-100">
                <div className="flex items-center justify-between bg-slate-50 px-4 py-2 border-b border-slate-200 text-xs">
                  <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                    <FileText className="h-4 w-4 text-rose-500" />
                    <span>Visualizador de Documento PDF ({arquivoAtivo.nome})</span>
                  </span>
                  <div className="flex items-center gap-2">
                    <a
                      href={`/api/dados/documento?caminho=${encodeURIComponent(arquivoAtivo.caminho)}`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-slate-700 hover:bg-slate-50 shadow-2xs transition-colors"
                    >
                      <ExternalLink className="h-3 w-3" />
                      <span>Abrir em Nova Aba</span>
                    </a>
                    <a
                      href={`/api/dados/download?caminho=${encodeURIComponent(arquivoAtivo.caminho)}`}
                      className="inline-flex items-center gap-1 rounded-lg bg-rose-600 px-2.5 py-1 text-white font-medium hover:bg-rose-700 shadow-2xs transition-colors"
                    >
                      <Download className="h-3 w-3" />
                      <span>Download</span>
                    </a>
                  </div>
                </div>
                <div className="flex-1 min-h-[580px] bg-slate-200">
                  <iframe
                    src={`/api/dados/documento?caminho=${encodeURIComponent(arquivoAtivo.caminho)}`}
                    className="h-full w-full border-0 min-h-[580px]"
                    title="PDF Viewer"
                  />
                </div>
              </div>
            ) : conteudo?.tipo === 'markdown' ? (
              <div className="max-w-4xl rounded-2xl border border-slate-200 bg-white p-6 shadow-2xs">
                <StreamingText content={conteudo.conteudo} />
              </div>
            ) : conteudo?.tipo === 'python' ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
                  <span>Script Python do Workspace ({arquivoAtivo.nome})</span>
                </div>
                <CodeBlock code={conteudo.conteudo || ''} language="python" />
              </div>
            ) : conteudo?.tipo === 'csv' || conteudo?.tipo === 'parquet' || conteudo?.linhas ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-xl bg-slate-50 p-3 text-xs text-slate-700 border border-slate-200/80">
                  <span>
                    Exibindo <strong>{conteudo.linhas?.length || 0}</strong> linhas (Total no dataset: {conteudo.total_linhas?.toLocaleString() || '—'})
                  </span>
                  <span className="font-mono text-slate-500">
                    Colunas: {conteudo.colunas?.length || 0}
                  </span>
                </div>
                <RecordsTable
                  columns={conteudo.colunas || Object.keys(conteudo.linhas?.[0] || {})}
                  data={conteudo.linhas || []}
                  title={`Registros de ${arquivoAtivo.nome}`}
                  maxHeight="calc(100vh - 220px)"
                />
              </div>
            ) : conteudo?.tipo === 'json' || arquivoAtivo?.tipo === 'json' ? (
              /* Suporte Completo: Visualização Estruturada vs JSON Nítido (Imagem 2 de Referência) */
              <div className="space-y-4 w-full h-full flex flex-col">
                {/* Toolbar do JSON Viewer */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-800">
                      Dicionário / Metadados
                    </span>
                    <h3 className="text-sm font-bold text-slate-900 font-mono">
                      {arquivoAtivo.nome}
                    </h3>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setJsonViewMode('estruturada')}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer select-none',
                        jsonViewMode === 'estruturada'
                          ? 'bg-blue-600 text-white shadow-xs'
                          : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                      )}
                    >
                      <LayoutGrid className="h-3.5 w-3.5" />
                      <span>Visualização Estruturada</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setJsonViewMode('raw')}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer select-none',
                        jsonViewMode === 'raw'
                          ? 'bg-blue-600 text-white shadow-xs'
                          : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                      )}
                    >
                      <Code2 className="h-3.5 w-3.5" />
                      <span>{'{ }'} JSON Nítido</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => copyJsonContent(JSON.stringify(jsonParsed, null, 2))}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs transition-colors cursor-pointer select-none"
                    >
                      {copiedJson ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-500" />
                          <span className="text-emerald-600">Copiado</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5 text-slate-400" />
                          <span>Copiar JSON</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Conteúdo: Visualização Estruturada ou JSON Nítido */}
                {jsonViewMode === 'estruturada' && (jsonParsed.columns || jsonParsed.metadata || jsonParsed.description) ? (
                  <div className="space-y-5">
                    {/* Grid de Metadados Principais */}
                    {jsonParsed.metadata && (
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                        {jsonParsed.metadata.category && (
                          <div>
                            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Categoria
                            </div>
                            <div className="mt-0.5 font-mono text-xs font-semibold text-slate-800 truncate">
                              {jsonParsed.metadata.category}
                            </div>
                          </div>
                        )}
                        {jsonParsed.metadata.table && (
                          <div>
                            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Tabela
                            </div>
                            <div className="mt-0.5 font-mono text-xs font-semibold text-blue-600 truncate">
                              {jsonParsed.metadata.table}
                            </div>
                          </div>
                        )}
                        {jsonParsed.metadata.source_file && (
                          <div>
                            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Arquivo Fonte
                            </div>
                            <div className="mt-0.5 font-mono text-xs font-semibold text-slate-800 truncate" title={jsonParsed.metadata.source_file}>
                              {jsonParsed.metadata.source_file}
                            </div>
                          </div>
                        )}
                        {jsonParsed.metadata.version && (
                          <div>
                            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Versão
                            </div>
                            <div className="mt-0.5 font-mono text-xs font-semibold text-slate-800">
                              {jsonParsed.metadata.version}
                            </div>
                          </div>
                        )}
                        {jsonParsed.metadata.updated_at && (
                          <div>
                            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Atualizado Em
                            </div>
                            <div className="mt-0.5 font-mono text-xs font-semibold text-slate-800">
                              {jsonParsed.metadata.updated_at}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Descrição e Chave Primária */}
                    <div className="space-y-2">
                      {jsonParsed.description && (
                        <p className="text-xs text-slate-700 leading-relaxed">
                          <strong>Descrição:</strong> {jsonParsed.description}
                        </p>
                      )}

                      {Array.isArray(jsonParsed.primary_key_candidates) && jsonParsed.primary_key_candidates.length > 0 && (
                        <div className="flex items-center gap-2 text-xs">
                          <strong className="text-slate-800">Chave Primária Recomendada:</strong>
                          {jsonParsed.primary_key_candidates.map((pk: string) => (
                            <span key={pk} className="rounded-md bg-blue-50 border border-blue-200 px-2 py-0.5 font-mono text-[11px] font-semibold text-blue-700">
                              {pk}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Lista de Colunas e Atributos de Negócio */}
                    {Array.isArray(jsonParsed.columns) && (
                      <div className="space-y-3">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                          Colunas e Atributos de Negócio ({jsonParsed.columns.length})
                        </h4>

                        <div className="space-y-2">
                          {jsonParsed.columns.map((col: any, idx: number) => (
                            <div
                              key={idx}
                              className="rounded-xl border border-slate-200/90 bg-white p-3.5 shadow-2xs transition-all hover:border-slate-300"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-mono text-xs font-bold text-slate-900">
                                  {col.name}
                                </span>
                                <div className="flex items-center gap-1.5">
                                  {col.data_type && (
                                    <span className="rounded-md bg-blue-50 border border-blue-200/80 px-2 py-0.5 font-mono text-[10px] font-semibold text-blue-700">
                                      {col.data_type}
                                    </span>
                                  )}
                                  {col.nullable !== undefined && (
                                    <span
                                      className={cn(
                                        'rounded-md px-2 py-0.5 text-[10px] font-semibold',
                                        col.nullable
                                          ? 'bg-slate-100 text-slate-600'
                                          : 'bg-amber-100 text-amber-800'
                                      )}
                                    >
                                      {col.nullable ? 'Nullable' : 'Required'}
                                    </span>
                                  )}
                                </div>
                              </div>
                              {col.description && (
                                <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                                  {col.description}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  /* JSON Nítido / Raw Box com Indentação Perfeita e Altura Fluida */
                  <pre className="overflow-auto rounded-2xl border border-slate-800 bg-[#0f172a] p-5 font-mono text-xs text-slate-200 leading-relaxed flex-1 w-full min-h-[550px] shadow-sm select-text">
                    {JSON.stringify(jsonParsed, null, 2)}
                  </pre>
                )}
              </div>
            ) : (
              <div className="text-xs text-slate-500">
                Formato não reconhecido para visualização interativa.
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default DataExplorerView;
