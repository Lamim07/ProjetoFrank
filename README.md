# TestingStudio Web

Aplicação Streamlit para documentar e explicar arquivos TXT, preparar testes funcionais
e visualizar fluxo de controle, pares Def-Uso e mutantes de funções Informix-4GL.
O código recebido não é executado.

## Executar no Windows

```powershell
cd 'C:\MEUS PROJETOS\Projeto Teste\ProjetoFrank'
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Use Python 3.11 ou superior. Se o ambiente não existir, crie-o com `python -m venv .venv`.
Reinicie o Streamlit após atualizar o projeto.

Documentação, explicação e derivação de requisitos usam `GEMINI_API_KEY` no ambiente. O modelo padrão é
`gemini-3.8-flash`, configurável por `GEMINI_MODEL`. `.env.example` documenta os nomes;
arquivos `.env` não são carregados automaticamente. A chave não deve entrar no Git.

## Como usar

A divisão oficial informada pelo responsável é:

| Sprint | Conteúdo | Evidência principal |
|---|---|---|
| 1 | Testes de Caixa Preta | PCE, AVL, epsilon, domínios e casos |
| 2 | Testes de Caixa Branca | Grafo e complexidade ciclomática |
| 3 | Fluxo de Dados e Mutantes | Def-Uso, variantes e avaliação de mutação |
| 4 | Pitch e Validação | Roteiro do pitch, matriz de aceite, testes e evidências |

Veja [os critérios por sprint](documentacao/sprints_e_validacao.md) e
[o roteiro do pitch](documentacao/pitch.md). Setup, integração Gemini, explicação,
documentação, requisitos/RTM e PDF são recursos de apoio.

Envie um TXT em UTF-8 com até 1 MB e escolha uma das sete opções:

- **Documentação:** resumo, estruturas, funções, regras e operações com evidências;
  permite baixar Markdown.
- **Explicar o código:** fluxo em etapas, entradas e saídas, cálculos, dados e lacunas.
- **PCE / AVL:** selecione entradas numéricas e confirme limites, casas decimais,
  inclusão das fronteiras e tratamento de NULL. A suíte contém classes, valores limite
  e casos de teste, com exportação JSON.
- **Fluxo de controle:** gera grafo e complexidade ciclomática por função. Permite
  selecionar a função, consultar nós/arestas completos e baixar DOT.
- **Requisitos e RTM:** propõe requisitos, casos de uso e casos de teste, permite
  revisá-los em tabelas e mostra a rastreabilidade nos dois sentidos. Exporta JSON,
  matriz CSV e relatório PDF.
- **Pares Def-Uso:** identifica definições alcançantes, usos em cálculos e condições,
  caminhos candidatos e possíveis usos sem inicialização. Exporta JSON e PDF.
- **Mutação:** gera variantes do TXT, registra evidências externas e calcula o escore.
  Também avalia automaticamente mutações de uma fórmula aritmética confirmada.

Depois de gerar qualquer resultado, clique em **Transformar em PDF** e **Baixar PDF**.
O PDF contém o resultado completo. O relatório estrutural inclui todas as funções,
diagramas e as limitações encontradas. Grafos grandes são representados integralmente
pelas tabelas de nós e arestas. Os PDFs ficam apenas na sessão. Trocar o conteúdo do
TXT apaga resultados e PDFs anteriores.

## Sprint 1 - Testes de Caixa Preta

O motor local usa `Decimal`: ε = 10^(-casas decimais), ou 1 para inteiros.
Limites abertos e limites fora da grade são convertidos no primeiro e no último valor
representável. AVL usa esses extremos e seus vizinhos de uma unidade de ε.
Intervalos sem valores representáveis são recusados.

`DECIMAL(p,s)` sugere nomes e casas decimais; não fornece limites de negócio.
O usuário confirma os critérios. São geradas classes para intervalo válido, abaixo,
acima, precisão inadequada, tipo não numérico e NULL. Se NULL for convertido em zero,
zero também precisa pertencer ao intervalo. A suíte varia uma entrada por vez; não
mede cobertura de combinações nem comprova que o programa implementa os critérios.

A fórmula opcional aceita números, nomes, `+`, `-`, `*`, `/` e parênteses. É interpretada
por uma árvore aritmética restrita, sem `eval`, chamadas ou acesso a arquivos. Os
resultados são previsões do modelo confirmado; não são execuções do TXT. Divisão por
zero e NULL sem conversão são marcados como comportamento a definir. Não há
arredondamento implícito da saída, pois isso depende de requisito.

Limites do motor: 12 entradas por suíte, 12 casas decimais e menos de 30 dígitos inteiros.

## Sprint 2 - Testes de Caixa Branca

Suporte ao subconjunto estruturado do TXT oficial: `FUNCTION`, `END FUNCTION`,
`IF ... THEN`, `ELSE`, `END IF`, `WHILE`, `FOR`, seus fechamentos e `RETURN`.
O cabeçalho de função e `IF ... THEN` devem caber em uma linha. IF inline, aninhamento
e retornos antecipados são suportados. Textos e comentários `#` não criam decisões.
Blocos sequenciais são agrupados e trechos inalcançáveis são removidos da métrica.

