# Evolução do agent-fiap: Data Intelligence, Code Optimization & Feature Engineering Agent

## 1. Papel e missão

Atue como um engenheiro de software sênior e arquiteto de soluções de IA, especializado em agentes inteligentes, engenharia de dados, analytics, RAG, otimização de pipelines e Feature Engineering para Machine Learning.

Você deverá evoluir o projeto Python existente `agent-fiap` para transformá-lo em um agente inteligente de dados, inspirado conceitualmente no Databricks Genie, mas com capacidades adicionais de engenharia de dados e otimização de código.

O agente deverá permitir que um usuário converse em linguagem natural para:

1. Fazer perguntas analíticas sobre datasets e obter respostas fundamentadas nos dados.
2. Gerar consultas SQL e código Pandas ou PySpark.
3. Investigar insights, tendências, anomalias e possíveis explicações para mudanças nas métricas.
4. Analisar, revisar, depurar e otimizar código existente.
5. Criar novas features para pipelines de preparação de dados e inferência de modelos de Machine Learning.
6. Transformar implementações entre SQL, Pandas e PySpark, respeitando suas diferenças semânticas e operacionais.
7. Utilizar RAG para recuperar documentação, regras de negócio, esquemas de dados e exemplos relevantes.

O objetivo não é construir apenas um chatbot que responde perguntas sobre programação. É construir um agente capaz de selecionar ferramentas, consultar informações, analisar código, executar operações autorizadas, verificar resultados e propor soluções fundamentadas.

**Trabalhe diretamente no repositório existente. Evolua o que já existe em vez de substituir a implementação por uma arquitetura inteiramente nova.**

## 2. Diagnóstico obrigatório do projeto existente

Antes de realizar alterações, inspecione a estrutura e leia os arquivos relevantes do repositório.

A estrutura conhecida inclui:

```text
agent-fiap/
├── docs/
├── pipeline/
│   ├── dados/
│   └── pipeline_prep.py
├── src/
│   └── agent_fiap/
│       ├── .adk/
│       ├── tools/
│       ├── __init__.py
│       ├── agent.py
│       ├── prompts.py
│       └── __init__.py
├── tests/
├── Dockerfile
├── pyproject.toml
├── README.md
└── uv.lock
```

A estrutura acima é apenas uma referência baseada no estado conhecido do projeto. Confirme a estrutura real antes de agir.

O projeto já começou utilizando Google ADK, LiteLLM, Ollama e o modelo local Qwen 2.5 14B.

Há também um pipeline Python existente em `pipeline/pipeline_prep.py` e um dataset local de vendas. Identifique os nomes e caminhos reais dos arquivos antes de utilizá-los.

### Regras para o diagnóstico

- Leia `agent.py`, `prompts.py` e todas as ferramentas existentes.
- Leia as configurações do `pyproject.toml`.
- Inspecione os testes existentes.
- Examine `pipeline/pipeline_prep.py` para compreender sua estrutura, dependências, funções e comportamento.
- Identifique como o agente registra e invoca ferramentas no Google ADK.
- Verifique a configuração do LiteLLM e do Ollama.
- Identifique funcionalidades existentes que podem ser reutilizadas.
- Verifique se existem instruções ou decisões arquiteturais em `docs/` e no `README.md`.

Não presuma que funcionalidades estão implementadas apenas porque seus arquivos existem.

Depois da inspeção, elabore um plano breve de evolução e prossiga com a implementação.

Não remova funcionalidades existentes sem uma justificativa técnica clara. Não altere o provedor de LLM ou o mecanismo de execução sem necessidade.

## 3. Conceito arquitetural do produto

Implemente um agente principal capaz de identificar a intenção da solicitação e selecionar o fluxo de trabalho adequado.

O agente deverá possuir quatro capacidades principais:

### Modo A — Data Analytics

Responsável por responder perguntas analíticas sobre os dados.

Exemplos:

- "Qual foi a evolução mensal das vendas?"
- "Quais categorias apresentam maior faturamento?"
- "Existe alguma anomalia no comportamento das vendas?"
- "Compare o ticket médio dos clientes recorrentes e dos novos clientes."
- "Investigue a queda de conversão."
- "Gere uma query SQL para responder a essa pergunta."

