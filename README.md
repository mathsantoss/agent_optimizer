# 🤖 Agent FIAP

Agente de IA local desenvolvido com **Google ADK**, **LiteLLM**, **Ollama** e **Qwen 2.5 14B**.

O projeto utiliza o Google ADK para criar e executar o agente, enquanto o Ollama executa o modelo localmente.

## 🛠️ Tecnologias

- Python 3.13+
- Google ADK
- LiteLLM
- Ollama
- Qwen 2.5 14B
- UV
- Conda

## 📋 Pré-requisitos

Antes de executar o projeto, tenha instalado:

- Git
- Conda
- Ollama

O projeto foi desenvolvido utilizando WSL2.

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd agent-fiap
```

### 2. Crie o ambiente Python

```bash
conda create -n fiap python=3.13
conda activate fiap
```

### 3. Instale as dependências

Instale o UV:

```bash
pip install uv
```

Depois execute:

```bash
uv sync
```

Isso instalará as dependências definidas no `pyproject.toml`.

### 4. Configure o Ollama

Instale o Ollama:

https://ollama.com/

Baixe o modelo utilizado pelo projeto:

```bash
ollama pull qwen2.5:14b
```

Verifique se o modelo está disponível:

```bash
ollama list
```

Você deverá encontrar:

```text
qwen2.5:14b
```

## ▶️ Executando o agente

Entre no diretório do agente:

```bash
cd agent_optimizer
```

Execute:

```bash
adk web
```

O ADK Web estará disponível em:

```text
http://localhost:8000
```

Abra o endereço no navegador e selecione o agente:

```text
agent_optimizer
```

## 🧪 Testando

Após abrir o ADK Web, envie uma mensagem para o agente, por exemplo:

```text
Olá
```

Para testar a Tool disponível no projeto:

```text
Que horas são?
```

O agente poderá utilizar a função `pegar_horas()` para consultar a hora atual.

## 📁 Estrutura

```text
agent-fiap/
│
├── agent_optimizer/
│   ├── __init__.py
│   └── agent.py
│
├── .gitignore
├── README.md
├── pyproject.toml
└── uv.lock
```

## 🔧 Configuração

O agente utiliza o Ollama em:

```text
http://localhost:11434
```

E o modelo:

```text
qwen2.5:14b
```

Caso o agente não responda, verifique se o Ollama está funcionando:

```bash
curl http://localhost:11434/api/tags
```
