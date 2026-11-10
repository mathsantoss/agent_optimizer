"""Módulo Web do Kraken Copilot contendo servidor FastAPI, rotas, runner e storage."""
from kraken_copilot.web.server import app, run, storage, adk_runner

__all__ = ["app", "run", "storage", "adk_runner"]

