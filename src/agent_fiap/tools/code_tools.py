"""Ferramentas para leitura, escrita, execução e teste de pipelines e código."""
import subprocess
import sys
from pathlib import Path
from .. import config
from ..utils import safe_path


def _resolver_arquivo(caminho_arquivo: str, write: bool = False) -> Path:
    """Resolve caminhos relativos facilitando se o usuário passar apenas 'pipeline_prep.py'."""
    caminho = caminho_arquivo.strip()
    if caminho == "pipeline_prep.py":
        caminho = "pipeline/pipeline_prep.py"
    return safe_path(caminho, write=write)


def ler_arquivo(caminho_arquivo: str = "pipeline/pipeline_prep.py") -> str:
    """
    Lê o conteúdo de um arquivo do projeto (como o pipeline ativo pipeline/pipeline_prep.py).
    Se o arquivo estiver vazio, retorna que está pronto para receber código via salvar_arquivo.
    """
    try:
        p = _resolver_arquivo(caminho_arquivo, write=False)
        if not p.is_file():
            return f"Arquivo não encontrado: {caminho_arquivo}"
        conteudo = p.read_text(encoding="utf-8")
        if not conteudo.strip():
            return f"O arquivo '{p.relative_to(config.PROJECT_ROOT)}' existe e está atualmente vazio (0 bytes). Pronto para receber a implementação via 'salvar_arquivo'."
        return conteudo
    except Exception as e:
        return f"Erro ao ler arquivo: {str(e)}"


def salvar_arquivo(caminho_arquivo: str = "pipeline/pipeline_prep.py", conteudo: str = "") -> str:
    """
    Salva ou atualiza código diretamente em um arquivo do projeto (padrão: 'pipeline/pipeline_prep.py').
    Valida a sintaxe Python (.py) antes de salvar e cria backup (.bak) se o arquivo já tiver conteúdo.
    SEMPRE invoque esta ferramenta quando criar, otimizar ou modificar código ou pipelines.
    """
    if not conteudo.strip():
        return "Erro: o conteúdo do arquivo a ser salvo não pode ser vazio."

    try:
        p = _resolver_arquivo(caminho_arquivo, write=True)

        # Validação de sintaxe Python para evitar gravação de scripts inválidos
        if p.suffix == ".py":
            try:
                compile(conteudo, p.name, "exec")
            except SyntaxError as e:
                return f"ERRO DE SINTAXE Python na linha {e.lineno}: {e.msg}. O arquivo NÃO foi salvo. Corrija o código."

        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and p.stat().st_size > 0:
            bak = p.with_suffix(p.suffix + ".bak")
            bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

        p.write_text(conteudo, encoding="utf-8")
        linhas = len(conteudo.splitlines())
        return f"Arquivo '{p.relative_to(config.PROJECT_ROOT)}' salvo com SUCESSO com {linhas} linhas gravadas no disco."
    except Exception as e:
        return f"Erro ao salvar arquivo: {str(e)}"


def salvar_pipeline(conteudo: str) -> str:
    """Compatibilidade retroativa: salva no pipeline ativo."""
    return salvar_arquivo("pipeline/pipeline_prep.py", conteudo)


def escrever_arquivo(caminho_arquivo: str, conteudo: str) -> str:
    """Compatibilidade retroativa: salva no caminho especificado."""
    return salvar_arquivo(caminho_arquivo, conteudo)


def executar_pipeline(caminho_arquivo: str = "pipeline/pipeline_prep.py") -> str:
    """
    Executa o script do pipeline com Python para validar se roda sem erros de execução ou sintaxe.
    """
    try:
        p = _resolver_arquivo(caminho_arquivo, write=False)
        if not p.is_file() or p.stat().st_size == 0:
            return f"Não é possível executar: o arquivo '{caminho_arquivo}' está vazio ou não existe. Use a ferramenta 'salvar_arquivo' para gravar o código antes de executar."

        res = subprocess.run(
            [sys.executable, str(p)],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if res.returncode == 0:
            saida = res.stdout.strip()
            return f"Pipeline executado com SUCESSO!\nSaída:\n{saida if saida else '(executou sem erros de terminal)'}"
        else:
            return f"Erro na execução do pipeline (exit code {res.returncode}):\n{res.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Execução do pipeline interrompida: excedeu o tempo limite de 45 segundos."
    except Exception as e:
        return f"Erro ao executar pipeline: {str(e)}"


def executar_testes(alvo: str = "tests") -> str:
    """
    Executa a suíte de testes automatizados com pytest.
    """
    try:
        p = safe_path(alvo, write=False)
        res = subprocess.run(
            [sys.executable, "-m", "pytest", str(p), "-q", "--no-header"],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        saida = (res.stdout + res.stderr).strip()
        status = "SUCESSO" if res.returncode == 0 else "FALHA"
        return f"Resultado dos testes [{status}]:\n{saida}"
    except Exception as e:
        return f"Erro ao executar testes: {str(e)}"
