import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in Kraken Copilot UI:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen w-screen flex-col items-center justify-center bg-[#fafbfd] p-6 text-slate-800">
          <div className="flex max-w-md flex-col items-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 shadow-sm">
              <AlertTriangle className="h-7 w-7" />
            </div>
            <h1 className="text-lg font-bold text-slate-900">Algo deu errado na interface</h1>
            <p className="mt-2 text-xs leading-relaxed text-slate-500">
              Ocorreu uma falha inesperada na renderização. Seus dados e sessões continuam salvos no backend.
            </p>
            {this.state.error && (
              <pre className="my-4 max-h-36 w-full overflow-auto rounded-xl border border-slate-200 bg-white p-3 text-left font-mono text-[11px] text-red-600 shadow-2xs">
                {this.state.error.message}
              </pre>
            )}
            <button
              type="button"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors cursor-pointer"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Recarregar Aplicação</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