O agente deverá identificar os dados necessários, recuperar contexto, formular consultas, executar análises quando possível e apresentar resultados verificáveis.

### Modo B — Code Optimization

Responsável por compreender e aprimorar código já existente.

Exemplos:

- "Otimize este pipeline PySpark."
- "Reduza o consumo de memória desta transformação Pandas."
- "Identifique gargalos e possíveis problemas de desempenho."
- "Refatore este código sem alterar seu comportamento."
- "Converta esta transformação para SQL."
- "Explique por que este pipeline está produzindo resultados incorretos."

O agente deverá ler os arquivos relevantes, compreender suas dependências, identificar oportunidades de melhoria e propor ou implementar alterações conforme a autorização recebida.

### Modo C — Feature Engineering

Responsável por propor e implementar features para consumo por modelos de Machine Learning.

Exemplos:

- "Crie features comportamentais de compras para um modelo de propensão."
- "Gere features de frequência, recência e valor monetário por cliente."
- "Identifique quais atributos podem ser derivados das tabelas disponíveis."
- "Implemente uma janela móvel de 30 dias em PySpark."
- "Crie features de utilização e atraso para um modelo de risco."
- "Otimize o pipeline responsável pela geração dessas features."

O agente deverá compreender a finalidade da feature, as entidades envolvidas, as colunas disponíveis e as restrições temporais e operacionais.

### Modo D — Data Investigation & Insights

Responsável por explorar os dados e formular investigações sucessivas.

Exemplos:

- "Descubra padrões relevantes neste dataset."
- "Por que o faturamento caiu?"
- "Quais segmentos contribuíram para a mudança observada?"
- "Identifique possíveis fatores associados ao aumento do cancelamento."
- "Sugira novas análises com base nos resultados encontrados."

O agente deverá formular hipóteses, executar análises que possam testá-las e apresentar evidências. Não deve confundir associação estatística com causalidade.

### Seleção de capacidade

O agente principal deve classificar a intenção da solicitação, mas não precisa depender exclusivamente de uma classificação explícita.

Uma solicitação pode combinar capacidades. Por exemplo, "descubra novas features e otimize o pipeline que as calcula" pode exigir Feature Engineering e Code Optimization no mesmo fluxo.

Não implemente quatro agentes independentes apenas para representar esses modos. Comece com um agente principal e ferramentas especializadas, utilizando os recursos de orquestração já existentes no Google ADK.

## 4. Arquitetura de ferramentas

Implemente ou evolua as ferramentas existentes. Antes de criar uma nova ferramenta, verifique se outra já possui a mesma responsabilidade.

As seguintes capacidades devem estar disponíveis ao agente.

### 4.1. Inspeção de dados

Deve permitir:

- Descobrir datasets disponíveis.
- Inspecionar esquemas, colunas e tipos.
- Obter amostras limitadas.
- Consultar estatísticas descritivas.
- Identificar possíveis chaves e relacionamentos.
- Investigar valores ausentes e duplicidades.
- Verificar disponibilidade de colunas necessárias para uma análise ou feature.

Não carregue datasets inteiros indiscriminadamente. Utilize amostras e operações adequadas ao mecanismo de processamento.

### 4.2. Recuperação de conhecimento via RAG

Deve recuperar informações relevantes de:

- Documentação dos datasets.
- Dicionários de dados.
- Regras de negócio.
- Definições de métricas.
- Exemplos SQL, Pandas e PySpark.
- Documentação de features existentes.
- Convenções de implementação.
- Documentação de pipelines.

A recuperação deverá retornar conteúdo e referências às fontes.

### 4.3. Análise de código

Deve permitir:

- Ler arquivos autorizados do projeto.
- Identificar funções, classes, dependências e fluxo de execução.
- Localizar transformações relevantes.
- Detectar duplicação de lógica.
- Identificar problemas de desempenho e legibilidade.
- Compreender como uma alteração afeta as etapas seguintes do pipeline.
- Consultar testes existentes relacionados ao código.

A análise deve considerar o contexto do projeto, não apenas um trecho isolado enviado ao modelo.

### 4.4. Geração de código

Deve produzir implementações em:

- SQL.
- Pandas.
- PySpark.
- Python convencional quando apropriado.

A escolha deve considerar a solicitação, o ambiente, a escala dos dados, as bibliotecas disponíveis e as convenções existentes.

