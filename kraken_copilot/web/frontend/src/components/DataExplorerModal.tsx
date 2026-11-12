import React, { useState, useEffect, useMemo } from 'react';
import {
  X,
  Database,
  FileSpreadsheet,
  FileText,
  FileCode2,
  FileJson,
  Package,
  Globe,
  Search,
  RefreshCw,
  Play,
  Maximize2,
  Minimize2,
  ExternalLink,
  Plus,
  Table as TableIcon,
  Tag,
  Code2,
  ChevronDown,
  ChevronRight,
  Folder,
  Zap,
  BookOpen,
  Terminal,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { RecordsTable } from './RecordsTable';
import { CodeBlock } from './CodeBlock';

export interface DataExplorerModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialFileName?: string | null;
  onAttachToChat?: (fileName: string) => void;
  onOpenFullExplorer?: (fileName: string) => void;
  onSendSqlToChat?: (sql: string) => void;
}

// Configuração visual das Seções padronizadas do Projeto
const SECTIONS_CONFIG: Record<
  string,
  { label: string; icon: any; color: string; badgeColor: string }
> = {
  DATALAKE: {
    label: 'DATALAKE',
    icon: Database,
    color: 'text-purple-600',
    badgeColor: 'bg-purple-100 text-purple-800',
  },
  METADADOS: {
    label: 'METADADOS',
    icon: Tag,
    color: 'text-fuchsia-600',
    badgeColor: 'bg-fuchsia-100 text-fuchsia-800',
  },
  OUTPUTS: {
    label: 'OUTPUTS',
    icon: Zap,
    color: 'text-violet-600',
    badgeColor: 'bg-violet-100 text-violet-800',
  },
  DOCUMENTAÇÕES: {
    label: 'DOCUMENTAÇÕES',
    icon: BookOpen,
    color: 'text-indigo-600',
    badgeColor: 'bg-indigo-100 text-indigo-800',
  },
  WORKSPACE: {
    label: 'WORKSPACE',
    icon: Terminal,
    color: 'text-pink-600',
    badgeColor: 'bg-pink-100 text-pink-800',
  },
};

const getSubcatIcon = (subcat: string) => {
  const s = subcat.toUpperCase();
  if (s === 'CSV') return FileSpreadsheet;
  if (s === 'PARQUET') return Package;
  if (s === 'HTML') return Globe;
  if (s === 'JSON') return FileJson;
  if (s === 'MARKDOWN') return FileText;
  if (s === 'PDF') return FileText;
  if (s === 'PYTHON') return FileCode2;
  return Folder;
};