Cada função tem entrada e saída normalizadas e P = 1 componente conectado.
V(G) = E - N + 2P. Cada IF ou laço é uma decisão; AND/OR não são decompostos em
curto-circuito. Chamadas e SQL são blocos; exceções implícitas não são modeladas.
Limites: 100 funções e 200 blocos por função.

CASE, FOREACH, GOTO, EXIT/CONTINUE e tratamento de exceções não recebem métricas
aproximadas: a função é listada com a limitação. Outras linguagens podem usar as opções
por IA e os domínios manuais de PCE/AVL. Pares Def-Uso e mutação estão disponíveis no
módulo avançado descrito abaixo.

No TXT oficial: `cad0001_main = 1`, `cad0001_calcula_valor = 4`, `cad0001_incluir = 3`,
`cad0001_alterar = 3` e `cad0001_excluir = 3`.

## Complemento da aula de 14/10/2026 — Requisitos e RTM

Envie um TXT de especificação ou descrição de casos de uso, escolha **Requisitos e RTM**
e clique em **Derivar requisitos e casos de teste**. A proposta preserva os IDs presentes
no texto e identifica fluxos principal, alternativo e de exceção quando sustentados pela
fonte. Casos incluem pré-condições, passos, resultado esperado, vínculos e pendências.
Cada requisito tem uma evidência literal validada contra o TXT.

Na revisão, é possível adicionar/remover linhas e ajustar textos ou vínculos. Separe IDs
por vírgula e passos por ` | `. Clique em **Aplicar revisão e atualizar RTM** para salvar.
IDs duplicados, referências inexistentes e evidências fora do TXT são recusados.
Os downloads usam a última revisão aplicada; rascunhos ainda no formulário não entram no PDF.

A RTM tem duas vistas: requisitos → testes e testes → requisitos. Um teste pode verificar
vários requisitos. Os vínculos precisam ser explícitos: ligar um caso ao caso de uso não
faz com que ele cubra automaticamente todos os requisitos daquele fluxo. São sinalizados
requisitos sem teste, testes sem requisito e casos com pendências. O percentual mede
requisitos com teste vinculado; não significa que o sistema foi testado ou aprovado.
Todos os casos permanecem **Não executado**, mesmo após o registro de revisão.

Se a entrada for código, o comportamento é marcado como **Observado no código** e deve
ser confrontado com uma especificação. A IA propõe a derivação, e a revisão humana ainda
precisa confirmar a correção semântica dos requisitos, cenários e resultados esperados.
Limites de resposta: 60 requisitos, 40 casos de uso e 200 casos de teste.

O exemplo didático `testes/arquivos_de_exemplo/biblioteca_requisitos.txt` acompanha o
material da aula. ISBN, busca, dívida, multa de R$ 2,00/dia e comprovante por e-mail
são requisitos do cenário de biblioteca; não são funcionalidades de negócio do TestingStudio.
Veja [o mapeamento da aula](documentacao/aula_14_10_2026.md).

