"""Os testes rodam contra um mini-projeto em tests/fixtures/projeto, para não
depender dos dados/pipelines de exemplo do repositório. Precisa executar antes
de qualquer import de kraken_copilot."""
import os
from pathlib import Path

os.environ["KRAKEN_COPILOT_ROOT"] = str(Path(__file__).parent / "fixtures" / "projeto")
