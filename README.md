# Delta Care

Plataforma de ensino para uma faculdade de medicina: turmas, materiais de
aula e um chat de IA que responde ao aluno **só** com base no material que o
professor publicou (RAG restrito, sem completar lacuna com conhecimento
externo do modelo).

Projeto acadêmico, pensado como demonstrativo — um deploy por instituição,
não SaaS multi-tenant.

---

## Entrega — Challenge Hospital Moinhos de Vento · Sprint 3

**FIAP · 1º Engenharia de Software · Semi Presencial — Porto Alegre**

| Integrante | RM |
|---|---|
| Arthur Veiga Demétrio | RM570056 |
| Jean Rodrigues Matias | RM571284 |
| Matheus Marques De Souza | RM573203 |

- **Repositório:** https://github.com/jeanrmatias/DeltaCare

### Contas para teste

A solução tem autenticação. Todas as contas usam a mesma senha:

| Perfil | E-mail | Senha |
|---|---|---|
| Administração | `adm@deltacare.com` | `demo123` |
| Professor | `professor@deltacare.com` | `demo123` |
| Aluno | `aluno@deltacare.com` | `demo123` |

As contas são criadas pelo `backend/seed_demo.py`, que grava no banco de
verdade — não são dados de fachada no navegador.

### Tecnologias utilizadas

| Camada | O que é usado |
|---|---|
| Interface | HTML5 semântico, CSS3 (Flexbox, CSS Grid, variáveis CSS, mobile first com media queries), JavaScript ES6+ sem framework |
| Componentização | Módulos JS próprios: diálogos, notificações, visualizador de material, renderizador de Markdown, perfil, catálogo de módulos |
| Persistência no navegador | `localStorage` (progresso e preferências) e `sessionStorage` (token da sessão) |
| API | Python 3 com FastAPI |
| Banco | SQLite |
| IA do produto | Ollama local: `gpt-oss:20b` (chat) e `nomic-embed-text` (embeddings) |
| Testes | `unittest` no backend, `node:test` no front, validador de HTML próprio |
| Deploy | Vercel (interface) |

Nenhuma dependência de front-end é baixada: não há Bootstrap, jQuery nem build
step. O `requirements.txt` do backend tem cinco pacotes.

### Onde e como usamos Inteligência Artificial no desenvolvimento

Usamos o **Claude Code (Anthropic)** como par de programação durante as Sprints
2 e 3. A IA foi usada para: implementar os itens do relatório de melhorias a
partir da descrição do problema, escrever a suíte de testes automatizados,
construir o módulo de atividades e revisar a documentação. Em todos os casos o
fluxo foi o mesmo: a equipe
descreveu o problema e o critério de aceite, a IA propôs a implementação, e a
equipe revisou, testou e decidiu o que entrava — inclusive recusando sugestões
(por exemplo, importar planilha a partir de PDF foi avaliado e descartado, e a
troca de `sessionStorage` por `localStorage` para o token de sessão foi
rejeitada por ser pior em segurança). Erros introduzidos pela IA aconteceram e
estão registrados na retrospectiva do `SPRINT_3.md`; foi por causa de um deles
que passamos a validar o HTML com parser em vez de expressão regular.

Isso é distinto da IA **dentro do produto**: o assistente de estudos do aluno
roda em Ollama local e responde apenas a partir do material publicado pelo
professor.

---

## O sistema exige o backend no ar

O front não tem modo de contingência: se a API não responder, a tela diz que
não conseguiu falar com o servidor e para por aí.

Isso é decisão de produto, não limitação. O Delta Care é usado por uma
instituição de ensino — mostrar turma, material ou nota fictícios quando o
servidor cai seria pior do que não mostrar nada, porque quem está na tela não
teria como saber que está olhando para algo que não existe.

Para rodar: suba o backend (ver **Configuração**) e sirva o front com
`python frontend/servir.py`.

## Estrutura

