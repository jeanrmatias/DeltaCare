# Delta Care

Plataforma de ensino para uma faculdade de medicina. Organiza turmas,
disciplinas, material de aula, atividades e notas, e tem um assistente de
estudos com IA que responde ao aluno **só** com base no material que o
professor publicou (RAG restrito: sem completar lacuna com conhecimento do
modelo).

É pensada para rodar nos servidores da própria instituição — uma instalação
por faculdade, com o modelo de IA também local. Nenhum dado de aluno sai para
serviço de terceiros.

---

## Entrega — Challenge Hospital Moinhos de Vento

**FIAP · 1º Engenharia de Software · Semi Presencial — Porto Alegre**

| Integrante | RM |
|---|---|
| Arthur Veiga Demétrio | RM570056 |
| Jean Rodrigues Matias | RM571284 |
| Matheus Marques De Souza | RM573203 |

- **Repositório:** https://github.com/jeanrmatias/DeltaCare
- Sprint 3 entregue em 25/09/2026 (ver [`SPRINT_3.md`](SPRINT_3.md)).

### Contas para teste

Criadas pelo `backend/seed_demo.py`, que grava no banco de verdade — não são
dados de fachada no navegador. Todas usam a senha `demo123`:

| Perfil | E-mail |
|---|---|
| Administração | `adm@deltacare.com` |
| Professor | `professor@deltacare.com` |
| Aluno | `aluno@deltacare.com` |

O seed cria também outros professores e alunos, no padrão
`nome.sobrenome@deltacare.com` (ex.: `lucas.martins@`, `beatriz.lemos@`) —
ver **Dados de demonstração**.

---

## O que a plataforma faz

Vocabulário: **turma** é o grupo de alunos que anda junto no semestre (ex.:
MED 3A); **disciplina** é a matéria (ex.: Cardiologia I). Uma turma tem várias
disciplinas, e quem entra na turma é matriculado em todas elas — menos nas que
a administração marcar como exceção (aproveitamento de estudos, por exemplo).

**Aluno**
- **Início:** nível e faixa do semestre (bronze, prata, ouro, platina),
  sequência de dias de estudo, avisos e as disciplinas com o material recente.
- **Chat de estudos:** pergunta ao assistente sobre o material das
  disciplinas; a resposta cita de onde veio, e o que não está no material ele
  recusa, oferecendo levar a dúvida ao professor.
- **Materiais** e **Atividades** (objetivas, corrigidas na hora, e
  dissertativas, com ou sem arquivo anexo), **Desempenho** por disciplina e
  por tópico.
- **Mensagens** com os professores, **Favoritos**, **Anotações** (privadas —
  nem a administração lê), **Ranking** da turma (só o topo aparece, e dá para
  sair dele) e **Semestres anteriores**, com busca dentro dos PDFs.
- **Denúncias** de conteúdo e **Meus dados** (no perfil): cópia de tudo,
  pedido de correção e de exclusão da conta.

**Professor**
- **Início** com o que tem para corrigir, mensagens não lidas e avisos.
- **Materiais** (PDF, documento, vídeo, link; rascunho e publicação agendada),
  **Atividades** e correção das entregas, **Calendário**, **Disciplinas**,
  **Chat** com os alunos, **Desempenho** da turma, **Avisos** e **Semestres
  anteriores**.

**Administração**
- **Turmas** (com as exceções por disciplina), **Disciplinas**, **Usuários**
  (um a um ou importando planilha CSV/XLSX) e o **semestre vigente**.
- **Denúncias**, **Avisos** para a instituição inteira, **Conteúdo**
  (supervisão do que os professores publicaram) e **Privacidade** (pedidos dos
  alunos sobre os próprios dados).
- **Relatórios** ainda não existe: o menu leva a uma página que diz o que o
  módulo vai fazer, em vez de simular com dados de exemplo.

---

## Tecnologias

