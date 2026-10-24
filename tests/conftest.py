"""Os testes rodam contra um mini-projeto em tests/fixtures/projeto, para não
depender dos dados/pipelines de exemplo do repositório. Precisa executar antes
de qualquer import de agent_fiap."""
import os
from pathlib import Path

os.environ["AGENT_FIAP_ROOT"] = str(Path(__file__).parent / "fixtures" / "projeto")
