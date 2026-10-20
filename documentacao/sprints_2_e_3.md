# Entrega das sprints 2 e 3

Escopo: Sprint 2 com PCE/AVL, ε e casos; Sprint 3 com grafo e V(G).
Exportação em PDF nos quatro tipos de resultado.

| Requisito | Componente | Verificação |
|---|---|---|
| Confirmar domínios sem inventar limites DECIMAL | `testes_funcionais.py`, formulário | Descoberta sem limites e confirmação obrigatória |
| Calcular ε e extremos representáveis | `NumericDomain` | 2 casas → 0,01; abertos, grade e intervalo vazio |
| Gerar PCE/AVL com rastreabilidade | `generate_suite` | Classes, fronteiras e casos com entrada, objetivo e esperado |
| Prever resultados de fórmula confirmada | `calculate_formula` | Decimal exato, rejeição de chamadas e divisão por zero |
| Gerar grafo por função 4GL | `fluxo_controle.py` | IF inline, ELSE, laço, retornos e código inalcançável |
| Calcular V(G) no grafo | `FunctionFlow` | Fixture oficial: 1, 4, 3, 3 e 3 |
| Recusar controle não suportado | `analyze_flow` | CASE e fechamentos ausentes não recebem métricas |
| Converter resultados em PDF | `exportacao_pdf.py` | Texto escapado, tabelas extensas e relatórios dos quatro modos |
| Limpar resultados ao trocar TXT | `app.py` | AppTest gera suíte/grafo/PDF e troca upload |

## Decisões de interface

A tela existente é a referência visual: fundo claro, texto azul escuro e ação verde.
O seletor recebeu duas opções. Formulários têm rótulos visíveis, confirmação e erros
próximos da ação, seguindo a referência `craft-details.md` do skill Refero Design.
O resultado identifica a última configuração gerada; editar campos exige gerar de novo.
O PDF acompanha esse resultado, não os rascunhos do formulário.

## Conferência manual

1. Enviar o TXT oficial e abrir PCE / AVL; selecionar `p_val1`, `p_val2`, `p_val3`.
2. Como cenário didático, informar 0 a 100 inclusive e 2 casas em cada entrada.
   Esses valores servem para conferir o motor; não são requisitos do TXT.
3. Informar `(p_val1 * p_val2) + p_val3`, confirmar e gerar.
4. Conferir ε = 0,01 e as fronteiras -0,01 / 0,00 / 0,01 e 99,99 / 100,00 / 100,01.
5. Baixar JSON e converter em PDF; conferir todas as classes e casos.
6. Abrir Fluxo de controle, gerar e escolher a função de cálculo; conferir V(G) = 4.
7. Converter em PDF; conferir funções, diagramas, nós e arestas.
8. Gerar documentação/explicação com Gemini e conferir seus PDFs.
9. Trocar o TXT; os resultados e PDFs anteriores devem desaparecer.

## Limites explícitos

O código e o SQL recebidos não são executados. A fórmula é um modelo aritmético;
os casos ainda precisam ser executados pelo responsável contra o sistema real.
O grafo modela o subconjunto 4GL descrito no README. A métrica é por função,
sem expansão de chamadas ou exceções implícitas. Não há mutação nem pares Def-Uso.
