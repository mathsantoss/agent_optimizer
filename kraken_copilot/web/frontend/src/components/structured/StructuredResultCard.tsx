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

  // Unwrap ToolResult wrapper if present ({ sucesso: true, data: {...}, schema_name: ... })
  const target = (data.data && typeof data.data === 'object') ? data.data : data;

  // 1. KrakenBenchmark
  if (target.kraken_benchmark || (target.tempo_execucao_otimizado !== undefined && target.speedup !== undefined)) {
    const benchData = (target.kraken_benchmark || target) as KrakenBenchmarkData;
    return <KrakenBenchmarkCard benchmark={benchData} className={className} />;
  }

  // 2. KrakenCodeDiff
  if (target.kraken_code_diff || (target.proposed_code && target.raw_diff !== undefined)) {
    const diffData = (target.kraken_code_diff || target) as KrakenCodeDiffData;
    return (
      <KrakenCodeDiffCard
        diff={diffData}
        onApprove={onApprove}
        onReject={onReject}
        className={className}
      />
    );
  }

  // 3. KrakenDataProfile
  if (target.kraken_data_profile || (target.dataset_nome && target.colunas && target.tamanho_kb !== undefined)) {
    const profileData = (target.kraken_data_profile || target) as KrakenDataProfileData;
    return <KrakenDataProfileCard profile={profileData} className={className} />;
  }

  // 4. KrakenStatisticalReport
  if (target.kraken_statistical_report || (target.total_linhas_analisadas && target.metricas_colunas)) {
    const statData = (target.kraken_statistical_report || target) as KrakenStatisticalReportData;
    return <KrakenStatisticalReportCard report={statData} className={className} />;
  }

  return null;
}

export default StructuredResultCard;
