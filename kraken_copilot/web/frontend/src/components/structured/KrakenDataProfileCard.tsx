import React, { useState } from 'react';
import {
  Database,
  Table,
  Key,
  Calendar,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface KrakenColumnInfoData {
  nome: string;
  tipo: string;
  valores_unicos: number;
  nulos: number;
  percentual_nulos: number;
}

export interface KrakenDataProfileData {
  dataset_nome: string;
  arquivo: string;
  caminho?: string;
  total_linhas: number;
  total_colunas: number;
  tamanho_kb: number;
  amostragem_ativa?: boolean;
  linhas_duplicadas?: number;
  chaves_candidatas?: string[];
  periodo_temporal?: Record<string, any> | string;
  colunas: KrakenColumnInfoData[] | Record<string, any>;
  amostra_linhas?: Array<Record<string, any>>;
  alertas_qualidade?: string[];
}

export interface KrakenDataProfileCardProps {
  profile: KrakenDataProfileData;
  className?: string;
}

export function KrakenDataProfileCard({ profile, className }: KrakenDataProfileCardProps) {
  const [showColumns, setShowColumns] = useState(false);
  const [showSample, setShowSample] = useState(false);

  // Normaliza lista de colunas caso venha como array ou dict
  const columnsList: KrakenColumnInfoData[] = Array.isArray(profile.colunas)
    ? profile.colunas
    : Object.entries(profile.colunas || {}).map(([colName, meta]: [string, any]) => ({
        nome: colName,
        tipo: meta.tipo || meta.data_type || 'object',
        valores_unicos: meta.valores_unicos || meta.unique_values || 0,
        nulos: meta.nulos || meta.null_count || 0,
        percentual_nulos: meta.percentual_nulos || meta.null_percentage || 0,
      }));

  return (
    <div
      className={cn(
        'my-3 overflow-hidden rounded-2xl border border-blue-200/90 bg-gradient-to-b from-white to-blue-50/20 shadow-xs transition-all',
        className
      )}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between border-b border-blue-100 bg-blue-50/60 px-4 py-2.5 text-xs">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-blue-600 text-white shadow-2xs">
            <Database className="h-3.5 w-3.5" />
          </div>
          <div>
            <span className="font-bold text-slate-900">Perfilamento de Dados (KrakenDataProfile)</span>
            <span className="ml-2 font-mono text-[11px] text-slate-500">
              {profile.arquivo || profile.dataset_nome}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {profile.amostragem_ativa && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800 border border-amber-200">
              Amostra ({profile.total_linhas.toLocaleString()} linhas)
            </span>
          )}
          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-[10px] font-mono font-bold text-blue-800">
            {profile.total_colunas} colunas
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200/90 bg-white p-3 shadow-2xs">
          <div className="text-[10.5px] font-medium text-slate-400">Total de Registros</div>
          <div className="mt-1 font-mono text-sm font-bold text-slate-900">
            {profile.total_linhas.toLocaleString()}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-400">Linhas analisadas</div>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-3 shadow-2xs">
          <div className="text-[10.5px] font-medium text-slate-400">Dimensão</div>
          <div className="mt-1 font-mono text-sm font-bold text-slate-900">
            {profile.total_colunas} Colunas
          </div>
          <div className="mt-0.5 text-[10px] text-slate-400">Features disponíveis</div>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-3 shadow-2xs">
          <div className="text-[10.5px] font-medium text-slate-400">Tamanho em Disco</div>
          <div className="mt-1 font-mono text-sm font-bold text-slate-900">
            {profile.tamanho_kb.toFixed(1)} KB
          </div>
          <div className="mt-0.5 text-[10px] text-slate-400">Armazenamento</div>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-3 shadow-2xs">
          <div className="text-[10.5px] font-medium text-slate-400">Duplicatas</div>
          <div className="mt-1 font-mono text-sm font-bold text-slate-900">
            {profile.linhas_duplicadas ?? 0}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-400">
            {profile.linhas_duplicadas ? 'Requer deduplicação' : '0 duplicatas (íntegro)'}
          </div>
        </div>
      </div>

      {/* Chaves Candidatas se houver */}
      {profile.chaves_candidatas && profile.chaves_candidatas.length > 0 && (
        <div className="mx-4 mb-3 flex items-center gap-2 rounded-xl bg-slate-50 border border-slate-200/80 px-3 py-2 text-xs">
          <Key className="h-3.5 w-3.5 text-blue-600 shrink-0" />
          <span className="font-semibold text-slate-700">Chaves Primárias Recomendadas:</span>
          <div className="flex flex-wrap gap-1">
            {profile.chaves_candidatas.map((keyName) => (
              <span
                key={keyName}
                className="rounded-md bg-white border border-blue-200 px-2 py-0.5 font-mono text-[10.5px] font-bold text-blue-700 shadow-2xs"
              >
                {keyName}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Accordion: Tabela de Colunas */}
      <div className="border-t border-slate-100 px-4 py-2 bg-white/70">
        <button
          type="button"
          onClick={() => setShowColumns(!showColumns)}
          className="flex w-full items-center justify-between py-1 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors cursor-pointer"
        >
          <span className="flex items-center gap-1.5">
            <Table className="h-3.5 w-3.5 text-blue-600" />
            <span>Estrutura e Tipos das Colunas ({columnsList.length})</span>
          </span>
          {showColumns ? <ChevronUp className="h-3.5 w-3.5 text-slate-400" /> : <ChevronDown className="h-3.5 w-3.5 text-slate-400" />}
        </button>

        {showColumns && (
          <div className="mt-2 max-h-56 overflow-y-auto rounded-xl border border-slate-200/80 bg-white">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-50 border-b border-slate-100 text-[10.5px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-3 py-2">Coluna</th>
                  <th className="px-3 py-2">Tipo</th>
                  <th className="px-3 py-2">Valores Únicos</th>
                  <th className="px-3 py-2">Nulos</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px] text-slate-700">
                {columnsList.map((col, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50">
                    <td className="px-3 py-1.5 font-bold text-slate-900 font-sans">{col.nome}</td>
                    <td className="px-3 py-1.5 text-slate-500">{col.tipo}</td>
                    <td className="px-3 py-1.5 text-slate-800">{col.valores_unicos.toLocaleString()}</td>
                    <td className="px-3 py-1.5">
                      <span className={cn(col.nulos > 0 ? 'text-amber-600 font-bold' : 'text-slate-400')}>
                        {col.nulos} ({col.percentual_nulos.toFixed(1)}%)
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Accordion: Preview de Amostra das Primeiras Linhas */}
      {profile.amostra_linhas && profile.amostra_linhas.length > 0 && (
        <div className="border-t border-slate-100 px-4 py-2 bg-white/70">
          <button
            type="button"
            onClick={() => setShowSample(!showSample)}
            className="flex w-full items-center justify-between py-1 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors cursor-pointer"
          >
            <span className="flex items-center gap-1.5">
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
              <span>Amostra das Primeiras Linhas ({profile.amostra_linhas.length})</span>
            </span>
            {showSample ? <ChevronUp className="h-3.5 w-3.5 text-slate-400" /> : <ChevronDown className="h-3.5 w-3.5 text-slate-400" />}
          </button>

          {showSample && (
            <div className="mt-2 overflow-x-auto rounded-xl border border-slate-200/80 bg-white">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 border-b border-slate-100 text-[10.5px] font-bold text-slate-500 uppercase tracking-wider">
                  <tr>
                    {Object.keys(profile.amostra_linhas[0]).map((h) => (
                      <th key={h} className="px-3 py-2 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono text-[11px] text-slate-700">
                  {profile.amostra_linhas.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-50/50">
                      {Object.values(row).map((val, cIdx) => (
                        <td key={cIdx} className="px-3 py-1.5 whitespace-nowrap">{String(val)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default KrakenDataProfileCard;

