# src/agent_fiap/tools/data_tools.py
import pandas as pd
import os

def explorar_esquema_dados(caminho_arquivo: str) -> str:
    """
    Retorna as colunas e os tipos de dados de um arquivo .csv ou .parquet.
    O agente deve passar o caminho completo (absoluto) ou relativo do arquivo.
    """
    # 1. Tenta verificar se o caminho exato passado existe
    caminho_completo = caminho_arquivo

    # 2. Se não existir, tenta compor com o caminho absoluto do seu projeto
    if not os.path.exists(caminho_completo):
        raiz_projeto = "/home/matheus/www/agent-fiap"
        caminho_completo = os.path.join(raiz_projeto, caminho_arquivo)
    
    # 3. Verifica uma última vez
    if not os.path.exists(caminho_completo):
        return f"Erro: Arquivo não encontrado nos caminhos: {caminho_arquivo} ou {caminho_completo}"

    try:
        if caminho_completo.endswith('.csv'):
            df = pd.read_csv(caminho_completo, nrows=2)
        elif caminho_completo.endswith('.parquet'):
            df = pd.read_parquet(caminho_completo).head(2)
        else:
            return "Formato não suportado. Use .csv ou .parquet."

        info = f"--- Esquema do arquivo localizado em: {caminho_completo} ---\n"
        info += "COLUNAS E TIPOS:\n"
        for col, dtype in df.dtypes.items():
            info += f"- {col}: {dtype}\n"
        
        info += "\nAMOSTRA DOS DADOS (2 linhas):\n"
        info += df.to_string(index=False)
        return info

    except Exception as e:
        return f"Erro ao ler os dados: {str(e)}"