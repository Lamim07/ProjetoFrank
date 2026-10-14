# Roteiro funcional — TXT oficial

## Entrada e interface

1. Enviar `cad0001_item_calculo.txt`: mostrar nome e prévia; habilitar análise.
2. Enviar arquivo vazio, só com espaços, extensão diferente ou UTF-8 inválido: impedir análise e mostrar mensagem específica.
3. Enviar arquivo acima de 1 MB: impedir envio ao Gemini.
4. Clicar em **Gerar documentação** sem chave: mostrar orientação para configurar `GEMINI_API_KEY`.
5. Com chave válida: mostrar documentação, evidências e opção de baixar Markdown.
6. Selecionar **Explicar o código**: mostrar fluxo em etapas, entradas e saídas, cálculos,
   operações e lacunas, com evidência literal do TXT.
7. Alternar entre as opções: preservar o resultado já gerado de cada uma.
8. Trocar o arquivo após uma análise: apagar os dois resultados anteriores.

## Conteúdo esperado no TXT

- Linguagem aparente: Informix-4GL / Framework Logix.
- `DATABASE logix` e `mr_item RECORD` com campos `DECIMAL(12,2)`.
- `cad0001_main` inicializa o registro e chama `cad0001_menu`, não definida neste TXT.
- `cad0001_calcula_valor` substitui entradas `NULL` por zero e calcula `(p_val1 * p_val2) + p_val3`.
- `cad0001_incluir` usa dois `INSERT`; `cad0001_alterar` usa dois `UPDATE`.
- `cad0001_excluir` apaga primeiro de `cad_item_calculo` e depois de `cad_item`.
- As três operações abrem transação, verificam `sqlca.sqlcode`, fazem rollback em erro e commit no sucesso.
- O relacionamento 1 para 1 aparece em comentários; sua imposição pelo banco não pode ser confirmada com este TXT.

## Falhas da integração

- Chave inválida ou sem permissão; quota excedida; serviço indisponível; falha de rede.
- Resposta vazia, JSON inválido, esquema incompleto ou evidência ausente do TXT.
- Em todos os casos, não exibir credencial nem texto bruto da exceção da API.
