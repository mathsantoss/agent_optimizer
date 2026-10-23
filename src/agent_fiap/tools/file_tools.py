import os


def ler_arquivo(caminho_arquivo: str) -> str:
    """
    Lê o conteúdo de um arquivo de código ou texto.
    Use isso para inspecionar o código do pipeline atual.
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Erro ao ler o arquivo: {str(e)}"

def escrever_arquivo(caminho_arquivo: str, conteudo: str) -> str:
    """
    Escreve ou sobrescreve um arquivo com o novo conteúdo otimizado.
    """
    try:
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        return f"Arquivo {caminho_arquivo} salvo com sucesso."
    except Exception as e:
        return f"Erro ao escrever no arquivo: {str(e)}"
