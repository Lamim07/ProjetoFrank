# Relatório de validação - quatro sprints

Data: 20/10/2026. Pasta validada: C:\MEUS PROJETOS\Projeto Teste\ProjetoFrank.

## Resultado técnico

- 101 testes de unidade/integração/AppTest passaram na pasta final.
- 12 cenários Playwright passaram na pasta final, em 67,143 segundos na execução consolidada.
- Python 3.14.7; Playwright 1.64.0; Chromium 156.0.8078.4.
- pip check: nenhuma incompatibilidade de dependências.
- git diff --check: sem erros; Git informou apenas conversão futura de LF para CRLF.
- Nove relatórios PDF do aplicativo e o roteiro PDF do pitch foram renderizados e revisados: 36 páginas ao todo.
- Nenhum commit ou push foi feito pelo agente. Alterações anteriores foram preservadas.

## Conformidade por sprint

| Sprint oficial | Entrega verificada | Situação |
|---|---|---|
| 1 - Testes de Caixa Preta | PCE, AVL, epsilon, critérios confirmados, classes e casos, JSON/PDF | Validada no escopo documentado |
| 2 - Testes de Caixa Branca | Grafo por função, nós/arestas, V(G)=1/4/3/3/3 no TXT oficial, DOT/PDF | Validada no subconjunto 4GL documentado |
| 3 - Fluxo de Dados e Mutantes | Def-Uso, 24 variantes no catálogo, 9 mutantes da função avaliados automaticamente no modelo restrito, NULL, trilhas e evidências | Validada no modelo e subconjunto documentados |
| 4 - Pitch e Validação | Roteiro de apresentação, pitch em PDF, matriz de aceite, suíte reproduzível e evidências | Artefatos preparados e validação técnica local concluída; apresentação oral/aceite humano pendentes |

A numeração acima substitui a classificação informal anterior. Setup e Gemini são recursos de apoio.
A validação não equivale a aceite acadêmico nem certificação de suporte completo a Informix-4GL.

## Cenários de navegador

| Cenário | Resultado | Duração |
|---|---|---|
| test_01_upload_errors_and_missing_key | Passou | 5.85 s |
| test_02_sprint1_black_box | Passou | 7.45 s |
| test_03_sprint2_white_box | Passou | 6.37 s |
| test_04_sprint3_data_flow | Passou | 4.61 s |
| test_05_sprint3_mutant_catalog | Passou | 4.23 s |
| test_06_sprint3_source_mutation | Passou | 5.17 s |
| test_07_arithmetic_experiment | Passou | 4.91 s |
| test_08_documentation_and_explanation_simulated | Passou | 7.29 s |
| test_09_requirements_review_and_rtm_simulated | Passou | 5.97 s |
| test_10_service_failure_simulated | Passou | 2.29 s |
| test_11_session_isolation_and_changed_file | Passou | 5.95 s |
| test_12_mobile_layout | Passou | 2.27 s |

A suíte cobre os sete modos da aplicação, uploads negativos, ausência de chave, exportações,
falha simulada de serviço, revisão RTM, troca de conteúdo, isolamento entre contextos e tela de 390 px.
Servidores de teste e Chromium são iniciados e encerrados pelo runner, usando somente localhost.

## Correções decorrentes da auditoria

1. Numeração e critérios das quatro sprints alinhados à definição expressa do responsável.
2. Nova avaliação de mutantes derivados da própria função de cálculo, preservando IF/ELSE e NULL.
3. Operadores IS NULL/IS NOT NULL incorporados; catálogo oficial agora tem 24 mutantes.
4. Resultados decimais longos do modelo passaram a ser comparados como valores, sem falso erro de entrada.
5. Entrada dos casos aritméticos padronizada em CSV após inconsistência observada no envio do editor durante E2E.
6. Harness de IA estabilizado entre reruns e troca de arquivo; uso exclusivo dos processos de teste.
7. Automação adaptada aos rótulos e seletor pesquisável do Streamlit, sem depender de índices visuais de função.

## IA real e simulação

Documentação, explicação e requisitos/RTM tiveram os fluxos de sucesso validados com respostas
Gemini simuladas, usando o mesmo código da aplicação em um harness separado e identificado na tela.
Ausência de chave foi testada no app.py real. As credenciais não aparecem nas evidências.

O teste real da API Gemini NÃO foi executado. A revisão automática rejeitou a transmissão dos
TXT por considerá-los potencialmente código privado. Foi solicitada autorização específica
para enviar somente cad0001_item_calculo.txt e biblioteca_requisitos.txt à API Gemini,
usando a chave já configurada e podendo consumir cota. Essa autorização permanece pendente.
O script opt-in testes/validar_gemini_real.py está preparado e não é acionado pela suíte padrão.

## Limites que permanecem

- O programa 4GL e seus comandos SQL não são executados pelo aplicativo.
- O escore automático da função refere-se a um modelo numérico restrito de LET, IF/ELSE e RETURN,
  com NULL e precisão Decimal de 64 dígitos. Não inclui SQL, chamadas externas, registros, arrays,
  laços ou arredondamento imposto pelo runtime/banco.
- Def-Uso é intraprocedural, e caminhos candidatos não provam viabilidade nem cobertura dinâmica.
- Mortos/sobreviventes de campanhas externas e equivalentes dependem das evidências do responsável.
- 100% sobre os nove mutantes da função e os casos didáticos não significa ausência de defeitos.
- A apresentação oral e o aceite do professor precisam ser realizados e registrados pelo responsável.

## Evidências e reprodução

- [Critérios das sprints](sprints_e_validacao.md)
- [Pitch em texto](pitch.md) e [roteiro em PDF](pitch_testingstudio.pdf)
- [Resultado bruto consolidado do Playwright](evidencias/resultado_playwright.json)
- [SHA-256 dos arquivos validados](evidencias/versao_validada_sha256.json)
- [Mutação da função no navegador](evidencias/mutacao_funcao.png)
- [Tela móvel](evidencias/tela_movel.png)

Downloads, capturas individuais e logs ficam localmente em evidencias/playwright, ignorados pelo Git.
Os comandos completos de instalação e execução estão no README e na matriz das sprints.
