# Delta Care

Plataforma de ensino para uma faculdade de medicina: turmas, materiais de
aula e um chat de IA que responde ao aluno **só** com base no material que o
professor publicou (RAG restrito, sem completar lacuna com conhecimento
externo do modelo).

Projeto acadêmico, pensado como demonstrativo — um deploy por instituição,
não SaaS multi-tenant.

## Estrutura

```
backend/
  main.py               - API FastAPI (rotas)
  database.py           - schema do SQLite (configurar_banco)
  security.py           - hash de senha (PBKDF2, sem dependência externa)
  logica.py              - login, cadastro, recuperação de senha
  logica_turmas.py       - CRUD de turma
  logica_materiais.py    - CRUD de material (PDF/link/vídeo)
  logica_matriculas.py   - matrícula/desmatrícula de aluno
  chat_ia.py              - RAG: indexação de PDF + chat restrito ao material
  arquivos.py             - salvar/ler arquivo de material no disco

frontend/
  index.html, script.js   - login (arquivo global, raiz)
  auth.js, config.js       - sessão no navegador + endereço da API
  administracao/           - páginas do admin
  professor/                - páginas do professor
  aluno/                     - páginas do aluno (inclui o chat)
```

Páginas dentro de `administracao/`, `professor/` e `aluno/` referenciam os
arquivos globais com `../` (ex.: `../auth.js`).

## Pré-requisitos

- Python 3.10+
- [Ollama](https://ollama.com) instalado e rodando, com os modelos de chat e
  de embedding baixados (veja abaixo)
- Um navegador para abrir o frontend (ele é HTML/JS estático, sem build)

## Configuração

1. Instale as dependências do backend:

   ```
   pip install -r requirements.txt
   ```

2. Suba o Ollama e baixe os modelos usados pelo chat:

   ```
   ollama pull gpt-oss:20b
   ollama pull nomic-embed-text
   ```

   > Se a GPU disponível for menor (ex.: 12GB de VRAM), o `gpt-oss:20b` pode
   > ficar lento por fazer offload para RAM/CPU. Para testar o fluxo mais
   > rápido, um modelo de chat menor (ex.: `llama3.1:8b`) também funciona —
   > basta baixá-lo e ajustar `MODELO_CHAT` em `backend/chat_ia.py`.

   Por padrão o backend fala com o Ollama em `http://localhost:11434`. Para
   apontar para outro endereço, defina a variável de ambiente `OLLAMA_URL`
   antes de subir o servidor.

3. Suba o backend:

   ```
   cd backend
   uvicorn main:app --reload
   ```

   Na primeira execução, `configurar_banco()` cria o `deltacare.db` (SQLite)
   na pasta `backend/` automaticamente — não precisa criar nada à mão.

   Teste em <http://127.0.0.1:8000> — deve responder
   `{"mensagem": "Backend funcionando :)"}`.

4. Abra o frontend: sirva a pasta `frontend/` com um servidor estático (ex.:
   `python -m http.server 5500` dentro de `frontend/`) e acesse
   `index.html` pelo navegador. Não abra o arquivo direto com `file://` —
   alguns navegadores bloqueiam as requisições à API nesse modo.

   Se o backend estiver rodando em outro endereço/porta, ajuste `API_URL`
   em [`frontend/config.js`](frontend/config.js).

## Fluxo básico para testar

1. Crie um admin (não existe cadastro público de admin/professor — só de
   aluno): use `POST /admin/usuarios` diretamente (ex.: via
   `curl`/Postman) com um admin "semente", ou rode um script de seed se
   houver um em `backend/`.
2. Login como admin → cria uma turma → cria/atribui um professor a ela.
3. Cadastro público (`/cadastro`, tela de login) cria uma conta de aluno →
   admin matricula esse aluno na turma.
4. Login como professor → sobe um material do tipo PDF na turma → publica
   (tira do rascunho). Isso dispara a indexação para o chat
   automaticamente (`chat_ia.indexar_material`).
5. Login como aluno → abre a turma → pergunta algo sobre o conteúdo do PDF
   no chat. A resposta deve citar o material como fonte.

## Limitações conhecidas (ver `CONTEXTO.md`)

- **Sem autenticação real ainda**: o backend confia no e-mail que o front
  manda em cada requisição, sem token de sessão. Não é seguro para dado
  real de aluno — é o item mais crítico antes de qualquer uso fora de
  demonstração.
- SQLite (sem concorrência de verdade), storage de arquivo em disco local,
  e-mail de recuperação de senha só imprime no console: tudo adequado para
  demo, não para produção.
- Chat indexa apenas PDF (vídeo e link ficam de fora do escopo inicial).
- Dashboard do professor tem partes ainda mockadas (entregas, gráfico,
  mensagens).

O `CONTEXTO.md` na raiz tem o histórico de decisões e a lista completa do
que falta para virar produto de verdade.
