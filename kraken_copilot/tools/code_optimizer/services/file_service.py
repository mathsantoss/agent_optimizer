"""Serviço de gerenciamento de arquivos: leitura segura, escrita autorizada, validação de caminhos e backups."""
from pathlib import Path
from typing import Any

from kraken_copilot import config
from kraken_copilot.utils import resolve_safe_path


def get_pipeline_tmp_dir() -> Path:
    """Retorna e assegura a existência do diretório fixo 'krakenlake/tmp' (ou 'pipeline/tmp')."""
    tmp_dir = config.PROJECT_ROOT / "krakenlake" / "tmp"
    if not (config.PROJECT_ROOT / "krakenlake").exists() and (config.PROJECT_ROOT / "pipeline").exists():
        tmp_dir = config.PROJECT_ROOT / "pipeline" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir


def get_file_tmp_paths(file_path: str | Path | None = None) -> tuple[Path, Path]:
    """Retorna os caminhos (original_bak, otimizado_bak) em krakenlake/tmp para o arquivo especificado."""
    tmp_dir = get_pipeline_tmp_dir()
    if not file_path:
        stem = "script"
    else:
        name = Path(file_path).name
        if name.endswith("_original.bak"):
            stem = name[:-len("_original.bak")]
        elif name.endswith("_otimizado.bak"):
            stem = name[:-len("_otimizado.bak")]
        elif name.endswith(".bak"):
            stem = Path(name).stem
        else:
            stem = Path(name).stem
    return tmp_dir / f"{stem}_original.bak", tmp_dir / f"{stem}_otimizado.bak"


def snapshot_workspace_file(target_file: str | Path, content: str | None = None, force: bool = False) -> Path | None:
    """
    Garante que existe um snapshot krakenlake/tmp/<stem>_original.bak congelado do arquivo do workspace.
    Se o snapshot já existir e não for 'force', preserva o original intacto como baseline do diff.
    """
    try:
        resolved = resolve_pipeline_path(target_file, allow_write=False)
        orig_file, _ = get_file_tmp_paths(resolved)
        if force or not orig_file.is_file() or orig_file.stat().st_size == 0:
            if content is None:
                if resolved.is_file():
                    content = resolved.read_text(encoding="utf-8")
                else:
                    content = ""
            if content:
                orig_file.write_text(content, encoding="utf-8")
        return orig_file
    except Exception:
        return None


def sync_pipeline_tmp_files(
    original_content: str = "",
    optimized_content: str | None = None,
    target_file: str | Path | None = None,
) -> tuple[Path, Path | None]:
    """
    Mantém fisicamente salvos os 2 arquivos dinâmicos na pasta krakenlake/tmp:
    1. krakenlake/tmp/<stem>_original.bak (backup do original congelado no contexto)
    2. krakenlake/tmp/<stem>_otimizado.bak (pipeline otimizado / proposta atual)
    Sempre faz overwrite atualizando o conteúdo com base no arquivo e proposta atual.
    Remove qualquer .bak legado da raiz de pipeline/ ou krakenlake/.
    """
    orig_file, opt_file = get_file_tmp_paths(target_file)

    if original_content:
        orig_file.write_text(original_content, encoding="utf-8")

    optimized_file = None
    if optimized_content is not None and optimized_content.strip():
        optimized_file = opt_file
        optimized_file.write_text(optimized_content, encoding="utf-8")
    elif opt_file.exists():
        optimized_file = opt_file

    # Remove qualquer pipeline_prep.py.bak da raiz legada da pasta pipeline/
    legacy_bak = config.PROJECT_ROOT / "pipeline" / "pipeline_prep.py.bak"
    if legacy_bak.is_file():
        try:
            legacy_bak.unlink()
        except Exception:
            pass

    return orig_file, optimized_file


def get_default_workspace_pipeline() -> str:
    """Descobre dinamicamente o arquivo Python principal no workspace do krakenlake."""
    ws_dir = config.PROJECT_ROOT / "krakenlake" / "workspace"
    if ws_dir.is_dir():
        py_files = sorted([f for f in ws_dir.glob("*.py") if not f.name.endswith(".bak") and not f.name.startswith(".")])
        with_content = [f for f in py_files if f.stat().st_size > 0]
        if with_content:
            return f"krakenlake/workspace/{with_content[0].name}"
        if py_files:
            return f"krakenlake/workspace/{py_files[0].name}"
    return "krakenlake/workspace/pipeline.py"


