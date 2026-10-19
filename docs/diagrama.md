::: mermaid
flowchart TD
    A["Usuário / Engenheiro de ML"] --> B["Código do Pipeline"]
    B --> C["Agente Otimizador de IA"]

    subgraph AGENT["Camada de Agente — Google ADK"]
        C --> D["Instruções e Contexto"]
        D --> E["LLM — Qwen via Ollama"]
        E --> F{"Precisa executar uma ação?"}
        F -->|Sim| G["Seleção e chamada de ferramentas"]
        F -->|Não| H["Resposta / Diagnóstico"]
        G --> I["Orquestração do fluxo"]
        I --> E
    end

    subgraph TOOLS["Camada de Ferramentas"]
        J["Leitura e análise de arquivos"]
        K["Edição de código"]
        L["Execução de testes"]
        M["Comparação de resultados"]
    end

    G --> J
    G --> K
    G --> L
    G --> M

    J --> I
    K --> I
    L --> I
    M --> I

    H --> N["Relatório de otimização"]
    I --> N
    N --> O["Código otimizado + evidências de validação"]

    classDef agent fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef tools fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef output fill:#fef3c7,stroke:#d97706,color:#78350f
    class C,D,E,F,G,I agent
    class J,K,L,M tools
    class N,O output
:::