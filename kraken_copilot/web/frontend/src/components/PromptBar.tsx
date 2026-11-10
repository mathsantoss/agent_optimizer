import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import {
  ArrowUp,
  Sparkles,
  Cpu,
  ChevronDown,
  Check,
  FileCode2,
  FolderCode,
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

export interface PromptBarProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  models: GeminiModel[];
  currentModel: string;
  onSelectModel: (modelId: string) => void;
  workspaceFiles: WorkspaceFile[];
  selectedWorkspaceFile: string;
  onSelectWorkspaceFile: (filename: string) => void;
  placeholder?: string;
  className?: string;
}

export function PromptBar({
  onSendMessage,
  isLoading,
  models = [],
  currentModel,
  onSelectModel,
  workspaceFiles = [],
  selectedWorkspaceFile,
  onSelectWorkspaceFile,
  placeholder = 'Pergunte sobre os dados, solicite features ou autorize otimização de pipeline...',
  className,
}: PromptBarProps) {
  const [text, setText] = useState('');
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [fileDropdownOpen, setFileDropdownOpen] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);
  const fileDropdownRef = useRef<HTMLDivElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(Math.max(scrollHeight, 44), 160)}px`;
    }
  }, [text]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(event.target as Node)) {
        setModelDropdownOpen(false);
      }
      if (fileDropdownRef.current && !fileDropdownRef.current.contains(event.target as Node)) {
        setFileDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const activeModelObj = models.find((m) => m.id === currentModel) || {
    id: currentModel || 'gemini-2.5-flash',
    nome: currentModel || 'Gemini 2.5 Flash',
  };

  return (
    <div className={cn('relative w-full max-w-5xl mx-auto px-4 sm:px-6 pb-4 select-none', className)}>
      {/* Container Principal */}
      <div className="relative rounded-2xl border border-slate-300/90 bg-white shadow-xs transition-all focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100/80">
        {/* Barra Superior com Controles: Seletor de Modelo Gemini + Seletor de Arquivo Workspace */}
        <div className="flex flex-wrap items-center justify-between border-b border-slate-100 px-3 py-1.5 text-xs gap-2">
          <div className="flex items-center gap-2">
            {/* Seletor do Modelo Gemini */}
            <div className="relative" ref={modelDropdownRef}>
              <button
                type="button"
                onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-slate-50/70 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                title="Trocar modelo da família Gemini"
              >
                <Cpu className="h-3.5 w-3.5 text-blue-600" />
                <span className="truncate max-w-[140px] sm:max-w-none">{activeModelObj.nome}</span>
                <ChevronDown className="h-3 w-3 text-slate-400" />
              </button>

              {modelDropdownOpen && (
                <div className="absolute bottom-full left-0 mb-1.5 w-80 max-h-80 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl z-50">
                  <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    Família Gemini (2.5 Flash até 4.0 Argon)
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
                        }}
                        className={cn(
                          'flex w-full items-start justify-between rounded-lg px-2.5 py-2 text-left text-xs transition-colors cursor-pointer',
                          isSelected
                            ? 'bg-blue-50 text-blue-900 font-semibold'
                            : 'text-slate-700 hover:bg-slate-50'
                        )}
                      >
                        <div className="flex-1 pr-2">
                          <div className="flex items-center gap-1.5">
                            <span>{mod.nome}</span>
                            {mod.destaque && (
                              <span className="rounded bg-blue-100/70 px-1.5 py-0.2 text-[10px] font-normal text-blue-700">
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

            {/* Seletor Dinâmico de Script no Workspace (krakenlake/workspace/) */}
            <div className="relative" ref={fileDropdownRef}>
              <button
                type="button"
                onClick={() => setFileDropdownOpen(!fileDropdownOpen)}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-slate-50/70 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                title="Selecionar script Python alvo no workspace"
              >
                <FileCode2 className="h-3.5 w-3.5 text-emerald-600" />
                <span className="font-mono text-emerald-800 truncate max-w-[150px] sm:max-w-none">
                  {selectedWorkspaceFile || 'pipeline_prep.py'}
                </span>
                <ChevronDown className="h-3 w-3 text-slate-400" />
              </button>

              {fileDropdownOpen && (
                <div className="absolute bottom-full left-0 mb-1.5 w-72 max-h-64 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl z-50">
                  <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    Workspace Scripts (krakenlake/workspace/)
                  </div>
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
                          'flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs transition-colors cursor-pointer',
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

          {/* Badge Informativo de Datalake Ativo */}
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-mono">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>krakenlake/catalog</span>
          </div>
        </div>

        {/* Textarea e Ação de Enviar */}
        <div className="relative flex flex-col p-3">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            disabled={isLoading}
            className="w-full resize-none border-0 bg-transparent text-sm text-slate-800 placeholder:text-slate-400 focus:outline-hidden focus:ring-0 leading-relaxed pr-24"
            style={{ minHeight: '44px' }}
          />

          <div className="mt-2 flex items-center justify-between">
            <div className="text-[11px] text-slate-400 select-none">
              <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-600">Enter</kbd> para enviar · <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-600">Shift+Enter</kbd> para nova linha
            </div>

            <button
              type="button"
              onClick={handleSend}
              disabled={!text.trim() || isLoading}
              className={cn(
                'inline-flex items-center justify-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold shadow-xs transition-all select-none',
                text.trim() && !isLoading
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
  );
}

export default PromptBar;
