# Pitch - TestingStudio Web

Roteiro de 5 minutos para a Sprint 4. Preparado para apresentação pelo responsável.
Não constitui registro de uma apresentação já realizada ou de aceite do professor.

## 1. Problema - 35 segundos

Ao receber código ou requisitos em TXT, é difícil transformar a leitura em um plano
de testes rastreável. Limites, decisões e variáveis precisam de critérios verificáveis.
O TestingStudio reúne a interpretação inicial e técnicas de teste em uma interface.

Fala sugerida: "Nosso objetivo é sair do arquivo de entrada com um plano revisável:
quais entradas testar, quais caminhos existem e quais falhas a suíte consegue detectar."

## 2. Sprint 1 - Caixa Preta - 45 segundos

Abrir PCE / AVL com o exemplo oficial. Informar 0 a 100 e duas casas decimais para
p_val1, p_val2 e p_val3. Esses são critérios didáticos, não limites inferidos do código.
Mostrar epsilon=0,01, classes válidas/inválidas e vizinhos -0,01 / 0,00 / 0,01 e
99,99 / 100,00 / 100,01. Baixar os casos em JSON ou PDF.

Fala sugerida: "Os critérios são confirmados por quem testa. O motor gera as classes
e fronteiras com Decimal, evitando inventar uma regra de negócio a partir do tipo do campo."

## 3. Sprint 2 - Caixa Branca - 40 segundos

Gerar o grafo, selecionar cad0001_calcula_valor e mostrar V(G)=4, correspondente às
três decisões de tratamento de NULL. Abrir nós/arestas e baixar o DOT.

Fala sugerida: "A complexidade é calculada no grafo. Construções fora do subconjunto
suportado são sinalizadas em vez de receber uma métrica aproximada."

## 4. Sprint 3 - Fluxo de Dados e Mutantes - 90 segundos

Mostrar os 13 pares Def-Uso da função de cálculo, distinguindo c-use e p-use.
Explicar que o caminho candidato não comprova execução de um teste.

Na opção Mutação, abrir Mutação da função e colar:

```csv
p_val1,p_val2,p_val3,Esperado
2,3,4,10
NULL,3,4,4
2,NULL,4,4
2,3,NULL,6
NULL,NULL,NULL,0
```

Confirmar e avaliar. Mostrar os nove mutantes da função e quais testes detectaram
cada alteração. Conferir o escore exibido e abrir as trilhas dos casos originais.
Trocar o primeiro esperado de 10 para 11: o modelo original deve reprovar e impedir
o novo escore. Restaurar o valor para continuar a demonstração.

Fala sugerida: "A avaliação usa um modelo numérico derivado da própria função,
preservando IF/ELSE e NULL. Não é execução do programa 4GL nem do banco. Só avaliamos
mutantes depois que todos os casos passam na base original."

## 5. Sprint 4 - Validação e evidências - 40 segundos

Abrir o relatório de validação da versão entregue. Mostrar resultados dos testes
automatizados e cenários Playwright, capturas e downloads reais. Diferenciar o teste
com Gemini simulado do teste real, quando autorizado e disponível.

Fala sugerida: "Os testes de navegador percorrem a interface real. As evidências
permitem repetir a demonstração e verificar o resultado, sem depender de uma afirmação verbal."

## 6. Encerramento e limites - 30 segundos

Mostrar os recursos de apoio: documentação, explicação, requisitos/RTM e relatórios PDF.
Reforçar que 100% de escore no conjunto avaliado não prova ausência de defeitos.

Próximos passos possíveis: ampliar a gramática suportada, validar o modelo contra
o runtime 4GL em ambiente controlado e incorporar novos critérios fornecidos nas aulas.

## Preparação

1. Iniciar a versão da pasta principal pelo comando do README.
2. Usar os dois exemplos de testes/arquivos_de_exemplo.
3. Deixar o relatório e os PDFs baixados disponíveis como evidências.
4. Ensaiar o tempo e registrar perguntas/observações do professor.
5. Não mostrar credenciais nem afirmar suporte completo a todas as instruções 4GL.