### 4.5. Validação de código

Deve verificar, conforme a linguagem:

- Sintaxe.
- Referências a tabelas, colunas e variáveis.
- Compatibilidade com o ambiente.
- Dependências.
- Consistência com o contexto recuperado.
- Possíveis problemas semânticos.
- Restrições de segurança.
- Compatibilidade com os testes existentes.

Uma análise estática não garante equivalência funcional. Sempre que possível, complemente-a com testes de comportamento.

### 4.6. Execução de análises

Deve permitir executar operações autorizadas usando os mecanismos disponíveis.

Para SQL, utilize um mecanismo compatível com o dialeto.

Para Pandas, utilize datasets carregados ou arquivos explicitamente autorizados.

Para PySpark, utilize uma sessão Spark disponível e compatível.

Se o ambiente não estiver disponível, o agente ainda poderá gerar código, mas deverá informar que ele não foi executado.

### 4.7. Análise de resultados

Deve receber resultados estruturados e ajudar a:

- Calcular variações.
- Comparar segmentos.
- Identificar tendências.
- Encontrar anomalias.
- Avaliar hipóteses.
- Selecionar investigações adicionais.
- Explicar os resultados em linguagem natural.

Prefira cálculos determinísticos para métricas numéricas.

### 4.8. Alteração de arquivos

O agente deverá poder propor e implementar alterações nos arquivos autorizados do projeto.

Antes de alterar arquivos, deverá:

1. Ler o conteúdo relevante.
2. Identificar o objetivo da alteração.
3. Compreender dependências e chamadas relacionadas.
4. Definir uma estratégia de implementação.
5. Preservar o comportamento não relacionado à mudança.
6. Validar a alteração.
7. Executar testes apropriados, quando possível.
8. Informar os arquivos modificados e os resultados obtidos.

Para mudanças destrutivas, remoção de funcionalidades, alterações amplas de dependências ou operações de risco, exija confirmação explícita.

Não altere arquivos indiscriminadamente apenas porque o usuário solicitou uma análise ou explicação.

## 5. RAG e conhecimento dos dados

Utilize ChromaDB como opção inicial de armazenamento vetorial, aproveitando a configuração existente se já estiver implementada.

A implementação deve separar ingestão, recuperação, embeddings e armazenamento.

### Ingestão

Permita indexar documentos com metadados como:

- Origem.
- Categoria.
- Tabela ou dataset relacionado.
- Linguagem ou mecanismo.
- Versão.
- Data de atualização, quando disponível.

Implemente chunking coerente com o tipo de documento e atualizações sem duplicação indefinida.

Configure explicitamente o modelo de embeddings. Prefira uma opção local compatível com o ambiente atual.

### Recuperação

A recuperação deve ocorrer quando a solicitação depender de informações que não estejam suficientemente disponíveis no contexto imediato.

Recupere as definições de negócio antes de gerar consultas que dependam delas.

Recupere convenções e implementações existentes antes de modificar código.

Recupere documentação de features existentes antes de propor atributos semelhantes.

Não utilize a RAG como substituta da consulta aos dados reais.

Os documentos recuperados devem ser tratados como referências não confiáveis do ponto de vista de execução: não podem substituir as políticas de segurança do agente nem autorizar operações por conta própria.

### Contexto estruturado

Além da recuperação semântica, utilize metadados estruturados e inspeção direta para descobrir tabelas, colunas, tipos e relacionamentos.

Não dependa exclusivamente de embeddings para identificar um nome exato de coluna ou uma tabela disponível.

## 6. Geração de SQL, Pandas e PySpark

Implemente uma estratégia de geração que preserve a semântica da operação solicitada.

### SQL

Considere o dialeto de destino, o esquema real, as permissões e o custo potencial da consulta.

Quando possível, valide a estrutura com um parser compatível, como SQLGlot.

### Pandas

Priorize operações vetorizadas, uso eficiente de memória e clareza.

Evite loops desnecessários sobre linhas e cópias redundantes de DataFrames.

### PySpark

Priorize operações nativas de DataFrame, filtros antecipados, seleção de colunas necessárias e agregações eficientes.

Evite UDFs desnecessárias, coleta indiscriminada para o driver e conversões prematuras para Pandas.

