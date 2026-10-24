# 🤖 Agent FIAP

Assistente Inteligente e Unificado de Ciência de Dados, Analytics e Engenharia de Pipelines inspirado conceitualmente no **Databricks Genie Code**. Desenvolvido com **Google ADK**, **LiteLLM**, **Ollama** e **Qwen 2.5 14B**.

O **`agent_fiap`** é um agente autônomo e genérico capaz de raciocinar sobre qualquer conjunto de dados (.csv e .parquet) colocado em `pipeline/dados/`, responder perguntas analíticas em linguagem natural, executar consultas SQL, recuperar regras de negócio via RAG, e criar, refatorar, salvar e validar fisicamente pipelines em `pipeline/pipeline_prep.py`.

---

## 🛠️ Tecnologias

- Python 3.13+
- Google ADK (Agent Development Kit)
- LiteLLM
- Ollama (`qwen2.5:14b`)
- ChromaDB (RAG para documentação e regras de negócio em `docs/`)
- Pandas & PyArrow (Exploração agnóstica de CSV e Parquet)
- Scikit-Learn (Pipelines de Feature Engineering e Modelos)
- SQLite em memória (Execução analítica SQL somente leitura com suporte a `GREATEST`, `LEAST`, `CONCAT`, `YEAR`, `MONTH`)
- Pytest (Validação e testes automatizados)

---

## 📋 Pré-requisitos

- Git
- Conda (ambiente `fiap` com Python 3.13)
- Ollama instalado com o modelo `qwen2.5:14b`

---

## 🚀 Como Executar

### 1. Inicie o Ollama
Certifique-se de que o Ollama está rodando e com o modelo disponível:
```bash
ollama serve
ollama list  # deve listar qwen2.5:14b
```

### 2. Ative o ambiente e instale dependências
```bash
conda activate fiap
uv sync --active
```

### 3. Inicie a interface Web do Google ADK
Navegue até a pasta `src` e execute o ADK Web:
```bash
cd src
adk web
```

Acesse no navegador:
```text
http://localhost:8000
```
Selecione o agente: **`agent_fiap`**.

---

## 🧰 Ferramentas Disponíveis ao Agente

O agente possui 9 ferramentas nativas e coordenadas:

### Análise e Exploração de Dados (Genie Analytics)
- **`listar_datasets`**: Descobre dinamicamente os datasets disponíveis em `pipeline/dados/`, tabelas SQL e tamanhos.
- **`explorar_dataset`**: Obtém contagem de linhas, colunas, tipos, nulos, valores únicos, período de datas e amostra real.
- **`resumo_estatistico`**: Gera resumo descritivo (médias, desvios, mínimos, percentis e máximos).
- **`consultar_sql`**: Executa queries SQL (apenas `SELECT`) sobre os datasets carregados em memória via SQLite.
- **`buscar_conhecimento`**: Busca semântica (RAG) em documentos e regras de negócio na pasta `docs/`.

### Engenharia de Código e Pipelines (Genie Code)
- **`ler_arquivo`**: Lê scripts, pipelines e documentação dentro do projeto (informa se o arquivo estiver vazio).
- **`salvar_arquivo`**: Salva ou atualiza código no projeto (padrão: `pipeline/pipeline_prep.py`) com validação de sintaxe Python e backup automático `.bak`.
- **`executar_pipeline`**: Executa o script do pipeline via Python em subprocesso e retorna a saída ou eventuais erros de execução.
- **`executar_testes`**: Roda a suíte de testes automatizados com `pytest`.

---

## 🧪 Testes Automatizados

Para executar os testes automatizados:
```bash
conda run -n fiap python -m pytest tests -v
```
