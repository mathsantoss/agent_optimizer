import React, {
  useState,
  useRef,
  useEffect,
  KeyboardEvent,
  DragEvent,
  useMemo,
} from 'react';
import {
  ArrowUp,
  Cpu,
  ChevronDown,
  Check,
  FileCode2,
  Database,
  BookOpen,
  Sparkles,
  AtSign,
  Slash,
  Plus,
  X,
  Search,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface GeminiModel {
  id: string;
  nome: string;
  descricao?: string;
  destaque?: string;
}

export interface WorkspaceFile {
  nome: string;
  caminho: string;
  linhas?: number;
}

export interface CatalogDataSource {
  key: string;
  nome: string;
  caminho: string;
  secao?: 'DATALAKE' | 'METADADOS' | 'WORKSPACE' | string;
  tipo?: string;
  tamanho_kb?: number;
  descricao?: string;
}

export interface PromptBarProps {
  onSendMessage: (text: string, attachedSources?: CatalogDataSource[]) => void;
  isLoading: boolean;
  models: GeminiModel[];
  currentModel: string;
  onSelectModel: (modelId: string) => void;
  workspaceFiles: WorkspaceFile[];
  selectedWorkspaceFile: string;
  onSelectWorkspaceFile: (filename: string) => void;
  catalogSources?: CatalogDataSource[];
  attachedSources: CatalogDataSource[];
  onAttachSource: (source: CatalogDataSource) => void;
  onRemoveAttachedSource: (caminho: string) => void;
  placeholder?: string;
  className?: string;
}

interface SlashCommandItem {
  key: string;
  name: string;
  desc: string;
  template: string;
  badge: string;
}

const SLASH_COMMANDS: SlashCommandItem[] = [
  {
    key: 'features',
    name: '/features',
    desc: 'Gerar pipeline completo de Feature Engineering para ML',
    template:
      'Crie um pipeline completo de Feature Engineering com base nos dados disponíveis e no dicionário RAG (incluindo RFM, ticket médio, interações financeiras e sazonalidade) para o script ativo.',
    badge: 'Kraken Code',
  },
  {
    key: 'criar',
    name: '/criar',
    desc: 'Criar script de modelagem ou exploração do zero',
    template:
      'Crie do zero o código completo em Python (Pandas) no script ativo, inspecionando os dados do catálogo e propondo as melhores features e transformações.',
    badge: 'Kraken Code',
  },
  {
    key: 'otimizar',
    name: '/otimizar',
    desc: 'Diagnosticar AST, vetorizar e rodar benchmark Antes vs Depois',
    template:
      'Inspecione o script ativo via AST, reescreva eliminando loops e gargalos de forma vetorizada e apresente a tabela de benchmark comparativo.',
    badge: 'Kraken Optimizer',
  },
  {
    key: 'explorar',
    name: '/explorar',
    desc: 'Análise exploratória profunda, estatísticas e qualidade',
    template:
      'Faça uma análise exploratória completa (estrutura, estatísticas descritivas, outliers IQR e regras de negócio) sobre os dados selecionados.',
    badge: 'Kraken Analyst',
  },
  {
    key: 'sql',
    name: '/sql',
    desc: 'Executar consulta SQL analítica sobre o catálogo',
    template:
      'Execute uma consulta SQL analítica sobre a tabela dados_vendas trazendo o ranking de faturamento, volume e ticket médio por categoria.',
    badge: 'Kraken Analyst',
  },
  {
    key: 'rag',
    name: '/rag',
    desc: 'Consultar Dicionário de Dados e regras no KrakenLake',
    template:
      'Consulte a base de conhecimento RAG e o dicionário de metadados para explicar o significado das colunas e sugerir features de negócio.',
    badge: 'RAG / Metadados',
  },
];

type CategoryFilter = 'TODOS' | 'DATALAKE' | 'METADADOS' | 'WORKSPACE';

export function PromptBar({
  onSendMessage,
  isLoading,
  models = [],
  currentModel,
  onSelectModel,
  workspaceFiles = [],
  selectedWorkspaceFile,
  onSelectWorkspaceFile,
  catalogSources = [],
  attachedSources = [],
  onAttachSource,
  onRemoveAttachedSource,
  placeholder = 'Pergunte sobre os dados, use @ para anexar contexto ou / para comandos...',
  className,
}: PromptBarProps) {
  const [text, setText] = useState('');
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  // Estados dos Menus Flutuantes
  const [activeMenu, setActiveMenu] = useState<'sources' | 'commands' | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('TODOS');
  const [searchFilter, setSearchFilter] = useState('');
  const [menuIndex, setMenuIndex] = useState(0);

  // Dropdowns de Modelo e Script
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [fileDropdownOpen, setFileDropdownOpen] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const composerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const menuContainerRef = useRef<HTMLDivElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);
  const fileDropdownRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const dictTimer = useRef<number | null>(null);

  // Consolidação de todas as fontes disponíveis
  const allSources: CatalogDataSource[] = useMemo(() => {
    const items: CatalogDataSource[] = [];
    const seen = new Set<string>();

    for (const src of catalogSources) {
      if (!seen.has(src.caminho)) {
        seen.add(src.caminho);
        items.push(src);
      }
    }

    const defaults: CatalogDataSource[] = [
      {
        key: 'dados_vendas.csv',
        nome: 'dados_vendas.csv',
        caminho: 'krakenlake/catalog/sources/dados_vendas.csv',
        secao: 'DATALAKE',
        tipo: 'csv',
        descricao: 'Base transacional de vendas, clientes, preços e categorias',
      },
      {
        key: 'dicionario_vendas.json',
        nome: 'dicionario_vendas.json',
        caminho: 'krakenlake/catalog/metadados/dicionario_vendas.json',
        secao: 'METADADOS',
        tipo: 'json',
        descricao: 'Dicionário semântico de colunas e regras de negócio (RAG)',
      },
    ];

    for (const d of defaults) {
      if (!seen.has(d.caminho) && !items.some((i) => i.nome === d.nome)) {
        seen.add(d.caminho);
        items.push(d);
      }
    }

    for (const wf of workspaceFiles) {
      const path = wf.caminho || `krakenlake/workspace/${wf.nome}`;
      if (!seen.has(path)) {
        seen.add(path);
        items.push({
          key: wf.nome,
          nome: wf.nome,
          caminho: path,
          secao: 'WORKSPACE',
          tipo: 'py',
          descricao: `Script do Workspace (${wf.linhas ?? 0} linhas)`,
        });
      }
    }

    return items;
  }, [catalogSources, workspaceFiles]);

  // Filtra itens do menu @
  const filteredSources = useMemo(() => {
    return allSources.filter((s) => {
      const matchesCategory =
        categoryFilter === 'TODOS' ||
        (categoryFilter === 'DATALAKE' && s.secao === 'DATALAKE') ||
        (categoryFilter === 'METADADOS' && s.secao === 'METADADOS') ||
        (categoryFilter === 'WORKSPACE' && s.secao === 'WORKSPACE');

      const q = searchFilter.trim().toLowerCase();
      const matchesSearch =
        !q ||
        s.nome.toLowerCase().includes(q) ||
        s.caminho.toLowerCase().includes(q) ||
        (s.descricao || '').toLowerCase().includes(q);

      return matchesCategory && matchesSearch;
    });
  }, [allSources, categoryFilter, searchFilter]);

  // Filtra comandos do menu /
  const filteredCommands = useMemo(() => {
    const q = searchFilter.trim().toLowerCase();
    if (!q) return SLASH_COMMANDS;
    return SLASH_COMMANDS.filter(
      (c) =>
        c.key.includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.desc.toLowerCase().includes(q) ||
        c.badge.toLowerCase().includes(q)
    );
  }, [searchFilter]);

  // Efeito Rainbow Sweep no Canvas ao trocar de modelo
  const playRainbowSweep = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width || 600;
    canvas.height = rect.height || 120;

    let start: number | null = null;
    const duration = 900;

    const step = (ts: number) => {
      if (!start) start = ts;
      const progress = (ts - start) / duration;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (progress < 1) {
        const x = -canvas.width * 0.4 + progress * (canvas.width * 1.8);
        const grad = ctx.createLinearGradient(x - 180, 0, x + 180, canvas.height);
        const alpha = Math.sin(progress * Math.PI) * 0.22;
        grad.addColorStop(0, 'rgba(239, 68, 68, 0)');
        grad.addColorStop(0.16, `rgba(249, 115, 22, ${alpha})`);
        grad.addColorStop(0.33, `rgba(234, 179, 8, ${alpha})`);
        grad.addColorStop(0.5, `rgba(34, 197, 94, ${alpha})`);
        grad.addColorStop(0.66, `rgba(6, 182, 212, ${alpha})`);
        grad.addColorStop(0.83, `rgba(59, 130, 246, ${alpha})`);
        grad.addColorStop(1, 'rgba(168, 85, 247, 0)');

        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        requestAnimationFrame(step);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    };

    requestAnimationFrame(step);
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(Math.max(scrollHeight, 44), 160)}px`;
    }
  }, [text]);

  // Click outside listener para fechar menus
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      if (menuContainerRef.current && !menuContainerRef.current.contains(target)) {
        // Se o clique não foi no botão de abrir menu
        const isTrigger = (event.target as HTMLElement)?.closest('[data-menu-trigger="true"]');
        if (!isTrigger) {
          setActiveMenu(null);
        }
      }
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(target)) {
        setModelDropdownOpen(false);
      }
      if (fileDropdownRef.current && !fileDropdownRef.current.contains(target)) {
        setFileDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    return () => {
      if (dictTimer.current) window.clearInterval(dictTimer.current);
    };
  }, []);

  // Monitora digitação de @ ou / no textarea para abrir os menus com busca contextual
  const handleTextChange = (val: string) => {
    setText(val);

    // Detecta token no cursor
    const match = /(^|\s)([@/])([\w._-]*)$/.exec(val);
    if (match) {
      const char = match[2];
      const query = match[3];
      if (char === '@') {
        setActiveMenu('sources');
        setSearchFilter(query);
        setMenuIndex(0);
      } else if (char === '/') {
        setActiveMenu('commands');
        setSearchFilter(query);
        setMenuIndex(0);
      }
    } else if (activeMenu && !searchFilter) {
      // Se não há token e não havia busca ativa, pode fechar
    }
  };

  // Alterna Menu @ Fontes
  const toggleSourcesMenu = () => {
    setModelDropdownOpen(false);
    setFileDropdownOpen(false);
    if (activeMenu === 'sources') {
      setActiveMenu(null);
      setSearchFilter('');
    } else {
      setActiveMenu('sources');
      setSearchFilter('');
      setCategoryFilter('TODOS');
      setMenuIndex(0);
    }
  };

  // Alterna Menu / Comandos
  const toggleCommandsMenu = () => {
    setModelDropdownOpen(false);
    setFileDropdownOpen(false);
    if (activeMenu === 'commands') {
      setActiveMenu(null);
      setSearchFilter('');
    } else {
      setActiveMenu('commands');
      setSearchFilter('');
      setMenuIndex(0);
    }
  };

  const pickSource = (src: CatalogDataSource) => {
    onAttachSource(src);
    // Se o usuário estava digitando um token @ no final, remove o token e foca
    const match = /(^|\s)@[\w._-]*$/.exec(text);
    if (match) {
      setText(text.slice(0, match.index) + (match[1] ? ' ' : ''));
    }
    setActiveMenu(null);
    setSearchFilter('');
    textareaRef.current?.focus();
  };

  const pickCommand = (cmd: SlashCommandItem) => {
    // Substitui o token / digitado ou define o prompt
    const match = /(^|\s)\/[\w._-]*$/.exec(text);
    if (match) {
      const before = text.slice(0, match.index) + (match[1] ? ' ' : '');
      setText(`${before}${cmd.template} `);
    } else {
      setText(cmd.template);
    }
    setActiveMenu(null);
    setSearchFilter('');
    textareaRef.current?.focus();
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if ((!trimmed && attachedSources.length === 0) || isLoading) return;

    onSendMessage(trimmed, [...attachedSources]);
    setText('');
    setActiveMenu(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (activeMenu) {
      const count = activeMenu === 'sources' ? filteredSources.length : filteredCommands.length;
      if (count > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          setMenuIndex((i) => (i + 1) % count);
          return;
        }
        if (e.key === 'ArrowUp') {
          e.preventDefault();
          setMenuIndex((i) => (i - 1 + count) % count);
          return;
        }
        if (e.key === 'Enter' || e.key === 'Tab') {
          e.preventDefault();
          const safeIdx = Math.min(menuIndex, count - 1);
          if (activeMenu === 'sources') {
            pickSource(filteredSources[safeIdx]);
          } else {
            pickCommand(filteredCommands[safeIdx]);
          }
          return;
        }
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setActiveMenu(null);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Drag and Drop sobre a PromptBar
  const handleDragOverComposer = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    if (!isDraggingOver) setIsDraggingOver(true);
  };

  const handleDragLeaveComposer = (e: DragEvent<HTMLDivElement>) => {
    if (composerRef.current && !composerRef.current.contains(e.relatedTarget as Node)) {
      setIsDraggingOver(false);
    }
  };

  const handleDropOnComposer = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDraggingOver(false);

    const rawSource = e.dataTransfer.getData('application/x-kraken-source');
    if (rawSource) {
      try {
        const parsed = JSON.parse(rawSource) as CatalogDataSource;
        onAttachSource(parsed);
        textareaRef.current?.focus();
        return;
      } catch {
        // segue para arquivos
      }
    }

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      Array.from(e.dataTransfer.files).forEach((f) => {
        onAttachSource({
          key: f.name,
          nome: f.name,
          caminho: `krakenlake/catalog/sources/${f.name}`,
          secao: 'DATALAKE',
          tipo: f.name.split('.').pop() || 'file',
        });
      });
      textareaRef.current?.focus();
    }
  };

  const handleLocalFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    Array.from(e.target.files).forEach((f) => {
      onAttachSource({
        key: f.name,
        nome: f.name,
        caminho: `krakenlake/catalog/sources/${f.name}`,
        secao: 'DATALAKE',
        tipo: f.name.split('.').pop() || 'file',
      });
    });
    e.target.value = '';
  };

  const activeModelObj = models.find((m) => m.id === currentModel) || {
    id: currentModel || 'gemini-2.5-flash',
    nome: currentModel || 'Gemini 2.5 Flash',
  };

  const canSend = (text.trim().length > 0 || attachedSources.length > 0) && !isLoading;

  return (
    <div className={cn('relative w-full max-w-4xl mx-auto px-4 sm:px-6 pb-4 select-none', className)}>
      {/* Input oculto para upload de arquivo local */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".csv,.parquet,.json,.md,.py,.txt"
        onChange={handleLocalFileSelect}
        className="hidden"
      />

      {/* POPUP FLUTUANTE CATEGORIZADO DE FONTES DE DADOS (@) */}
      {activeMenu === 'sources' && (
        <div
          ref={menuContainerRef}
          role="dialog"
          aria-label="Fontes de dados categorizadas"
          className="absolute bottom-full left-4 right-4 sm:left-6 sm:right-6 mb-2 max-w-xl rounded-2xl border border-slate-200/90 bg-white shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        >
          {/* Header do Menu com Busca e Botão Fechar */}
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/70 px-3 py-2">
            <div className="flex items-center gap-2 flex-1 mr-2">
              <Search className="h-3.5 w-3.5 text-slate-400 shrink-0" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => {
                  setSearchFilter(e.target.value);
                  setMenuIndex(0);
                }}
                placeholder="Filtrar datasets, metadados ou scripts..."
                className="w-full bg-transparent text-xs text-slate-800 placeholder:text-slate-400 outline-none font-medium"
                autoFocus
              />
            </div>
            <button
              type="button"
              onClick={() => setActiveMenu(null)}
              title="Fechar (Esc)"
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-200/60 hover:text-slate-700 transition-colors cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Abas de Categorias */}
          <div className="flex items-center gap-1 border-b border-slate-100 bg-white px-3 py-1.5 text-[11px] overflow-x-auto no-scrollbar">
            {(
              [
                { id: 'TODOS', label: 'Todos' },
                { id: 'DATALAKE', label: 'Datasets' },
                { id: 'METADADOS', label: 'Metadados / RAG' },
                { id: 'WORKSPACE', label: 'Workspace' },
              ] as const
            ).map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => {
                  setCategoryFilter(cat.id);
                  setMenuIndex(0);
                }}
                className={cn(
                  'rounded-lg px-2.5 py-1 font-semibold transition-colors cursor-pointer shrink-0',
                  categoryFilter === cat.id
                    ? 'bg-blue-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:bg-slate-100'
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Lista de Itens Filtrados com Highlight Confiável */}
          <div className="max-h-60 overflow-y-auto p-1.5 space-y-0.5">
            {filteredSources.length === 0 ? (
              <div className="py-6 text-center text-xs text-slate-400">
                Nenhum arquivo encontrado para &quot;{searchFilter}&quot;
              </div>
            ) : (
              filteredSources.map((s, i) => {
                const isSelected = i === menuIndex;
                const isAttached = attachedSources.some((a) => a.caminho === s.caminho);

                return (
                  <button
                    key={s.caminho}
                    ref={(el) => {
                      itemRefs.current[i] = el;
                    }}
                    type="button"
                    onMouseEnter={() => setMenuIndex(i)}
                    onClick={() => pickSource(s)}
                    className={cn(
                      'flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-xs transition-all cursor-pointer',
                      isSelected
                        ? 'bg-blue-50 text-blue-900 border border-blue-200/80 shadow-2xs'
                        : 'text-slate-700 hover:bg-slate-50 border border-transparent'
                    )}
                  >
                    <span
                      className={cn(
                        'flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border',
                        s.secao === 'DATALAKE'
                          ? 'border-blue-200 bg-blue-50 text-blue-600'
                          : s.secao === 'METADADOS'
                          ? 'border-purple-200 bg-purple-50 text-purple-600'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-600'
                      )}
                    >
                      {s.secao === 'DATALAKE' ? (
                        <Database className="h-3.5 w-3.5" />
                      ) : s.secao === 'METADADOS' ? (
                        <BookOpen className="h-3.5 w-3.5" />
                      ) : (
                        <FileCode2 className="h-3.5 w-3.5" />
                      )}
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-bold text-slate-800 truncate">
                          @{s.nome}
                        </span>
                        <span
                          className={cn(
                            'rounded px-1.5 py-0.2 text-[9px] font-semibold uppercase',
                            s.secao === 'DATALAKE'
                              ? 'bg-blue-100 text-blue-800'
                              : s.secao === 'METADADOS'
                              ? 'bg-purple-100 text-purple-800'
                              : 'bg-emerald-100 text-emerald-800'
                          )}
                        >
                          {s.secao === 'DATALAKE'
                            ? 'Dataset'
                            : s.secao === 'METADADOS'
                            ? 'RAG / Metadados'
                            : 'Workspace'}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 truncate mt-0.5">
                        {s.descricao || s.caminho}
                      </div>
                    </div>

                    {isAttached && (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700 shrink-0">
                        Anexado
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>

          <div className="border-t border-slate-100 bg-slate-50/70 px-3 py-1.5 text-[10px] text-slate-400 flex items-center justify-between">
            <span>Dica: você também pode digitar @ no prompt para abrir</span>
            <span className="font-mono">↑↓ navegar · Enter selecionar · Esc fechar</span>
          </div>
        </div>
      )}

      {/* POPUP FLUTUANTE DE COMANDOS RÁPIDOS (/) */}
      {activeMenu === 'commands' && (
        <div
          ref={menuContainerRef}
          role="dialog"
          aria-label="Comandos de especialista"
          className="absolute bottom-full left-4 right-4 sm:left-6 sm:right-6 mb-2 max-w-lg rounded-2xl border border-slate-200/90 bg-white shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        >
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/70 px-3 py-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Slash className="h-3.5 w-3.5 text-emerald-600" />
              <span>Comandos Especialistas</span>
            </span>
            <button
              type="button"
              onClick={() => setActiveMenu(null)}
              title="Fechar (Esc)"
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-200/60 hover:text-slate-700 transition-colors cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="max-h-60 overflow-y-auto p-1.5 space-y-0.5">
            {filteredCommands.map((c, i) => {
              const isSelected = i === menuIndex;
              return (
                <button
                  key={c.key}
                  type="button"
                  onMouseEnter={() => setMenuIndex(i)}
                  onClick={() => pickCommand(c)}
                  className={cn(
                    'flex w-full items-center justify-between gap-2.5 rounded-xl px-2.5 py-2 text-left text-xs transition-all cursor-pointer',
                    isSelected
                      ? 'bg-emerald-50 text-emerald-950 border border-emerald-200/80 shadow-2xs font-semibold'
                      : 'text-slate-700 hover:bg-slate-50 border border-transparent'
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-900">{c.name}</span>
                      <span className="rounded bg-slate-100 px-1.5 py-0.2 text-[9px] font-semibold text-slate-600">
                        {c.badge}
                      </span>
                    </div>
                    <div className="mt-0.5 text-[11px] text-slate-500 truncate font-normal">
                      {c.desc}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="border-t border-slate-100 bg-slate-50/70 px-3 py-1.5 text-[10px] text-slate-400 flex items-center justify-between">
            <span>Dica: digite / no prompt para acionar diretamente</span>
            <span className="font-mono">Enter usar · Esc fechar</span>
          </div>
        </div>
      )}

      {/* CONTAINER PRINCIPAL DO COMPOSER */}
      <div
        ref={composerRef}
        onDragOver={handleDragOverComposer}
        onDragLeave={handleDragLeaveComposer}
        onDrop={handleDropOnComposer}
        className={cn(
          'relative rounded-2xl border bg-white shadow-sm transition-all overflow-visible',
          isDraggingOver
            ? 'border-blue-500 ring-4 ring-blue-100 bg-blue-50/20'
            : 'border-slate-300/90 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100/80'
        )}
      >
        {/* Canvas de animação Rainbow Sweep */}
        <canvas
          ref={canvasRef}
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 h-full w-full rounded-2xl z-0"
        />

        {/* Overlay visual quando arrastando arquivo do menu lateral sobre o composer */}
        {isDraggingOver && (
          <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center rounded-2xl bg-blue-600/10 backdrop-blur-[1px]">
            <div className="flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-xs font-bold text-blue-700 shadow-lg border border-blue-200">
              <Database className="h-4 w-4 animate-bounce text-blue-600" />
              <span>Solte aqui para anexar a fonte ao contexto do agente</span>
            </div>
          </div>
        )}

        {/* Barra Superior: Seletor de Modelo Gemini + Seletor de Script Workspace */}
        <div className="relative z-10 flex flex-wrap items-center justify-between border-b border-slate-100 px-3 py-1.5 text-xs gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            {/* Seletor do Modelo Gemini */}
            <div className="relative" ref={modelDropdownRef}>
              <button
                type="button"
                onClick={() => {
                  setModelDropdownOpen(!modelDropdownOpen);
                  setFileDropdownOpen(false);
                  setActiveMenu(null);
                }}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-slate-50/70 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                title="Trocar versão do modelo Gemini"
              >
                <Cpu className="h-3.5 w-3.5 text-blue-600" />
                <span className="truncate max-w-[130px] sm:max-w-none">{activeModelObj.nome}</span>
                <ChevronDown className="h-3 w-3 text-slate-400" />
              </button>

              {modelDropdownOpen && (
                <div className="absolute bottom-full left-0 mb-1.5 w-80 max-h-80 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-1.5 shadow-2xl z-50">
                  <div className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    Família Gemini · Seleção Ativa
                  </div>
                  {models.map((mod) => {
                    const isSelected = mod.id === currentModel;
                    return (
                      <button
                        key={mod.id}
                        type="button"
                        onClick={() => {
                          onSelectModel(mod.id);
                          setModelDropdownOpen(false);
                          playRainbowSweep();
                        }}
                        className={cn(
                          'flex w-full items-start justify-between rounded-xl px-2.5 py-2 text-left text-xs transition-colors cursor-pointer',
                          isSelected
                            ? 'bg-blue-50 text-blue-900 font-semibold'
                            : 'text-slate-700 hover:bg-slate-50'
                        )}
                      >
                        <div className="flex-1 pr-2">
                          <div className="flex items-center gap-1.5">
                            <span>{mod.nome}</span>
                            {mod.destaque && (
                              <span className="rounded bg-blue-100/70 px-1.5 py-0.2 text-[10px] font-medium text-blue-700">
                                {mod.destaque}
                              </span>
                            )}
                          </div>
                          {mod.descricao && (
                            <div className="mt-0.5 text-[11px] font-normal text-slate-500">
                              {mod.descricao}
                            </div>
                          )}
                        </div>
                        {isSelected && <Check className="mt-0.5 h-3.5 w-3.5 text-blue-600 shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Seletor Dinâmico de Script no Workspace */}
            <div className="relative" ref={fileDropdownRef}>
              <button
                type="button"
                onClick={() => {
                  setFileDropdownOpen(!fileDropdownOpen);
                  setModelDropdownOpen(false);
                  setActiveMenu(null);
                }}
                className={cn(
                  'flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition-colors cursor-pointer',
                  selectedWorkspaceFile
                    ? 'border-emerald-200 bg-emerald-50/80 text-emerald-900 hover:bg-emerald-100/70'
                    : 'border-slate-200/80 bg-slate-50/70 text-slate-600 hover:bg-slate-100'
                )}
                title="Selecionar script Python alvo no workspace"
              >
                <FileCode2 className={cn('h-3.5 w-3.5', selectedWorkspaceFile ? 'text-emerald-600' : 'text-slate-400')} />
                <span className={cn('truncate max-w-[140px] sm:max-w-none', selectedWorkspaceFile ? 'font-mono text-emerald-800' : 'text-slate-500 font-normal')}>
                  {selectedWorkspaceFile || 'Nenhum script alvo'}
                </span>
                {selectedWorkspaceFile ? (
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectWorkspaceFile('');
                    }}
                    title="Desvincular script ativo"
                    className="ml-0.5 rounded-full p-0.5 text-slate-400 hover:bg-emerald-200/70 hover:text-emerald-900 transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </span>
                ) : (
                  <ChevronDown className="h-3 w-3 text-slate-400" />
                )}
              </button>

              {fileDropdownOpen && (
                <div className="absolute bottom-full left-0 mb-1.5 w-72 max-h-64 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-1.5 shadow-2xl z-50">
                  <div className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    Scripts do Workspace (krakenlake/workspace/)
                  </div>

                  {/* Opção Padrão: Nenhum script selecionado */}
                  <button
                    type="button"
                    onClick={() => {
                      onSelectWorkspaceFile('');
                      setFileDropdownOpen(false);
                    }}
                    className={cn(
                      'flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-xs transition-colors cursor-pointer border-b border-slate-100 mb-1',
                      !selectedWorkspaceFile
                        ? 'bg-slate-100 text-slate-900 font-semibold'
                        : 'text-slate-600 hover:bg-slate-50'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <FileCode2 className="h-3.5 w-3.5 text-slate-400" />
                      <span>Nenhum script (Contexto geral)</span>
                    </div>
                    {!selectedWorkspaceFile && <Check className="h-3.5 w-3.5 text-slate-700 shrink-0" />}
                  </button>

                  {workspaceFiles.map((wf) => {
                    const isSelected = wf.nome === selectedWorkspaceFile;
                    return (
                      <button
                        key={wf.nome}
                        type="button"
                        onClick={() => {
                          onSelectWorkspaceFile(wf.nome);
                          setFileDropdownOpen(false);
                        }}
                        className={cn(
                          'flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-xs transition-colors cursor-pointer',
                          isSelected
                            ? 'bg-emerald-50 text-emerald-900 font-semibold'
                            : 'text-slate-700 hover:bg-slate-50'
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <FileCode2 className="h-3.5 w-3.5 text-emerald-600" />
                          <span className="font-mono text-xs">{wf.nome}</span>
                        </div>
                        {wf.linhas !== undefined && (
                          <span className="text-[10px] text-slate-400 font-mono">
                            {wf.linhas} linhas
                          </span>
                        )}
                        {isSelected && <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Badge Informativo */}
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-mono">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>krakenlake/catalog</span>
          </div>
        </div>

        {/* Chips de Fontes de Dados Anexadas ao Contexto */}
        {attachedSources.length > 0 && (
          <div className="relative z-10 flex flex-wrap items-center gap-1.5 px-3 pt-2.5">
            {attachedSources.map((src) => (
              <span
                key={src.caminho}
                className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50/90 px-2.5 py-1 text-[11px] font-medium text-blue-900 shadow-2xs"
              >
                {src.secao === 'METADADOS' ? (
                  <BookOpen className="h-3 w-3 text-purple-600" />
                ) : src.secao === 'WORKSPACE' ? (
                  <FileCode2 className="h-3 w-3 text-emerald-600" />
                ) : (
                  <Database className="h-3 w-3 text-blue-600" />
                )}
                <span className="font-mono text-[11px]">@{src.nome}</span>
                <button
                  type="button"
                  onClick={() => onRemoveAttachedSource(src.caminho)}
                  aria-label={`Remover ${src.nome}`}
                  className="ml-0.5 rounded-full p-0.5 text-blue-600 hover:bg-blue-200/70 hover:text-blue-900 cursor-pointer"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Textarea e Ações */}
        <div className="relative z-10 flex flex-col p-3">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => handleTextChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            disabled={isLoading}
            className="w-full resize-none border-0 bg-transparent text-sm text-slate-800 placeholder:text-slate-400 focus:outline-hidden focus:ring-0 leading-relaxed"
            style={{ minHeight: '44px' }}
          />

          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 pt-1">
            {/* Botões de Ação: + (Upload), @ Fontes (Toggle), / Comandos (Toggle) */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                title="Anexar arquivo local ao contexto"
                className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200/80 bg-slate-50/80 text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors cursor-pointer"
              >
                <Plus className="h-3.5 w-3.5" />
              </button>

              <button
                type="button"
                data-menu-trigger="true"
                onClick={toggleSourcesMenu}
                title="Alternar menu de fontes e metadados (@)"
                className={cn(
                  'inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition-all cursor-pointer',
                  activeMenu === 'sources'
                    ? 'border-blue-400 bg-blue-100 text-blue-800 shadow-2xs ring-1 ring-blue-300'
                    : 'border-slate-200/80 bg-slate-50/80 text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                )}
              >
                <AtSign className="h-3.5 w-3.5 text-blue-600" />
                <span>Fontes</span>
                <ChevronDown
                  className={cn(
                    'h-3 w-3 text-slate-400 transition-transform duration-150',
                    activeMenu === 'sources' && 'rotate-180'
                  )}
                />
              </button>

              <button
                type="button"
                data-menu-trigger="true"
                onClick={toggleCommandsMenu}
                title="Alternar menu de comandos (/)"
                className={cn(
                  'inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition-all cursor-pointer',
                  activeMenu === 'commands'
                    ? 'border-emerald-400 bg-emerald-100 text-emerald-800 shadow-2xs ring-1 ring-emerald-300'
                    : 'border-slate-200/80 bg-slate-50/80 text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                )}
              >
                <Slash className="h-3.5 w-3.5 text-emerald-600" />
                <span>Comandos</span>
                <ChevronDown
                  className={cn(
                    'h-3 w-3 text-slate-400 transition-transform duration-150',
                    activeMenu === 'commands' && 'rotate-180'
                  )}
                />
              </button>

              <span className="hidden lg:inline-block ml-2 text-[11px] text-slate-400">
                Arraste arquivos da barra lateral ou use <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-600">@</kbd> e <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-600">/</kbd>
              </span>
            </div>

            {/* Enviar */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                className={cn(
                  'inline-flex items-center justify-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold shadow-xs transition-all select-none',
                  canSend
                    ? 'bg-blue-600 text-white hover:bg-blue-700 active:scale-98 cursor-pointer'
                    : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                )}
              >
                <span>Enviar</span>
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PromptBar;
