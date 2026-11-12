import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Activity,
  ExternalLink,
  RefreshCw,
  ShieldCheck,
  AlertCircle,
  Cpu,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ObservabilityViewProps {
  onBackToChat: () => void;
  className?: string;
}

const GRAFANA_URL =
  'http://localhost:3000/d/kraken-copilot-observability/kraken-copilot-observability?orgId=1&kiosk=tv';

export function ObservabilityView({ onBackToChat, className }: ObservabilityViewProps) {
  const [iframeKey, setIframeKey] = useState(0);
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(true);

  const checkGrafanaHealth = async () => {
    setChecking(true);
    try {
      // Tenta checar o health endpoint do Grafana ou endpoint local
      const res = await fetch('http://localhost:3000/api/health', {
        mode: 'no-cors',
      });
      // no-cors resolve mesmo com tipo opaque
      setIsOnline(true);
    } catch {
      setIsOnline(false);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkGrafanaHealth();
  }, []);

  const handleRefresh = () => {
    setIframeKey((prev) => prev + 1);
    checkGrafanaHealth();
  };

  return (
    <div className={cn('flex flex-col h-full overflow-hidden bg-[#fafbfd]', className)}>
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-slate-200/90 bg-white px-6 py-3 shadow-2xs select-none">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBackToChat}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-blue-600 transition-all active:scale-98 cursor-pointer"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Voltar ao Chat</span>
          </button>

          <div className="h-4 w-[1px] bg-slate-200" />

          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Observabilidade e Telemetria (Grafana &amp; OpenTelemetry)
            </h2>
            <span className="hidden sm:inline-block rounded-full bg-emerald-50 border border-emerald-200/70 px-2 py-0.5 text-[10px] font-mono font-semibold text-emerald-700">
              LGTM Stack
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={handleRefresh}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-slate-900 transition-all cursor-pointer"
            title="Recarregar painel"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', checking && 'animate-spin')} />
            <span>Recarregar</span>
          </button>

          <a
            href="http://localhost:3000/d/kraken-copilot-observability/kraken-copilot-observability?orgId=1"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-emerald-700 transition-all cursor-pointer"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            <span>Abrir no Grafana</span>
          </a>
        </div>
      </div>

      {/* Main Container com Iframe do Grafana */}
      <div className="flex-1 relative overflow-hidden bg-slate-900">
        <iframe
          key={iframeKey}
          src={GRAFANA_URL}
          className="h-full w-full border-0"
          title="Grafana Observability Dashboard"
        />

        {/* Fallback de Ajuda se o Grafana não carregar */}
        <div className="pointer-events-none absolute bottom-4 right-4 z-10">
          <div className="pointer-events-auto flex items-center gap-2 rounded-xl bg-slate-900/90 backdrop-blur-md px-3.5 py-2 text-[11px] text-slate-300 shadow-xl border border-slate-700">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Porta 3000 (LGTM / Grafana)</span>
            <span className="text-slate-500">·</span>
            <a
              href="http://localhost:3000"
              target="_blank"
              rel="noreferrer"
              className="font-medium text-emerald-400 hover:underline"
            >
              http://localhost:3000
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ObservabilityView;