| Camada | O que é usado |
|---|---|
| Interface | HTML5 semântico, CSS3 (Flexbox, Grid, variáveis, mobile first) e JavaScript ES6+ sem framework |
| Design system | `frontend/tokens.css` (cores, espaçamento, tipografia) e a fonte Inter, do Google Fonts |
| Componentes | Módulos JS próprios: diálogos, notificações, visualizador de material, Markdown, perfil, calendário |
| Sessão no navegador | `sessionStorage` (o token some ao fechar a aba) |
| API | Python 3.10+ com FastAPI, servida pelo Uvicorn |
| Banco | SQLite (modo WAL, chaves estrangeiras cobradas) |
| IA do produto | Ollama local: `gpt-oss:20b` (chat) e `nomic-embed-text` (embeddings) |
| E-mail | SMTP da instituição, pela biblioteca padrão do Python |
| Testes | `unittest` no backend, `node:test` no front, validador de HTML e conferência front↔back próprios |
| Implantação | Servidor Linux com systemd, Caddy na frente (HTTPS automático) |

O front não baixa biblioteca nenhuma (sem Bootstrap, jQuery ou build step). O
backend tem cinco pacotes no `requirements.txt` — FastAPI, Uvicorn, Pydantic,
pypdf e AnyIO —, com versão presa; o resto (hash de senha, e-mail, banco,
leitura de XLSX) vem da biblioteca padrão.

### Onde e como usamos Inteligência Artificial no desenvolvimento

Usamos o **Claude Code (Anthropic)** como par de programação a partir da
Sprint 2. O fluxo é sempre o mesmo: a equipe descreve o problema e o critério
de aceite, a IA propõe a implementação, e a equipe revisa, testa e decide o
que entra — inclusive recusando sugestões (importar planilha a partir de PDF
foi avaliado e descartado; trocar `sessionStorage` por `localStorage` para o
token foi rejeitado por ser pior em segurança).

Todo teste novo é conferido reintroduzindo o defeito que ele deveria pegar: se
o teste continua passando com o defeito, ele não serve e é refeito. Erros
introduzidos pela IA aconteceram e estão registrados na retrospectiva do
`SPRINT_3.md`; foi por causa de um deles que passamos a validar o HTML com
parser em vez de expressão regular.

Isso é distinto da IA **dentro do produto**: o assistente de estudos roda em
Ollama, na infraestrutura da instituição, e responde apenas a partir do
material publicado pelo professor.

---

## O sistema exige o backend no ar

O front não tem modo de contingência: se a API não responder, a tela diz que
não conseguiu falar com o servidor e para por aí.

Isso é decisão de produto, não limitação. Mostrar turma, material ou nota
fictícios quando o servidor cai seria pior do que não mostrar nada, porque
quem está na tela não teria como saber que está olhando para algo que não
existe.

## Como rodar