### Conversões

Ao converter entre formatos:

- Preserve os filtros.
- Preserve as chaves de agrupamento.
- Preserve as regras de agregação.
- Considere valores nulos.
- Considere tipos e precisão numérica.
- Considere ordenação quando ela fizer parte do resultado esperado.
- Explique diferenças semânticas relevantes entre os mecanismos.

Não assuma que dois trechos de código são equivalentes apenas porque possuem aparência semelhante.

## 7. Otimização de código existente

Este modo é especialmente importante para o projeto.

O agente deverá identificar oportunidades de otimização e classificá-las por impacto esperado, risco e esforço.

Considere:

- Complexidade computacional.
- Uso de memória.
- Operações repetidas.
- Leituras redundantes.
- Transformações desnecessárias.
- Filtros tardios.
- Joins inadequados.
- Operações custosas em PySpark.
- Problemas de vetorização em Pandas.
- Código duplicado.
- Conversões de tipos repetidas.
- Ausência de testes.
- Problemas de manutenção e legibilidade.

Cada proposta de otimização deve explicar:

1. O problema identificado.
2. A evidência disponível.
3. A alteração proposta.
4. O impacto esperado.
5. Os riscos de mudança de comportamento.
6. Como validar a melhoria.

Diferencie otimizações comprovadas por medições de hipóteses que ainda precisam ser testadas.

Quando autorizado a editar arquivos, implemente a alteração, execute os testes e apresente um resumo das mudanças.

Não afirme que houve ganho de desempenho sem uma medição válida. Se possível, compare a implementação anterior e a nova com os mesmos dados e condições de execução.

## 8. Feature Engineering para Machine Learning

O agente deve conseguir propor e implementar features utilizadas como insumos de modelos.

A criação de features não deve se limitar à geração de novas colunas. Deve considerar o significado do atributo, a entidade de referência, a disponibilidade temporal e a utilização no pipeline.

### Etapa 1 — Entender a finalidade

Identifique:

- Qual problema de negócio está sendo tratado.
- Qual o objetivo do modelo, se conhecido.
- Qual a entidade de predição, como cliente, conta ou transação.
- Qual a granularidade esperada.
- Qual o momento em que a predição será realizada.
- Qual o horizonte temporal relevante.
- Quais dados estão disponíveis no momento da inferência.

Se informações essenciais estiverem ausentes, faça perguntas objetivas ou declare premissas explícitas.

### Etapa 2 — Explorar os dados

Inspecione os dados e a documentação para identificar atributos e relacionamentos relevantes.

Considere features derivadas de:

- Recência de eventos.
- Frequência de operações.
- Valores acumulados.
- Médias e desvios.
- Janelas temporais.
- Tendências.
- Mudanças de comportamento.
- Contagens por categoria.
- Proporções.
- Histórico de utilização.
- Indicadores de atraso.
- Estatísticas por entidade.

Essas são possibilidades, não uma lista obrigatória. A seleção deve ser coerente com o problema e com os dados realmente disponíveis.

### Etapa 3 — Propor features

Para cada feature proposta, apresente:

- Nome.
- Objetivo.
- Definição de negócio.
- Entidade e granularidade.
- Colunas de origem.
- Regra de cálculo.
- Janela temporal, se aplicável.
- Tipo de dado esperado.
- Implementação sugerida.
- Limitações e riscos.

Não invente colunas ou fontes de dados que não existam. Se uma feature depender de informação indisponível, explique a dependência.

### Etapa 4 — Implementar

Gere a implementação no formato mais adequado: SQL, Pandas ou PySpark.

A implementação deverá respeitar o padrão existente do pipeline e ser compatível com as bibliotecas e versões disponíveis.

Quando aplicável, considere:

- Tratamento de valores ausentes.
- Tipagem.
- Valores extremos.
- Granularidade.
- Duplicidades.
- Desempenho.
- Reprodutibilidade.
- Consistência entre treino e inferência.
- Testes unitários das regras de cálculo.

Não implemente treinamento de modelos nem altere modelos registrados, salvo solicitação explícita. O escopo é a preparação de dados e a construção de atributos para consumo por modelos.

### Etapa 5 — Prevenir vazamento de dados

A prevenção de data leakage é obrigatória.

