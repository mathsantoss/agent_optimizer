## Kraken Planner — Planejador Híbrido

O `kraken_planner` é responsável por interpretar solicitações operacionais, elaborar planos estruturados e definir como os especialistas do Kraken Copilot devem trabalhar para alcançar o objetivo do usuário.

**O Planner não precisa ser necessariamente um agente LLM do Google ADK.** Sua implementação deve ser híbrida, combinando lógica determinística em Python com chamadas a LLM quando houver necessidade real.

### 1. Responsabilidades

O Planner deve:

- Interpretar o objetivo da solicitação.
- Identificar quais especialistas são necessários.
- Decompor solicitações complexas em etapas menores.
- Definir dependências entre as etapas.
- Identificar atividades que podem ser executadas em paralelo.
- Estabelecer critérios de sucesso.
- Criar e atualizar o `ExecutionPlan`.
- Apoiar o replanejamento quando necessário.

O Planner não executa as atividades dos especialistas. Essa responsabilidade pertence ao Coordinator e aos agentes especialistas.

### 2. Estratégia híbrida de planejamento

Priorize a abordagem mais simples e eficiente para cada solicitação.

**Planejamento determinístico (Python)**

Utilize regras e lógica Python quando:
- A intenção da solicitação for clara.
- O fluxo de execução for conhecido.
- A seleção dos especialistas puder ser feita por regras confiáveis.
- A decomposição puder ser realizada sem interpretação semântica complexa.

**Planejamento com LLM**

Utilize uma chamada ao LLM quando:
- A solicitação apresentar ambiguidade relevante.
- For necessário interpretar objetivos complexos.
- Houver necessidade de decompor uma solicitação em atividades não previstas nas regras existentes.
- For necessário identificar dependências entre tarefas com base no contexto.
- A lógica determinística não conseguir produzir um plano confiável.

**Abordagem híbrida**

Quando necessário, combine as duas estratégias:
1. Faça uma classificação inicial da solicitação utilizando Python.
2. Identifique se o planejamento determinístico é suficiente.
3. Caso necessário, utilize o LLM para interpretar e decompor a solicitação.
4. Converta o resultado em um `ExecutionPlan` estruturado.
5. Valide o plano antes de encaminhá-lo ao Coordinator.

Não utilize o LLM em todas as solicitações por padrão. Evite chamadas redundantes, especialmente quando uma regra determinística já resolve adequadamente o problema.

### 3. Contrato de planejamento

Preserve a integração com os modelos existentes:

- `ExecutionPlan`
- `PlanStep`
- `StepStatus`
- `StepAttempt`

O resultado do planejamento deve seguir o mesmo contrato, independentemente de ter sido produzido por regras Python ou por LLM.

Valide:
- Existência de especialistas permitidos.
- Identificadores únicos das etapas.
- Integridade das dependências.
- Ausência de dependências circulares.
- Critérios de sucesso definidos.
- Consistência dos grupos de execução paralela.

Utilize os modelos Pydantic existentes sempre que possível, evitando criar estruturas duplicadas.

### 4. Integração com o Coordinator

O Planner deve entregar um plano válido ao `kraken_coordinator`.

O Coordinator continua responsável por:
- Executar as etapas.
- Encaminhar tarefas aos especialistas.
- Controlar dependências.
- Coordenar paralelismo.
- Gerenciar validações e tentativas.
- Solicitar replanejamento quando necessário.

O Planner pode ser acionado novamente para atualizar o plano, mas não deve assumir responsabilidades de execução do Coordinator.

### 5. Implementação arquitetural

Avalie a melhor implementação para o projeto atual.

O Planner pode ser:
- Um componente Python interno.
- Um serviço interno de planejamento que utiliza LLM sob demanda.
- Um Agent do ADK, caso exista uma justificativa técnica concreta para isso.

Não imponha que ele seja um `Agent`, `SequentialAgent` ou qualquer outro componente específico do Google ADK.

Priorize uma implementação coesa, simples, tipada, testável e fácil de entender.

Evite criar múltiplas classes, factories, agentes ou abstrações para separar operações que podem permanecer juntas de maneira organizada.

### 6. Replanejamento

Quando uma etapa falhar ou o contexto da execução mudar, avalie se o plano precisa ser atualizado.

