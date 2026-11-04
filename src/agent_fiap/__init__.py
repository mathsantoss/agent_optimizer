import sys
from pathlib import Path

# Assegura que o diretório 'src' esteja presente no sys.path
_src_dir = str(Path(__file__).resolve().parents[1])
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Registra aliases no sys.modules para unificar 'src.agent_fiap' e 'agent_fiap'
_curr = sys.modules.get(__name__)
if _curr is not None:
    sys.modules.setdefault("agent_fiap", _curr)
    sys.modules.setdefault("src.agent_fiap", _curr)

from . import agent
from .agent import root_agent
from .observability import flush_observability, setup_observability

# Garante que ambos os identificadores no sys.modules apontem para a mesma instância
if __name__ in sys.modules:
    sys.modules["agent_fiap"] = sys.modules[__name__]
    sys.modules["src.agent_fiap"] = sys.modules[__name__]

setup_observability(root_agent)

__all__ = ["agent", "root_agent", "setup_observability", "flush_observability"]
