# Etapas do TestingStudio - entrega de 20/10/2026

Atualização: a divisão oficial confirmada pelo usuário é Sprint 1 Caixa Preta,
Sprint 2 Caixa Branca, Sprint 3 Fluxo de Dados e Mutantes e Sprint 4 Pitch e Validação.
Veja [sprints_e_validacao.md](sprints_e_validacao.md) para os critérios atuais.
A seção histórica abaixo descreve a numeração informal anterior.

## Conferência do planejamento

O kickoff define três módulos, sem numerar sprints posteriores à Sprint 1.
As entregas chamadas Sprint 2 e Sprint 3 neste repositório correspondem a PCE/AVL
e fluxo de controle/V(G), conforme o escopo já aprovado pelo usuário.

| Etapa funcional | Situação | Componentes |
|---|---|---|
| Base, upload, Gemini, documentação e explicação | Implementada | app.py, analyzer.py, gemini_client.py |
| Módulo 1: PCE, AVL, epsilon e casos | Implementada | testes_funcionais.py |
| Módulo 2: grafo e complexidade ciclomática | Implementada | fluxo_controle.py |
| Complemento da aula: requisitos, casos de uso e RTM | Implementado | requisitos.py, interface_requisitos.py |
| Módulo 3: pares Def-Uso | Implementado no subconjunto documentado | def_uso.py |
| Módulo 3: mutação e escore | Implementado com os limites abaixo | mutacao.py |
| PDF dos resultados | Implementado | exportacao_pdf.py e interfaces |

Antes desta entrega, faltavam duas funcionalidades do módulo avançado. Ambas agora
estão disponíveis. Isso encerra esse recorte funcional, sem presumir suporte completo
à linguagem Informix-4GL ou execução automática do programa recebido.

## Critérios e verificação

| Requisito | Comportamento verificado |
|---|---|
| Definições alcançantes | Sequência, kill na redefinição, união de ramos e ponto fixo em WHILE |
| Definições e usos na mesma instrução | RHS lido antes da definição; iterações podem vincular o nó a si próprio |
| c-use e p-use | Uso no nó ou associado às duas arestas do predicado |
| Origem e evidências | Linha original, ID do nó, variável e caminho candidato |
| Alertas | Possível uso sem definição local, definição sem uso e função não suportada |
| Mutação de primeira ordem | Uma alteração por variante, com original preservado |
| Revisão de mutantes | IDs preservados; evidência exigida para classificação; pendente por padrão |
| Escore | Mortos/(mortos+sobreviventes); equivalentes/ inválidos justificados excluídos |
| Campanha incompleta | Escore final indisponível com pendências/erros; sem denominador não há percentual |
| Experimento aritmético | Resultados esperados independentes, base aprovada e tabela de detecção por teste |
| Exportação e sessão | PDFs e JSON dos resultados, variante TXT, troca de conteúdo limpa resultados |

Def-Uso usa a transferência OUT = GEN união (IN menos KILL), com união dos predecessores,
até estabilização. Fatos sintéticos de ausência de definição permitem identificar caminhos
que chegam a um uso sem inicialização. Não há prova de viabilidade das condições.
Os caminhos não devem ser tratados como testes executados ou cobertura dinâmica.

O catálogo de mutantes só altera expressões selecionadas. Compilação, efeitos externos,
equivalência e execução real devem ser verificados no ambiente da linguagem antes de
registrar evidências. A aplicação não executa programas nem SQL e não conecta ao banco.
O experimento automático usa apenas a árvore aritmética restrita já adotada na PCE/AVL.

## Roteiro manual

1. Iniciar o aplicativo e enviar o TXT oficial.
2. Escolher Pares Def-Uso e analisar. Conferir a função cad0001_calcula_valor e 13 pares.
   As outras funções devem indicar construções sem modelo de efeitos.
3. Conferir definições dos parâmetros, três condições NULL, a atribuição do cálculo e RETURN.
4. Baixar JSON e PDF, conferindo todas as linhas da tabela.
5. Escolher Mutação, gerar catálogo e conferir a troca de um operador por variante.
6. Baixar uma variante: original e comentário devem permanecer, exceto pela substituição indicada.
7. Aplicar resultados sem classificação: nenhum escore final disponível.
8. Informar classificação sem evidência: a revisão deve ser recusada e a anterior preservada.
9. Após executar/verificar externamente, informar situação e evidência de cada mutante; aplicar.
10. Na aba Experimento aritmético, usar `(a*b)+c`, com a=2, b=3, c=4 e esperado=10.
    Confirmar: seis variantes aritméticas, todas detectadas por esse caso, MS do modelo=100%.
11. Trocar esperado para 11 e avaliar: a base deve falhar e nenhum novo escore ser publicado.
12. Exportar PDF/JSON, depois trocar TXT: resultados e PDFs anteriores devem desaparecer.

## Referência visual e decisões

Alvo: interface já existente do TestingStudio (captura das sprints 2/3) e tema .streamlit.
Preservar fundo claro, títulos azul escuro, ação primária verde, largura de leitura e tabelas
expansíveis. Referência de apoio: craft-details.md do skill Refero Design (rótulos visíveis,
formulários, erros próximos à ação e estados claros).

| Decisão | Referência / motivo |
|---|---|
| Duas novas opções no seletor existente | Produto atual: um resultado próprio por modo |
| Mutantes e experimento em abas | Separar evidência externa de execução do modelo confirmado |
| Tabelas para eventos, pares e resultados | Produto atual e craft de formulários; revisão legível |
| Escore final separado do parcial | Não confundir campanha incompleta com análise concluída |
| Sem nova identidade visual | Extensão dos padrões do aplicativo já utilizado |

## Limites operacionais

- Def-Uso: até 100 funções, 200 nós, 80 variáveis e 5.000 pares por função.
- Sem efeitos de chamadas, SQL, arrays, registros, aliases ou atualização implícita de FOR.
- Mutantes: até 300; truncamento explicitamente identificado. Geração não implica compilação.
- Fórmula: até 300 caracteres, 12 entradas, 100 casos, Decimal com precisão de 64 dígitos.
- Sem NULL, tolerância ou arredondamento implícitos no experimento aritmético.
- A classificação externa e a equivalência são justificativas do usuário, não provas produzidas pelo sistema.
- Testes locais não consomem Gemini. Deploy/hospedagem e novas aulas não têm etapas definidas neste recorte.

## Validação da entrega

Em 20/10/2026, 89 testes automatizados passaram na área de desenvolvimento e novamente
na pasta principal. git diff --check não apontou erros de whitespace.
A conferência visual no navegador usou o TXT oficial: 13 pares Def-Uso na função de
cálculo e 21 mutantes no catálogo. As telas mantiveram o tema existente.
Os três relatórios novos (Def-Uso, campanha e experimento aritmético) foram gerados,
renderizados e conferidos quanto a tabelas, paginação e acentos.
A avaliação automática de fórmulas foi validada pelos testes de interface e de motor;
não houve execução do programa 4GL nem chamadas reais ao Gemini nesta entrega.
Alterações aplicadas localmente; commit e push ainda não realizados pelo agente.