O replanejamento deve:
- Preservar etapas concluídas que continuem válidas.
- Reavaliar dependências das etapas restantes.
- Evitar repetir atividades desnecessariamente.
- Registrar o motivo da revisão.
- Incrementar a revisão do plano.
- Manter a consistência do estado compartilhado.

Utilize LLM somente quando a situação exigir uma nova interpretação ou decomposição semântica.

### 7. Critério de qualidade

A implementação deve equilibrar inteligência, simplicidade e confiabilidade.

Não crie um framework genérico de planejamento. O Planner existe para atender às necessidades específicas do Kraken Copilot:

- Análise de dados.
- Geração de código para engenharia de features e Feature Store.
- Otimização de código e pipelines.

A arquitetura deve ser proporcional a essas responsabilidades.


## 8. Qualidade de código, simplicidade e legibilidade

Este requisito é fundamental para toda a implementação do Kraken Planner.

A solução deve ser tecnicamente sólida, mas simples de entender, utilizar, testar e manter.

O objetivo não é construir um framework genérico de planejamento de agentes, mas implementar um componente que atenda adequadamente às necessidades reais do Kraken Copilot.

### Princípios obrigatórios

1. **Legibilidade acima de sofisticação:** prefira código explícito, direto e fácil de acompanhar.
2. **Simplicidade:** implemente somente o necessário para atender aos requisitos.
3. **Responsabilidade clara:** cada função, classe ou módulo deve ter uma finalidade bem definida.
4. **Reutilização:** aproveite estruturas, modelos e funções que já existem no projeto.
5. **Baixo acoplamento:** evite dependências desnecessárias entre Planner, Coordinator e especialistas.
6. **Tipagem:** utilize type hints e os modelos Pydantic existentes quando fizer sentido.
7. **Manutenibilidade:** facilite futuras alterações sem exigir modificações em várias partes independentes do código.

### Evite complexidade desnecessária

Não crie estruturas como:
- Factories para instanciar componentes simples.
- Interfaces ou classes abstratas sem necessidade concreta.
- Múltiplas classes para separar operações pequenas e relacionadas.
- Managers, handlers, registries ou services que apenas repassem chamadas.
- Estratégias intercambiáveis quando existe apenas uma implementação necessária.
- Camadas adicionais de configuração e abstração.
- Novos agentes para responsabilidades que podem ser resolvidas pelo próprio Planner.
- Sistemas genéricos de regras ou roteamento sem necessidade real.

Esses recursos não são proibidos. Devem ser utilizados somente quando houver um benefício técnico claro e proporcional à complexidade introduzida.

### Organização do código

Prefira uma estrutura pequena e coerente.

Por exemplo, se for suficiente, o Planner pode ter:
- Uma classe `KrakenPlanner`.
- Métodos para decidir a estratégia de planejamento.
- Métodos para construir e validar o `ExecutionPlan`.
- Uma integração com LLM utilizada somente quando necessário.

Não considere essa estrutura obrigatória. Analise o projeto existente e escolha a organização mais simples que preserve a separação adequada de responsabilidades.

Evite funções excessivamente longas, mas também não divida operações simples em dezenas de funções pequenas sem necessidade.

### Decisões de implementação

Antes de adicionar qualquer classe, função, módulo, dependência ou abstração, avalie:

- Isso resolve um problema real?
- Essa responsabilidade já existe em outro componente?
- É possível resolver com o código existente?
- A abstração facilita efetivamente a compreensão e a manutenção?
- O benefício justifica a complexidade adicionada?

Se não houver uma justificativa clara, não implemente.

### Regra para refatoração

Não faça alterações apenas para deixar o código diferente ou mais sofisticado.

Preserve implementações existentes que estejam corretas e sejam úteis. Remova ou substitua componentes quando isso representar uma melhoria arquitetural real, sem perder funcionalidades importantes.

**Critério final: um desenvolvedor deve conseguir entender como o Planner decide entre planejamento determinístico e LLM, como constrói o plano e como o entrega ao Coordinator sem precisar navegar por várias camadas de abstração.**

Prefira sempre a implementação mais simples, legível e confiável que resolva o problema.

**Diretriz principal: o Planner deve saber quando não precisa de um LLM e quando a inteligência de um LLM realmente agrega valor. A escolha da estratégia de planejamento deve ser interna, transparente e independente do contrato `ExecutionPlan`.**