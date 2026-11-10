import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Bot,
  User,
  Search,
  ExternalLink,
  Copy,
  Check,
  RotateCcw,
  Zap,
  Activity,
  Database,
  MessageSquare,
  FileCode,
  FileCode2,
  Menu,
  ShieldCheck,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { SidebarNav, ConversaItem } from './components/SidebarNav';
import { PromptBar, GeminiModel, WorkspaceFile, CatalogDataSource } from './components/PromptBar';
import { ThinkingState, ThinkingStep } from './components/ThinkingState';
import { LoadingState } from './components/LoadingState';
import { StreamingText } from './components/StreamingText';
import { ToolChips, ToolCallItem, DiffInfo } from './components/ToolChips';
import { ApprovalCard } from './components/ApprovalCard';
import { InsightCards, BenchmarkMetrics } from './components/InsightCards';
import { DataExplorerView } from './components/DataExplorerView';
import { InvestigationView } from './components/InvestigationView';
import { ObservabilityView } from './components/ObservabilityView';
import { SideCodePanel } from './components/SideCodePanel';

export interface Mensagem {
  id?: string;
  autor?: 'user' | 'assistant' | 'sistema';
  role?: string;
  texto: string;
  anexos?: CatalogDataSource[];
  especialista?: string;
  execucao_id?: string;
  has_approval_request?: boolean;
  proposed_code?: string;
  diff_info?: DiffInfo;
  ferramentas_executadas?: ToolCallItem[];
  sugestoes_acoes?: string[];
  benchmark_metrics?: BenchmarkMetrics;
  timestamp?: string;
}

// Limpa qualquer prefixo técnico ou colchetes da bolha do usuário
function cleanUserBubbleText(text: string): string {
  if (!text) return '';
  return text.replace(/^\[(?:Fontes e contexto|Script alvo)[^\]]+\]\s*/i, '').trim();
}

// Extrai fontes anexadas para renderizar como badges discretos
function extractBubbleAttachments(msg: Mensagem): string[] {
  if (msg.anexos && msg.anexos.length > 0) {
    return msg.anexos.map((a) => a.nome);
  }
  const metaAnexos = (msg as any).metadados?.anexos;
  if (Array.isArray(metaAnexos) && metaAnexos.length > 0) {
    return metaAnexos.map((c: string) => c.split('/').pop() || c);
  }
  const match = /^\[Fontes e contexto anexados \(@\):\s*([^\]]+)\]/i.exec(msg.texto || '');
  if (match) {
    return match[1]
      .split(',')
      .map((s) => s.trim().split(' ')[0])
      .filter(Boolean);
  }
  return [];
}

// Helper para extrair sugestões rápidas de ação caso o backend não tenha enviado explicitamente
function extractSuggestionsFromText(text: string): string[] {
  if (!text) return [];
  const triggerRegex =
    /(?:o que você gostaria|posso ajudar com|posso realizar|próximos passos|sugestões|gostaria de|como deseja prosseguir|ações recomendadas|opções a seguir|posso ajudar|posso te ajudar)/i;
  const match = triggerRegex.exec(text);
  const slice = match ? text.slice(match.index) : text.split('\n').slice(-6).join('\n');
  const suggestions: string[] = [];

  for (const line of slice.split('\n')) {
    const listMatch = line.trim().match(/^(?:[-*•]|\d+\.)\s+(.+)$/);
    if (listMatch) {
      const clean = listMatch[1]
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/^["'«“]|["'»”]$/g, '')
        .trim();
      if (clean.length >= 6 && clean.length <= 120 && !clean.toLowerCase().startsWith('http')) {
        suggestions.push(clean);
      }
    }
  }

  // Se mencionou operações analíticas entre parênteses
  if (text.toLowerCase().includes('structure') && text.toLowerCase().includes('statistics')) {
    suggestions.push('Faça uma análise de estrutura completa (structure)');
    suggestions.push('Gere o resumo estatístico detalhado com outliers (statistics)');
    suggestions.push('Exiba uma amostra das primeiras linhas (sample)');
  }

  return Array.from(new Set(suggestions)).slice(0, 5);
}

// Remove texto de opções finais repetitivas do corpo da mensagem caso os botões de ação já estejam presentes
function cleanDisplayText(text: string, hasSuggestions: boolean): string {
  if (!text || !hasSuggestions) return text;
  const triggerRegex =
    /(?:\n\s*)*\n*(?:o que você gostaria de fazer a seguir\??|posso ajudar com:?|gostaria de aprofundar|como deseja prosseguir\??|próximos passos recomendados:?|ações que você pode realizar:?)[\s\S]*$/i;
  return text.replace(triggerRegex, '').trim();
}

function formatTimestamp(ts?: string): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    if (!isNaN(d.getTime())) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
  } catch {}
  return ts.length > 8 ? ts.slice(11, 19) : ts;
}

