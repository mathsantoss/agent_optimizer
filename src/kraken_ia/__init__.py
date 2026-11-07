from .agent import root_agent
from .observability import flush_observability, setup_observability

setup_observability(root_agent)