## Sprint 3 - Fluxo de Dados e Mutantes

**Def-Uso:** selecione a opção e clique em **Analisar definições e usos**. O motor calcula
definições alcançantes por ponto fixo no grafo por instrução, preserva linhas e distingue
`c-use` (cálculo/saída) de `p-use` (condição, em cada aresta). Redefinições interrompem
o vínculo anterior. Parâmetros são definições de entrada; usos sem definição local e
definições sem uso recebem alertas. Os caminhos são candidatos estruturais: sua viabilidade
lógica e a cobertura por testes não são comprovadas.

Subconjunto: parâmetros escalares, declarações simples numéricas/CHAR/DATE, LET,
IF/ELSE, WHILE, RETURN, DISPLAY e MESSAGE. Chamadas, SQL, arrays, registros, aliases,
FOR e instruções sem modelo de efeitos impedem a análise da função, com motivo explícito.
Limites: 100 funções, 200 nós, 80 variáveis e 5.000 pares por função. No TXT oficial,
a função de cálculo produz 13 pares; as outras quatro funções têm efeitos não modelados.

**Mutantes do TXT:** gere um catálogo de até 300 variantes de primeira ordem (100 por
padrão). Operadores aritméticos, relacionais, AND/OR e TRUE/FALSE são substituídos em
expressões de LET, IF, WHILE e RETURN. Strings, comentários, declarações e comandos SQL
não são alterados. Chamadas/índices não são mutados. A variante inteira pode ser baixada
sem alterar o original. Geração não garante compilação ou diferença de comportamento.

Registre **Morto**, **Sobrevivente**, **Equivalente**, **Inválido** ou **Erro de execução**
com teste/resultado ou justificativa. O aplicativo não verifica execuções externas.
MS = mortos / (mortos + sobreviventes). Equivalentes e inválidos justificados são excluídos.
Pendências/erros impedem o escore final; o escore dos avaliados fica identificado separadamente.
Sem mutantes elegíveis, o escore não se aplica. Sobrevivência não comprova equivalência.

**Experimento aritmético:** confirme uma fórmula e preencha entradas e resultados esperados
independentes em CSV. A original precisa passar em todos os casos antes de avaliar
trocas de operadores binários +, -, *, /. São usados Decimal com precisão de 64 dígitos
e comparação numérica sem tolerância/arredondamento implícitos. Um erro aritmético no
mutante, com original aprovada, detecta a falha. Não há NULL neste experimento.
Limites: 300 caracteres, 12 entradas e 100 casos. O resultado mede apenas o modelo;
não mede o programa 4GL, transações, persistência ou comportamento de arredondamento do banco.

Todos os resultados avançados permitem PDF e JSON. A campanha permite baixar cada TXT
mutante. Os resultados ficam na sessão e são limpos ao trocar o conteúdo de entrada.
Veja [o estado das etapas e o roteiro avançado](documentacao/modulo_avancado.md).

**Mutação da função:** a terceira aba da opção Mutação extrai um modelo numérico da
própria função do TXT, incluindo IF/ELSE, LET, RETURN e NULL. Preencha os casos CSV com
resultados esperados independentes. A base deve passar antes de avaliar variantes da
mesma função. Trocas IS NULL/IS NOT NULL também são geradas. Cada resultado informa
linha, alteração, testes que detectaram, saída obtida e trilha do modelo original.
No exemplo oficial, há nove mutantes na função de cálculo; o catálogo completo passa
a ter 24 variantes (inclui funções não avaliáveis pelo modelo).

Essa avaliação não compila nem executa o programa 4GL. SQL, chamadas externas,
registros, arrays e laços são recusados no modelo numérico. DECIMAL não impõe
arredondamento; o modelo usa precisão de 64 dígitos. Aceitação no modelo não prova
equivalência com o runtime/banco da aplicação original.

## Sprint 4 - Pitch e Validação

