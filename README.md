# TestingStudio Web — Sprint 1

Aplicação local em Streamlit para analisar estaticamente arquivos TXT com o Gemini. Ela identifica tipo de conteúdo, linguagem aparente, estruturas, funções, regras de negócio, operações e transações. O TXT **não é executado** e não há conexão com bancos mencionados nele.

## Requisitos

- Python 3.11 ou superior
- Acesso à API Gemini e uma chave válida para usar a análise real

## Instalação local

No PowerShell, na pasta `C:\MEUS PROJETOS\Projeto Teste`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Se o ambiente virtual já existia, execute novamente a instalação acima para atualizar
`google-genai` para a versão 2 ou superior. Reinicie o Streamlit após a atualização.

Configure a chave apenas na sessão do terminal ou em um gerenciador de segredos:

```powershell
$env:GEMINI_API_KEY = "sua-chave"
```

O modelo padrão é `gemini-3.8-flash`. Para usar outro modelo disponível em sua conta, defina `GEMINI_MODEL`. `.env.example` documenta os nomes das variáveis; a aplicação não lê arquivos `.env` automaticamente. Nunca coloque a chave no código nem faça commit de `.env` ou `.streamlit/secrets.toml`.

Inicie a aplicação:

```powershell
python -m streamlit run app.py
```

## Uso

1. Envie um arquivo `.txt` codificado em UTF-8, com até 1 MB.
2. Confira o nome e a prévia limitada a 12.000 caracteres.
3. Escolha **Documentação** ou **Explicar o código** e clique no botão correspondente.
   Nesse momento o conteúdo completo é enviado à API Gemini.
4. Em **Documentação**, leia os achados e baixe o arquivo Markdown se desejar.
   Em **Explicar o código**, acompanhe fluxo, entradas e saídas, cálculos e operações.
   Cada opção mantém seu resultado durante a sessão para o TXT atual.

Arquivos vazios, ilegíveis, com extensão diferente ou acima do limite são recusados antes do envio. A resposta do Gemini precisa seguir o esquema esperado; cada trecho de evidência deve existir no arquivo. Uma análise por IA ainda pode conter interpretações incorretas e precisa de revisão humana.

## Testes

```powershell
python -m unittest discover -s testes -v
```

Os testes automatizados usam um cliente simulado e não consomem a API. O arquivo `testes/arquivos_de_exemplo/cad0001_item_calculo.txt` é a cópia do TXT oficial usada nas verificações. A conexão real depende de uma chave configurada e deve ser conferida manualmente pela interface.

## Organização

- `app.py`: entrada do Streamlit, upload e exibição dos resultados.
- `aplicacao/`: validação, leitura do TXT, integração Gemini, análise e documentação.
- `testes/`: testes automatizados e arquivos de exemplo.
- `documentacao/`: roteiro de verificação funcional.
- `.streamlit/`: configuração exigida pelo Streamlit.
- `.venv/`: ambiente virtual local do Python.

## Limites da Sprint 1

A interface fica preparada para PCE e AVL, mas não gera classes, valores limite, ε ou casos de teste. `DECIMAL(12,2)` no TXT é uma declaração de tipo; limites de negócio e arredondamento requerem especificação adicional.