export function DataExplorerModal({
  isOpen,
  onClose,
  initialFileName,
  onAttachToChat,
  onOpenFullExplorer,
  onSendSqlToChat,
}: DataExplorerModalProps) {
  const [arquivos, setArquivos] = useState<any[]>([]);
  const [catalogTree, setCatalogTree] = useState<Record<string, Record<string, any[]>>>({});
  const [arquivoAtivo, setArquivoAtivo] = useState<any>(null);
  const [conteudo, setConteudo] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [loadingLista, setLoadingLista] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [buscaArquivo, setBuscaArquivo] = useState('');
  const [abaAtiva, setAbaAtiva] = useState<'preview' | 'schema' | 'sql'>('preview');
  const [sqlQuery, setSqlQuery] = useState('');

  // Estados de colapso das seções e subcategorias padronizados
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    DATALAKE: true,
    METADADOS: true,
    OUTPUTS: true,
    DOCUMENTAÇÕES: true,
    WORKSPACE: true,
  });
  const [openSubcats, setOpenSubcats] = useState<Record<string, boolean>>({});

  const toggleSection = (sec: string) => {
    setOpenSections((prev) => ({ ...prev, [sec]: !prev[sec] }));
  };

  const toggleSubcat = (key: string) => {
    setOpenSubcats((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Fechar com ESC
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Carregar lista de arquivos e árvore ao abrir
  useEffect(() => {
    if (isOpen) {
      carregarListaArquivos();
    }
  }, [isOpen]);

  const carregarListaArquivos = async () => {
    try {
      setLoadingLista(true);
      const res = await fetch('/api/dados/arquivos');
      if (res.ok) {
        const data = await res.json();
        const lista = data.arquivos || [];
        setArquivos(lista);
        setCatalogTree(data.arvore || {});

        // Localiza arquivo inicial solicitado ou seleciona o primeiro
        let target = lista[0];
        if (initialFileName) {
          const match = lista.find(
            (a: any) =>
              a.nome?.toLowerCase() === initialFileName.toLowerCase() ||
              a.caminho?.toLowerCase() === initialFileName.toLowerCase() ||
              a.caminho?.toLowerCase().endsWith(initialFileName.toLowerCase()) ||
              initialFileName.toLowerCase().endsWith(a.nome?.toLowerCase())
          );
          if (match) target = match;
        }

        if (target) {
          selecionarArquivo(target);
        }
      }
    } catch (err) {
      console.error('Erro ao listar arquivos no modal:', err);
    } finally {
      setLoadingLista(false);
    }
  };

  // Se initialFileName mudar enquanto modal estiver aberto
  useEffect(() => {
    if (isOpen && initialFileName && arquivos.length > 0) {
      const match = arquivos.find(
        (a: any) =>
          a.nome?.toLowerCase() === initialFileName.toLowerCase() ||
          a.caminho?.toLowerCase() === initialFileName.toLowerCase() ||
          a.caminho?.toLowerCase().endsWith(initialFileName.toLowerCase()) ||
          initialFileName.toLowerCase().endsWith(a.nome?.toLowerCase())
      );
      if (match) {
        selecionarArquivo(match);
      }
    }
  }, [initialFileName, arquivos]);

  const selecionarArquivo = async (item: any) => {
    setArquivoAtivo(item);
    const fileName = item.nome || item;
    const caminho = item.caminho || fileName;

    // Atualiza consulta SQL padrão
    const tableName = (item.nome || fileName).replace(/\.[^/.]+$/, '').replace(/[-\s]/g, '_');
    setSqlQuery(`SELECT * FROM ${tableName} LIMIT 10;`);

    if (fileName.endsWith('.pdf')) {
      setConteudo({ tipo: 'pdf', nome: fileName, caminho });
      return;
    }

    try {
      setLoading(true);
      const res = await fetch(`/api/dados/arquivo?caminho=${encodeURIComponent(caminho)}`);
      if (res.ok) {
        const data = await res.json();
        setConteudo(data);
      } else {
        setConteudo(null);
      }
    } catch (err) {
      console.error('Erro ao carregar preview do arquivo:', err);
      setConteudo(null);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const nomeAtual = arquivoAtivo?.nome || initialFileName || 'Arquivo';
  const isPdf = nomeAtual.endsWith('.pdf');
  const isHtml = nomeAtual.endsWith('.html');
  const isPython = nomeAtual.endsWith('.py');

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-2 sm:p-4 backdrop-blur-xs animate-in fade-in duration-150 select-none"
      onClick={onClose}
    >
      <div
        className={cn(
          'flex flex-col overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-2xl transition-all duration-200 select-text',
          isMaximized ? 'h-[98vh] w-[99vw]' : 'h-[94vh] w-[98vw] max-w-[1900px]'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header do Modal Flutuante */}
        <div className="flex items-center justify-between border-b border-slate-200/90 px-5 py-3 bg-slate-50/90 select-none">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-100 text-blue-700 shadow-2xs shrink-0">
              {isPython ? (
                <FileCode2 className="h-4.5 w-4.5 text-emerald-600" />
              ) : isPdf ? (
                <FileText className="h-4.5 w-4.5 text-rose-600" />
              ) : isHtml ? (
                <Globe className="h-4.5 w-4.5 text-cyan-600" />
              ) : (
                <Database className="h-4.5 w-4.5 text-blue-600" />
              )}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-800 truncate font-mono">
                  {nomeAtual}
                </h3>
                {arquivoAtivo?.secao && (
                  <span className="rounded bg-slate-200/80 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-600">
                    {arquivoAtivo.secao}
                  </span>
                )}
                {conteudo?.total_linhas && (
                  <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-mono font-medium text-emerald-800">
                    {conteudo.total_linhas.toLocaleString()} registros
                  </span>
                )}
                {conteudo?.colunas && (
                  <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-mono font-medium text-blue-800">
                    {conteudo.colunas.length} colunas
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500 truncate font-mono">
                {arquivoAtivo?.caminho || nomeAtual}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {onAttachToChat && (
              <button
                type="button"
                onClick={() => {
                  onAttachToChat(nomeAtual);
                  onClose();
                }}
                className="inline-flex items-center gap-1 rounded-xl bg-blue-50 border border-blue-200/90 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 hover:border-blue-300 transition-colors cursor-pointer shadow-2xs"
                title="Adicionar arquivo ao contexto do Chat"
              >
                <Plus className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Anexar ao Chat</span>
              </button>
            )}

            {onOpenFullExplorer && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onOpenFullExplorer(nomeAtual);
                }}
                className="hidden sm:inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 hover:text-blue-700 transition-colors cursor-pointer shadow-2xs"
                title="Abrir no Explorador Completo de Dados"
              >
                <span>Explorador Completo</span>
                <ExternalLink className="h-3 w-3" />
              </button>
            )}

            <button
              type="button"
              onClick={() => setIsMaximized(!isMaximized)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition-colors cursor-pointer"
              title={isMaximized ? 'Restaurar tamanho' : 'Maximizar'}
            >
              {isMaximized ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </button>

            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-100 hover:text-rose-700 transition-colors cursor-pointer"
              title="Fechar (ESC)"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Corpo: Catálogo de Arquivos do Projeto à Esquerda + Preview com Aproveitamento Máximo */}
        <div className="flex flex-1 overflow-hidden min-h-0">
          {/* Listagem Lateral de Arquivos com Layout Idêntico a "Arquivos do Projeto" */}
          <div className="w-72 sm:w-80 border-r border-slate-200/90 bg-slate-50/70 flex flex-col shrink-0 overflow-hidden select-none">
            {/* Campo de Busca de Arquivos */}
            <div className="p-3 border-b border-slate-200/80 bg-white">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filtrar arquivos..."
                  value={buscaArquivo}
                  onChange={(e) => setBuscaArquivo(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50/50 pl-8 pr-2.5 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-purple-500 focus:bg-white focus:outline-hidden"
                />
              </div>
            </div>

            {/* Árvore Hierárquica Idêntica a Arquivos do Projeto da Navbar */}
            <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
              {loadingLista ? (
                <div className="flex flex-col items-center justify-center py-12 text-xs text-slate-400 gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin text-purple-600" />
                  <span>Carregando catálogo de arquivos...</span>
                </div>
              ) : Object.keys(catalogTree).length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-400">
                  Nenhum arquivo encontrado.
                </div>
              ) : (
                Object.entries(catalogTree).map(([secaoNome, subcategorias]) => {
                  const conf = SECTIONS_CONFIG[secaoNome] || {
                    label: secaoNome,
                    icon: Folder,
                    color: 'text-slate-600',
                    badgeColor: 'bg-slate-100 text-slate-700',
                  };
                  const SecIcon = conf.icon;
                  const isSecOpen = openSections[secaoNome] ?? true;

                  // Coleta e filtra arquivos da seção
                  const subEntries = Object.entries(subcategorias || {});
                  let totalSecArquivos = 0;
                  subEntries.forEach(([_, items]) => {
                    const filtered = (items || []).filter((item: any) =>
                      !buscaArquivo.trim()
                        ? true
                        : (item.nome || '').toLowerCase().includes(buscaArquivo.toLowerCase()) ||
                        (item.caminho || '').toLowerCase().includes(buscaArquivo.toLowerCase())
                    );
                    totalSecArquivos += filtered.length;
                  });

                  if (totalSecArquivos === 0 && buscaArquivo.trim()) return null;

                  return (
                    <div
                      key={secaoNome}
                      className="rounded-xl border border-slate-200/80 bg-white overflow-hidden shadow-2xs"
                    >
                      {/* Nível 1: Cabeçalho da Seção */}
                      <div
                        onClick={() => toggleSection(secaoNome)}
                        className="flex items-center justify-between px-3 py-2 bg-slate-50/60 hover:bg-slate-100/70 cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          {isSecOpen ? (
                            <ChevronDown className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          ) : (
                            <ChevronRight className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          )}
                          <SecIcon className={cn('h-4 w-4 shrink-0', conf.color)} />
                          <span className="font-bold text-xs text-slate-800 tracking-wide truncate">
                            {conf.label}
                          </span>
                        </div>
                        <span className={cn('rounded-md px-1.5 py-0.5 text-[9.5px] font-bold uppercase shrink-0', conf.badgeColor)}>
                          {totalSecArquivos} {totalSecArquivos === 1 ? 'ARQUIVO' : 'ARQUIVOS'}
                        </span>
                      </div>

                      {/* Conteúdo da Seção: Subcategorias por Tipo */}
                      {isSecOpen && (
                        <div className="p-1 space-y-1 bg-white border-t border-slate-100">
                          {subEntries.map(([subcatNome, arquivosSubcat]) => {
                            const SubIcon = getSubcatIcon(subcatNome);
                            const subcatKey = `${secaoNome}_${subcatNome}`;
                            const isSubOpen = openSubcats[subcatKey] ?? (buscaArquivo.trim() ? true : subcatNome.toUpperCase() === 'CSV');

                            const arquivosFiltrados = (arquivosSubcat || []).filter((item: any) =>
                              !buscaArquivo.trim()
                                ? true
                                : (item.nome || '').toLowerCase().includes(buscaArquivo.toLowerCase()) ||
                                (item.caminho || '').toLowerCase().includes(buscaArquivo.toLowerCase())
                            );

                            if (arquivosFiltrados.length === 0) return null;

                            return (
                              <div key={subcatNome} className="rounded-lg">
                                {/* Nível 2: Cabeçalho da Subcategoria */}
                                <div
                                  onClick={() => toggleSubcat(subcatKey)}
                                  className="flex items-center justify-between px-2.5 py-1.5 rounded-md hover:bg-slate-50 cursor-pointer text-slate-700 transition-colors"
                                >
                                  <div className="flex items-center gap-2 min-w-0">
                                    {isSubOpen ? (
                                      <ChevronDown className="h-3 w-3 text-slate-400 shrink-0" />
                                    ) : (
                                      <ChevronRight className="h-3 w-3 text-slate-400 shrink-0" />
                                    )}
                                    <SubIcon className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                                    <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider truncate">
                                      {subcatNome}
                                    </span>
                                  </div>
                                  <span className="rounded-full bg-slate-100 px-1.5 py-0.2 text-[9.5px] font-mono font-medium text-slate-500 shrink-0">
                                    {arquivosFiltrados.length}
                                  </span>
                                </div>

                                {/* Nível 3: Arquivos da Subcategoria */}
                                {isSubOpen && (
                                  <div className="pl-6 pr-1 py-0.5 space-y-0.5">
                                    {arquivosFiltrados.map((item: any) => {
                                      const isSelected = (item.nome || item) === (arquivoAtivo?.nome || arquivoAtivo);
                                      return (
                                        <button
                                          key={item.caminho || item.nome || item}
                                          type="button"
                                          onClick={() => selecionarArquivo(item)}
                                          className={cn(
                                            'w-full flex items-center justify-between rounded-lg px-2 py-1.5 text-xs text-left transition-all cursor-pointer border',
                                            isSelected
                                              ? 'bg-blue-50 border-blue-200/90 text-blue-900 font-bold shadow-2xs'
                                              : 'border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                                          )}
                                        >
                                          <span className="truncate font-mono text-[11px] pr-1">
                                            {item.nome || item}
                                          </span>
                                          <span className="text-[10px] text-slate-400 font-mono shrink-0">
                                            {item.tamanho_kb ? `${item.tamanho_kb} KB` : ''}
                                          </span>
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
          </div>

          {/* Área Principal de Visualização com Aproveitamento Máximo de Espaço */}
          <div className="flex flex-1 flex-col overflow-hidden bg-white min-w-0 min-h-0">
            {/* Abas Superiores */}
            <div className="flex items-center justify-between border-b border-slate-200/90 px-5 pt-1.5 bg-slate-50/50 select-none shrink-0">
              <div className="flex items-center gap-1 text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setAbaAtiva('preview')}
                  className={cn(
                    'flex items-center gap-1.5 rounded-t-lg border-b-2 px-3.5 py-2 transition-colors cursor-pointer',
                    abaAtiva === 'preview'
                      ? 'border-blue-600 text-blue-900 font-semibold bg-white'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  )}
                >
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                  <span>Tabela / Preview</span>
                </button>

                {conteudo?.colunas && (
                  <button
                    type="button"
                    onClick={() => setAbaAtiva('schema')}
                    className={cn(
                      'flex items-center gap-1.5 rounded-t-lg border-b-2 px-3.5 py-2 transition-colors cursor-pointer',
                      abaAtiva === 'schema'
                        ? 'border-blue-600 text-blue-900 font-semibold bg-white'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    )}
                  >
                    <Tag className="h-3.5 w-3.5" />
                    <span>Esquema / Colunas ({conteudo.colunas.length})</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => setAbaAtiva('sql')}
                  className={cn(
                    'flex items-center gap-1.5 rounded-t-lg border-b-2 px-3.5 py-2 transition-colors cursor-pointer',
                    abaAtiva === 'sql'
                      ? 'border-blue-600 text-blue-900 font-semibold bg-white'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  )}
                >
                  <Code2 className="h-3.5 w-3.5" />
                  <span>Consulta SQL</span>
                </button>
              </div>

              {conteudo?.linhas && (
                <div className="text-[11px] text-slate-400 font-mono hidden md:block">
                  Amostra de {conteudo.linhas.length} linhas
                </div>
              )}
            </div>

            {/* Conteúdo Renderizado Expandido em 100% da Largura e Altura */}
              <div className="flex-1 overflow-auto p-3 sm:p-5 min-w-0 min-h-0 flex flex-col">
                {loading ? (
                  <div className="flex flex-1 items-center justify-center text-xs text-slate-400 gap-2">
                    <RefreshCw className="h-5 w-5 animate-spin text-blue-600" />
                    <span>Carregando dados com delimitador automático...</span>
                  </div>
                ) : isPdf ? (
                  <div className="flex-1 w-full rounded-xl border border-slate-200 overflow-hidden min-h-[500px]">
                    <iframe
                      src={`/api/dados/documento?caminho=${encodeURIComponent(conteudo?.caminho || arquivoAtivo?.caminho || nomeAtual)}`}
                      className="h-full w-full"
                      title="Documento PDF"
                    />
                  </div>
                ) : isHtml ? (
                  <div className="flex-1 w-full rounded-xl border border-slate-200 overflow-hidden min-h-[500px]">
                    <iframe
                      srcDoc={conteudo?.conteudo}
                      className="h-full w-full bg-white"
                      title="Relatório HTML"
                    />
                  </div>
                ) : isPython ? (
                  <div className="flex-1 w-full rounded-xl border border-slate-200 overflow-hidden">
                    <CodeBlock code={conteudo?.conteudo || ''} language="python" />
                  </div>
                ) : abaAtiva === 'schema' && conteudo?.colunas ? (
                      <div className="space-y-4 flex-1 min-h-0 flex flex-col">
                        <div className="shrink-0 rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-xs text-slate-700">
                          <p className="font-bold text-slate-800 text-sm">Resumo da Tabela:</p>
                          <p className="mt-1 text-slate-600">
                            Total de linhas: <strong>{conteudo.total_linhas?.toLocaleString() || '—'}</strong> |
                            Total de colunas detectadas: <strong>{conteudo.colunas?.length || 0}</strong>
                          </p>
                        </div>
                        <RecordsTable
                          columns={['posicao', 'coluna', 'tipo_detectado']}
                          data={conteudo.colunas.map((col: any, idx: number) => ({
                            posicao: idx + 1,
                            coluna: String(col.nome || col),
                            tipo_detectado: col.tipo || (typeof (conteudo.linhas?.[0]?.[col] ?? '') === 'number' ? 'numeric' : 'string'),
                          }))}
                          title={`Estrutura e Tipos de Coluna (${nomeAtual})`}
                          fullHeight={true}
                        />
                      </div>
                      ) : abaAtiva === 'sql' ? (
                      <div className="space-y-4 max-w-4xl">
                        <div>
                          <h4 className="text-xs font-bold text-slate-800">Executar SQL no Dataset</h4>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Envie consultas diretamente para o Kraken Analyst processar no banco SQLite:
                          </p>
                        </div>
                        <textarea
                          value={sqlQuery}
                          onChange={(e) => setSqlQuery(e.target.value)}
                          rows={6}
                          className="w-full rounded-xl border border-slate-300 p-3.5 font-mono text-xs text-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-hidden"
                        />
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              if (onSendSqlToChat) {
                                onSendSqlToChat(sqlQuery);
                                onClose();
                              }
                            }}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-colors cursor-pointer"
                          >
                            <Play className="h-3.5 w-3.5" />
                            <span>Executar Consulta no Chat</span>
                          </button>
                        </div>
                      </div>
              ) : conteudo?.linhas && conteudo.linhas.length > 0 ? (
                      <div className="flex-1 w-full min-h-0 flex flex-col">
                        <RecordsTable
                          columns={conteudo.colunas || Object.keys(conteudo.linhas[0] || {})}
                          data={conteudo.linhas}
                          title={`Registros de ${nomeAtual}`}
                          fullHeight={true}
                        />
                      </div>
                      ) : (
                      <div className="flex flex-1 flex-col items-center justify-center text-xs text-slate-400 gap-1.5">
                        <Database className="h-6 w-6 text-slate-300 mb-1" />
                        <span>Nenhum registro encontrado para este arquivo.</span>
                      </div>
              )}
                    </div>
                  </div>
        </div>

              {/* Rodapé do Modal */}
              <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/70 px-5 py-2.5 text-[11px] text-slate-500 select-none">
                <span className="font-mono text-slate-400">
                  {conteudo?.linhas ? `Exibindo ${conteudo.linhas.length} linhas de amostra` : nomeAtual}
                </span>
                <span className="text-[10px] text-slate-400">Pressione ESC para fechar</span>
              </div>
            </div>
          </div>
          );
}

          export default DataExplorerModal;
