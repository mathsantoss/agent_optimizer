import React, { useMemo, useCallback, useState } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  Handle,
  Position,
  MarkerType,
  type Node,
  type Edge,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  User,
  ShieldCheck,
  Bot,
  Terminal,
  Activity,
  CheckCircle2,
  AlertTriangle,
  UserCheck,
  Zap,
  Sparkles,
  Cpu,
  FileCode,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Tipagem dos dados passados para os nós customizados
export interface WorkflowNodeData extends Record<string, unknown> {
  title: string;
  subtitle?: string;
  category: 'user' | 'guardrail' | 'orchestrator' | 'specialist' | 'skill' | 'tool' | 'benchmark' | 'hitl' | 'output';
  status?: 'success' | 'running' | 'pending' | 'warning' | 'neutral';
  duration?: string;
  stepIndex?: number;
  highlight?: boolean;
}

// Componente de nó customizado para o React Flow
function WorkflowCustomNode({ data, selected }: NodeProps<Node<WorkflowNodeData>>) {
  const getCategoryConfig = (category: string) => {
    switch (category) {
      case 'user':
        return {
          icon: User,
          iconBg: 'bg-blue-100 text-blue-700',
          borderClass: 'border-blue-300/80',
          badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
        };
      case 'guardrail':
        return {
          icon: ShieldCheck,
          iconBg: 'bg-emerald-100 text-emerald-700',
          borderClass: 'border-emerald-300/80',
          badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200',
        };
      case 'orchestrator':
        return {
          icon: Cpu,
          iconBg: 'bg-purple-100 text-purple-700',
          borderClass: 'border-purple-300/80',
          badgeClass: 'bg-purple-50 text-purple-700 border-purple-200',
        };
      case 'specialist':
        return {
          icon: Bot,
          iconBg: 'bg-indigo-100 text-indigo-700',
          borderClass: 'border-indigo-300/80',
          badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200',
        };
      case 'skill':
        return {
          icon: Sparkles,
          iconBg: 'bg-purple-100 text-purple-800',
          borderClass: 'border-purple-400',
          badgeClass: 'bg-purple-50 text-purple-900 border-purple-300',
        };
      case 'tool':
        return {
          icon: Terminal,
          iconBg: 'bg-cyan-100 text-cyan-800',
          borderClass: 'border-cyan-300/80',
          badgeClass: 'bg-cyan-50 text-cyan-800 border-cyan-200',
        };
      case 'benchmark':
        return {
          icon: Activity,
          iconBg: 'bg-amber-100 text-amber-800',
          borderClass: 'border-amber-300/80',
          badgeClass: 'bg-amber-50 text-amber-800 border-amber-200',
        };
      case 'hitl':
        return {
          icon: UserCheck,
          iconBg: 'bg-amber-100 text-amber-900',
          borderClass: 'border-amber-400',
          badgeClass: 'bg-amber-50 text-amber-900 border-amber-300',
        };
      case 'output':
      default:
        return {
          icon: Sparkles,
          iconBg: 'bg-emerald-100 text-emerald-700',
          borderClass: 'border-emerald-300/80',
          badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200',
        };
    }
  };

  const config = getCategoryConfig(data.category);
  const IconComponent = config.icon;

  return (
    <div
      className={cn(
        'w-[240px] rounded-2xl border bg-white p-3.5 shadow-sm transition-all text-xs font-sans select-none',
        config.borderClass,
        selected ? 'ring-2 ring-blue-500 shadow-md' : 'hover:shadow-md hover:border-blue-400'
      )}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-blue-600 transition-colors"
      />

      {/* Header do Card */}
      <div className="flex items-center justify-between gap-1.5">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className={cn('flex h-7 w-7 shrink-0 items-center justify-center rounded-xl shadow-2xs', config.iconBg)}>
            <IconComponent className="h-3.5 w-3.5" />
          </div>
          <span className="font-bold text-slate-900 truncate text-[11.5px]">
            {data.title}
          </span>
        </div>

        {data.status && (
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-[9.5px] font-bold border select-none shrink-0 uppercase tracking-tight',
              config.badgeClass
            )}
          >
            {data.status}
          </span>
        )}
      </div>

      {/* Subtítulo / Detalhe */}
      {data.subtitle && (
        <p className="mt-2 text-[11px] text-slate-600 font-mono line-clamp-2 leading-relaxed bg-slate-50/70 p-1.5 rounded-lg border border-slate-100">
          {data.subtitle}
        </p>
      )}

      {/* Footer com Duração e Etapa */}
      <div className="mt-2.5 flex items-center justify-between border-t border-slate-100 pt-2 text-[10px] text-slate-400 font-medium">
        <span>{data.stepIndex !== undefined ? `Passo #${data.stepIndex + 1}` : 'Execução'}</span>
        {data.duration && <span className="font-mono text-slate-500 font-semibold">{data.duration}</span>}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-blue-600 transition-colors"
      />
    </div>
  );
}

