# TestingStudio Web — Sprints 1, 2 e 3

Aplicação Streamlit para documentar e explicar arquivos TXT, preparar testes funcionais
e visualizar o fluxo de controle de funções Informix-4GL. O código recebido não é executado.

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

Envie um TXT em UTF-8 com até 1 MB e escolha uma das cinco opções:

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

Depois de gerar qualquer resultado, clique em **Transformar em PDF** e **Baixar PDF**.
O PDF contém o resultado completo. O relatório estrutural inclui todas as funções,
diagramas e as limitações encontradas. Grafos grandes são representados integralmente
pelas tabelas de nós e arestas. Os PDFs ficam apenas na sessão. Trocar o conteúdo do
TXT apaga resultados e PDFs anteriores.

## Sprint 2 — PCE e AVL

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

## Sprint 3 — Grafo e complexidade

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
por IA e os domínios manuais de PCE/AVL. Pares Def-Uso e teste de mutação pertencem ao
módulo avançado e não fazem parte deste recorte das sprints 2 e 3.

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

## Estrutura e verificação

- `app.py`: upload, seleção de funcionalidade e resultados por IA.
- `aplicacao/`: integração Gemini, modelos, leitura e análise da Sprint 1.
- `aplicacao/testes_funcionais.py`: domínios, ε, PCE, AVL e oráculo aritmético.
- `aplicacao/fluxo_controle.py`: análise de funções, grafo, DOT e V(G).
- `aplicacao/exportacao_pdf.py`: relatórios em PDF com fontes incorporadas.
- `aplicacao/interface_testes.py`: formulários e resultados das sprints 2 e 3.
- `aplicacao/interface_relatorios.py`: conversão e download dos PDFs da sessão.
- `aplicacao/requisitos.py`: modelos, derivação, validação dos vínculos e RTM.
- `aplicacao/interface_requisitos.py`: revisão por tabelas e visualização da rastreabilidade.
- `aplicacao/relatorio_requisitos.py`: relatório completo de requisitos/casos/RTM para PDF.
- `testes/`: testes automatizados e TXT de referência.
- `documentacao/`: critérios de aceite e roteiro funcional.
- `.streamlit/`: tema e configuração de upload.
- `.venv/`: ambiente virtual local, ignorado pelo Git.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s testes -v
```

Os testes não consomem Gemini. Validam a Sprint 1 com cliente simulado, domínios, ε,
fronteiras abertas, precisão, NULL, fórmulas, grafos e métricas conhecidas, PDF e os
fluxos locais no AppTest do Streamlit. Também validam derivação com Gemini simulado,
relações muitos para muitos, lacunas, revisão, exportação e limpeza da RTM ao trocar TXT.
A chamada real ao Gemini depende da chave no processo.

## Referências técnicas

- [ISTQB CTFL 4.0.1 — classes de equivalência e valores limite](https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf)
- [ReportLab — documentos com Platypus](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/)
- [ReportLab — tabelas e paginação](https://docs.reportlab.com/reportlab/userguide/ch7_tables/)