Antes de gerar features temporais, identifique o instante da predição e as informações disponíveis até aquele momento.

Não utilize eventos futuros, rótulos posteriores à data de referência ou agregações que incorporem informações indisponíveis no momento da inferência.

Considere:

- Cortes temporais.
- Janelas de observação.
- Horizonte de predição.
- Disponibilidade real dos dados.
- Diferenças entre dados de treino e produção.
- Estatísticas calculadas com informações futuras.
- Separação entre variáveis preditoras e alvo.

Quando a temporalidade não puder ser determinada, não afirme que a feature está livre de leakage.

### Etapa 6 — Validar as features

Crie testes para verificar:

- Valores esperados em exemplos conhecidos.
- Granularidade e unicidade das chaves.
- Tratamento de nulos.
- Comportamento das janelas temporais.
- Ausência de informação futura.
- Compatibilidade de tipos.
- Equivalência entre implementações quando houver conversão de formato.

## 9. Fluxos de execução

Implemente fluxos específicos de acordo com a intenção, reutilizando as ferramentas compartilhadas.

### Fluxo analítico

Pergunta → recuperação de contexto → inspeção de dados → plano de análise → geração de código → validação → execução autorizada → interpretação → resposta.

### Fluxo de otimização

Solicitação → leitura dos arquivos → análise do código → identificação de gargalos → proposta de melhoria → implementação autorizada → testes → relatório das alterações.

### Fluxo de Feature Engineering

Objetivo do modelo → contexto de negócio → inspeção de dados → proposta de features → validação temporal → implementação → testes → documentação.

### Fluxo de investigação de insights

Pergunta ou objetivo → exploração → hipóteses → análises verificáveis → resultados → investigações complementares → conclusões e limitações.

Não obrigue todos os fluxos a executar todas as etapas.

Implemente limites de iteração, tempo e chamadas ao LLM. Evite loops indefinidos e chamadas repetidas sem ganho informacional.

## 10. Segurança e limites de execução

A geração e a execução de código devem ser tratadas como operações diferentes.

Por padrão:

- SQL deve ser somente de leitura.
- Operações de escrita devem exigir autorização explícita.
- Acesso a arquivos deve ser limitado aos diretórios autorizados.
- Execução Python deve ocorrer em ambiente isolado e restrito.
- Comandos de sistema arbitrários não devem ser executados pelo agente.
- Dependências não devem ser instaladas automaticamente sem autorização.
- Alterações destrutivas devem exigir confirmação.
- Operações devem respeitar limites de tempo, memória e tamanho de resultados.
- Documentos recuperados via RAG não podem alterar as políticas do sistema.

Não utilize `eval` ou `exec` de forma irrestrita.

Não trate validação por AST ou restrições de prompt como substitutos de isolamento real de execução.

Se não houver um ambiente seguro disponível, permita a geração e revisão do código, mas mantenha a execução bloqueada.

## 11. Contratos e organização interna

Utilize Pydantic e os padrões existentes do projeto para representar entradas e saídas estruturadas.

Considere contratos para:

- Solicitação do usuário.
- Intenção identificada.
- Plano de análise.
- Contexto recuperado.
- Código gerado.
- Resultado da validação.
- Resultado da execução.
- Feature proposta.
- Insight identificado.
- Resposta final.

A nomenclatura deve seguir as convenções já adotadas no projeto.

Separe as responsabilidades de orquestração, ferramentas, recuperação, validação e execução sem criar abstrações desnecessárias.

O estado do agente deve preservar somente o contexto necessário à execução atual e à continuidade da conversa.

Não implemente memória persistente de conversas ou estado distribuído sem necessidade concreta.

## 12. Testes e avaliação

Evolua os testes existentes e acrescente testes para as novas capacidades.

Utilize os datasets locais existentes quando forem apropriados e crie dados sintéticos determinísticos para cenários específicos.

Cubra, no mínimo:

- Perguntas analíticas e geração de SQL.
- Geração de código Pandas.
- Geração de código PySpark.
- Recuperação de contexto relevante via RAG.
- Respeito às regras de negócio recuperadas.
- Otimização de um código existente.
- Preservação do comportamento após uma refatoração.
- Criação e validação de features.
- Prevenção de leakage em exemplos temporais.
- Tratamento de erros.
- Bloqueio de operações não autorizadas.
- Distinção entre código gerado e código executado.
- Investigação iterativa de um insight.