export function App() {
  const [activeView, setActiveView] = useState<'chat' | 'dados' | 'investigacao' | 'observabilidade'>('chat');
  const [activeExecucaoId, setActiveExecucaoId] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [conversas, setConversas] = useState<ConversaItem[]>([]);
  const [conversaAtivaId, setConversaAtivaId] = useState<string | null>(null);
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Thinking State
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
  const [activeAgent, setActiveAgent] = useState<string>('Kraken Copilot');

  // Model Selector
  const [models, setModels] = useState<GeminiModel[]>([]);
  const [currentModel, setCurrentModel] = useState<string>('gemini-2.5-flash');

  // Workspace Python Files & Catalog Data Sources
  const [workspaceFiles, setWorkspaceFiles] = useState<WorkspaceFile[]>([]);
  const [selectedWorkspaceFile, setSelectedWorkspaceFile] = useState<string>('');
  const [catalogSources, setCatalogSources] = useState<CatalogDataSource[]>([]);
  const [attachedSources, setAttachedSources] = useState<CatalogDataSource[]>([]);

  const handleAttachSource = (source: CatalogDataSource) => {
    setAttachedSources((prev) => {
      if (prev.some((s) => s.caminho === source.caminho)) return prev;
      return [...prev, source];
    });
    if (source.secao === 'WORKSPACE' && source.nome.endsWith('.py')) {
      setSelectedWorkspaceFile(source.nome);
    }
  };

  const handleRemoveAttachedSource = (caminho: string) => {
    setAttachedSources((prev) => prev.filter((s) => s.caminho !== caminho));
  };

  // Side Code Panel State (Visualização lateral em tempo real)
  const [sideCodeOpen, setSideCodeOpen] = useState(false);
  const [sideCodeContent, setSideCodeContent] = useState('');
  const [sideCodeDiff, setSideCodeDiff] = useState<DiffInfo | undefined>(undefined);
  const [sideCodeHasApproval, setSideCodeHasApproval] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (activeView === 'chat') {
      scrollToBottom();
    }
  }, [mensagens, thinkingSteps, isLoading, activeView]);

  // Inicialização
  useEffect(() => {
    carregarModelos();
    carregarWorkspaceFiles();
    carregarCatalogSources();
    carregarConversas(false);
  }, []);

  useEffect(() => {
    if (selectedWorkspaceFile) {
      carregarWorkspaceCode(selectedWorkspaceFile);
    }
  }, [selectedWorkspaceFile]);

  const carregarWorkspaceCode = async (filename: string) => {
    if (!filename) {
      setSideCodeContent('');
      setSideCodeDiff(undefined);
      return;
    }
    try {
      setSideCodeDiff(undefined);
      setSideCodeHasApproval(false);
      const res = await fetch(`/api/dados/arquivo?caminho=krakenlake/workspace/${filename}`);
      if (res.ok) {
        const data = await res.json();
        setSideCodeContent(typeof data.conteudo === 'string' ? data.conteudo : '');
      } else {
        setSideCodeContent('');
      }
    } catch {
      setSideCodeContent('');
    }
  };

  // Atalho global Ctrl+N / Cmd+N
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        criarNovaConversa();
        setActiveView('chat');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [conversas]);

  const carregarModelos = async () => {
    try {
      const res = await fetch('/api/modelos');
      if (res.ok) {
        const data = await res.json();
        setModels(data.modelos || []);
        if (data.modelo_atual || data.modelo_ativo) {
          setCurrentModel(data.modelo_atual || data.modelo_ativo);
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar modelos Gemini:', err);
    }
  };

  const carregarWorkspaceFiles = async (keepSelection: boolean = false) => {
    try {
      const res = await fetch('/api/dados/workspace/arquivos');
      if (res.ok) {
        const data = await res.json();
        const files: WorkspaceFile[] = data.arquivos || [];
        setWorkspaceFiles(files);
        if (!keepSelection && files.length > 0 && !selectedWorkspaceFile) {
          setSelectedWorkspaceFile(files[0].nome);
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar arquivos do workspace:', err);
    }
  };

  const carregarCatalogSources = async () => {
    try {
      const res = await fetch('/api/dados/arquivos');
      if (res.ok) {
        const data = await res.json();
        const rawList = data.arquivos || [];
        const mapped: CatalogDataSource[] = rawList
          .filter((a: any) => a.secao === 'DATALAKE' || a.secao === 'METADADOS' || a.secao === 'DOCUMENTAÇÕES')
          .map((a: any) => ({
            key: a.nome,
            nome: a.nome,
            caminho: a.caminho,
            secao: a.secao === 'DOCUMENTAÇÕES' ? 'METADADOS' : a.secao,
            tipo: a.tipo,
            tamanho_kb: a.tamanho_kb,
            descricao: `${a.categoria_nome || a.secao} · ${a.tamanho_kb ?? 0} KB`,
          }));
        setCatalogSources(mapped);
      }
    } catch (err) {
      console.warn('Erro ao carregar fontes do catálogo:', err);
    }
  };

  const carregarConversas = async (manterAtiva: boolean = false) => {
    try {
      const res = await fetch('/api/conversas');
      if (res.ok) {
        const data = await res.json();
        const lista: ConversaItem[] = data.conversas || [];
        setConversas(lista);
        if (manterAtiva && conversaAtivaId) {
          return;
        }

        // Tenta restaurar a conversa ativa salva localmente após F5
        const savedId = localStorage.getItem('kraken_active_session_id');
        if (savedId && lista.some((c) => c.id === savedId)) {
          selecionarConversa(savedId);
        } else {
          // Permanece em tela de chat limpa sem criar sessão fantasma no banco
          setConversaAtivaId(null);
          setMensagens([]);
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar conversas:', err);
    }
  };

  const selecionarConversa = async (id: string) => {
    setConversaAtivaId(id);
    localStorage.setItem('kraken_active_session_id', id);
    setActiveView('chat');
    try {
      const res = await fetch(`/api/conversas/${id}`);
      if (res.ok) {
        const data = await res.json();
        setMensagens(data.mensagens || []);
      }
    } catch (err) {
      console.error('Erro ao buscar conversa:', err);
    }
  };

  const criarNovaConversa = () => {
    // Inicia um chat vazio em memória sem poluir o banco até o envio da 1ª mensagem
    setConversaAtivaId(null);
    setMensagens([]);
    localStorage.removeItem('kraken_active_session_id');
    setActiveView('chat');
  };

  const deletarConversa = async (id: string) => {
    try {
      const res = await fetch(`/api/conversas/${id}`, { method: 'DELETE' });
      if (res.ok) {
        const rest = conversas.filter((c) => c.id !== id);
        setConversas(rest);
        if (conversaAtivaId === id) {
          localStorage.removeItem('kraken_active_session_id');
          if (rest.length > 0) {
            selecionarConversa(rest[0].id);
          } else {
            criarNovaConversa();
          }
        }
      }
    } catch (err) {
      console.error('Erro ao deletar conversa:', err);
    }
  };

  const handleSelectModel = async (modelId: string) => {
    setCurrentModel(modelId);
    try {
      await fetch('/api/conversas/modelo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modelo: modelId }),
      });
    } catch (err) {
      console.warn('Erro ao atualizar modelo ativo:', err);
    }
  };

  const handleSendMessage = async (texto: string, anexosEnviados?: CatalogDataSource[]) => {
    const anexosAtivos = anexosEnviados || attachedSources;
    const cleanUserText = texto.trim() || (anexosAtivos.length > 0 ? 'Analise as fontes de dados selecionadas.' : '');
    if (!cleanUserText || isLoading) return;

    // Limpa a seleção na PromptBar
    setAttachedSources([]);

    let targetConversaId = conversaAtivaId;
    if (!targetConversaId) {
      // Cria a sessão no banco sob demanda apenas ao enviar a 1ª mensagem
      try {
        const resNovo = await fetch('/api/conversas', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        if (resNovo.ok) {
          const dataNova = await resNovo.json();
          targetConversaId = dataNova.id;
          const novaItem: ConversaItem = { id: dataNova.id, titulo: dataNova.titulo || 'Nova conversa' };
          setConversas((prev) => [novaItem, ...prev]);
          setConversaAtivaId(dataNova.id);
          localStorage.setItem('kraken_active_session_id', dataNova.id);
        } else {
          throw new Error('Falha ao criar sessão');
        }
      } catch (err) {
        console.error('Erro ao inicializar sessão para envio:', err);
        return;
      }
    }

    // Mensagem otimista do usuário (100% limpa e com anexos separados)
    const userMsg: Mensagem = {
      id: `usr-${Date.now()}`,
      autor: 'user',
      role: 'user',
      texto: cleanUserText,
      anexos: [...anexosAtivos],
      timestamp: new Date().toLocaleTimeString(),
    };
    setMensagens((prev) => [...prev, userMsg]);
    setIsLoading(true);

    // Se o usuário solicitou otimização ou alteração de código, abre o painel lateral em tempo real
    if (
      cleanUserText.toLowerCase().includes('otimi') ||
      cleanUserText.toLowerCase().includes('pipeline') ||
      cleanUserText.toLowerCase().includes('pyspark') ||
      cleanUserText.toLowerCase().includes('feature') ||
      cleanUserText.toLowerCase().includes('reescrev') ||
      cleanUserText.toLowerCase().includes('benchmark')
    ) {
      setSideCodeOpen(true);
    }

    // Etapas simuladas do ThinkingState durante o processamento
    setActiveAgent('Kraken Copilot');
    setThinkingSteps([
      { text: `Roteando intenção sobre script ${selectedWorkspaceFile}...`, done: false },
    ]);

    const stepTimer1 = setTimeout(() => {
      setThinkingSteps([
        { text: `Roteando intenção sobre script ${selectedWorkspaceFile}...`, done: true, duration: '0.4s' },
        { text: 'Executando raciocínio com ferramentas e dados...', done: false },
      ]);
    }, 900);

    try {
      const anexosPaths = anexosAtivos.map((a) => a.caminho);
      const res = await fetch(`/api/conversas/${targetConversaId}/mensagens`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          texto: cleanUserText,
          modelo: currentModel,
          arquivo_alvo: selectedWorkspaceFile,
          anexos: anexosPaths,
        }),
      });

      clearTimeout(stepTimer1);

      if (res.ok) {
        const data = await res.json();
        setThinkingSteps((prev) =>
          prev.map((s) => ({ ...s, done: true, duration: s.duration || '0.8s' }))
        );

        const assistantMsg: Mensagem = {
          id: `ast-${Date.now()}`,
          autor: 'assistant',
          role: 'assistant',
          texto: data.resposta || '',
          especialista: data.especialista || 'Kraken Copilot',
          execucao_id: data.execucao_id,
          has_approval_request: data.has_approval_request,
          proposed_code: data.proposed_code,
          diff_info: data.diff_info,
          ferramentas_executadas: data.ferramentas_executadas || [],
          sugestoes_acoes: data.sugestoes_acoes || [],
          benchmark_metrics: data.benchmark_metrics,
          timestamp: new Date().toLocaleTimeString(),
        };

        if (data.proposed_code) {
          setSideCodeContent(data.proposed_code);
          setSideCodeDiff(data.diff_info);
          setSideCodeHasApproval(Boolean(data.has_approval_request));
          setSideCodeOpen(true);
        } else if (data.diff_info) {
          setSideCodeDiff(data.diff_info);
          setSideCodeHasApproval(Boolean(data.has_approval_request));
          setSideCodeOpen(true);
        } else if (selectedWorkspaceFile) {
          carregarWorkspaceCode(selectedWorkspaceFile);
          carregarWorkspaceFiles(true);
        }

        setMensagens((prev) => [...prev, assistantMsg]);
        carregarConversas(true); // mantém conversa ativa
      } else {
        const errText = await res.text();
        setMensagens((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            autor: 'assistant',
            role: 'assistant',
            texto: `⚠️ Ocorreu uma instabilidade na execução: ${errText.slice(0, 180)}`,
            especialista: 'Kraken Copilot',
          },
        ]);
      }
    } catch (err: any) {
      setMensagens((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          autor: 'assistant',
          role: 'assistant',
          texto: `⚠️ Erro de conexão com o servidor: ${err.message}`,
          especialista: 'Kraken Copilot',
        },
      ]);
    } finally {
      setIsLoading(false);
      setTimeout(() => setThinkingSteps([]), 2500);
    }
  };

  const handleApprove = async (execucaoId?: string, fileToApply?: string) => {
    if (execucaoId) {
      try {
        await fetch(`/api/execucoes/${execucaoId}/decisao`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ aprovado: true }),
        });
      } catch (err) {
        console.warn('Erro ao enviar aprovação:', err);
      }
    }
    const target = fileToApply || selectedWorkspaceFile;
    handleSendMessage(`Aprovado. Por favor, aplique o código proposto em krakenlake/workspace/${target} e valide os resultados.`);
  };

  const handleReject = async (execucaoId?: string, fileToApply?: string) => {
    if (execucaoId) {
      try {
        await fetch(`/api/execucoes/${execucaoId}/decisao`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ aprovado: false }),
        });
      } catch (err) {
        console.warn('Erro ao enviar rejeição:', err);
      }
    }
    handleSendMessage('Proposta de alteração rejeitada. Por favor, mantenha o código atual sem modificações.');
  };

  const handleCopyText = async (msgId: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // fallback
    }
  };

  const getAgentColor = (especialista?: string) => {
    if (!especialista) return 'bg-blue-600 text-white';
    if (especialista.includes('Analyst') || especialista.includes('analyst')) {
      return 'bg-purple-600 text-white';
    }
    if (especialista.includes('Code') || especialista.includes('code')) {
      return 'bg-emerald-600 text-white';
    }
    if (especialista.includes('Optimizer') || especialista.includes('optimizer')) {
      return 'bg-amber-600 text-white';
    }
    return 'bg-blue-600 text-white';
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fafbfd] text-slate-800 antialiased font-sans">
      {/* Sidebar Navigation */}
      <SidebarNav
        conversas={conversas}
        conversaAtivaId={conversaAtivaId}
        activeView={activeView}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        onSelectConversa={(id) => {
          selecionarConversa(id);
          setMobileMenuOpen(false);
        }}
        onNovaConversa={() => {
          criarNovaConversa();
          setMobileMenuOpen(false);
        }}
        onDeleteConversa={deletarConversa}
        onNavigate={(view) => {
          setActiveView(view);
          setMobileMenuOpen(false);
        }}
        onOpenObservability={() => {
          setActiveExecucaoId(null);
          setActiveView('investigacao');
          setMobileMenuOpen(false);
        }}
        catalogSources={catalogSources}
        workspaceFiles={workspaceFiles}
        selectedWorkspaceFile={selectedWorkspaceFile}
        onSelectWorkspaceFile={setSelectedWorkspaceFile}
        onAttachSource={handleAttachSource}
      />

      {/* Main Container */}
      <main className="flex flex-1 flex-col overflow-hidden min-w-0 w-full">
        {/* Top Header com Abas de Navegação */}
        <header className="flex h-14 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 sm:px-6 backdrop-blur-xs select-none">
          <div className="flex items-center gap-3 sm:gap-4">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden rounded-lg p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              title="Abrir menu lateral"
            >
              <Menu className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-2 overflow-hidden">
              <span className="font-bold text-slate-900 text-sm truncate max-w-[150px] sm:max-w-xs">
                {conversas.find((c) => c.id === conversaAtivaId)?.titulo || 'Nova Conversa'}
              </span>
              <span className="hidden sm:inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-mono text-slate-500">
                {currentModel}
              </span>
            </div>

            {/* Abas no Topo */}
            <div className="hidden sm:flex items-center gap-1 rounded-xl bg-slate-100/80 p-1 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setActiveView('chat')}
                className={cn(
                  'flex items-center gap-1.5 rounded-lg px-3 py-1 transition-all cursor-pointer',
                  activeView === 'chat'
                    ? 'bg-white text-blue-600 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                )}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                <span>Chat</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveView('dados')}
                className={cn(
                  'flex items-center gap-1.5 rounded-lg px-3 py-1 transition-all cursor-pointer',
                  activeView === 'dados'
                    ? 'bg-white text-purple-600 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                )}
              >
                <Database className="h-3.5 w-3.5" />
                <span>Dados &amp; Documentos</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveView('observabilidade')}
                className={cn(
                  'flex items-center gap-1.5 rounded-lg px-3 py-1 transition-all cursor-pointer',
                  activeView === 'observabilidade'
                    ? 'bg-white text-emerald-600 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                )}
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Observabilidade</span>
              </button>

              {activeView === 'investigacao' && (
                <button
                  type="button"
                  className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-1 text-emerald-600 shadow-2xs font-semibold"
                >
                  <Activity className="h-3.5 w-3.5" />
                  <span>Investigação</span>
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {activeView === 'chat' && (
              <button
                type="button"
                onClick={() => setSideCodeOpen(!sideCodeOpen)}
                className={cn(
                  'flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer select-none',
                  sideCodeOpen
                    ? 'bg-blue-600 text-white shadow-2xs'
                    : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                )}
                title="Abrir/Fechar painel lateral de código do workspace"
              >
                <FileCode className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Código</span>
                {sideCodeHasApproval && (
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
                )}
              </button>
            )}

            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="truncate max-w-[140px] sm:max-w-none">
                krakenlake/workspace/{selectedWorkspaceFile}
              </span>
            </div>
          </div>
        </header>

        {/* Renderização Condicional de Vistas */}
        {activeView === 'dados' ? (
          <DataExplorerView
            onBackToChat={() => setActiveView('chat')}
            onSendToChat={(prompt) => {
              setActiveView('chat');
              handleSendMessage(prompt);
            }}
          />
        ) : activeView === 'investigacao' ? (
          <InvestigationView
            execucaoId={activeExecucaoId || 'latest'}
            onBackToChat={() => setActiveView('chat')}
          />
        ) : activeView === 'observabilidade' ? (
          <ObservabilityView
            onBackToChat={() => setActiveView('chat')}
          />
        ) : (
          /* View Padrão: Chat com Painel Lateral de Código Split */
          <div className="flex-1 flex overflow-hidden min-w-0">
            <div
              className="flex-1 flex flex-col overflow-hidden min-w-0"
              onDragOver={(e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'copy';
              }}
              onDrop={(e) => {
                e.preventDefault();
                const raw = e.dataTransfer.getData('application/x-kraken-source');
                if (raw) {
                  try {
                    const parsed = JSON.parse(raw);
                    handleAttachSource(parsed);
                  } catch {}
                }
              }}
            >
              <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 min-w-0 w-full">
                <div className="mx-auto max-w-5xl w-full space-y-6 pb-8 min-w-0">
                  {mensagens.length === 0 ? (
                    /* Welcome Screen Estilo Beautiful UI */
                    <div className="flex flex-col items-center justify-center py-16 text-center select-none">
                      <img
                        src="/kraken-copilot.svg"
                        alt="Kraken Copilot"
                        className="h-16 w-16 rounded-2xl shadow-md mb-4 object-contain"
                      />
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">
                      Kraken Copilot
                    </h2>
                    <p className="mt-1.5 max-w-md text-xs text-slate-500 leading-relaxed">
                      Assistente especializado em Ciência de Dados, Analytics, Engenharia de Features e Otimização de Pipelines.
                    </p>

                    {/* Quick Start Action Cards */}
                    <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3 w-full max-w-2xl text-left">
                      <button
                        type="button"
                        onClick={() => handleSendMessage('Quais dados temos disponíveis no datalake e suas características?')}
                        className="group rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs hover:border-purple-300 hover:shadow-xs transition-all cursor-pointer"
                      >
                        <div className="font-semibold text-xs text-slate-800 group-hover:text-purple-600">
                          📊 Análise de Dados
                        </div>
                        <div className="mt-1 text-[11px] text-slate-500 leading-relaxed">
                          Explorar bases do datalake, resumos estatísticos e qualidade.
                        </div>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSendMessage(`Crie uma nova feature de ticket médio e recarga mensal para o script ${selectedWorkspaceFile}`)}
                        className="group rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all cursor-pointer"
                      >
                        <div className="font-semibold text-xs text-slate-800 group-hover:text-emerald-600">
                          ⚙️ Engenharia de Features
                        </div>
                        <div className="mt-1 text-[11px] text-slate-500 leading-relaxed">
                          Criação e enriquecimento de features em Pandas e PySpark.
                        </div>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSendMessage(`Inspecione os gargalos de performance de ${selectedWorkspaceFile} e gere benchmark antes vs depois`)}
                        className="group rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs hover:border-amber-300 hover:shadow-xs transition-all cursor-pointer"
                      >
                        <div className="font-semibold text-xs text-slate-800 group-hover:text-amber-600">
                          🚀 Otimização de Código
                        </div>
                        <div className="mt-1 text-[11px] text-slate-500 leading-relaxed">
                          Benchmark comparativo de tempo e memória com validação.
                        </div>
                      </button>
                    </div>
                  </div>
                ) : (
                  mensagens.map((msg, idx) => {
                    // Correção estrita: checa autor ou role para nunca inverter o usuário
                    const isUser = msg.autor === 'user' || msg.role === 'user';
                    const sugestoes =
                      msg.sugestoes_acoes && msg.sugestoes_acoes.length > 0
                        ? msg.sugestoes_acoes
                        : extractSuggestionsFromText(msg.texto);
                    return (
                      <div
                        key={msg.id || idx}
                        className={cn(
                          'flex items-start gap-3.5 transition-all w-full min-w-0',
                          isUser ? 'flex-row-reverse' : 'flex-row'
                        )}
                      >
                        {/* Avatar do Emissor */}
                        <div
                          className={cn(
                            'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl shadow-xs text-xs font-bold select-none overflow-hidden',
                            isUser ? 'bg-slate-800 text-white' : ''
                          )}
                        >
                          {isUser ? (
                            <User className="h-4 w-4" />
                          ) : (
                            <img
                              src="/web/ui/kraken-copilot.svg"
                              alt={msg.especialista || 'Kraken Copilot'}
                              className="h-8 w-8 object-contain"
                            />
                          )}
                        </div>

                        {/* Corpo da Mensagem */}
                        <div
                          className={cn(
                            'flex flex-col min-w-0',
                            isUser ? 'items-end max-w-2xl ml-auto' : 'items-start flex-1 w-full'
                          )}
                        >
                          {/* Badge do Agente */}
                          {!isUser && (
                            <div className="mb-1.5 flex items-center gap-2 text-[11px] text-slate-500 select-none">
                              <span className="font-semibold text-slate-700">
                                {msg.especialista || 'Kraken Copilot'}
                              </span>
                              {msg.timestamp && (
                                <span className="text-[10px] text-slate-400 font-mono">
                                  {formatTimestamp(msg.timestamp)}
                                </span>
                              )}
                            </div>
                          )}

                          {/* Caixa de Texto com Suporte a Markdown & Tabelas */}
                          <div
                            className={cn(
                              'rounded-2xl px-4 py-3 text-xs leading-relaxed shadow-xs w-full min-w-0',
                              isUser
                                ? 'bg-blue-600 text-white font-medium rounded-tr-xs'
                                : 'bg-white border border-slate-200/90 text-slate-800 rounded-tl-xs'
                            )}
                          >
                            {isUser ? (
                              <div className="select-text">
                                {extractBubbleAttachments(msg).length > 0 && (
                                  <div className="flex flex-wrap items-center gap-1.5 mb-1.5 justify-end">
                                    {extractBubbleAttachments(msg).map((anexoNome, aIdx) => (
                                      <span
                                        key={aIdx}
                                        className="inline-flex items-center gap-1 rounded-md bg-white/20 backdrop-blur-xs px-2 py-0.5 text-[10px] font-mono font-semibold text-white shadow-2xs"
                                      >
                                        <Database className="h-2.5 w-2.5" />
                                        <span>@{anexoNome.split('/').pop()}</span>
                                      </span>
                                    ))}
                                  </div>
                                )}
                                <p className="text-xs text-white font-medium leading-relaxed whitespace-pre-wrap">
                                  {cleanUserBubbleText(msg.texto)}
                                </p>
                              </div>
                            ) : (
                              <StreamingText content={cleanDisplayText(msg.texto, sugestoes.length > 0)} />
                            )}

                            {/* Tool Chips com Diff inline */}
                            {msg.ferramentas_executadas && msg.ferramentas_executadas.length > 0 && (
                              <ToolChips tools={msg.ferramentas_executadas} />
                            )}

                            {/* Benchmark Comparativo (Insight Cards) */}
                            {msg.benchmark_metrics && (
                              <InsightCards metrics={msg.benchmark_metrics} />
                            )}

                            {/* Card de Aprovação Nativo Beautiful UI no Chat (Exibe SOMENTE para kraken_code/kraken_optimizer quando há código proposto) */}
                            {Boolean(
                              (
                                msg.proposed_code ||
                                (msg as any).metadados?.proposed_code ||
                                msg.diff_info?.proposed_code ||
                                (msg as any).metadados?.diff_info?.proposed_code
                              )?.trim() &&
                              !msg.especialista?.toLowerCase().includes('analyst') &&
                              (
                                msg.has_approval_request ||
                                (msg as any).metadados?.has_approval_request ||
                                (!isUser && (
                                  msg.texto.toLowerCase().includes('deseja confirmar a aplicação') ||
                                  msg.texto.toLowerCase().includes('deseja aprovar') ||
                                  msg.texto.toLowerCase().includes('autoriza a aplicação') ||
                                  msg.texto.toLowerCase().includes('substituir definitivamente o arquivo')
                                ))
                              )
                            ) && (
                              <ApprovalCard
                                execucaoId={msg.execucao_id}
                                targetFile={msg.diff_info?.arquivo || (msg as any).metadados?.diff_info?.arquivo || selectedWorkspaceFile}
                                diffInfo={msg.diff_info || (msg as any).metadados?.diff_info}
                                proposedCode={
                                  msg.proposed_code ||
                                  (msg as any).metadados?.proposed_code ||
                                  msg.diff_info?.proposed_code ||
                                  (msg as any).metadados?.diff_info?.proposed_code
                                }
                                onApprove={handleApprove}
                                onReject={handleReject}
                              />
                            )}
                          </div>

                          {/* Ações sugeridas (Backend + Extração Inteligente) */}
                          {!isUser && sugestoes.length > 0 && (
                            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                              <span className="text-[11px] font-semibold text-slate-500 select-none">
                                💡 Ações Sugeridas:
                              </span>
                              {sugestoes.map((sugestao, sIdx) => (
                                <button
                                  key={sIdx}
                                  type="button"
                                  onClick={() => handleSendMessage(sugestao)}
                                  className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50/90 px-3 py-1 text-[11px] font-medium text-blue-800 hover:bg-blue-100/90 hover:border-blue-300 transition-all shadow-2xs select-none cursor-pointer active:scale-98"
                                >
                                  <Sparkles className="h-3 w-3 text-blue-600" />
                                  <span>{sugestao}</span>
                                </button>
                              ))}
                            </div>
                          )}

                          {/* Footer da Mensagem com Cópia e Investigação inline */}
                          {!isUser && (
                            <div className="mt-2 flex items-center gap-3 text-[11px] text-slate-400 select-none">
                              <button
                                type="button"
                                onClick={() => handleCopyText(msg.id || String(idx), msg.texto)}
                                className="flex items-center gap-1 hover:text-slate-600 transition-colors cursor-pointer"
                              >
                                {copiedId === (msg.id || String(idx)) ? (
                                  <>
                                    <Check className="h-3 w-3 text-emerald-500" />
                                    <span className="text-emerald-600">Copiado</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="h-3 w-3" />
                                    <span>Copiar resposta</span>
                                  </>
                                )}
                              </button>

                              {msg.execucao_id && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActiveExecucaoId(msg.execucao_id || null);
                                    setActiveView('investigacao');
                                  }}
                                  className="flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium transition-colors cursor-pointer"
                                >
                                  <Search className="h-3 w-3" />
                                  <span>Investigação da execução →</span>
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}

                {/* Thinking State & Loading State (Beautiful UI) */}
                {isLoading && (
                  <div className="flex flex-col gap-2.5">
                    <LoadingState
                      label={`O ${activeAgent} está processando sobre ${selectedWorkspaceFile}...`}
                      variant="Drive"
                    />
                    <div className="flex items-start gap-3.5">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl shadow-xs select-none overflow-hidden">
                        <img
                          src="/kraken-copilot.svg"
                          alt={activeAgent}
                          className="h-8 w-8 object-contain"
                        />
                      </div>
                      <div className="flex-1 max-w-[85%]">
                        <ThinkingState
                          isThinking={isLoading}
                          agentName={activeAgent}
                          steps={thinkingSteps}
                        />
                      </div>
                    </div>
                  </div>
                )}

                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Prompt Bar Integrada na Base da Coluna de Chat */}
              <PromptBar
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                models={models}
                currentModel={currentModel}
                onSelectModel={handleSelectModel}
                workspaceFiles={workspaceFiles}
                selectedWorkspaceFile={selectedWorkspaceFile}
                onSelectWorkspaceFile={setSelectedWorkspaceFile}
                catalogSources={catalogSources}
                attachedSources={attachedSources}
                onAttachSource={handleAttachSource}
                onRemoveAttachedSource={handleRemoveAttachedSource}
              />
            </div>

            {/* Painel Lateral de Código (Side Bar Code) ao lado do Chat */}
            <SideCodePanel
              isOpen={sideCodeOpen}
              onClose={() => setSideCodeOpen(false)}
              filename={selectedWorkspaceFile}
              code={sideCodeContent}
              diffInfo={sideCodeDiff}
              isOptimizing={isLoading && (sideCodeContent.length === 0 || sideCodeHasApproval)}
            />
          </div>
      )}
      </main>
    </div>
  );
}

export default App;
