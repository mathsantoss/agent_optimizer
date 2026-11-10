#!/usr/bin/env bash
set -e

# ==============================================================================
# Kraken Copilot - Inicializador Unificado
# Sobe a stack de observabilidade (LGTM/Grafana) e o servidor web FastAPI/React
# ==============================================================================

echo "=========================================================="
echo "🐙 Inicializando Kraken Copilot (Analytics & Pipelines)"
echo "=========================================================="

DEV_MODE=false
if [[ "$1" == "--dev" ]]; then
  DEV_MODE=true
  echo "🔧 Modo de desenvolvimento ativado (--dev)"
fi

# 1. Checa e sobe a stack de observabilidade no Docker se disponível
if command -v docker &> /dev/null && docker info &> /dev/null; then
  echo "📊 Subindo stack de observabilidade (Grafana, Loki, Tempo, Prometheus)..."
  if docker compose version &> /dev/null; then
    docker compose -f docker-compose.observability.yml up -d
  elif command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.observability.yml up -d
  fi
  echo "✓ Observabilidade online em http://localhost:3000"
else
  echo "⚠️ Docker daemon não detectado ou inativo. Continuando sem stack de observabilidade Docker."
  echo "   (Para ativar o Grafana local, inicie o Docker Desktop ou serviço docker)."
fi

# 2. Garante que os assets do frontend React estão compilados
if [ ! -f "kraken_copilot/web/ui/dist/index.html" ]; then
  echo "📦 Compilando assets do frontend React..."
  npm run build
fi

# 3. Execução dos servidores
PYTHON_BIN="python"
if [ -f "/home/matheus/miniconda3/envs/fiap/bin/python" ]; then
  PYTHON_BIN="/home/matheus/miniconda3/envs/fiap/bin/python"
elif command -v python3 &> /dev/null; then
  PYTHON_BIN="python3"
fi

if [ "$DEV_MODE" = true ]; then
  echo "🚀 Iniciando backend FastAPI e frontend Vite Dev..."
  # Executa ambos em background com cleanup no Ctrl+C
  trap 'kill 0' SIGINT SIGTERM EXIT
  $PYTHON_BIN -m kraken_copilot.web.server &
  npm --prefix kraken_copilot/web/frontend run dev &
  wait
else
  echo "🚀 Servidor Kraken Copilot rodando em:"
  echo "   👉 http://localhost:8080"
  echo "   👉 Swagger API: http://localhost:8080/docs"
  echo "   👉 Grafana:     http://localhost:3000"
  echo "=========================================================="
  exec $PYTHON_BIN -m kraken_copilot.web.server
fi

