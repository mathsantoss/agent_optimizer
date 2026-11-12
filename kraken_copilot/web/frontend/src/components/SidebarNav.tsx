import React, { useState, useRef, useEffect, useMemo, DragEvent } from 'react';
import {
  MessageSquare,
  Plus,
  Trash2,
  Database,
  ExternalLink,
  ShieldCheck,
  Search,
  BookOpen,
  ChevronLeft,
  Sparkles,
  ChevronDown,
  X,
  FileCode2,
  GripVertical,
  Layers,
  AtSign,
  Eye,
  FileText,
  Pencil,
  Check,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { CatalogDataSource, WorkspaceFile } from './PromptBar';

export interface ConversaItem {
  id: string;
  titulo: string;
  criado_em?: string;
  atualizado_em?: string;
}

export interface SidebarNavProps {
  conversas: ConversaItem[];
  conversaAtivaId: string | null;
  activeView: 'chat' | 'dados' | 'investigacao' | 'observabilidade';
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
  onSelectConversa: (id: string) => void;
  onNovaConversa: () => void;
  onDeleteConversa: (id: string) => void;
  onRenameConversa?: (id: string, novoTitulo: string) => void;
  onNavigate: (view: 'chat' | 'dados' | 'observabilidade') => void;
  onOpenObservability: () => void;
  catalogSources?: CatalogDataSource[];
  workspaceFiles?: WorkspaceFile[];
  selectedWorkspaceFile?: string;
  onSelectWorkspaceFile?: (filename: string) => void;
  onAttachSource?: (source: CatalogDataSource) => void;
  className?: string;
}

export function SidebarNav({
  conversas = [],
  conversaAtivaId,
  activeView,
  mobileOpen = false,
  onCloseMobile,
  onSelectConversa,
  onNovaConversa,
  onDeleteConversa,
  onRenameConversa,
  onNavigate,
  onOpenObservability,
  catalogSources = [],
  workspaceFiles = [],
  selectedWorkspaceFile = '',
  onSelectWorkspaceFile,
  onAttachSource,
  className,
}: SidebarNavProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [sidebarTab, setSidebarTab] = useState<'conversas' | 'arquivos'>('conversas');
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [fileQuery, setFileQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const searchInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId) {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }
  }, [editingId]);

  const handleStartRename = (c: ConversaItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(c.id);
    setEditingTitle(c.titulo);
  };

  const handleConfirmRename = (id: string, e?: React.MouseEvent | React.KeyboardEvent) => {
    e?.stopPropagation();
    if (editingTitle.trim() && onRenameConversa) {
      onRenameConversa(id, editingTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e?: React.MouseEvent | React.KeyboardEvent) => {
    e?.stopPropagation();
    setEditingId(null);
  };

  useEffect(() => {
    if (searchOpen) {
      searchInputRef.current?.focus();
    }
  }, [searchOpen]);

  const visibleConversas = conversas.filter((c) =>
    (c.titulo || '').toLowerCase().includes(query.trim().toLowerCase())
  );

  // Consolidação de arquivos para a aba "Arquivos do Projeto"
  const projectFiles: CatalogDataSource[] = useMemo(() => {
    const items: CatalogDataSource[] = [];
    const seen = new Set<string>();

    for (const src of catalogSources) {
      if (!seen.has(src.caminho)) {
        seen.add(src.caminho);
        items.push(src);
      }
    }

    // Default datalake e metadados
    const defaults: CatalogDataSource[] = [
      {
        key: 'dados_vendas.csv',
        nome: 'dados_vendas.csv',
        caminho: 'krakenlake/catalog/sources/dados_vendas.csv',
        secao: 'DATALAKE',
        tipo: 'csv',
        tamanho_kb: 7405.8,
        descricao: 'Base transacional de vendas, clientes e preços',
      },
      {
        key: 'dicionario_vendas.json',
        nome: 'dicionario_vendas.json',
        caminho: 'krakenlake/catalog/metadados/dicionario_vendas.json',
        secao: 'METADADOS',
        tipo: 'json',
        tamanho_kb: 2.84,
        descricao: 'Dicionário semântico e regras de negócio (RAG)',
      },
    ];

    for (const d of defaults) {
      if (!seen.has(d.caminho) && !items.some((i) => i.nome === d.nome)) {
        seen.add(d.caminho);
        items.push(d);
      }
    }

    // Scripts do workspace
    for (const wf of workspaceFiles) {
      const p = wf.caminho || `krakenlake/workspace/${wf.nome}`;
      if (!seen.has(p)) {
        seen.add(p);
        items.push({
          key: wf.nome,
          nome: wf.nome,
          caminho: p,
          secao: 'WORKSPACE',
          tipo: 'py',
          descricao: `Script do Workspace (${wf.linhas ?? 0} linhas)`,
        });
      }
    }

    return items;
  }, [catalogSources, workspaceFiles]);

  const filteredFiles = useMemo(() => {
    const q = fileQuery.trim().toLowerCase();
    if (!q) return projectFiles;
    return projectFiles.filter(
      (f) =>
        f.nome.toLowerCase().includes(q) ||
        f.caminho.toLowerCase().includes(q) ||
        (f.descricao || '').toLowerCase().includes(q)
    );
  }, [projectFiles, fileQuery]);

  const datalakeFiles = filteredFiles.filter((f) => f.secao === 'DATALAKE');
  const metadataFiles = filteredFiles.filter((f) => f.secao === 'METADADOS');
  const workspaceScripts = filteredFiles.filter((f) => f.secao === 'WORKSPACE');

  const handleDragStart = (e: DragEvent<HTMLDivElement>, file: CatalogDataSource) => {
    e.dataTransfer.setData('application/x-kraken-source', JSON.stringify(file));
    e.dataTransfer.setData('text/plain', `@${file.nome}`);
    e.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <>
      {/* Backdrop escuro no mobile */}
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-2xs md:hidden"
        />
      )}

      <aside
        data-sidebar-collapsed={collapsed}
        aria-label="Workspace navigation"
        className={cn(
          'flex h-screen flex-col border-r border-slate-200/90 bg-white transition-[width] duration-250 z-40 select-none shadow-2xs',
          'fixed inset-y-0 left-0 md:relative',
          mobileOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0',
          collapsed ? 'md:w-16' : 'w-64',
          className
        )}
      >
        {/* Workspace Switcher / Header */}
        <div
          className={cn(
            'flex h-14 items-center border-b border-slate-100 transition-all',
            collapsed ? 'justify-center px-0' : 'justify-between px-3'
          )}
        >
          {collapsed ? (
            <button
              type="button"
              onClick={() => setCollapsed(false)}
              className="group relative flex h-10 w-10 mx-auto items-center justify-center rounded-xl transition-all cursor-pointer hover:ring-2 hover:ring-blue-400 p-0"
              title="Expandir menu lateral"
            >
              <img
                src="/kraken-copilot.svg"
                alt="Kraken Copilot"
                className="h-8 w-8 rounded-xl object-contain group-hover:scale-105 transition-transform"
              />
            </button>
          ) : (
            <>
              <div className="flex items-center gap-2 overflow-hidden">
                <img
                  src="/kraken-copilot.svg"
                  alt="Kraken Copilot"
                  className="h-8 w-8 rounded-xl object-contain shadow-xs shrink-0"
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-bold text-slate-900 leading-tight">
                    Kraken Copilot
                  </div>
                  <div className="truncate text-[10px] text-slate-400 font-medium">
                    Analytics &amp; Pipelines
                  </div>
                </div>
              </div>

              <button
                type="button"
                aria-label="Recolher barra lateral"
                onClick={() => setCollapsed(true)}
                className="hidden md:flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors cursor-pointer"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            </>
          )}
        </div>

        {/* Ação Primária: New Chat */}
        <div className={cn(collapsed ? 'p-2 flex justify-center' : 'p-2.5')}>
          <button
            type="button"
            onClick={onNovaConversa}
            className={cn(
              'flex items-center justify-center rounded-xl border border-slate-200/90 bg-slate-50/80 text-xs font-semibold text-slate-700 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 shadow-2xs transition-all cursor-pointer active:scale-98',
              collapsed ? 'h-10 w-10 p-0 mx-auto' : 'w-full gap-2 px-3 py-2'
            )}
            title="Iniciar Nova Conversa (Ctrl+N)"
          >
            <Plus className="h-4 w-4 text-blue-600 shrink-0" />
            {!collapsed && <span>Nova Conversa</span>}
          </button>
        </div>

        {/* Menu de Navegação Primária */}
        <nav className={cn('border-b border-slate-100 pb-2 space-y-1', collapsed ? 'px-2 flex flex-col items-center' : 'px-2 space-y-0.5')}>
          <button
            type="button"
            onClick={() => onNavigate('chat')}
            className={cn(
              'flex items-center rounded-xl text-xs font-medium transition-colors cursor-pointer',
              collapsed ? 'h-10 w-10 p-0 justify-center mx-auto' : 'w-full gap-2.5 px-2.5 py-2',
              activeView === 'chat'
                ? 'bg-blue-50 text-blue-700 font-semibold'
                : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900'
            )}
            title="Chat Principal"
          >
            <MessageSquare className="h-4 w-4 shrink-0" />
            {!collapsed && <span>Chat</span>}
          </button>

          <button
            type="button"
            onClick={() => onNavigate('dados')}
            className={cn(
              'flex items-center rounded-xl text-xs font-medium transition-colors cursor-pointer',
              collapsed ? 'h-10 w-10 p-0 justify-center mx-auto' : 'w-full gap-2.5 px-2.5 py-2',
              activeView === 'dados'
                ? 'bg-purple-50 text-purple-700 font-semibold'
                : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900'
            )}
            title="Explorador de Dados e Documentos"
          >
            <Database className="h-4 w-4 shrink-0" />
            {!collapsed && <span>Dados &amp; Documentos</span>}
          </button>

          <button
            type="button"
            onClick={() => onNavigate('observabilidade')}
            className={cn(
              'flex items-center rounded-xl text-xs font-medium transition-colors cursor-pointer',
              collapsed ? 'h-10 w-10 p-0 justify-center mx-auto' : 'w-full gap-2.5 px-2.5 py-2',
              activeView === 'observabilidade'
                ? 'bg-emerald-50 text-emerald-700 font-semibold'
                : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900'
            )}
            title="Painel de Observabilidade"
          >
            <ShieldCheck className="h-4 w-4 shrink-0" />
            {!collapsed && <span>Observabilidade</span>}
          </button>
        </nav>

        {/* Seletor de Abas da Barra Lateral: Conversas vs Arquivos do Projeto (Drag & Drop) */}
        {!collapsed && (
          <div className="px-2 pt-2 pb-1">
            <div className="flex items-center rounded-xl bg-slate-100/90 p-0.5 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setSidebarTab('conversas')}
                className={cn(
                  'flex-1 rounded-lg py-1 text-center transition-all cursor-pointer',
                  sidebarTab === 'conversas'
                    ? 'bg-white text-slate-900 shadow-2xs font-bold'
                    : 'text-slate-500 hover:text-slate-800 font-medium'
                )}
              >
                Chats ({conversas.length})
              </button>
              <button
                type="button"
                onClick={() => setSidebarTab('arquivos')}
                className={cn(
                  'flex-1 rounded-lg py-1 text-center transition-all cursor-pointer flex items-center justify-center gap-1',
                  sidebarTab === 'arquivos'
                    ? 'bg-white text-blue-700 shadow-2xs font-bold'
                    : 'text-slate-500 hover:text-slate-800 font-medium'
                )}
              >
                <Layers className="h-3 w-3" />
                <span>Arquivos ({projectFiles.length})</span>
              </button>
            </div>
          </div>
        )}

        {/* CONTEÚDO DA BARRA LATERAL */}
        <div className="flex-1 overflow-y-auto px-2 py-1.5">
          {/* ABA 1: SESSÕES RECENTES */}
          {sidebarTab === 'conversas' && (
            <div>
              {!collapsed && (
                <div className="relative mb-2 flex items-center justify-between px-1">
                  {searchOpen ? (
                    <div className="flex w-full items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 shadow-2xs">
                      <Search className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                      <input
                        ref={searchInputRef}
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Escape') {
                            setSearchOpen(false);
                            setQuery('');
                          }
                        }}
                        placeholder="Buscar histórico..."
                        className="w-full bg-transparent text-xs text-slate-800 outline-none placeholder:text-slate-400 font-medium"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          setSearchOpen(false);
                          setQuery('');
                        }}
                        className="text-slate-400 hover:text-slate-600"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Histórico de Conversas
                      </span>
                      <button
                        type="button"
                        aria-label="Buscar chats"
                        onClick={() => setSearchOpen(true)}
                        className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors cursor-pointer"
                      >
                        <Search className="h-3.5 w-3.5" />
                      </button>
                    </>
                  )}
                </div>
              )}

              {/* Lista de Sessões Recentes */}
              <div className={cn(collapsed ? 'space-y-1 flex flex-col items-center' : 'space-y-0.5')}>
                {visibleConversas.length === 0 ? (
                  !collapsed && (
                    <div className="px-2 py-4 text-center text-xs text-slate-400">
                      {query ? 'Nenhum chat encontrado' : 'Nenhuma conversa ativa'}
                    </div>
                  )
                ) : (
                  (collapsed ? visibleConversas.slice(0, 3) : visibleConversas).map((c) => {
                    const isSelected = c.id === conversaAtivaId;
                    const isEditing = editingId === c.id;

                    if (isEditing && !collapsed) {
                      return (
                        <div
                          key={c.id}
                          className="flex items-center gap-1.5 rounded-xl border border-blue-400 bg-white px-2 py-1 shadow-xs"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MessageSquare className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                          <input
                            ref={renameInputRef}
                            type="text"
                            value={editingTitle}
                            onChange={(e) => setEditingTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleConfirmRename(c.id, e);
                              if (e.key === 'Escape') handleCancelRename(e);
                            }}
                            className="flex-1 bg-transparent text-xs text-slate-900 outline-none font-medium min-w-0"
                          />
                          <button
                            type="button"
                            onClick={(e) => handleConfirmRename(c.id, e)}
                            className="p-0.5 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 rounded"
                            title="Salvar nome"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleCancelRename(e)}
                            className="p-0.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"
                            title="Cancelar"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      );
                    }

                    if (collapsed) {
                      return (
                        <button
                          key={c.id}
                          type="button"
                          className={cn(
                            'group relative flex h-10 w-10 items-center justify-center rounded-xl transition-all cursor-pointer mx-auto p-0',
                            isSelected
                              ? 'bg-blue-50/90 text-blue-700 font-semibold border border-blue-200/80 shadow-2xs'
                              : 'text-slate-500 hover:bg-slate-100/80 hover:text-slate-900'
                          )}
                          onClick={() => onSelectConversa(c.id)}
                          title={c.titulo}
                        >
                          <MessageSquare
                            className={cn(
                              'h-4 w-4 shrink-0 transition-colors',
                              isSelected ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600'
                            )}
                          />
                        </button>
                      );
                    }

                    return (
                      <div
                        key={c.id}
                        className={cn(
                          'group relative flex items-center justify-between rounded-xl px-2.5 py-1.5 text-xs transition-colors cursor-pointer',
                          isSelected
                            ? 'bg-blue-50/80 font-semibold text-blue-900 border border-blue-200/60 shadow-2xs'
                            : 'text-slate-600 hover:bg-slate-100/70 hover:text-slate-900'
                        )}
                        onClick={() => onSelectConversa(c.id)}
                        onDoubleClick={(e) => handleStartRename(c, e)}
                        title={c.titulo}
                      >
                        <div className="flex items-center gap-2 overflow-hidden flex-1 min-w-0">
                          <MessageSquare
                            className={cn(
                              'h-3.5 w-3.5 shrink-0',
                              isSelected ? 'text-blue-600' : 'text-slate-400'
                            )}
                          />
                          <span className="truncate text-[12px]">{c.titulo}</span>
                        </div>

                        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                          <button
                            type="button"
                            onClick={(e) => handleStartRename(c, e)}
                            className="p-1 text-slate-400 hover:text-blue-600 hover:bg-blue-50/80 rounded transition-colors"
                            title="Renomear conversa"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onDeleteConversa(c.id);
                            }}
                            className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50/80 rounded transition-colors"
                            title="Excluir conversa"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* ABA 2: ARQUIVOS DO PROJETO (DRAG & DROP PARA O CHAT) */}
          {sidebarTab === 'arquivos' && !collapsed && (
            <div className="space-y-3">
              {/* Busca rápida de arquivos */}
              <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 shadow-2xs">
                <Search className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                <input
                  type="text"
                  value={fileQuery}
                  onChange={(e) => setFileQuery(e.target.value)}
                  placeholder="Filtrar arquivos..."
                  className="w-full bg-transparent text-xs text-slate-800 outline-none placeholder:text-slate-400 font-medium"
                />
                {fileQuery && (
                  <button
                    type="button"
                    onClick={() => setFileQuery('')}
                    className="text-slate-400 hover:text-slate-600"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              <div className="text-[10px] text-slate-400 font-mono px-1 flex items-center gap-1">
                <GripVertical className="h-3 w-3 text-blue-500 shrink-0" />
                <span>Arraste qualquer item para o Chat ou clique em @ para anexar.</span>
              </div>

              {/* 1. DATA SOURCES / DATALAKE */}
              {datalakeFiles.length > 0 && (
                <div>
                  <div className="px-1 mb-1 text-[10px] font-bold uppercase tracking-wider text-blue-600 flex items-center gap-1.5">
                    <Database className="h-3 w-3" />
                    <span>Data Sources ({datalakeFiles.length})</span>
                  </div>
                  <div className="space-y-1">
                    {datalakeFiles.map((file) => (
                      <div
                        key={file.caminho}
                        draggable
                        onDragStart={(e) => handleDragStart(e, file)}
                        className="group flex items-center justify-between rounded-xl border border-slate-200/80 bg-white p-2 text-xs hover:border-blue-300 hover:bg-blue-50/40 hover:shadow-2xs transition-all cursor-grab active:cursor-grabbing select-none"
                        title="Arraste para o chat ou use o botão @"
                      >
                        <div className="flex items-center gap-1.5 min-w-0 flex-1 pr-1">
                          <GripVertical className="h-3 w-3 text-slate-300 group-hover:text-blue-500 shrink-0" />
                          <Database className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                          <div className="min-w-0 flex-1">
                            <div className="font-mono text-[11px] font-bold text-slate-800 truncate">
                              {file.nome}
                            </div>
                            <div className="text-[10px] text-slate-400 truncate">
                              {file.tamanho_kb ? `${file.tamanho_kb} KB` : 'CSV / Parquet'}
                            </div>
                          </div>
                        </div>

                        {onAttachSource && (
                          <button
                            type="button"
                            onClick={() => onAttachSource(file)}
                            title="Anexar ao contexto do Chat"
                            className="shrink-0 flex h-6 w-6 items-center justify-center rounded-lg text-slate-400 hover:text-blue-700 hover:bg-blue-100/80 border border-transparent hover:border-blue-200 transition-colors cursor-pointer"
                          >
                            <Plus className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 2. METADADOS & RAG */}
              {metadataFiles.length > 0 && (
                <div>
                  <div className="px-1 mb-1 text-[10px] font-bold uppercase tracking-wider text-purple-600 flex items-center gap-1.5">
                    <BookOpen className="h-3 w-3" />
                    <span>Metadados &amp; RAG ({metadataFiles.length})</span>
                  </div>
                  <div className="space-y-1">
                    {metadataFiles.map((file) => (
                      <div
                        key={file.caminho}
                        draggable
                        onDragStart={(e) => handleDragStart(e, file)}
                        className="group flex items-center justify-between rounded-xl border border-slate-200/80 bg-white p-2 text-xs hover:border-purple-300 hover:bg-purple-50/40 hover:shadow-2xs transition-all cursor-grab active:cursor-grabbing select-none"
                        title="Arraste para o chat ou use o botão @"
                      >
                        <div className="flex items-center gap-1.5 min-w-0 flex-1 pr-1">
                          <GripVertical className="h-3 w-3 text-slate-300 group-hover:text-purple-500 shrink-0" />
                          <BookOpen className="h-3.5 w-3.5 text-purple-600 shrink-0" />
                          <div className="min-w-0 flex-1">
                            <div className="font-mono text-[11px] font-bold text-slate-800 truncate">
                              {file.nome}
                            </div>
                            <div className="text-[10px] text-slate-400 truncate">
                              {file.tipo?.toUpperCase() || 'DOC'} · RAG
                            </div>
                          </div>
                        </div>

                        {onAttachSource && (
                          <button
                            type="button"
                            onClick={() => onAttachSource(file)}
                            title="Anexar ao contexto do Chat"
                            className="shrink-0 flex h-6 w-6 items-center justify-center rounded-lg text-slate-400 hover:text-purple-700 hover:bg-purple-100/80 border border-transparent hover:border-purple-200 transition-colors cursor-pointer"
                          >
                            <Plus className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 3. SCRIPTS DO WORKSPACE */}
              {workspaceScripts.length > 0 && (
                <div>
                  <div className="px-1 mb-1 text-[10px] font-bold uppercase tracking-wider text-emerald-600 flex items-center gap-1.5">
                    <FileCode2 className="h-3 w-3" />
                    <span>Scripts do Workspace ({workspaceScripts.length})</span>
                  </div>
                  <div className="space-y-1">
                    {workspaceScripts.map((file) => {
                      const isSelected = file.nome === selectedWorkspaceFile;
                      return (
                        <div
                          key={file.caminho}
                          draggable
                          onDragStart={(e) => handleDragStart(e, file)}
                          onClick={() => {
                            if (onSelectWorkspaceFile) {
                              onSelectWorkspaceFile(isSelected ? '' : file.nome);
                            }
                          }}
                          className={cn(
                            'group flex items-center justify-between rounded-xl border p-2 text-xs transition-all cursor-grab active:cursor-grabbing select-none',
                            isSelected
                              ? 'border-emerald-300 bg-emerald-50/80 text-emerald-950 font-semibold shadow-2xs'
                              : 'border-slate-200/80 bg-white hover:border-emerald-300 hover:bg-emerald-50/30'
                          )}
                          title="Clique para selecionar ou arraste para o chat"
                        >
                          <div className="flex items-center gap-1.5 min-w-0 flex-1 pr-1">
                            <GripVertical className="h-3 w-3 text-slate-300 group-hover:text-emerald-500 shrink-0" />
                            <FileCode2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                            <div className="min-w-0 flex-1">
                              <div className="font-mono text-[11px] font-bold truncate">
                                {file.nome}
                              </div>
                              <div className="text-[10px] text-slate-400 truncate">
                                Python · {isSelected ? 'Script Ativo' : 'Workspace'}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-1 shrink-0">
                            {onAttachSource && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onAttachSource(file);
                                }}
                                title="Anexar ao contexto do Chat"
                                className="shrink-0 flex h-6 w-6 items-center justify-center rounded-lg text-slate-400 hover:text-emerald-700 hover:bg-emerald-100/80 border border-transparent hover:border-emerald-200 transition-colors cursor-pointer"
                              >
                                <Plus className="h-3.5 w-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer com Links Externos */}
        <div className="border-t border-slate-100 p-2.5">
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className={cn(
              'flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100/80 hover:text-slate-900 transition-colors',
              collapsed && 'justify-center px-0'
            )}
            title="Swagger API Docs"
          >
            <BookOpen className="h-3.5 w-3.5 shrink-0 text-slate-500" />
            {!collapsed && (
              <>
                <span className="flex-1 truncate">API Swagger</span>
                <ExternalLink className="h-3 w-3 text-slate-400" />
              </>
            )}
          </a>
        </div>
      </aside>
    </>
  );
}

export default SidebarNav;