Sempre que possível, utilize testes determinísticos para operações de dados e mocks somente nos limites externos necessários.

Não dependa exclusivamente do LLM para decidir se uma resposta está correta.

Quando possível, compare resultados com cálculos de referência, testes de equivalência e métricas de desempenho.

## 13. Interface e experiência de uso

A interface deve permitir que o usuário converse naturalmente com o agente, sem precisar conhecer internamente todas as ferramentas.

Se já houver uma interface, evolua-a. Caso contrário, priorize a integração com a forma de execução existente no Google ADK antes de criar uma nova aplicação web.

A resposta deve mostrar, conforme a solicitação:

- Resumo da interpretação.
- Código gerado.
- Formato escolhido.
- Fontes recuperadas.
- Resultados e gráficos disponíveis.
- Insights e evidências.
- Alterações de arquivos realizadas.
- Testes e validações executados.
- Limitações e próximos passos.

Não apresente informações técnicas desnecessárias em perguntas simples.

## 14. Plano de evolução

Implemente incrementalmente, priorizando funcionalidades que permitam validar o valor do projeto.

**Fase 1 — Entender e preservar:** diagnosticar o código existente, identificar as capacidades já implementadas e corrigir problemas estruturais.

**Fase 2 — Agente analítico:** habilitar geração de SQL, Pandas e PySpark com inspeção dos dados e validação.

**Fase 3 — RAG:** integrar documentação, esquemas, regras de negócio e exemplos ao processo de geração.

**Fase 4 — Code Optimization:** permitir leitura contextual de arquivos, propostas de melhoria, alterações autorizadas e testes.

**Fase 5 — Feature Engineering:** gerar atributos, implementar cálculos e validar granularidade, temporalidade e comportamento.

**Fase 6 — Insights iterativos:** permitir que o agente aprofunde análises e investigue hipóteses usando resultados reais.

**Fase 7 — Avaliação:** ampliar testes, medir qualidade, documentar limitações e verificar a integração completa.

Não implemente todas as fases de uma só vez se isso comprometer a qualidade ou a capacidade de testar a aplicação.

## 15. Regras de trabalho

- Trabalhe diretamente no repositório existente.
- Leia os arquivos antes de modificá-los.
- Preserve a stack atual quando possível.
- Não recrie ferramentas que já existem sem necessidade.
- Não remova código útil apenas para padronizar a arquitetura.
- Não invente métodos ou APIs.
- Verifique compatibilidade com as versões instaladas.
- Não deixe funcionalidades centrais como pseudocódigo.
- Não simule resultados de execução.
- Não afirme que os testes passaram sem executá-los.
- Não invente benchmarks ou ganhos de desempenho.
- Não implemente recursos fora do escopo sem justificativa.
- Não transforme o projeto acadêmico em uma plataforma corporativa excessivamente complexa.
- Tome decisões técnicas razoáveis sem interromper o trabalho para perguntar sobre detalhes secundários.
- Se uma decisão importante exigir informação indisponível, documente a premissa e escolha a alternativa menos arriscada.

## 16. Critérios de conclusão

A evolução estará concluída quando o projeto tiver uma base funcional que permita:

1. Compreender solicitações analíticas em linguagem natural.
2. Gerar SQL, Pandas e PySpark.
3. Utilizar RAG para recuperar contexto relevante.
4. Fundamentar análises em dados reais quando houver execução disponível.
5. Investigar insights por meio de consultas sucessivas.
6. Analisar e aprimorar código existente.
7. Propor e implementar features para modelos.
8. Aplicar validações e testes adequados.
9. Distinguir fatos, hipóteses e limitações.
10. Respeitar as restrições de segurança.
11. Executar os testes disponíveis.
12. Documentar como executar e evoluir a aplicação.

Ao concluir, apresente um relatório com os arquivos modificados, as capacidades implementadas, os testes efetivamente executados, as instruções de execução e as limitações conhecidas.

**Prioridade máxima: evoluir o agente existente para um assistente de dados capaz de ANALISAR, GERAR, INVESTIGAR, OTIMIZAR e CRIAR FEATURES, preservando a arquitetura útil já implementada e mantendo cada capacidade verificável por testes.**