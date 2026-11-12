import React from 'react';
import { KrakenBenchmarkCard, KrakenBenchmarkData } from './KrakenBenchmarkCard';
import { KrakenDataProfileCard, KrakenDataProfileData } from './KrakenDataProfileCard';
import { KrakenCodeDiffCard, KrakenCodeDiffData } from './KrakenCodeDiffCard';
import { KrakenStatisticalReportCard, KrakenStatisticalReportData } from './KrakenStatisticalReportCard';

export interface StructuredResultCardProps {
  data: any;
  onApprove?: (targetFile: string) => void;
  onReject?: (targetFile: string) => void;
  className?: string;
}

export function StructuredResultCard({
  data,
  onApprove,
  onReject,
  className,
}: StructuredResultCardProps) {
  if (!data || typeof data !== 'object') return null;

  // Desempacota recursivamente wrappers comuns (ToolResult.data, function_response.resultado, etc.)
  let target = data;
  if (target?.resultado && typeof target.resultado === 'object') {
    target = target.resultado;
  }
  if (target?.data && typeof target.data === 'object') {
    target = target.data;
  }
  if (target?.resultado && typeof target.resultado === 'object') {
    target = target.resultado;
  }
  if (target?.data && typeof target.data === 'object') {
    target = target.data;
  }

  // 1. KrakenBenchmark
  const benchCandidate = target.kraken_benchmark || target.benchmark || target;
  if (benchCandidate && (benchCandidate.speedup !== undefined || (benchCandidate.duracao_otimizado_s !== undefined && benchCandidate.duracao_baseline_s !== undefined))) {
    return <KrakenBenchmarkCard benchmark={benchCandidate as KrakenBenchmarkData} className={className} />;
  }

  // 2. KrakenCodeDiff
  const diffCandidate = target.kraken_code_diff || target.diff_info || target;
  if (diffCandidate && (diffCandidate.raw_diff !== undefined || (diffCandidate.proposed_code && (diffCandidate.adicoes !== undefined || diffCandidate.linhas)))) {
    return (
      <KrakenCodeDiffCard
        diff={diffCandidate as KrakenCodeDiffData}
        onApprove={onApprove}
        onReject={onReject}
        className={className}
      />
    );
  }

  // 3. KrakenDataProfile
  const profileCandidate = target.kraken_data_profile || target.estrutura?.kraken_data_profile || target;
  if (profileCandidate && profileCandidate.colunas && (profileCandidate.dataset_nome || profileCandidate.total_linhas !== undefined || profileCandidate.tamanho_kb !== undefined)) {
    return <KrakenDataProfileCard profile={profileCandidate as KrakenDataProfileData} className={className} />;
  }

  // 4. KrakenStatisticalReport
  const statCandidate = target.kraken_statistical_report || target.estatisticas?.kraken_statistical_report || target;
  if (statCandidate && statCandidate.metricas_colunas && (statCandidate.total_linhas_analisadas !== undefined || statCandidate.total_linhas_avaliadas !== undefined)) {
    return <KrakenStatisticalReportCard report={statCandidate as KrakenStatisticalReportData} className={className} />;
  }

  return null;
}

export default StructuredResultCard;