def resolve_pipeline_path(file_path: str | Path | None = None, allow_write: bool = False) -> Path:
    """Resolve caminhos relativos do projeto, aceitando arquivos no workspace krakenlake e atalhos de tmp."""
    if not file_path or not str(file_path).strip():
        file_path = get_default_workspace_pipeline()
    clean_path = str(file_path).strip()

    # Atalhos de arquivos de backup/temporários dinâmicos
    tmp_dir = get_pipeline_tmp_dir()
    clean_name = Path(clean_path).name
    if clean_name.endswith("_original.bak") or clean_name.endswith("_otimizado.bak"):
        tmp_target = tmp_dir / clean_name
        if tmp_target.is_file():
            return resolve_safe_path(str(tmp_target.relative_to(config.PROJECT_ROOT)), allow_write=allow_write)

    if clean_path in ("pipeline_prep.py.bak", "pipeline_prep.bak", "pipeline/pipeline_prep.py.bak", "pipeline_prep_original.bak", "pipeline/tmp/pipeline_prep_original.bak", "pipeline_prep_original.py"):
        orig = tmp_dir / "pipeline_prep_original.bak"
        return resolve_safe_path(str(orig.relative_to(config.PROJECT_ROOT)), allow_write=allow_write)
    elif clean_path in ("pipeline_prep_otimizado.bak", "pipeline_prep_otimizado", "pipeline/tmp/pipeline_prep_otimizado.bak", "pipeline_prep_otimizado.py"):
        otim = tmp_dir / "pipeline_prep_otimizado.bak"
        return resolve_safe_path(str(otim.relative_to(config.PROJECT_ROOT)), allow_write=allow_write)

    # 1. Verifica se existe no workspace do krakenlake
    ws_file = config.PROJECT_ROOT / "krakenlake" / "workspace" / Path(clean_path).name
    if ws_file.is_file():
        return resolve_safe_path(str(ws_file.relative_to(config.PROJECT_ROOT)), allow_write=allow_write)

    # 2. Verifica se o arquivo é relativo direto sob krakenlake/
    kl_file = config.PROJECT_ROOT / "krakenlake" / clean_path
    if kl_file.is_file():
        return resolve_safe_path(str(kl_file.relative_to(config.PROJECT_ROOT)), allow_write=allow_write)

    # 3. Caso o usuário forneça apenas o nome de um arquivo (ex: 'outro_pipeline.py') e a pasta workspace exista
    if not clean_path.startswith("krakenlake/") and not clean_path.startswith("pipeline/"):
        target_ws = config.PROJECT_ROOT / "krakenlake" / "workspace" / clean_path
        if (config.PROJECT_ROOT / "krakenlake" / "workspace").exists():
            return resolve_safe_path(str(target_ws.relative_to(config.PROJECT_ROOT)), allow_write=allow_write)

    # 4. Caso legado 'pipeline/pipeline_prep.py'
    if clean_path.startswith("pipeline/"):
        candidate = config.PROJECT_ROOT / "krakenlake" / "workspace" / Path(clean_path).name
        if candidate.is_file():
            return resolve_safe_path(str(candidate.relative_to(config.PROJECT_ROOT)), allow_write=allow_write)

    return resolve_safe_path(clean_path, allow_write=allow_write)


def read_source_file(file_path: str | None = None) -> dict[str, Any]:
    """Lê o conteúdo de um arquivo do projeto de forma segura."""
    if not file_path or not str(file_path).strip():
        file_path = get_default_workspace_pipeline()
    try:
        resolved_path = resolve_pipeline_path(file_path, allow_write=False)
        if not resolved_path.is_file():
            return {
                "success": False,
                "file_path": file_path,
                "content": "",
                "line_count": 0,
                "is_empty": True,
                "error": f"Arquivo não encontrado: {file_path}",
            }

        content = resolved_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        is_empty = len(content.strip()) == 0

        try:
            rel_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            rel_path = str(resolved_path)

        return {
            "success": True,
            "file_path": rel_path,
            "content": content,
            "line_count": len(lines),
            "is_empty": is_empty,
            "error": None,
        }
    except Exception as err:
        return {
            "success": False,
            "file_path": file_path,
            "content": "",
            "line_count": 0,
            "is_empty": True,
            "error": f"Erro ao ler arquivo: {str(err)}",
        }


def create_backup_file(resolved_path: Path) -> Path | None:
    """Cria uma cópia de segurança em krakenlake/tmp/<stem>_original.bak do arquivo alvo."""
    if resolved_path.is_file() and resolved_path.stat().st_size > 0:
        content = resolved_path.read_text(encoding="utf-8")
        orig_file, _ = sync_pipeline_tmp_files(original_content=content, target_file=resolved_path)

        # Remove qualquer .bak legado da pasta de trabalho
        legacy_bak = resolved_path.parent / f"{resolved_path.name}.bak"
        if legacy_bak.is_file():
            try:
                legacy_bak.unlink()
            except Exception:
                pass

        # Se for teste isolado fora do projeto padrão, preserva backup local para asserts de teste
        if resolved_path.parent != config.PROJECT_ROOT / "pipeline" and resolved_path.parent != config.PROJECT_ROOT / "krakenlake" / "workspace":
            backup_path = resolved_path.with_suffix(resolved_path.suffix + ".bak")
            backup_path.write_text(content, encoding="utf-8")
            return backup_path

        return orig_file
    return None


def write_source_file(
    file_path: str | None = None,
    content: str = "",
    create_backup: bool = True,
) -> dict[str, Any]:
    """
    Grava o código no disco criando automaticamente backup (.bak) do arquivo original
    e sincronizando fisicamente os arquivos fixos em pipeline/tmp/.
    Garante que o diretório de destino exista e respeite os diretórios permitidos.
    """
    if not file_path or not str(file_path).strip():
        file_path = get_default_workspace_pipeline()
    if not content or not content.strip():
        return {
            "success": False,
            "file_path": file_path,
            "backup_created": False,
            "error": "O conteúdo do arquivo não pode ser vazio.",
        }

    try:
        resolved_path = resolve_pipeline_path(file_path, allow_write=True)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        backup_path = None
        if create_backup:
            backup_path = create_backup_file(resolved_path)

        resolved_path.write_text(content, encoding="utf-8")
        lines = len(content.splitlines())

        try:
            sync_pipeline_tmp_files(optimized_content=content, target_file=resolved_path)
        except Exception:
            pass

        try:
            rel_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            rel_path = str(resolved_path)

        return {
            "success": True,
            "file_path": rel_path,
            "line_count": lines,
            "backup_created": backup_path is not None,
            "backup_file": str(backup_path.name) if backup_path else None,
            "error": None,
        }
    except Exception as err:
        return {
            "success": False,
            "file_path": file_path,
            "backup_created": False,
            "error": f"Erro ao gravar arquivo: {str(err)}",
        }