```
backend/
  main.py                  - API FastAPI: rotas e dependências de autenticação
  seed_demo.py             - cria os dados de demonstração
  seed_semestre.py         - o resto do semestre de demonstração (chamado pelo seed_demo)
  criar_admin.py           - cria o primeiro admin numa instalação nova
  backup.py                - cópia conferida do banco e dos arquivos enviados
  testes.py                - testes das regras (rodam sem o Ollama)
  rodar_testes.py          - roda os mesmos testes em paralelo
  contrato_front.py        - confere se o front chama rotas que existem

  infra/                   - infraestrutura: o que o sistema USA
    database.py              schema e caminho único do banco
    security.py              hash de senha (PBKDF2, sem dependência externa)
    sessoes.py               token de sessão
    arquivos.py              gravação dos uploads

  regras/                  - regras de negócio: o que o sistema DECIDE
    autenticacao.py          login, cadastro, recuperação de senha
    turmas.py                disciplinas, professores, usuários
    coortes.py               turma de alunos (MED 3A) e exceções por disciplina
    semestres.py             semestre vigente e histórico dos anteriores
    ranking.py               ranking da turma pelo XP do semestre
    avisos.py                professor e coordenação escrevendo para as turmas
    favoritos.py             material guardado pelo aluno, entre semestres
    anotacoes.py             caderno do aluno — privado, sem rota para mais ninguém
    materiais.py             materiais na visão do PROFESSOR
    aluno.py                 materiais na visão do ALUNO, XP e acompanhamento
    atividades.py            atividades, entregas e correção
    desempenho.py            notas, evolução e erro por tópico
    denuncias.py             conteúdo reportado: quem reporta e quem trata
    matriculas.py            matrículas
    notificacoes.py          avisos gerados por eventos reais
    importacao.py            leitura de planilha CSV/XLSX (sem dependência)
    chat_ia.py               RAG: indexação, busca híbrida, resposta

frontend/
  index.html                - login
  privacidade.html          - política de privacidade (LGPD)
  servir.py                 - servidor estático de desenvolvimento (no-store)

  config.js                 - endereço da API
  auth.js                   - token de sessão e helper api() autenticado
  dialogo.js                - diálogos próprios (substituem alert/confirm/prompt)
  markdown.js               - renderiza a resposta da IA (sem innerHTML)
  notificacoes.js           - sino e painel de notificações
  visualizador.js           - abre material na plataforma, sem download
  calendario.js             - seletor de data e hora (digitado ou pelo calendário)
  reportar.js               - reportar material de dentro da própria lista
  denuncias.js              - acompanhamento das denúncias (aluno e professor)
  modulos.js                - catálogo dos módulos ainda não construídos
  testes.mjs                - testes do JavaScript (node testes.mjs)

  administracao/            - adm.html, adm-turmas.html, usuarios.html
  professor/                - prof.html, turmas.html, materiais.html
  aluno/                    - inicio.html, aluno.html (chat), materiais.html

  */em-breve.html           - página de módulo planejado, uma por perfil
```

> A pasta do administrador chama-se `administracao`, mas o valor de `tipo`
> no banco é `adm`. Os dois já estiveram trocados e quebraram o
> redirecionamento do login.

Páginas dentro de `administracao/`, `professor/` e `aluno/` referenciam os
arquivos globais com `../` (ex.: `../auth.js`), e os `<script>`/`<link>` levam
`?v=N` — ao mexer em .js ou .css compartilhado, suba esse número.

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
   > basta baixá-lo e definir a variável de ambiente `MODELO_CHAT`.

   A configuração vem de variáveis de ambiente. Os padrões servem para rodar
   na máquina; no servidor da instituição, as quatro primeiras mudam:

   | Variável | Padrão | Para quê |
   |---|---|---|
   | `OLLAMA_URL` | `http://localhost:11434` | Onde está o servidor do modelo |
   | `MODELO_CHAT` | `gpt-oss:20b` | Modelo que responde o aluno |
   | `DELTACARE_ORIGENS` | `http://127.0.0.1:5500,http://localhost:5500` | Endereços de onde o navegador pode chamar a API (vários, separados por vírgula) |
   | `DELTACARE_IA_SIMULTANEAS` | `4` | Chamadas ao modelo ao mesmo tempo. Não é limite de perguntas: quem passa espera sem travar o resto do sistema. Suba conforme o servidor do modelo aguentar |
   | `DELTACARE_DB` | `deltacare.db` | Arquivo do banco |
   | `DELTACARE_UPLOADS` | `uploads` | Pasta dos arquivos enviados (material e entregas) |
   | `DELTACARE_SMTP_HOST` e afins | (vazio) | Servidor de e-mail da recuperação de senha. Vazio, o código só aparece no console — o servidor avisa ao subir. Lista completa em [`deploy/deltacare.env.exemplo`](deploy/deltacare.env.exemplo) |
   | `DELTACARE_BACKUPS` | `backups/` ao lado do banco | Onde o `backup.py` guarda as cópias |

