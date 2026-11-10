import React, { useState, useRef, useEffect } from 'react';
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
  ChevronRight,
  Sparkles,
  ChevronDown,
  X,
  FileCode2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

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
  onNavigate: (view: 'chat' | 'dados' | 'observabilidade') => void;
  onOpenObservability: () => void;
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
  onNavigate,
  onOpenObservability,
  className,
}: SidebarNavProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (searchOpen) {
      searchInputRef.current?.focus();
    }
  }, [searchOpen]);

  const visibleConversas = conversas.filter((c) =>
    (c.titulo || '').toLowerCase().includes(query.trim().toLowerCase())
  );

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
        {/* Workspace Switcher / Header (Estilo Beautiful UI) */}
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
              className="group relative flex h-9 w-9 items-center justify-center rounded-xl transition-all cursor-pointer hover:ring-2 hover:ring-blue-400 p-0.5"
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

        {/* Ação Primária: New Chat (Beautiful UI) */}
        <div className="p-2.5">
          <button
            type="button"
            onClick={onNovaConversa}
            className={cn(
              'flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200/90 bg-slate-50/80 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 shadow-2xs transition-all cursor-pointer active:scale-98',
              collapsed && 'px-0'
            )}
            title="Iniciar Nova Conversa (Ctrl+N)"
          >
            <Plus className="h-4 w-4 text-blue-600" />
            {!collapsed && <span>Nova Conversa</span>}
          </button>
        </div>

        {/* Menu de Navegação Primária */}
        <nav className="px-2 space-y-0.5 border-b border-slate-100 pb-2">
          <button
            type="button"
            onClick={() => onNavigate('chat')}
            className={cn(
              'flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-medium transition-colors cursor-pointer',
              activeView === 'chat'
                ? 'bg-blue-50 text-blue-700 font-semibold'
                : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900',
              collapsed && 'justify-center px-0'
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
              'flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-medium transition-colors cursor-pointer',
              activeView === 'dados'
                ? 'bg-purple-50 text-purple-700 font-semibold'
                : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900',
              collapsed && 'justify-center px-0'
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
              'flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-medium transition-colors cursor-pointer',
              activeView === 'observabilidade'
                ? 'bg-emerald-50 text-emerald-700 font-semibold'
                : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900',
              collapsed && 'justify-center px-0'
            )}
            title="Painel de Observabilidade (Grafana & Telemetria)"
          >
            <ShieldCheck className="h-4 w-4 shrink-0" />
            {!collapsed && <span>Observabilidade</span>}
          </button>
        </nav>

        {/* Seção de Sessões Recentes com Chat Search Storyboard */}
        <div className="flex-1 overflow-y-auto px-2 py-2">
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
                    Sessões Recentes
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
          <div className="space-y-0.5">
            {visibleConversas.length === 0 ? (
              !collapsed && (
                <div className="px-2 py-4 text-center text-xs text-slate-400">
                  {query ? 'Nenhum chat encontrado' : 'Nenhuma conversa ativa'}
                </div>
              )
            ) : (
              (collapsed ? visibleConversas.slice(0, 3) : visibleConversas).map((c) => {
                const isSelected = c.id === conversaAtivaId;
                return (
                  <div
                    key={c.id}
                    className={cn(
                      'group relative flex items-center justify-between rounded-xl px-2.5 py-1.5 text-xs transition-colors cursor-pointer',
                      isSelected
                        ? 'bg-blue-50/80 font-semibold text-blue-900 border border-blue-200/60 shadow-2xs'
                        : 'text-slate-600 hover:bg-slate-100/70 hover:text-slate-900',
                      collapsed && 'justify-center px-0'
                    )}
                    onClick={() => onSelectConversa(c.id)}
                    title={c.titulo}
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <MessageSquare
                        className={cn(
                          'h-3.5 w-3.5 shrink-0',
                          isSelected ? 'text-blue-600' : 'text-slate-400'
                        )}
                      />
                      {!collapsed && (
                        <span className="truncate text-[12px]">{c.titulo}</span>
                      )}
                    </div>

                    {!collapsed && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteConversa(c.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 transition-opacity"
                        title="Excluir conversa"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
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
