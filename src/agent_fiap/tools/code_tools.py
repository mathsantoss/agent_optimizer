"""Ferramentas de engenharia de código: leitura, gravação segura, execução de pipelines e testes."""
import subprocess
import sys
from pathlib import Path

from .. import config
from ..utils import resolve_safe_path


def _resolve_project_file(file_path: str, allow_write: bool = False) -> Path:
    """Resolve caminhos relativos do projeto, aceitando 'pipeline_prep.py' como atalho para 'pipeline/pipeline_prep.py'."""
    normalized_path = file_path.strip()
    if normalized_path == "pipeline_prep.py":
        normalized_path = "pipeline/pipeline_prep.py"
    return resolve_safe_path(normalized_path, allow_write=allow_write)


def read_file(file_path: str = "pipeline/pipeline_prep.py") -> str:
    """
    Lê o conteúdo de um arquivo do projeto (padrão: 'pipeline/pipeline_prep.py').
    Se o arquivo estiver vazio, informa que está pronto para receber código via save_file.
    """
    try:
        resolved_path = _resolve_project_file(file_path, allow_write=False)
        if not resolved_path.is_file():
            return f"Arquivo não encontrado: {file_path}"

        file_content = resolved_path.read_text(encoding="utf-8")
        if not file_content.strip():
            relative_path = resolved_path.relative_to(config.PROJECT_ROOT)
            return (
                f"O arquivo '{relative_path}' existe e está atualmente vazio (0 bytes). "
                "Pronto para receber a implementação via 'save_file'."
            )
        return file_content
    except Exception as error:
        return f"Erro ao ler arquivo: {str(error)}"


def save_file(file_path: str = "pipeline/pipeline_prep.py", content: str = "") -> str:
    """
    Salva ou atualiza código em um arquivo permitido do projeto (padrão: 'pipeline/pipeline_prep.py').
    Valida a sintaxe Python (.py) antes de gravar e cria backup automático (.bak) se o arquivo já possuir conteúdo.
    """
    if not content.strip():
        return "Erro: o conteúdo do arquivo a ser salvo não pode ser vazio."

    try:
        resolved_path = _resolve_project_file(file_path, allow_write=True)

        # Valida a sintaxe Python antes de persistir no disco
        if resolved_path.suffix == ".py":
            try:
                compile(content, resolved_path.name, "exec")
            except SyntaxError as syntax_error:
                return (
                    f"ERRO DE SINTAXE Python na linha {syntax_error.lineno}: {syntax_error.msg}. "
                    "O arquivo NÃO foi salvo. Corrija o código."
                )

        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        if resolved_path.exists() and resolved_path.stat().st_size > 0:
            backup_path = resolved_path.with_suffix(resolved_path.suffix + ".bak")
            backup_path.write_text(resolved_path.read_text(encoding="utf-8"), encoding="utf-8")

        resolved_path.write_text(content, encoding="utf-8")
        line_count = len(content.splitlines())
        relative_path = resolved_path.relative_to(config.PROJECT_ROOT)
        return f"Arquivo '{relative_path}' salvo com SUCESSO com {line_count} linhas gravadas no disco."
    except Exception as error:
        return f"Erro ao salvar arquivo: {str(error)}"


def run_pipeline(file_path: str = "pipeline/pipeline_prep.py") -> str:
    """
    Executa o script do pipeline com Python em subprocesso para validar seu funcionamento.
    """
    try:
        resolved_path = _resolve_project_file(file_path, allow_write=False)
        if not resolved_path.is_file() or resolved_path.stat().st_size == 0:
            return (
                f"Não é possível executar: o arquivo '{file_path}' está vazio ou não existe. "
                "Use a ferramenta 'save_file' para gravar o código antes de executar."
            )

        completed_process = subprocess.run(
            [sys.executable, str(resolved_path)],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if completed_process.returncode == 0:
            standard_output = completed_process.stdout.strip()
            output_message = standard_output if standard_output else "(executou sem erros de terminal)"
            return f"Pipeline executado com SUCESSO!\nSaída:\n{output_message}"
        return f"Erro na execução do pipeline (exit code {completed_process.returncode}):\n{completed_process.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Execução do pipeline interrompida: excedeu o tempo limite de 45 segundos."
    except Exception as error:
        return f"Erro ao executar pipeline: {str(error)}"


def run_tests(target_path: str = "tests") -> str:
    """
    Executa a suíte de testes automatizados do projeto com pytest.
    """
    try:
        resolved_path = resolve_safe_path(target_path, allow_write=False)
        completed_process = subprocess.run(
            [sys.executable, "-m", "pytest", str(resolved_path), "-q", "--no-header"],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        combined_output = (completed_process.stdout + completed_process.stderr).strip()
        execution_status = "SUCESSO" if completed_process.returncode == 0 else "FALHA"
        return f"Resultado dos testes [{execution_status}]:\n{combined_output}"
    except Exception as error:
        return f"Erro ao executar testes: {str(error)}"