**Pré-requisitos:** Python 3.10+, [Ollama](https://ollama.com) e um navegador.
Node 18+ só para os testes do front.

1. **Dependências:**

   ```
   pip install -r requirements.txt
   ```

2. **Modelos de IA** (com o Ollama rodando):

   ```
   ollama pull gpt-oss:20b
   ollama pull nomic-embed-text
   ```

   > Com GPU menor (ex.: 12GB de VRAM), o `gpt-oss:20b` fica lento por fazer
   > offload para RAM/CPU. Um modelo menor, como o `llama3.1:8b`, também
   > funciona: baixe-o e defina `MODELO_CHAT=llama3.1:8b`.

3. **Backend:**

   ```
   cd backend
   uvicorn main:app
   ```

   Na primeira execução o banco (`deltacare.db`) é criado sozinho; nas
   seguintes, migrado sozinho. Confira em <http://127.0.0.1:8000/saude>.

   **Sem `--reload`, de propósito:** o reloader do uvicorn já deixou aqui um
   processo órfão segurando a porta 8000 e servindo código antigo. Para
   reiniciar, encerre e suba de novo.

4. **Telas.** A própria API já as serve: abra <http://127.0.0.1:8000>. Para
   desenvolver o front, use o servidor sem cache:

   ```
   cd frontend
   python servir.py
   ```

   e abra <http://127.0.0.1:5500>. O `servir.py` existe em vez do
   `python -m http.server` porque envia `Cache-Control: no-store` — sem isso o
   navegador guarda `.js` antigo e você depura um comportamento que já não
   está no código. Não abra o HTML por `file://`.

   O front descobre sozinho onde está a API
   ([`frontend/config.js`](frontend/config.js)): na porta 5500, na 8000 do
   mesmo computador; em qualquer outro caso, na mesma origem da página.

5. **Dados de demonstração** (opcional, ver abaixo): `python seed_demo.py`,
   dentro de `backend/`.

### Configuração

Tudo por variável de ambiente. Os padrões servem para rodar na máquina; o
modelo completo para o servidor está em
[`deploy/deltacare.env.exemplo`](deploy/deltacare.env.exemplo).

| Variável | Padrão | Para quê |
|---|---|---|
| `DELTACARE_DB` | `deltacare.db` | Arquivo do banco |
| `DELTACARE_UPLOADS` | `uploads` | Pasta dos arquivos enviados (material e entregas) |
| `DELTACARE_ORIGENS` | `http://127.0.0.1:5500,http://localhost:5500` | De onde o navegador pode chamar a API (CORS). Com as telas servidas pela própria API, não é preciso mexer |
| `OLLAMA_URL` | `http://localhost:11434` | Onde está o servidor do modelo |
| `MODELO_CHAT` | `gpt-oss:20b` | Modelo que responde o aluno |
| `MODELO_EMBEDDING` | `nomic-embed-text` | Modelo que indexa o material |
| `ESFORCO_RACIOCINIO` | `low` | Esforço de raciocínio do modelo (modelos que não raciocinam ignoram). `low` corta o tempo de resposta pela metade sem perder qualidade, medido |
| `DELTACARE_IA_SIMULTANEAS` | `4` | Chamadas ao modelo ao mesmo tempo. **Não é limite de perguntas:** quem passa espera, sem travar login nem telas. Suba conforme o servidor do modelo aguentar |
| `DELTACARE_SMTP_HOST`, `_PORTA`, `_SEGURANCA`, `_USUARIO`, `_SENHA`, `_REMETENTE` | vazio, `587`, `starttls` | E-mail da recuperação de senha e dos avisos de privacidade. Sem host, o código aparece no console — e o servidor avisa ao subir |
| `DELTACARE_BACKUPS` | `backups/` ao lado do banco | Onde o `backup.py` guarda as cópias |
| `DELTACARE_BACKUPS_MANTER` | `14` | Quantas cópias o `backup.py` mantém |

## Dados de demonstração

```
cd backend
python seed_demo.py
```

Monta um semestre plausível de medicina, pelas mesmas funções que as telas
usam:

- a turma **MED 3A** com Cardiologia I, Anatomia e Fisiologia, três
  professores e oito alunos (Pedro Albuquerque fica fora de Fisiologia, por
  aproveitamento de estudos — o caso de exceção);
- atividades com prazo e entregas de vários alunos, uma dissertativa já
  corrigida e outra esperando o professor; o ranking tem gente em posições
  diferentes (Júlia Fernandes escolheu não aparecer);
- mensagens (uma não lida para o professor), um aviso urgente da disciplina e
  um geral da coordenação, uma denúncia aberta, favorito e anotação, e um
  pedido de correção de dados esperando a administração;
- o semestre anterior, com a turma **MED 2A** e Histologia, com PDF indexado,
  para a tela Semestres anteriores e a busca dentro do material.

Pode rodar mais de uma vez — o que já existe é reaproveitado (há teste para
isso). Sem o Ollama no ar, tudo é criado e só a indexação dos PDFs fica para
quando ele subir.

O conteúdo dos PDFs é fictício de propósito (um "Protocolo Delta-7" e um
medicamento "Cardiolex" que não existem). Assim dá para provar que o
assistente respondeu lendo o material, e não com conhecimento próprio do
modelo: pergunte a dose do Cardiolex e depois algo fora do material, como
tratamento de apendicite — ele deve recusar a segunda.

**Nunca rode o seed em produção:** ele cria contas com a senha `demo123`.

### Sem o seed

1. O primeiro admin nasce pelo `criar_admin.py`: não existe cadastro público,
   e `POST /admin/usuarios` exige um admin já logado.
2. Como admin: crie a turma (ex.: MED 3A), as disciplinas com seus
   professores e as contas dos alunos (uma a uma ou pela planilha), e
   matricule os alunos na turma.
3. Como professor: suba um PDF na disciplina e publique. A publicação dispara
   a indexação para o chat.
4. Como aluno: pergunte no chat algo do conteúdo do PDF. A resposta cita o
   material como fonte.

## Segurança

- **Sessão por token.** O login devolve um token (validade de 12 horas),
  enviado em `Authorization: Bearer`. Nenhuma rota aceita identidade vinda do
  cliente: quem está chamando é deduzido do token
  ([`backend/infra/sessoes.py`](backend/infra/sessoes.py)). Antes disso, o
  backend acreditava no e-mail enviado pelo front, e bastava trocá-lo para agir
  em nome de outra pessoa.
- **Cada perfil na sua porta.** As rotas exigem o perfil certo, e as regras
  conferem de novo o vínculo (o professor só vê as disciplinas dele; o aluno,
  só o material publicado das disciplinas em que está matriculado).
- **Senha** guardada como PBKDF2-SHA256 com salt individual (260 mil
  iterações).
- **Login com limite:** 5 erros em 15 minutos bloqueiam o e-mail por um tempo.
  Conta que existe e que não existe respondem igual — na mensagem **e** no
  tempo de resposta —, para a tela não servir de verificador de quem é aluno
  daqui. A recuperação de senha segue o mesmo cuidado.
- **Sem cadastro público:** toda conta nasce pela administração ou pela
  planilha.
- **Banco que não trava:** toda conexão aberta durante uma requisição é
  fechada ao fim dela, mesmo que a rota tenha quebrado no meio
  ([`backend/infra/database.py`](backend/infra/database.py)).
- **Privado pela ausência de rota:** anotações e entregas não têm rota para a
  administração. Não é a tela que esconde; é o servidor que não entrega.

## Privacidade (LGPD)

O aluno exerce os direitos de titular pela tela **Meus dados** (link no
perfil); as regras estão em
[`backend/regras/privacidade.py`](backend/regras/privacidade.py), e a política
em [`frontend/privacidade.html`](frontend/privacidade.html).

| Pedido | Quem decide | O que acontece |
|---|---|---|
| Cópia dos dados | ninguém — sai na hora | Arquivo JSON com cadastro, disciplinas, entregas e notas, acessos, favoritos, anotações, conversas e notificações. Fica registrado que foi entregue. |
| Correção (nome, e-mail, matrícula) | administração | A tela **Privacidade** mostra o valor de hoje ao lado do pedido; aprovado, troca na hora. |
| Exclusão da conta | administração | Aprovada, a conta é **desativada** (não entra, sessões encerradas, sai do ranking) e o aluno recebe e-mail. **45 dias depois** é anonimizada. Até lá, a administração pode reverter. |

A anonimização apaga nome, e-mail, matrícula, anotações, favoritos,
notificações e conversas (com o assistente e com os professores). Notas,
entregas, matrículas e acessos ficam, ligados a um "Aluno removido": é o
registro acadêmico que a instituição precisa guardar.

Antes de uso com dados reais, a instituição precisa indicar o encarregado de
dados (DPO) e aprovar a política.

## Implantação

Um servidor Linux, com GPU se o modelo de IA rodar nele. Um processo só serve
a API **e** as telas (em `/app/`); na frente, o
[Caddy](https://caddyserver.com) cuida do HTTPS. Os arquivos estão em
[`deploy/`](deploy).

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
4. **Serviço:** copie `deploy/deltacare.service` para
   `/etc/systemd/system/` e `systemctl enable --now deltacare`. Um processo
   só, de propósito: o SQLite aceita um escritor por vez.
5. **HTTPS:** instale o Caddy, ponha o domínio no `deploy/Caddyfile`, copie
   para `/etc/caddy/Caddyfile` e `systemctl reload caddy`. O certificado sai e
   se renova sozinho.
6. **Rotinas diárias** (crontab do usuário `deltacare`):
   ```
   30 3 * * * cd /opt/deltacare/backend && set -a && . /etc/deltacare.env && set +a && ../.venv/bin/python backup.py >> /var/log/deltacare-backup.log 2>&1
   45 3 * * * cd /opt/deltacare/backend && set -a && . /etc/deltacare.env && set +a && ../.venv/bin/python anonimizar_vencidas.py >> /var/log/deltacare-lgpd.log 2>&1
   ```
   O `backup.py` copia o banco pela API do SQLite (cópia consistente com o
   sistema no ar), confere a cópia e guarda as últimas 14. **Leve as cópias
   para fora do servidor** — backup na mesma máquina não sobrevive ao disco.
   O `anonimizar_vencidas.py` anonimiza as contas cuja exclusão passou dos 45
   dias; o servidor também faz isso ao subir e quando a administração abre a
   fila, e o agendamento cobre o servidor que fica meses no ar sem ninguém
   abrir a fila.
7. **Conferir:** `https://<domínio>/saude` responde `{"status": "ok"}`, e
   `https://<domínio>/` abre a tela de login. Peça o código de recuperação de
   senha para uma conta sua: se o e-mail não chegar, o SMTP está errado (o
   log do serviço diz o motivo).

**Atualizar:** backup, `git pull`, `pip install -r requirements.txt` e
`systemctl restart deltacare`. O banco migra sozinho na subida.

## Testes

```
cd backend
python rodar_testes.py   # regras e rotas, em paralelo (~45s)
python testes.py         # os mesmos, em série
python contrato_front.py # toda chamada do front tem rota no back?

cd ../frontend
node testes.mjs          # JavaScript
python testar_html.py    # estrutura das páginas
```

- **Backend (451 testes):** permissões de cada perfil, visibilidade de
  material, sessão e limite de login, turmas e exceções, atividades e
  correção, XP e ranking, avisos, privacidade e anonimização, integridade do
  banco ao excluir, e o próprio seed. Rodam num banco temporário e **não
  precisam do Ollama** — as funções que falam com o modelo entram como
  parâmetro.
- **Front (74 testes):** Markdown (inclusive que HTML vindo do modelo **não**
  é interpretado), diálogos, calendário, endereço da API e os rótulos de
  status da privacidade conferidos contra o backend. Usa um DOM mínimo escrito
  no próprio arquivo, em vez do jsdom.
- **Páginas (35):** HTML validado por parser.
- **Contrato front↔back:** lê as chamadas `api()` do front e confere com as
  rotas do backend, e os `querySelector` contra os ids das páginas. Pega a
  tela que chama uma rota que não existe antes de alguém clicar.

## Estrutura

```
backend/
  main.py                  - API: rotas, perfis e o middleware de conexões
  seed_demo.py             - dados de demonstração (chama o seed_semestre.py)
  seed_semestre.py         - o semestre de demonstração completo
  criar_admin.py           - primeiro admin numa instalação nova
  backup.py                - cópia conferida do banco e dos arquivos enviados
  anonimizar_vencidas.py   - LGPD: anonimiza exclusões vencidas (1x por dia)
  testes.py                - testes do backend
  rodar_testes.py          - os mesmos testes, em paralelo
  contrato_front.py        - confere o front contra as rotas

  infra/                   - o que o sistema USA
    database.py              esquema, migrações e caminho único do banco
    sessoes.py               token de sessão
    security.py              hash de senha (PBKDF2)
    email.py                 envio por SMTP, em segundo plano
    arquivos.py              gravação dos uploads

  regras/                  - o que o sistema DECIDE
    autenticacao.py          login, contas, recuperação de senha
    coortes.py               turma de alunos e exceções por disciplina
    turmas.py                disciplinas, professores, usuários
    matriculas.py            matrículas
    semestres.py             semestre vigente e histórico
    materiais.py             material na visão do professor
    aluno.py                 material na visão do aluno, XP e nível
    atividades.py            atividades, entregas e correção
    desempenho.py            notas, evolução e erro por tópico
    calendario.py            prazos e liberações do mês
    ranking.py               ranking da turma pelo XP do semestre
    mensagens.py             conversa aluno ↔ professor
    avisos.py                avisos de professor e coordenação
    notificacoes.py          notificações geradas por eventos reais
    favoritos.py             material guardado pelo aluno
    anotacoes.py             caderno privado do aluno
    denuncias.py             conteúdo reportado
    conteudo.py              supervisão do conteúdo pela administração
    privacidade.py           LGPD: cópia, correção, exclusão, anonimização
    importacao.py            planilha CSV/XLSX
    chat_ia.py               RAG: indexação, busca híbrida e resposta

deploy/                    - serviço systemd, Caddyfile e modelo de configuração

frontend/
  index.html, script.js    - login e recuperação de senha
  privacidade.html         - política de privacidade
  servir.py                - servidor de desenvolvimento sem cache
  tokens.css               - design system (cores, espaços, tipografia)
  config.js                - onde está a API
  auth.js                  - sessão e o helper api()
  *.js                     - módulos compartilhados: diálogos, notificações,
                             perfil, Markdown, visualizador, calendário,
                             mensagens, avisos, histórico, denúncias,
                             privacidade, catálogo de módulos
  testes.mjs, testar_html.py

  aluno/                   - 13 telas
  professor/               - 11 telas
  administracao/           - 9 telas
```

A pasta da administração chama-se `administracao`, mas o `tipo` no banco é
`adm` — os dois já estiveram trocados e quebraram o redirecionamento do login.
Os `<script>` e `<link>` levam `?v=N`: ao mexer em `.js` ou `.css`, suba esse
número em todas as páginas, senão o navegador continua com o antigo.

## Limitações conhecidas

- **SQLite aceita um escritor por vez:** aguenta uma faculdade (60 entregas
  simultâneas se enfileiram em ~2s), não uma rede de faculdades.
- **HTTPS depende do Caddy.** Rodando o uvicorn direto numa rede, o token
  viaja em texto claro.
- **A implantação (systemd e Caddy) ainda não rodou num servidor real.**
- Arquivos enviados ficam no disco do servidor, não num serviço de storage.
- O chat indexa só PDF (vídeo e link ficam de fora).
- Professor e administração não têm a tela Meus dados: os pedidos deles sobre
  dados pessoais seguem pela secretaria.
- Relatórios para a coordenação ainda não existem.

## Documentos relacionados

- [`SPRINT_3.md`](SPRINT_3.md) — entrega da Sprint 3: backlog com as user
  stories e critérios de aceite, decisões de experiência, incremento e
  retrospectiva.
- [`TUTORIAL.md`](TUTORIAL.md) — como usar a plataforma, perfil por perfil.
- [`ARQUITETURA.md`](ARQUITETURA.md) — diagramas, fluxo de autenticação, RAG,
  modelo de dados e matriz de permissões.
- [`ROTEIRO_DEMO.md`](ROTEIRO_DEMO.md) — passo a passo da apresentação, com as
  perguntas a fazer no chat e plano B se algum serviço cair.
