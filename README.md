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
  index.html, script.js   - login
  privacidade.html         - política de privacidade (LGPD)
  auth.js                   - token de sessão + helper api() autenticado
  config.js                 - endereço da API
  markdown.js               - renderiza a resposta da IA (sem innerHTML)
  servir.py                 - servidor estático de desenvolvimento (no-store)
  administracao/           - adm.html, adm-turmas.html
  professor/                - prof.html (dashboard), turmas.html, materiais.html
  aluno/                     - inicio.html, aluno.html (chat), materiais.html
```

> A pasta do administrador chama-se `administracao`, mas o valor de `tipo`
> no banco é `adm`. Os dois já estiveram trocados e quebraram o
> redirecionamento do login.

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

4. Abra o frontend:

   ```
   cd frontend
   python servir.py
   ```

   Acesse <http://127.0.0.1:5500>. Não abra o HTML direto com `file://` —
   alguns navegadores bloqueiam as requisições à API nesse modo.

   O `servir.py` existe em vez do `python -m http.server` porque envia
   `Cache-Control: no-store`. Sem isso o navegador guarda os `.js` antigos e
   você fica depurando um comportamento que já não está no código.

   Se o backend estiver rodando em outro endereço/porta, ajuste `API_URL`
   em [`frontend/config.js`](frontend/config.js).

## Dados de demonstração

```
cd backend
python seed_demo.py
```

Cria as três contas, uma turma com professor e aluno matriculado, e um PDF
de exemplo já indexado para o chat. Pode rodar mais de uma vez — o que já
existe é reaproveitado.

| Perfil | E-mail | Senha |
|---|---|---|
| Admin | `adm@deltacare.com` | `demo123` |
| Professor | `professor@deltacare.com` | `demo123` |
| Aluno | `aluno@deltacare.com` | `demo123` |

O conteúdo do PDF é fictício de propósito (um "Protocolo Delta-7" e um
medicamento "Cardiolex" que não existem). Assim dá para provar que o
assistente respondeu lendo o material, e não com conhecimento próprio do
modelo — pergunte a dose do Cardiolex e depois pergunte algo fora do
material, como tratamento de apendicite: ele deve recusar a segunda.

## Fluxo manual (se quiser testar sem o seed)

1. O primeiro admin só nasce pelo `seed_demo.py`: o cadastro público cria
   apenas aluno, e `POST /admin/usuarios` exige um admin já logado.
2. Login como admin → cria uma turma e atribui a um professor.
3. Cadastro público (`/cadastro`, tela de login) cria uma conta de aluno →
   admin matricula esse aluno na turma.
4. Login como professor → sobe um material do tipo PDF na turma → publica
   (tira do rascunho). Isso dispara a indexação para o chat
   automaticamente (`chat_ia.indexar_material`).
5. Login como aluno → abre a turma → pergunta algo sobre o conteúdo do PDF
   no chat. A resposta deve citar o material como fonte.

## Autenticação

O login devolve um token de sessão, guardado na tabela `sessoes` e enviado
pelo front no header `Authorization: Bearer <token>` (ver
[`backend/sessoes.py`](backend/sessoes.py) e [`frontend/auth.js`](frontend/auth.js)).

Nenhuma rota protegida aceita identidade vinda do cliente: quem está
chamando é sempre deduzido do token, pelas dependências `usuario_logado` e
`exigir_perfil` em [`backend/main.py`](backend/main.py). Antes disso, o
backend acreditava no e-mail enviado pelo front, o que permitia agir em nome
de outra pessoa apenas trocando esse campo.

## Limitações conhecidas (ver `CONTEXTO.md`)

- Sem HTTPS: o token viaja em texto claro. Em rede local de demonstração é
  aceitável; para uso real é obrigatório antes de qualquer dado de aluno.
- Sem rate limiting no login — nada impede tentativas repetidas de senha.
- SQLite (sem concorrência de verdade), storage de arquivo em disco local,
  e-mail de recuperação de senha só imprime no console: tudo adequado para
  demo, não para produção.
- Chat indexa apenas PDF (vídeo e link ficam de fora do escopo inicial).
- Dashboard do professor tem partes ainda mockadas (entregas, gráfico,
  mensagens).

## Documentos relacionados

- [`ROTEIRO_DEMO.md`](ROTEIRO_DEMO.md) — passo a passo da apresentação, com
  as perguntas a fazer no chat, respostas para as dúvidas mais prováveis e
  plano B se algum serviço cair.
- [`CONTEXTO.md`](CONTEXTO.md) — histórico de decisões, o que falta para
  virar produto e as armadilhas já encontradas (para não repetir).
