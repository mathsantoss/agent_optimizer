#!/usr/bin/env python3
"""Inicializador unificado do Kraken Copilot via Python."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()


def check_and_start_docker():
    """Tenta inicializar a stack de observabilidade se o Docker estiver disponível."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        print("[!] Docker não encontrado no PATH. Observabilidade Docker não inicializada.")
        return

    try:
        res = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            print("[✓] Docker ativo. Subindo stack de observabilidade (LGTM/Grafana)...")
            compose_file = ROOT / "docker-compose.observability.yml"
            if compose_file.exists():
                subprocess.run(["docker", "compose", "-f", str(compose_file), "up", "-d"], check=False)
                print("[✓] Grafana online em http://localhost:3000")
        else:
            print("[!] Docker daemon inativo. Continuando sem container do Grafana.")
    except Exception as e:
        print(f"[!] Aviso ao verificar Docker: {e}")


def ensure_frontend_built():
    """Compila o frontend React se dist/index.html não existir."""
    dist_index = ROOT / "kraken_copilot" / "web" / "ui" / "dist" / "index.html"
    if not dist_index.exists():
        print("[*] Compilando frontend React com npm run build...")
        subprocess.run(["npm", "run", "build"], cwd=str(ROOT), check=False)


def main():
    check_and_start_docker()
    ensure_frontend_built()

    print("\n" + "=" * 58)
    print("🐙 Kraken Copilot - Analytics & Pipelines")
    print("   👉 Aplicação Web: http://localhost:8080")
    print("   👉 Swagger API:   http://localhost:8080/docs")
    print("   👉 Grafana:       http://localhost:3000")
    print("=" * 58 + "\n")

    os.environ.setdefault("PYTHONPATH", str(ROOT))
    import uvicorn
    from kraken_copilot.web.server import app

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    main()