3. Suba o backend:

   ```
   cd backend
   uvicorn main:app
   ```

   Na primeira execução, `configurar_banco()` cria o `deltacare.db` (SQLite)
   na pasta `backend/` automaticamente — não precisa criar nada à mão.

   **Sem `--reload`, de propósito:** o reloader do uvicorn já deixou aqui um
   worker órfão segurando a porta 8000 e servindo código antigo, com os
   restarts falhando em silêncio. Para reiniciar, encerre o processo e suba de
   novo.

   Teste em <http://127.0.0.1:8000/saude> — deve responder `{"status": "ok"}`.
   A raiz (<http://127.0.0.1:8000>) já abre as telas: a API também as serve,
   em `/app/`.

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

   O front descobre sozinho onde está a API (ver
   [`frontend/config.js`](frontend/config.js)): na porta 5500 ela está na 8000
   do mesmo computador; em produção, na mesma origem.

## Dados de demonstração

```
cd backend
python seed_demo.py
```

Monta um semestre plausível de medicina, pelas mesmas funções que as telas
usam:

- a turma de alunos **MED 3A** com Cardiologia I, Anatomia e Fisiologia, três
  professores e oito alunos (Pedro Albuquerque fica fora de Fisiologia, por
  aproveitamento de estudos — o caso de exceção);
- atividades com prazo e entregas de vários alunos, uma dissertativa já
  corrigida e outra esperando o professor, o que dá ranking com gente em
  posições diferentes (Júlia Fernandes escolheu não aparecer);
- mensagens (uma não lida para o professor), um aviso urgente da disciplina e
  um geral da coordenação, uma denúncia aberta, favorito e anotação;
- o semestre anterior com **MED 2A** e Histologia, com PDF indexado, para a
  tela Semestres anteriores e a busca dentro do material.

Pode rodar mais de uma vez — o que já existe é reaproveitado. As contas extras
seguem o padrão `nome.sobrenome@deltacare.com` (ex.: `lucas.martins@`,
`beatriz.lemos@`), todas com a senha `demo123`.

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

1. O primeiro admin nasce pelo `criar_admin.py` (ou pelo `seed_demo.py`): o
   cadastro público cria apenas aluno, e `POST /admin/usuarios` exige um
   admin já logado.
2. Login como admin → cria uma turma e atribui a um professor.
3. Cadastro público (`/cadastro`, tela de login) cria uma conta de aluno →
   admin matricula esse aluno na turma.
4. Login como professor → sobe um material do tipo PDF na turma → publica
   (tira do rascunho). Isso dispara a indexação para o chat
   automaticamente (`regras.chat_ia.indexar_material`).
5. Login como aluno → abre a turma → pergunta algo sobre o conteúdo do PDF
   no chat. A resposta deve citar o material como fonte.

## Autenticação

O login devolve um token de sessão, guardado na tabela `sessoes` e enviado
pelo front no header `Authorization: Bearer <token>` (ver
[`backend/infra/sessoes.py`](backend/infra/sessoes.py) e [`frontend/auth.js`](frontend/auth.js)).

Nenhuma rota protegida aceita identidade vinda do cliente: quem está
chamando é sempre deduzido do token, pelas dependências `usuario_logado` e
`exigir_perfil` em [`backend/main.py`](backend/main.py). Antes disso, o
backend acreditava no e-mail enviado pelo front, o que permitia agir em nome
de outra pessoa apenas trocando esse campo.

## Limitações conhecidas

- Sem HTTPS: o token viaja em texto claro. Em rede local de demonstração é
  aceitável; para uso real é obrigatório antes de qualquer dado de aluno.
- SQLite aceita um escritor por vez: aguenta uma faculdade (60 entregas
  simultâneas se enfileiram em ~2s), não uma rede de faculdades.
- Arquivos enviados ficam no disco do servidor, não num serviço de storage.
- Chat indexa apenas PDF (vídeo e link ficam de fora do escopo inicial).

## Implantação

Um servidor Linux, com GPU se o modelo de IA rodar nele. Um processo só serve
a API **e** as telas (em `/app/`); na frente, o [Caddy](https://caddyserver.com)
cuida do HTTPS. Os arquivos estão em [`deploy/`](deploy).

1. **Código e dependências**
   ```
   git clone <repositório> /opt/deltacare
   cd /opt/deltacare && python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
2. **Configuração:** copie `deploy/deltacare.env.exemplo` para
   `/etc/deltacare.env`, preencha (domínio, SMTP, pastas de dados) e
   `chmod 600 /etc/deltacare.env`. Crie a pasta dos dados
   (`/var/lib/deltacare`) com dono `deltacare`.
3. **Primeira conta de administração:**
   ```
   cd /opt/deltacare/backend
   set -a; . /etc/deltacare.env; set +a
   ../.venv/bin/python criar_admin.py
   ```
   **Nunca rode o `seed_demo.py` em produção:** ele cria contas com a senha
   `demo123`.
4. **Serviço:** copie `deploy/deltacare.service` para
   `/etc/systemd/system/` e `systemctl enable --now deltacare`.
5. **HTTPS:** instale o Caddy, ponha o domínio no `deploy/Caddyfile`, copie
   para `/etc/caddy/Caddyfile` e `systemctl reload caddy`. O certificado sai e
   se renova sozinho.
6. **Backup diário** (crontab do usuário `deltacare`):
   ```
   30 3 * * * cd /opt/deltacare/backend && set -a && . /etc/deltacare.env && set +a && ../.venv/bin/python backup.py >> /var/log/deltacare-backup.log 2>&1
   ```
   O `backup.py` copia o banco pela API do SQLite (cópia consistente com o
   sistema no ar), confere a cópia e guarda as últimas 14. **Leve as cópias
   para fora do servidor** — backup na mesma máquina não sobrevive ao disco.
7. **Conferir:** `https://<domínio>/saude` responde `{"status": "ok"}`, e
   `https://<domínio>/` abre a tela de login. Peça o código de recuperação de
   senha para uma conta sua: se o e-mail não chegar, o SMTP está errado (o
   log do serviço diz o motivo).

**Atualizar:** `git pull`, `pip install -r requirements.txt`, `systemctl
restart deltacare`. O banco migra sozinho na subida; faça um backup antes.

## Testes

```
cd backend
python rodar_testes.py  # regras de negócio, em paralelo (~25s)
python testes.py        # os mesmos, em série (~2min)

cd ../frontend
node testes.mjs         # JavaScript
python testar_html.py   # estrutura das páginas
```

**Backend:** permissões, visibilidade de material, sessão, notificações,
importação de planilha, progresso do aluno e integridade do banco ao excluir.
Rodam num banco temporário e **não precisam do Ollama ligado** — as funções que
falam com o modelo entram como parâmetro, que é para isso que elas foram
isoladas em `regras/chat_ia.py`.

**Frontend:** renderização de Markdown (incluindo que HTML vindo do modelo
**não** é interpretado), nome de exibição, formatos que o visualizador aceita e
consistência entre os links do menu e o catálogo de módulos. Usa um DOM mínimo
escrito no próprio arquivo, em vez do jsdom — as funções testadas usam meia
dúzia de métodos, e uma dependência de 3 MB para isso seria desproporcional.

Requer Node 18+ (só para os testes; a aplicação não usa Node).

## Documentos relacionados

- [`SPRINT_3.md`](SPRINT_3.md) — entrega da Sprint 3 da disciplina Software &
  Total Experience Design: objetivo, sprint backlog com as user stories e seus
  critérios de aceite, decisões de experiência, incremento e retrospectiva.
- [`TUTORIAL.md`](TUTORIAL.md) — como usar a plataforma, perfil por perfil:
  criar contas e turmas, publicar material com rascunho e agendamento, e como
  o aluno usa o assistente de estudos.
- [`ARQUITETURA.md`](ARQUITETURA.md) — diagramas de arquitetura, fluxo de
  autenticação, funcionamento do RAG, modelo de dados e matriz de permissões.
- [`ROTEIRO_DEMO.md`](ROTEIRO_DEMO.md) — passo a passo da apresentação, com
  as perguntas a fazer no chat, respostas para as dúvidas mais prováveis e
  plano B se algum serviço cair.