Instalar as dependências de desenvolvimento e o navegador de teste:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -B -m unittest discover -s testes -q
.\.venv\Scripts\python.exe -B -m testes.navegador.validar_com_playwright
```

Playwright usa Chromium real, sobe servidores apenas em localhost e os encerra no final.
As evidências ficam em `evidencias/playwright/`: capturas, downloads, logs e resultado JSON.
Essa pasta é ignorada pelo Git. Casos de sucesso com Gemini usam um harness exclusivo
de testes, identificado na tela, que não muda a aplicação de produção. O servidor de
teste da aplicação real é iniciado sem chave para conferir a mensagem de configuração.

O teste real de Gemini é opcional e consome cota. Somente após autorizar o envio dos
dois exemplos didáticos para esse destino, execute:

```powershell
.\.venv\Scripts\python.exe -B -m testes.validar_gemini_real
```

O roteiro de pitch inclui demonstração de todas as sprints, resultados verificáveis e
limitações. Apresentação oral e aceite do professor precisam ser realizados pelo responsável.

## Estrutura e verificação

- `app.py`: upload, seleção de funcionalidade e resultados por IA.
- `aplicacao/`: integração Gemini, modelos, leitura e análise inicial.
- `aplicacao/testes_funcionais.py`: domínios, ε, PCE, AVL e oráculo aritmético.
- `aplicacao/fluxo_controle.py`: análise de funções, grafo, DOT e V(G).
- `aplicacao/exportacao_pdf.py`: relatórios em PDF com fontes incorporadas.
- `aplicacao/interface_testes.py`: formulários e resultados das sprints 1 e 2.
- `aplicacao/interface_relatorios.py`: conversão e download dos PDFs da sessão.
- `aplicacao/requisitos.py`: modelos, derivação, validação dos vínculos e RTM.
- `aplicacao/interface_requisitos.py`: revisão por tabelas e visualização da rastreabilidade.
- `aplicacao/relatorio_requisitos.py`: relatório completo de requisitos/casos/RTM para PDF.
- `aplicacao/def_uso.py`: definições alcançantes, pares e alertas no grafo por instrução.
- `aplicacao/mutacao.py`: variantes, revisão do escore e experimento aritmético.
- `aplicacao/interface_avancada.py`: interface e relatórios dos dois recursos avançados.
- `aplicacao/modelo_funcao.py`: modelo numérico restrito da função e avaliação dos mutantes.
- `testes/navegador/`: execução Playwright e harness de respostas Gemini simuladas.
- `testes/`: testes automatizados e TXT de referência.
- `documentacao/`: critérios de aceite e roteiro funcional.
- `.streamlit/`: tema e configuração de upload.
- `.venv/`: ambiente virtual local, ignorado pelo Git.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s testes -v
```

Os testes padrão não consomem Gemini. Validam IA com cliente simulado, domínios, ε,
fronteiras abertas, precisão, NULL, fórmulas, grafos e métricas conhecidas, PDF e os
fluxos locais no AppTest do Streamlit. Também validam derivação com Gemini simulado,
relações muitos para muitos, lacunas, revisão, exportação e limpeza da RTM ao trocar TXT.
A chamada real ao Gemini depende da chave no processo.
O módulo avançado é validado com casos de sequências, bifurcações, laços, redefinições,
evidências, escore parcial/final, falha da base aritmética e isolamento da sessão.

## Referências técnicas

- [ISTQB CTFL 4.0.1 — classes de equivalência e valores limite](https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf)
- [ReportLab — documentos com Platypus](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/)
- [ReportLab — tabelas e paginação](https://docs.reportlab.com/reportlab/userguide/ch7_tables/)
- [Cornell - definições alcançantes](https://courses.cs.cornell.edu/courses/cs4120/2026sp/notes.html?id=reachdef)
- [Purdue - análise de fluxo de dados](https://www.cs.purdue.edu/homes/xyzhang/spring08/9-df.pdf)
- [PIT - mutantes equivalentes e limites da análise](https://blog.pitest.org/less-is-more/)
- [Playwright Python - instalação e biblioteca](https://playwright.dev/python/docs/library)
- [Streamlit - testes E2E em navegador](https://github.com/streamlit/streamlit/blob/develop/wiki/running-e2e-tests.md)
