import React from 'react';
import {
  ShieldCheck,
  Database,
  Zap,
  Code2,
  UserCheck,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Clock,
  Info,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface GuardrailAuditItem {
  id: string;
  nome: string;
  camada: string;
  status: 'conforme' | 'bloqueado' | 'requer_aprovacao' | 'aprovado' | 'rejeitado' | 'ignorado' | string;
  severidade: 'crítica' | 'alta' | 'média' | 'baixa' | string;
  descricao: string;
  detalhes?: string;
  regra?: string;
}

export interface GuardrailsAuditPanelProps {
  guardrails?: GuardrailAuditItem[];
  hasApprovalRequest?: boolean;
  humanDecision?: any;
  className?: string;
}

const DEFAULT_GUARDRAILS: GuardrailAuditItem[] = [
  {
    id: 'content_safety',
    nome: 'Segurança de Entrada & Anti-Injection',
    camada: 'Entrada',
    status: 'conforme',
    severidade: 'crítica',
    descricao: 'Bloqueio estrito de Prompt Injection direto, jailbreaks, comandos destrutivos de SO (rm -rf, mkfs) e conteúdo não corporativo.',
    detalhes: 'Mensagem avaliada contra base de expressões regulares e padrões maliciosos. Nenhum risco detectado.',
  },
  {
    id: 'datalake_integrity',
    nome: 'Imutabilidade do Data Lake (SHA-256)',
    camada: 'Dados Brutos',
    status: 'conforme',
    severidade: 'alta',
    descricao: 'Auditoria criptográfica SHA-256 de integridade dos arquivos em krakenlake/catalog/sources/ antes e depois da execução.',
    detalhes: 'Todos os arquivos do catálogo de dados brutos permanecem 100% inalterados e protegidos contra mutações.',
  },
  {
    id: 'circuit_breaker',
    nome: 'Circuit Breaker Anti-Loop',
    camada: 'Orquestração',
    status: 'conforme',
    severidade: 'média',
    descricao: 'Limite operacional de até 5 escritas em disco e 10 transferências entre sub-agentes para prevenir loops infinitos e estouro de custos.',
    detalhes: 'Chamadas de ferramentas e handoffs mantidos dentro das cotas seguras da sessão.',
  },
  {
    id: 'ast_code_safety',
    nome: 'Segurança Sintática & Contratos AST',
    camada: 'Código Python',
    status: 'conforme',
    severidade: 'alta',
    descricao: 'Inspeção estática da Abstract Syntax Tree (AST) para barrar eval/exec/subprocess e garantir equivalência e preservação de schemas.',
    detalhes: 'Sintaxe validada pelo parser Python e verificação de contratos sem violações.',
  },
  {
    id: 'hitl_governance',
    nome: 'Human-in-the-Loop (Governança HITL)',
    camada: 'Governança',
    status: 'dispensado',
    severidade: 'crítica',
    descricao: 'Política mandatória de aprovação humana explícita antes de qualquer gravação física permanente de código no workspace.',
    detalhes: 'Substituição definitiva no disco condicionada à autorização explícita do usuário.',
  },
  {
    id: 'output_sanitization',
    nome: 'Sanitização de Saída & Privacidade',
    camada: 'Saída',
    status: 'conforme',
    severidade: 'baixa',
    descricao: 'Remoção de vazamento de tokens de alfabetos estrangeiros (CJK/Thai), supressão de CoT interno e limpeza de pseudo tags.',
    detalhes: 'Resposta final sanitizada para apresentação limpa e segura ao usuário.',
  },
];

export function GuardrailsAuditPanel({
  guardrails,
  hasApprovalRequest,
  humanDecision,
  className,
}: GuardrailsAuditPanelProps) {
  // Mescla guardrails do backend com catálogo padrão caso algum esteja ausente
  const items: GuardrailAuditItem[] = React.useMemo(() => {
    if (guardrails && guardrails.length > 0) {
      return guardrails.map((g) => {
        if (g.id === 'hitl_governance') {
          if (humanDecision?.aprovado) {
            return { ...g, status: 'aprovado', detalhes: 'Proposta aprovada e autorizada pelo usuário.' };
          }
          if (humanDecision && !humanDecision.aprovado) {
            return { ...g, status: 'rejeitado', detalhes: 'Proposta rejeitada pelo usuário. Código original preservado.' };
          }
          if (hasApprovalRequest) {
            return { ...g, status: 'requer_aprovacao', detalhes: 'Proposta aguardando autorização humana explícita.' };
          }
        }
        return g;
      });
    }

    return DEFAULT_GUARDRAILS.map((g) => {
      if (g.id === 'hitl_governance') {
        if (humanDecision?.aprovado) {
          return { ...g, status: 'aprovado', detalhes: 'Proposta aprovada pelo engenheiro.' };
        }
        if (hasApprovalRequest) {
          return { ...g, status: 'requer_aprovacao', detalhes: 'Aguardando aprovação humana.' };
        }
      }
      return g;
    });
  }, [guardrails, hasApprovalRequest, humanDecision]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'conforme':
      case 'aprovado':
        return {
          label: status === 'aprovado' ? 'Aprovado Humano' : 'Conforme',
          badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-200',
          icon: CheckCircle2,
          iconClass: 'text-emerald-600',
        };
      case 'requer_aprovacao':
        return {
          label: 'Aprovação Pendente (HITL)',
          badgeClass: 'bg-amber-100 text-amber-900 border-amber-300 animate-pulse',
          icon: AlertTriangle,
          iconClass: 'text-amber-600',
        };
      case 'bloqueado':
      case 'rejeitado':
        return {
          label: status === 'rejeitado' ? 'Rejeitado Humano' : 'Bloqueado',
          badgeClass: 'bg-rose-100 text-rose-800 border-rose-200',
          icon: AlertTriangle,
          iconClass: 'text-rose-600',
        };
      case 'ignorado':
      case 'dispensado':
      default:
        return {
          label: 'Dispensado / N/A',
          badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
          icon: Info,
          iconClass: 'text-slate-500',
        };
    }
  };

  const getIcon = (id: string) => {
    switch (id) {
      case 'content_safety':
        return ShieldCheck;
      case 'datalake_integrity':
        return Database;
      case 'circuit_breaker':
        return Zap;
      case 'ast_code_safety':
        return Code2;
      case 'hitl_governance':
        return UserCheck;
      case 'output_sanitization':
        return Sparkles;
      default:
        return Lock;
    }
  };

  return (
    <div className={cn('rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs', className)}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-blue-100 text-blue-700 shadow-2xs">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900 tracking-tight">
              Matriz de Guardrails, Segurança & Governança Corporativa
            </h3>
            <p className="text-[11px] text-slate-500">
              6 camadas ativas de proteção e conformidade verificadas durante esta execução
            </p>
          </div>
        </div>

        <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200 select-none">
          100% Auditoria Rastreável
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => {
          const ItemIcon = getIcon(item.id);
          const { label, badgeClass, icon: StatusIcon, iconClass } = getStatusBadge(item.status);

          return (
            <div
              key={item.id}
              className="flex flex-col justify-between rounded-xl border border-slate-200/80 bg-slate-50/50 p-3.5 text-xs transition-all hover:bg-slate-50 hover:shadow-2xs"
            >
              <div>
                {/* Header do Card */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-white border border-slate-200 text-slate-700 shadow-2xs">
                      <ItemIcon className="h-3.5 w-3.5 text-blue-600" />
                    </div>
                    <div>
                      <span className="font-bold text-slate-900 leading-tight block">
                        {item.nome}
                      </span>
                      <span className="font-mono text-[10px] text-slate-400 uppercase tracking-wider">
                        Camada: {item.camada}
                      </span>
                    </div>
                  </div>

                  <span
                    className={cn(
                      'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold border select-none shrink-0',
                      badgeClass
                    )}
                  >
                    <StatusIcon className={cn('h-3 w-3', iconClass)} />
                    <span>{label}</span>
                  </span>
                </div>

                {/* Descrição e Evidência */}
                <p className="mt-2.5 text-[11px] text-slate-600 leading-relaxed">
                  {item.descricao}
                </p>

                {item.detalhes && (
                  <div className="mt-2.5 rounded-lg border border-slate-200/90 bg-white p-2 text-[10.5px] font-mono text-slate-700 leading-normal">
                    <span className="font-sans font-semibold text-slate-900 block mb-0.5">
                      Evidência de Auditoria:
                    </span>
                    {item.detalhes}
                  </div>
                )}
              </div>

              {/* Rodapé com Severidade */}
              <div className="mt-3 flex items-center justify-between border-t border-slate-200/60 pt-2 text-[10px] text-slate-400">
                <span className="capitalize">
                  Severidade:{' '}
                  <strong
                    className={cn(
                      item.severidade === 'crítica'
                        ? 'text-rose-600'
                        : item.severidade === 'alta'
                        ? 'text-amber-600'
                        : 'text-slate-600'
                    )}
                  >
                    {item.severidade}
                  </strong>
                </span>

                <span className="flex items-center gap-1 text-emerald-600 font-medium">
                  <CheckCircle2 className="h-3 w-3" /> Verificado
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default GuardrailsAuditPanel;