const nodeTypes = {
  workflowNode: WorkflowCustomNode,
};

export interface ExecutionWorkflowFlowProps {
  execucao: any;
  onSelectStep?: (idx: number) => void;
  isFullHeight?: boolean;
  className?: string;
}

export function ExecutionWorkflowFlow({
  execucao,
  onSelectStep,
  isFullHeight = false,
  className,
}: ExecutionWorkflowFlowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const effectiveFull = isFullHeight || isExpanded;

  // Constrói dinamicamente os nós e arestas com base nos spans reais da execução
  const { nodes, edges } = useMemo(() => {
    if (!execucao) return { nodes: [], edges: [] };

    const generatedNodes: Node<WorkflowNodeData>[] = [];
    const generatedEdges: Edge[] = [];

    let currentX = 50;
    const spacingX = 290;
    const defaultY = 120;

    // 1. Nó: Entrada do Usuário
    const promptText = execucao.mensagem_usuario || 'Solicitação do usuário';
    const truncatedPrompt = promptText.length > 55 ? `${promptText.slice(0, 52)}...` : promptText;
    generatedNodes.push({
      id: 'node-user-prompt',
      type: 'workflowNode',
      position: { x: currentX, y: defaultY },
      data: {
        title: 'Entrada do Usuário',
        subtitle: truncatedPrompt,
        category: 'user',
        status: 'success',
        duration: '0ms',
        stepIndex: 0,
      },
    });

    // 2. Nó: Guardrail de Entrada
    currentX += spacingX;
    generatedNodes.push({
      id: 'node-guardrail-in',
      type: 'workflowNode',
      position: { x: currentX, y: defaultY },
      data: {
        title: 'Guardrail de Entrada',
        subtitle: 'Content Safety & Anti-Injection',
        category: 'guardrail',
        status: 'success',
        duration: '1ms',
        stepIndex: 1,
      },
    });
    generatedEdges.push({
      id: 'edge-prompt-to-guardrail',
      source: 'node-user-prompt',
      target: 'node-guardrail-in',
      animated: true,
      style: { stroke: '#10b981', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' },
    });

    // 3. Nó: Orquestrador ADK (Kraken Copilot)
    currentX += spacingX;
    const modeloNome = (execucao.modelo || 'gemini-2.5-flash').replace('vertex_ai/', '').replace('gemini/', '');
    generatedNodes.push({
      id: 'node-orchestrator',
      type: 'workflowNode',
      position: { x: currentX, y: defaultY },
      data: {
        title: 'Orquestrador ADK',
        subtitle: `Kraken Copilot (${modeloNome})`,
        category: 'orchestrator',
        status: 'success',
        duration: 'Orquestrado',
      },
    });
    generatedEdges.push({
      id: 'edge-guardrail-to-orchestrator',
      source: 'node-guardrail-in',
      target: 'node-orchestrator',
      animated: true,
      style: { stroke: '#8b5cf6', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' },
    });

    let lastNodeId = 'node-orchestrator';

    // 4. Nó: Especialista Ativo (se diferente do orquestrador raiz)
    const specialist = execucao.especialista;
    if (specialist && specialist !== 'kraken_copilot') {
      currentX += spacingX;
      const specialistId = 'node-specialist';
      generatedNodes.push({
        id: specialistId,
        type: 'workflowNode',
        position: { x: currentX, y: defaultY },
        data: {
          title: `Agente: ${specialist}`,
          subtitle: 'Delegação e Planejamento',
          category: 'specialist',
          status: 'success',
        },
      });
      generatedEdges.push({
        id: `edge-${lastNodeId}-to-specialist`,
        source: lastNodeId,
        target: specialistId,
        animated: true,
        style: { stroke: '#6366f1', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' },
      });
      lastNodeId = specialistId;
    }

    // 4.5. Nó: Skills ADK em Operação (Google ADK & Seb1n / K-Dense AI)
    const skillsAtivas: string[] = execucao.skills_ativas || [];
    if (skillsAtivas.length > 0) {
      currentX += spacingX;
      const skillsNodeId = 'node-skills-adk';
      const skillsDesc = skillsAtivas.slice(0, 3).join(', ') + (skillsAtivas.length > 3 ? ` (+${skillsAtivas.length - 3})` : '');
      generatedNodes.push({
        id: skillsNodeId,
        type: 'workflowNode',
        position: { x: currentX, y: defaultY },
        data: {
          title: `Skills ADK (${skillsAtivas.length})`,
          subtitle: skillsDesc,
          category: 'skill',
          status: 'success',
        },
      });
      generatedEdges.push({
        id: `edge-${lastNodeId}-to-skills`,
        source: lastNodeId,
        target: skillsNodeId,
        animated: true,
        style: { stroke: '#a855f7', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#a855f7' },
      });
      lastNodeId = skillsNodeId;
    }

    // 5. Nós de Ferramentas Executadas
    const tools: any[] = execucao.ferramentas_executadas || [];
    if (tools.length > 0) {
      // Cria um nó para cada ferramenta executada
      tools.forEach((tool, tIdx) => {
        currentX += spacingX;
        const toolNodeId = `node-tool-${tIdx}`;
        const toolName = tool.ferramenta || tool.nome || 'Ferramenta';
        const toolArgs = tool.argumentos || {};
        const targetDesc =
          toolArgs.file_path ||
          toolArgs.target_file_path ||
          toolArgs.caminho ||
          toolArgs.dataset_name ||
          (toolArgs.query ? `SQL: ${String(toolArgs.query).slice(0, 30)}...` : 'Executada com sucesso');

        generatedNodes.push({
          id: toolNodeId,
          type: 'workflowNode',
          position: { x: currentX, y: defaultY + (tIdx % 2 === 0 ? 0 : 20) },
          data: {
            title: toolName,
            subtitle: String(targetDesc),
            category: 'tool',
            status: 'success',
            stepIndex: tIdx + 2,
          },
        });

        generatedEdges.push({
          id: `edge-${lastNodeId}-to-${toolNodeId}`,
          source: lastNodeId,
          target: toolNodeId,
          animated: true,
          style: { stroke: '#06b6d4', strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#06b6d4' },
        });

        lastNodeId = toolNodeId;
      });
    }

    // 6. Nó: Benchmark Comparativo de Performance (se aplicável)
    const hasBenchmark = tools.some(
      (t) => (t.ferramenta || t.nome) === 'optimize_pipeline' || (t.ferramenta || t.nome) === 'compare_pipeline_runs'
    );
    if (hasBenchmark) {
      currentX += spacingX;
      const benchId = 'node-benchmark';
      generatedNodes.push({
        id: benchId,
        type: 'workflowNode',
        position: { x: currentX, y: defaultY },
        data: {
          title: 'Benchmark & Equivalência',
          subtitle: 'Validação funcional e speedup',
          category: 'benchmark',
          status: 'success',
        },
      });
      generatedEdges.push({
        id: `edge-${lastNodeId}-to-benchmark`,
        source: lastNodeId,
        target: benchId,
        animated: true,
        style: { stroke: '#f59e0b', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' },
      });
      lastNodeId = benchId;
    }

    // 7. Nó: Human-in-the-Loop (se exigiu proposta de aprovação)
    if (execucao.has_approval_request || execucao.decisao_humana) {
      currentX += spacingX;
      const hitlId = 'node-hitl';
      const isApproved = execucao.decisao_humana?.aprovado === true;
      const isRejected = execucao.decisao_humana?.aprovado === false;
      const hitlStatus = isApproved ? 'success' : isRejected ? 'warning' : 'pending';

      generatedNodes.push({
        id: hitlId,
        type: 'workflowNode',
        position: { x: currentX, y: defaultY },
        data: {
          title: 'Human-in-the-Loop',
          subtitle: isApproved
            ? 'Autorizado pelo Engenheiro'
            : isRejected
              ? 'Rejeitado pelo Engenheiro'
              : 'Aguardando Confirmação',
          category: 'hitl',
          status: hitlStatus,
        },
      });
      generatedEdges.push({
        id: `edge-${lastNodeId}-to-hitl`,
        source: lastNodeId,
        target: hitlId,
        animated: true,
        style: { stroke: '#f59e0b', strokeWidth: 2, strokeDasharray: '4 4' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' },
      });
      lastNodeId = hitlId;
    }

    // 8. Nó: Resposta Final / Entrega
    currentX += spacingX;
    const finalId = 'node-delivery';
    generatedNodes.push({
      id: finalId,
      type: 'workflowNode',
      position: { x: currentX, y: defaultY },
      data: {
        title: 'Resposta & Conclusão',
        subtitle: `Latência total: ${execucao.latencia_segundos ?? execucao.latencia_s ?? '0'}s`,
        category: 'output',
        status: execucao.status === 'sucesso' ? 'success' : 'warning',
      },
    });
    generatedEdges.push({
      id: `edge-${lastNodeId}-to-final`,
      source: lastNodeId,
      target: finalId,
      animated: true,
      style: { stroke: '#10b981', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' },
    });

    return { nodes: generatedNodes, edges: generatedEdges };
  }, [execucao]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const stepIdx = (node.data as WorkflowNodeData)?.stepIndex;
      if (typeof stepIdx === 'number' && onSelectStep) {
        onSelectStep(stepIdx);
      }
    },
    [onSelectStep]
  );

  return (
    <div className={cn('overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xs transition-all', className)}>
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3.5 bg-slate-50/80">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-purple-100 text-purple-700 shadow-2xs">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>Diagrama do Workflow Interativo de Execução</span>
              {execucao.skills_ativas && execucao.skills_ativas.length > 0 && (
                <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 text-purple-700 px-2 py-0.5 text-[10px] font-semibold border border-purple-200">
                  <Sparkles className="h-2.5 w-2.5" />
                  {execucao.skills_ativas.length} Skills ADK
                </span>
              )}
            </h3>
            <p className="text-[11px] text-slate-500">
              Orquestração, Skills Especialistas e Governança
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
            title={effectiveFull ? 'Recolher altura do diagrama' : 'Expandir diagrama para preencher o espaço da tela'}
          >
            {effectiveFull ? (
              <>
                <Minimize2 className="h-3.5 w-3.5 text-slate-500" />
                <span>Recolher</span>
              </>
            ) : (
              <>
                <Maximize2 className="h-3.5 w-3.5 text-slate-500" />
                <span>Expandir Espaço</span>
              </>
            )}
          </button>

          <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-[10px] font-bold text-blue-700 border border-blue-200 select-none">
            React Flow Interativo
          </span>
        </div>
      </div>

      <div className={cn('w-full bg-[#f8fafc] relative transition-all duration-200', effectiveFull ? 'h-[calc(100vh-270px)] min-h-[560px]' : 'h-[360px]')}>
        <ReactFlow
          key={effectiveFull ? 'full-view' : 'compact-view'}
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#cbd5e1" gap={16} size={1} variant={BackgroundVariant.Dots} />
          <Controls className="!bg-white !border !border-slate-200 !shadow-sm !rounded-xl !text-slate-700" />
        </ReactFlow>
      </div>

      <div className="border-t border-slate-100 bg-slate-50/50 px-5 py-2 text-[11px] text-slate-400 flex items-center justify-between">
        <span>💡 Dica: Você pode arrastar, aproximar (zoom) e clicar nos nós para navegar no percurso.</span>
        <div className="flex items-center gap-3">
          {effectiveFull && (
            <span className="text-[10px] text-blue-600 font-semibold bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100">
              Modo Espaço Total Ativo
            </span>
          )}
          <span className="font-mono text-[10.5px] text-slate-500 font-semibold">{nodes.length} nós no pipeline</span>
        </div>
      </div>
    </div>
  );
}

export default ExecutionWorkflowFlow;

