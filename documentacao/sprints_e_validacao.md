# Sprints oficiais e critérios de aceite

Divisão confirmada pelo responsável em 20/10/2026. Esta classificação substitui a
numeração informal usada nos primeiros registros do desenvolvimento.

| Sprint | Escopo | Critério verificável | Evidência |
|---|---|---|---|
| 1 - Testes de Caixa Preta | PCE, AVL, epsilon e casos | Domínios confirmados; classes válidas/inválidas; fronteiras e vizinhos com Decimal; NULL e precisão | test_testes_funcionais.py; Playwright test_02; JSON/PDF |
| 2 - Testes de Caixa Branca | Grafo e V(G) | Nós/arestas por função; E-N+2; fixture oficial com 1/4/3/3/3; construções sem suporte explicitadas | test_fluxo_controle.py; Playwright test_03; DOT/PDF |
| 3 - Fluxo de Dados e Mutantes | Def-Uso, variantes e avaliação | Definições alcançantes com kill; c-use/p-use; mutantes de primeira ordem; base aprovada antes do escore; evidências por teste | test_def_uso.py, test_mutacao.py, test_modelo_funcao.py; Playwright test_04 a test_07 |
| 4 - Pitch e Validação | Apresentação, demonstração e evidências | Pitch com roteiro; regressão automatizada; navegação e downloads em Chromium; relato honesto de limites e pendências | pitch.md; validar_com_playwright.py; evidencias/playwright/resultado.json |

## Recursos de apoio

Upload, validação UTF-8/tamanho, documentação, explicação, Gemini, requisitos/RTM,
exportações e isolamento de sessão apoiam as quatro sprints. Os cenários Playwright
test_01 e test_08 a test_12 verificam esses fluxos, inclusive tela móvel e falhas.

## O que significa aprovação técnica

1. Os testes automatizados passam na pasta final.
2. O Playwright usa um navegador Chromium real para interagir com o aplicativo.
3. Downloads são salvos e verificados; JSON tem valores esperados e PDF tem cabeçalho válido.
4. PDFs relevantes são renderizados e conferidos visualmente além das verificações automáticas.
5. Casos com Gemini simulado são identificados como simulação. Seu sucesso não prova o serviço externo.
6. O teste real de Gemini só ocorre após autorização específica para transmitir os exemplos didáticos.
7. A apresentação oral, validação de negócio e aceite do professor continuam sendo atos humanos.

Não foi fornecida rubrica detalhada da Sprint 4 além de Pitch e Validação. O pacote
prepara roteiro, demonstração e evidências; não presume notas ou aceite acadêmico.

## Limites da conformidade

- Caixa preta: limites de negócio são confirmados pelo usuário; DECIMAL não é regra de negócio.
- Caixa branca: subconjunto 4GL explícito, sem controle excepcional implícito de SQL.
- Def-Uso: análise intraprocedural; caminhos candidatos não provam viabilidade/cobertura dinâmica.
- Mutação da função: avaliação de um modelo restrito derivado da função, incluindo NULL,
  IF/ELSE, LET e RETURN. Recusa SQL, chamadas, registros, arrays e laços. Não executa o runtime 4GL.
- Equivalência entre modelo, tipos DECIMAL e runtime real não foi provada. Sem arredondamento implícito.
- Campanha externa: mortes/sobrevivências e equivalentes exigem evidência humana e são identificadas como externas.
- Escore é relativo aos mutantes gerados e casos fornecidos. 100% nesse conjunto não significa ausência de defeitos.

## Comandos reproduzíveis

```powershell
cd 'C:\MEUS PROJETOS\Projeto Teste\ProjetoFrank'
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -B -m unittest discover -s testes -q
.\.venv\Scripts\python.exe -B -m testes.navegador.validar_com_playwright
```

O runner de navegador inicia dois servidores efêmeros somente em 127.0.0.1. Um executa
app.py sem credencial; o outro usa o harness de testes com respostas Gemini simuladas.
Contextos de navegador são separados por cenário; servidores e navegador são encerrados.
Não há alteração de dados externos, banco de dados ou envio de TXT pela suíte E2E.

Os testes reais de API são executados separadamente e não são requisito para instalar
ou usar as funções locais. Sua aprovação/rejeição deve aparecer no relatório final.

## Referência visual

Continuidade da interface existente e das capturas do módulo avançado. Mantidos fundo
claro, largura de leitura, títulos azul escuro e ação primária verde. A nova avaliação
entra como terceira aba de Mutação. Referência de apoio: Refero Design/craft-details.md
(rótulos, confirmação de critérios, erros junto da ação e estados explícitos).

## Checklist da apresentação

- [ ] Responsável ensaiou o pitch com a versão validada.
- [ ] Evidências e downloads abrem no computador usado na apresentação.
- [ ] Os limites do modelo 4GL são apresentados antes de interpretar o escore.
- [ ] Gemini real disponível ou demonstração claramente identificada como simulada.
- [ ] Professor/responsável registrou o aceite e as observações.
