import React, { useState } from 'react';
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
  const [searchTerm, setSearchTerm] = useState('');
  const [collapsed, setCollapsed] = useState(false);

  const filteredConversas = conversas.filter((c) =>
    (c.titulo || '').toLowerCase().includes(searchTerm.toLowerCase())
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
        className={cn(
          'flex h-screen flex-col border-r border-slate-200/90 bg-[#f8fafc] transition-all duration-300 z-40 select-none',
          'fixed inset-y-0 left-0 md:relative',
          mobileOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0',
          collapsed ? 'md:w-16' : 'w-72',
          className
        )}
      >
      {/* Header com Logo e Branding */}
      <div
        className={cn(
          'flex h-14 items-center border-b border-slate-200/80',
          collapsed ? 'justify-center px-2' : 'justify-between px-4'
        )}
      >
        {!collapsed ? (
          <>
            <div
              className="flex items-center gap-2.5 cursor-pointer"
              onClick={() => onNavigate('chat')}
            >
              <img
                src="/web/ui/kraken-copilot.svg"
                alt="Kraken Copilot"
                className="h-8 w-8 rounded-xl object-contain shadow-xs"
              />
              <div>
                <h1 className="text-xs font-bold tracking-tight text-slate-900">
                  Kraken Copilot
                </h1>
                <span className="text-[10px] font-medium text-slate-400">
                  Analytics & Pipelines
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setCollapsed(true)}
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-200/60 hover:text-slate-600 transition-colors cursor-pointer"
              title="Recolher barra lateral"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => setCollapsed(false)}
            className="flex h-9 w-9 items-center justify-center rounded-xl p-0.5 shadow-2xs hover:scale-105 transition-all cursor-pointer"
            title="Expandir barra lateral"
          >
            <img
              src="/web/ui/kraken-copilot.svg"
              alt="Kraken Copilot"
              className="h-8 w-8 rounded-xl object-contain"
            />
          </button>
        )}
      </div>

      {/* Ação Nova Conversa */}
      <div className="p-2.5">
        <button
          type="button"
          onClick={() => {
            onNovaConversa();
            onNavigate('chat');
          }}
          className={cn(
            'flex items-center justify-center rounded-xl border border-slate-200/90 bg-white py-2 text-xs font-semibold text-slate-700 shadow-2xs transition-all hover:border-blue-400 hover:bg-blue-50/50 active:scale-98 cursor-pointer',
            collapsed ? 'h-10 w-10 mx-auto' : 'w-full gap-2 px-3'
          )}
          title="Nova Conversa (⌘N / Ctrl+N)"
        >
          <Plus className="h-4 w-4 text-blue-600" />
          {!collapsed && <span>Nova Conversa</span>}
        </button>
      </div>

      {/* Busca rápida de sessões */}
      {!collapsed && (
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar histórico..."
              className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-800 placeholder:text-slate-400 focus:border-blue-500 focus:outline-hidden"
            />
          </div>
        </div>
      )}

      {/* Lista de Sessões Recentes */}
      <div className="flex-1 overflow-y-auto px-2 py-1">
        {!collapsed && (
          <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Sessões Recentes
          </div>
        )}

        <div className="space-y-1">
          {filteredConversas.length === 0 ? (
            !collapsed && (
              <div className="px-3 py-4 text-center text-xs text-slate-400">
                Nenhuma conversa encontrada
              </div>
            )
          ) : (
            filteredConversas.map((conversa) => {
              const isActive = conversa.id === conversaAtivaId && activeView === 'chat';
              return (
                <div
                  key={conversa.id}
                  className={cn(
                    'group relative flex items-center justify-between rounded-xl px-2.5 py-2 text-xs transition-colors cursor-pointer select-none',
                    isActive
                      ? 'bg-blue-50/90 font-medium text-blue-900 shadow-2xs'
                      : 'text-slate-600 hover:bg-slate-200/50 hover:text-slate-900',
                    collapsed && 'justify-center px-0'
                  )}
                  onClick={() => {
                    onSelectConversa(conversa.id);
                    onNavigate('chat');
                  }}
                  title={conversa.titulo}
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    <MessageSquare
                      className={cn(
                        'h-4 w-4 shrink-0',
                        isActive ? 'text-blue-600' : 'text-slate-400'
                      )}
                    />
                    {!collapsed && (
                      <span className="truncate text-[12px]">{conversa.titulo || 'Nova conversa'}</span>
                    )}
                  </div>

                  {!collapsed && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversa(conversa.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 rounded p-1 text-slate-400 hover:bg-rose-100 hover:text-rose-600 transition-all cursor-pointer"
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

      {/* Navegação Inferior de Vistas */}
      <div className="border-t border-slate-200/80 p-2 space-y-1">
        <button
          type="button"
          onClick={() => onNavigate('dados')}
          className={cn(
            'flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-semibold transition-colors cursor-pointer',
            activeView === 'dados'
              ? 'bg-purple-50 text-purple-900 shadow-2xs'
              : 'text-slate-700 hover:bg-slate-200/60',
            collapsed && 'justify-center px-0'
          )}
          title="Explorador de Dados"
        >
          <Database className="h-4 w-4 text-purple-600 shrink-0" />
          {!collapsed && <span>Explorador de Dados</span>}
        </button>

        <button
          type="button"
          onClick={() => onNavigate('observabilidade')}
          className={cn(
            'flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-semibold transition-colors cursor-pointer',
            activeView === 'observabilidade'
              ? 'bg-emerald-50 text-emerald-900 shadow-2xs'
              : 'text-slate-700 hover:bg-slate-200/60',
            collapsed && 'justify-center px-0'
          )}
          title="Observabilidade & Auditoria (Grafana)"
        >
          <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
          {!collapsed && (
            <span className="flex flex-1 items-center justify-between">
              <span>Observabilidade</span>
            </span>
          )}
        </button>

        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          className={cn(
            'flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer',
            collapsed && 'justify-center px-0'
          )}
          title="Documentação OpenAPI (Swagger)"
        >
          <BookOpen className="h-4 w-4 text-slate-500 shrink-0" />
          {!collapsed && (
            <span className="flex flex-1 items-center justify-between">
              <span>API Swagger</span>
              <ExternalLink className="h-3 w-3 text-slate-400" />
            </span>
          )}
        </a>
      </div>
    </aside>
    </>
  );
}

export default SidebarNav;
