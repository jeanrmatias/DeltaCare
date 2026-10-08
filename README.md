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
- Sprint 3 entregue em 25/09/2026 (ver [`docs/SPRINT_3.md`](docs/SPRINT_3.md)).
- **Sprint 4 — entrega em 25/10/2026** (Web Development e Front-End Design;
  documento da entrega em [`docs/SPRINT_4.md`](docs/SPRINT_4.md)):

  | O que a sprint pede | Onde está |
  |---|---|
  | React com componentes, props e hooks nativos | todas as telas, em [`frontend/src/`](frontend/src) |
  | Ao menos um hook próprio | `useSessao`, `useApi`, `useDialogo`, `useApagarAnotacao`, `useTituloDaPagina` e `useEnvio`, em [`frontend/src/hooks/`](frontend/src/hooks) |
  | Rotas públicas e privadas | [`frontend/src/App.jsx`](frontend/src/App.jsx) e [`frontend/src/rotas/RotaPrivada.jsx`](frontend/src/rotas/RotaPrivada.jsx): login e privacidade públicos; cada área só para o próprio perfil |
  | Tailwind CSS | tema do projeto em [`frontend/src/index.css`](frontend/src/index.css) |
  | Validação de usabilidade com no mínimo 3 participantes | [`docs/validacao/`](docs/validacao/README.md) e a seção **Validação de usabilidade** abaixo |

### Contas para teste

Criadas pelo `backend/scripts/seed_demo.py`, que grava no banco de verdade — não são
dados de fachada no navegador. Todas usam a senha `demo123` e entram direto,
sem a troca de senha do primeiro acesso e sem o código por e-mail que conta
de verdade de professor e administração exige:

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
  disciplinas — no modo automático, o padrão, sem escolher a disciplina: ele
  procura em todas e diz de qual veio a resposta. A resposta cita a fonte, e o
  que não está no material ele recusa, oferecendo levar a dúvida ao professor.
  O aluno apaga a conversa quando quiser.
- **Materiais** e **Atividades** (objetivas, corrigidas na hora, e
  dissertativas, com ou sem arquivo anexo), **Desempenho** por disciplina e
  por tópico.
- **Mensagens** com os professores, **Favoritos**, **Anotações** (privadas —
  nem a administração lê), **Ranking** da turma (só o topo aparece, e dá para
  sair dele) e **Semestres anteriores**, com busca dentro dos PDFs.
- **Denúncias** de conteúdo e **Meus dados** (no perfil): cópia de tudo,
  pedido de correção e de exclusão da conta.

**Professor**
- **Início** com o que tem para corrigir, mensagens não lidas, avisos e o que
  falta no material.
- **Lacunas do material:** o que os alunos perguntam ao assistente e o
  material não responde — por assunto ("dobutamina: o material diz quando
  usar, mas não a dose; 4 alunos"), sem o nome nem o texto da pergunta, e só
  com assunto de pelo menos dois alunos.
- **Materiais** (PDF, documento, vídeo, link; rascunho e publicação agendada),
  **Atividades** e correção das entregas, **Calendário**, **Disciplinas**,
  **Chat** com os alunos, **Desempenho** da turma, **Avisos** e **Semestres
  anteriores**.
- **Relatórios** da turma nas disciplinas dele: ao vivo e mês a mês.

**Administração**
- **Turmas** (com as exceções por disciplina), **Disciplinas**, **Usuários**
  (um a um ou importando planilha CSV/XLSX) e o **semestre vigente**.
- **Denúncias**, **Avisos** para a instituição inteira, **Conteúdo**
  (supervisão do que os professores publicaram), **Privacidade** (pedidos dos
  alunos sobre os próprios dados) e **Auditoria** (quem fez o quê, quando e
  de onde).
- **Usuários** inclui **excluir a conta** de quem saiu (desativa na hora,
  anonimiza em 45 dias, dá para desfazer) e **Disciplinas**, **trocar o
  professor** de uma disciplina.
- **Relatórios:** a turma **ao vivo** (quem estudou na última hora e em 24
  horas, atividades em aberto, o que acabou de acontecer — atualiza sozinho a
  cada 30 segundos), **por mês** (aproveitamento, entregas no prazo,
  atrasadas e não entregues, alunos ativos, dias de estudo, XP, perguntas ao
  assistente e quanto o material respondeu; baixa em planilha) e a
  **dificuldade por disciplina**: as disciplinas do semestre da de menor
  aproveitamento para a de maior, com os alunos abaixo de 60%, as entregas
  que faltam, as perguntas que o material não respondeu e o tópico com mais
  erro. Sem nome de aluno.

---

## Tecnologias

| Camada | O que é usado |
|---|---|
| Interface | **React 19** com **React Router** (rotas públicas e privadas por perfil), em JavaScript, compilado pelo **Vite** |
| Estilo | **Tailwind CSS 4**, com o tema (cores, espaços, raios) montado a partir do design system do projeto, em português (`bg-primaria`, `rounded-cartao`). Tipografia "editorial clínica": títulos e números em **Literata** (serifada de leitura), texto em **Source Sans 3** |
| Componentes | Próprios: painel com menu e sino, cartões, modal, visualizador de material, Markdown, calendário, gráficos de desempenho |
| Hooks próprios | `useSessao` (quem está logado), `useApi` (busca com carregando e erro tratados), `useDialogo` (confirmar e avisar), `useApagarAnotacao`, `useTituloDaPagina` (o nome da página na aba), `useEnvio` (um envio de formulário por vez) |
| Sessão no navegador | `sessionStorage` (o token some ao fechar a aba) |
| API | Python 3.10+ com FastAPI, servida pelo Uvicorn |
| Banco | SQLite (modo WAL, chaves estrangeiras cobradas) |
| IA do produto | Ollama local: `gpt-oss:20b` (chat) e `nomic-embed-text` (embeddings) |
| E-mail | SMTP da instituição, pela biblioteca padrão do Python |
| Testes | `unittest` no backend, `node:test` no front (as telas React renderizadas no Node), conferência front↔back própria |
| Implantação | Servidor Linux com systemd, Caddy na frente (HTTPS automático) |

As dependências são poucas e com versão presa nos dois lados. O front usa
React, React DOM, React Router e Tailwind (com o Vite para compilar), sem
biblioteca de componentes nem de gráficos. O backend tem cinco pacotes no
`requirements.txt` — FastAPI, Uvicorn, Pydantic, pypdf e AnyIO —; o resto
(hash de senha, e-mail, banco, leitura de XLSX) vem da biblioteca padrão.

> **O front antigo.** Até a Sprint 3 as telas eram HTML, CSS e JavaScript sem
> framework. Na Sprint 4 todas foram reescritas em React, que é o que o
> servidor entrega, e o front antigo saiu do repositório — continua no
> histórico do git, para quem quiser comparar.

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
`docs/SPRINT_3.md`; foi por causa de um deles que passamos a validar o HTML com
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

**Pré-requisitos:** Python 3.10+, Node 18+, [Ollama](https://ollama.com) e um
navegador.

1. **Dependências:**

   ```
   pip install -r backend/requirements.txt
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
   uvicorn main:app --app-dir app
   ```

   O código fica em `backend/app/`, e o `--app-dir` diz ao uvicorn onde está
   o `main.py`. Rode sempre de dentro de `backend/`: o banco e os arquivos
   enviados ficam ali, ao lado do código e fora dele.

   Na primeira execução o banco (`deltacare.db`) é criado sozinho; nas
   seguintes, migrado sozinho. Confira em <http://127.0.0.1:8000/saude>.

   **Sem `--reload`, de propósito:** o reloader do uvicorn já deixou aqui um
   processo órfão segurando a porta 8000 e servindo código antigo. Para
   reiniciar, encerre e suba de novo.

4. **Telas** (React):

   ```
   cd frontend
   npm install      # só na primeira vez
   npm run dev      # recarga instantânea, em http://localhost:5173/app/
   ```

   Para ver como fica em produção, compile (`npm run build`): a própria API
   passa a entregar as telas em <http://127.0.0.1:8000/app/>. As telas
   descobrem sozinhas onde está a API
   ([`frontend/src/lib/api.js`](frontend/src/lib/api.js)): no Vite (5173), na 8000 do
   mesmo computador; em produção, na mesma origem.

5. **Dados de demonstração** (opcional, ver abaixo):
   `python scripts/seed_demo.py`, dentro de `backend/`.

### Configuração

Tudo por variável de ambiente. Os padrões servem para rodar na máquina; o
modelo completo para o servidor está em
[`deploy/deltacare.env.exemplo`](deploy/deltacare.env.exemplo).

| Variável | Padrão | Para quê |
|---|---|---|
| `DELTACARE_DB` | `deltacare.db` | Arquivo do banco |
| `DELTACARE_UPLOADS` | `uploads` | Pasta dos arquivos enviados (material e entregas) |
| `DELTACARE_FUSO_HORAS` | `-3` | Fuso da instituição em horas, em relação ao UTC (Brasília e Porto Alegre: −3, sem horário de verão). O banco guarda em UTC; calendário, dias de estudo, sequência, XP por dia, ranking da semana e relatórios por mês usam o dia e a hora locais |
| `DELTACARE_TELAS` | `frontend/dist` | Pasta das telas compiladas (`npm run build`) que a API entrega em `/app/` |
| `DELTACARE_ORIGENS` | portas 5500 e 5173 da máquina local | De onde o navegador pode chamar a API (CORS). Com as telas servidas pela própria API, não é preciso mexer |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Onde está o servidor do modelo. Use o IP, não `localhost`: no Windows, `localhost` tenta o IPv6 antes e soma ~2 s a cada chamada (5 s por pergunta no chat) |
| `MODELO_CHAT` | `gpt-oss:20b` | Modelo que responde o aluno |
| `MODELO_EMBEDDING` | `nomic-embed-text` | Modelo que indexa o material |
| `ESFORCO_RACIOCINIO` | `low` | Esforço de raciocínio do modelo (modelos que não raciocinam ignoram). `low` corta o tempo de resposta pela metade sem perder qualidade, medido |
| `DELTACARE_IA_SIMULTANEAS` | `4` | Chamadas ao modelo ao mesmo tempo. **Não é limite de perguntas:** quem passa espera, sem travar login nem telas. Suba conforme o servidor do modelo aguentar |
| `DELTACARE_SMTP_HOST`, `_PORTA`, `_SEGURANCA`, `_USUARIO`, `_SENHA`, `_REMETENTE` | vazio, `587`, `starttls` | E-mail do código de acesso de professor e administração, da recuperação de senha e dos avisos de privacidade. Sem host, o código aparece no console — serve para desenvolver, **não para produção**: sem e-mail, professor e administração não entram |
| `DELTACARE_BACKUPS` | `backups/` ao lado do banco | Onde o `backup.py` guarda as cópias |
| `DELTACARE_BACKUPS_MANTER` | `14` | Quantas cópias o `backup.py` mantém |

## Dados de demonstração

```
cd backend
python scripts/seed_demo.py
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
- PDFs em todas as disciplinas, indexados para o chat e para a busca
  dentro do material;
- o semestre anterior, com a turma **MED 2A** e Histologia, para a tela
  Semestres anteriores.

Pode rodar mais de uma vez — o que já existe é reaproveitado (há teste para
isso). Sem o Ollama no ar, tudo é criado e só a indexação dos PDFs fica para
quando ele subir.

Os PDFs são material didático de verdade, com as referências no fim de
cada aula ([`backend/scripts/material_demo.py`](backend/scripts/material_demo.py)):
insuficiência cardíaca aguda, fibrilação atrial, saúde mental e doença
cardiovascular (Cardiologia I); ossos e base do crânio (Anatomia); ciclo
cardíaco, resposta ao estresse e sono (Fisiologia); tecido epitelial e
nervoso (Histologia). Para ver que o assistente se prende ao material: cada
resposta diz de qual aula saiu; pergunte *quando usar a dobutamina e qual a
dose* (a aula diz quando, não a dose) e algo fora do material, como o
tratamento da apendicite — ele traz só o que o material tem e recusa o resto.

**Nunca rode o seed em produção:** ele cria contas com a senha `demo123`, que
todo mundo que viu o projeto conhece, e sem o código por e-mail. São as
únicas contas que o sistema deixa existir assim.

### Sem o seed

1. O primeiro admin nasce pelo `scripts/criar_admin.py`: não existe cadastro público,
   e `POST /admin/usuarios` exige um admin já logado.
2. Como admin: crie a turma (ex.: MED 3A), as disciplinas com seus
   professores e as contas dos alunos (uma a uma ou pela planilha), e
   matricule os alunos na turma. A senha que você define é provisória: cada
   pessoa escolhe a sua no primeiro acesso.
3. Como professor: suba um PDF na disciplina e publique. A publicação dispara
   a indexação para o chat.
4. Como aluno: pergunte no chat algo do conteúdo do PDF. A resposta cita o
   material como fonte.

## Segurança

- **Sessão por token.** O login devolve um token (validade de 12 horas),
  enviado em `Authorization: Bearer`. Nenhuma rota aceita identidade vinda do
  cliente: quem está chamando é deduzido do token
  ([`backend/app/infra/sessoes.py`](backend/app/infra/sessoes.py)). Antes disso, o
  backend acreditava no e-mail enviado pelo front, e bastava trocá-lo para agir
  em nome de outra pessoa. O banco guarda só o hash do token: uma cópia dele
  (o backup é diário) não abre sessão de ninguém.
- **Tamanho de tudo o que chega.** Cada texto tem limite — a pergunta ao
  assistente, títulos, enunciados, respostas, descrições, nomes
  ([`backend/app/regras/limites.py`](backend/app/regras/limites.py)) —, e o
  Caddy barra a requisição inteira acima de 25 MB. Sem isso, uma pergunta de
  um megabyte ia inteira para o modelo de IA.
- **Nada em dobro, nem com cliques simultâneos.** O que não pode se repetir —
  conta, disciplina, turma, matrícula, entrega, denúncia aberta, pedido de
  privacidade em aberto — é garantido por restrição única no próprio banco,
  e não só por uma conferência antes de gravar (que duas requisições ao
  mesmo tempo passavam juntas). Na tela, o formulário trava do clique até a
  resposta (`useEnvio`).
- **Testada com entradas malformadas.** Cada rota recebeu milhares de
  requisições com tipos trocados, números fora da faixa, textos enormes e
  caracteres estranhos, de todos os perfis e sem login: nenhuma resposta 500.
- **Cada perfil na sua porta.** As rotas exigem o perfil certo, e as regras
  conferem de novo o vínculo (o professor só vê as disciplinas dele; o aluno,
  só o material publicado das disciplinas em que está matriculado).
- **Senha** guardada como PBKDF2-SHA256 com salt individual (260 mil
  iterações). Toda senha nova tem **8 caracteres ou mais** e não pode ser uma
  das conhecidas ("12345678", "medicina123") nem o próprio e-mail ou nome
  ([`backend/app/regras/senhas.py`](backend/app/regras/senhas.py)). Sem troca
  periódica forçada nem "maiúscula, número e símbolo": a recomendação atual
  (NIST SP 800-63B) desaconselha as duas, porque produzem senhas
  previsíveis.
- **Dois fatores para professor e administração:** a senha certa não abre a
  sessão; chega um código de 6 dígitos no e-mail, válido por 10 minutos, com
  5 tentativas e até 3 reenvios. O código não é guardado (só o hash), e cada
  código errado conta como erro de login — quem descobrir a senha não ganha
  chutes infinitos. O aluno entra só com a senha (decisão da instituição).
- **Login com limite:** 5 erros em 15 minutos bloqueiam o e-mail por um tempo.
  Conta que existe e que não existe respondem igual — na mensagem **e** no
  tempo de resposta —, para a tela não servir de verificador de quem é aluno
  daqui. A recuperação de senha segue o mesmo cuidado.
- **Sem cadastro público:** toda conta nasce pela administração ou pela
  planilha.
- **Senha provisória troca no primeiro acesso.** A conta criada pela
  administração ou pela planilha (que dá a mesma senha à turma inteira) entra
  numa tela que pede uma senha nova antes de qualquer outra. Quem bloqueia é o
  servidor: com a senha provisória, toda rota responde 403, menos ver o
  próprio perfil, trocar a senha e sair. A troca, ali ou em **Alterar senha**
  no perfil, pede a senha atual e encerra as outras sessões abertas da conta.
- **Banco que não trava:** toda conexão aberta durante uma requisição é
  fechada ao fim dela, mesmo que a rota tenha quebrado no meio
  ([`backend/app/infra/database.py`](backend/app/infra/database.py)).
- **Privado pela ausência de rota:** anotações e entregas não têm rota para a
  administração. Não é a tela que esconde; é o servidor que não entrega.
- **Trilha de auditoria:** toda ação da administração, as exclusões de
  conteúdo do professor, a cópia de dados pessoais e os eventos de acesso
  (login certo e errado, código, troca e recuperação de senha) ficam
  registrados com quem, quando, de qual IP e se deu certo — num ponto só, na
  entrada da API, para nenhuma rota nova escapar. Senha, código e arquivo
  nunca entram. Só a administração consulta (menu **Auditoria**), não há como
  apagar pela API, e cada registro sai sozinho depois de 1 ano
  ([`backend/app/regras/auditoria.py`](backend/app/regras/auditoria.py)).
- **Cabeçalhos de segurança** em toda resposta, pela própria API
  ([`backend/app/infra/cabecalhos.py`](backend/app/infra/cabecalhos.py)):
  Content-Security-Policy nas telas (só script do próprio servidor — um XSS
  que escapasse não rodaria), proibição de abrir o site dentro de outro
  (clickjacking), `nosniff`, `Referrer-Policy` e `Permissions-Policy`. O
  Caddy acrescenta o HSTS.
- **Upload conferido pelo conteúdo:** além da extensão permitida e do limite
  de 15 MB, o começo do arquivo precisa ser do formato que a extensão diz (um
  programa renomeado para `.pdf` é recusado), e o nome no disco é sorteado.
- **Injeção de SQL e XSS:** todo valor vai ao banco como parâmetro; o React
  escapa todo texto, e o Markdown da IA vira elemento, nunca HTML.
- **Termos de uso** e **política de privacidade** públicos, em `/app/termos`
  e `/app/privacidade` (minutas para a instituição aprovar).

### O que é da infraestrutura, e não do código

Ficam com quem instala o servidor — o passo a passo da implantação aponta
cada um:

- **WAF e proteção contra DDoS:** um serviço na frente do Caddy (Cloudflare,
  por exemplo). A aplicação já se defende de SQLi e XSS e limita o login e o
  uso do modelo de IA, mas não segura uma enxurrada de tráfego.
- **Criptografia em repouso:** disco do servidor cifrado (LUKS). O sistema
  não guarda CPF, cartão nem dado financeiro — o que não existe não vaza.
- **Backup fora do servidor**, **antivírus** na pasta de uploads (ClamAV),
  **logs centralizados** (o systemd guarda os do serviço; a trilha de
  auditoria fica no banco) e **teste de invasão** feito por gente de fora.
- **Atualizações:** `npm audit` (hoje, 0 vulnerabilidades) e `pip-audit` a
  cada atualização das dependências, que têm versão presa.

## No celular

As mesmas telas, sem app à parte. Conferido num navegador com tamanho de
celular e de tablet (360, 390, 768 e 1280 px de largura), nas 34 telas dos
três perfis: nenhuma transborda para os lados.

- **Menu numa gaveta lateral:** no celular, uma barra fina com a logo e o
  botão **Menu**; o menu desliza da direita, sobre um fundo escurecido. Abre
  pelo botão ou puxando da borda direita da tela; fecha escolhendo um item,
  tocando fora, com Esc ou empurrando-a de volta. Aberto o tempo todo, o menu
  ocupava quase metade da tela antes do conteúdo. A partir do tablet, volta a
  ser a coluna da esquerda.
- **A logo leva ao início** do perfil, no celular e no computador.
- **Troca de tela com um esmaecer curto** (220 ms); quem pede menos
  movimento nas configurações do sistema não vê animação nenhuma.
- **Listas de escolha com a cara do produto:** no Chrome e no Edge (135 em
  diante) a lista aberta segue o tema (marca no item escolhido, grupos com
  rótulo); nos outros navegadores fica a lista do sistema, que no iPhone é a
  roda de seleção.
- **Cabeçalhos que quebram linha** (busca, seletores e botões), números do
  topo dois por linha, e o cartão de progresso do aluno empilhado.
- **Tabelas largas** (relatório mês a mês, auditoria) rolam de lado dentro do
  próprio cartão, sem quebrar a página.
- **PDF:** o Chrome do Android não mostra PDF dentro da página, e o iPhone
  mostra só a primeira folha. O visualizador tem **Abrir em outra aba**, que
  abre o leitor do próprio aparelho.
- O campo de código do login abre o teclado numérico.

## Acessibilidade

Auditada na Sprint 4, contra o WCAG 2.1 nível AA:

- **Contraste e cores da marca.** As cores são as da marca do hospital e não
  mudam. Onde não há texto pequeno em cima (logo, barras, gráficos, ícones,
  anel de foco), vale a cor **exata** da marca; em texto pequeno e botões, o
  mesmo matiz um pouco mais escuro, porque os tons originais não passavam em
  texto pequeno: o azul de links e botões (4,45:1), o cinza das descrições sobre o
  fundo (4,44), o vermelho das mensagens de erro (3,76), o verde (3,30) e o
  contorno dos campos (1,35, para um mínimo de 3). Cada um foi escurecido só
  até passar, no mesmo matiz. Um teste lê os tokens do
  [`frontend/src/index.css`](frontend/src/index.css) e confere os pares usados nas telas.
- **Teclado.** Anel de foco visível em tudo que recebe Tab, fora das camadas
  do Tailwind para nenhum `outline-none` apagá-lo, e o atalho **Pular para o
  conteúdo** antes do menu lateral.
- **Leitor de tela.** Todo campo tem rótulo ligado a ele; o idioma da página é
  `pt-BR`; os diálogos usam o `<dialog>` nativo (prende o foco, fecha com Esc)
  e têm nome; a resposta do assistente e as mensagens novas são anunciadas
  (`role="log"`), e o cronômetro do "consultando o material" não é lido a cada
  segundo; o título da aba muda com a página.
- **Auditoria automática.** Todas as telas dos três perfis e as públicas
  passaram pelo [axe-core](https://github.com/dequelabs/axe-core) (WCAG 2.1 A
  e AA e boas práticas), no computador e no celular: nenhuma violação. A
  auditoria achou e fez corrigir o nome da faixa e o selo "Urgente" com pouco
  contraste, a hora das mensagens enviadas, títulos que pulavam de nível,
  tabelas e gráficos que rolam de lado sem acesso pelo teclado e a conversa de
  Mensagens que não recebia foco para rolar.
- **O que ainda não foi feito:** o teste com leitor de tela real (NVDA) e
  com usuários com deficiência. O roteiro está pronto em
  [`validacao/TESTE_LEITOR_DE_TELA.md`](docs/validacao/TESTE_LEITOR_DE_TELA.md).

## Privacidade (LGPD)

**A administração acadêmica é a encarregada pelo tratamento de dados (DPO)**,
por decisão da instituição. O aluno exerce os direitos de titular pela tela
**Meus dados** (link no perfil); as regras estão em
[`backend/app/regras/privacidade.py`](backend/app/regras/privacidade.py), e a política
na tela pública **Privacidade e uso de dados**
([`frontend/src/paginas/publicas/Privacidade.jsx`](frontend/src/paginas/publicas/Privacidade.jsx)).

| Pedido | Quem decide | O que acontece |
|---|---|---|
| Cópia dos dados | ninguém — sai na hora | Arquivo JSON com cadastro, disciplinas, entregas e notas, acessos, favoritos, anotações, conversas e notificações. Fica registrado que foi entregue. |
| Apagar a conversa com o assistente | ninguém — no próprio chat | Some o texto das perguntas, das respostas e dos trechos citados daquela disciplina. Fica, sem conteúdo, o que já contava: o dia, se o material respondeu e o assunto (que o professor já via, sem nome) — o XP e os relatórios não mudam. Na pergunta fica só um hash, para apagar e perguntar de novo não pontuar duas vezes. |
| Correção (nome, e-mail, matrícula) | administração | A tela **Privacidade** mostra o valor de hoje ao lado do pedido; aprovado, troca na hora. |
| Exclusão da conta | administração | Aprovada, a conta é **desativada** (não entra, sessões encerradas, sai do ranking) e o aluno recebe e-mail. **45 dias depois** é anonimizada. Até lá, a administração pode reverter. |
| Exclusão pela administração (aluno ou professor que saiu) | administração, por conta própria | O mesmo caminho, já aprovado, com o **motivo registrado** (Usuários → Excluir). Professor com disciplina só sai com alguém para assumi-las: material, atividades e notas passam para o novo professor e continuam com os alunos. |

**Lacunas do material.** A conversa com o assistente é individual, mas quando
ele não encontra a resposta no material o professor vê o **assunto** da dúvida
(em poucas palavras, resumido pelo modelo) e quantos alunos perguntaram —
nunca o texto nem quem perguntou, e só a partir de dois alunos diferentes por
assunto ([`backend/app/regras/lacunas.py`](backend/app/regras/lacunas.py)). O aluno é
avisado disso no próprio chat e na política de privacidade.

A anonimização apaga nome, e-mail, matrícula, anotações, favoritos,
notificações e conversas (com o assistente e com os professores). Notas,
entregas, matrículas e acessos ficam, ligados a um "Aluno removido": é o
registro acadêmico que a instituição precisa guardar.

O professor apaga o próprio conteúdo (material, atividade, aviso); a
administração **não** despublica material de professor.

**Relatórios** mostram números da turma, nunca aluno identificado
([`backend/app/regras/relatorios.py`](backend/app/regras/relatorios.py)).

Antes de uso com dados reais, a instituição precisa aprovar formalmente a
política e publicar o contato da administração para assuntos de dados.

## Implantação

Um servidor Linux, com GPU se o modelo de IA rodar nele. Um processo só serve
a API **e** as telas (em `/app/`); na frente, o
[Caddy](https://caddyserver.com) cuida do HTTPS. Os arquivos estão em
[`deploy/`](deploy).

1. **Código e dependências**
   ```
   git clone <repositório> /opt/deltacare
   cd /opt/deltacare && python3 -m venv .venv
   .venv/bin/pip install -r backend/requirements.txt
   cd frontend && npm ci && npm run build
   ```
   O `npm run build` gera `frontend/dist/`, que a API entrega em `/app/`. Sem
   ele, `/app/` responde dizendo que as telas não estão compiladas. (Dá para
   compilar em outra máquina e copiar só o `frontend/dist/`: o servidor não precisa
   do Node para rodar, só para compilar.)
2. **Modelo de IA:** instale o [Ollama](https://ollama.com) no servidor (ele
   sobe como serviço) e baixe os dois modelos com
   `ollama pull gpt-oss:20b` e `ollama pull nomic-embed-text`. Sem GPU que
   comporte o `gpt-oss:20b`, use um menor e defina `MODELO_CHAT`. Se o Ollama
   cair, o resto do sistema segue; o chat avisa que o assistente está fora do
   ar, e o PDF publicado nesse meio-tempo aparece como "Fora do chat" para o
   professor indexar depois.
3. **Configuração:** copie `deploy/deltacare.env.exemplo` para
   `/etc/deltacare.env`, preencha (domínio, **SMTP — obrigatório**: é por ele
   que professor e administração recebem o código de acesso, pastas de dados) e
   `chmod 600 /etc/deltacare.env`. Crie a pasta dos dados
   (`/var/lib/deltacare`) com dono `deltacare`.
4. **Primeira conta de administração** (ela também entra com o código por
   e-mail, então o SMTP precisa estar certo antes):
   ```
   cd /opt/deltacare/backend
   set -a; . /etc/deltacare.env; set +a
   ../.venv/bin/python scripts/criar_admin.py
   ```
5. **Serviço:** copie `deploy/deltacare.service` para
   `/etc/systemd/system/` e `systemctl enable --now deltacare`. Um processo
   só, de propósito: o SQLite aceita um escritor por vez.
6. **HTTPS:** instale o Caddy, ponha o domínio no `deploy/Caddyfile`, copie
   para `/etc/caddy/Caddyfile` e `systemctl reload caddy`. O certificado sai e
   se renova sozinho.
7. **Rotinas diárias** (crontab do usuário `deltacare`):
   ```
   30 3 * * * cd /opt/deltacare/backend && set -a && . /etc/deltacare.env && set +a && ../.venv/bin/python scripts/backup.py >> /var/log/deltacare-backup.log 2>&1
   45 3 * * * cd /opt/deltacare/backend && set -a && . /etc/deltacare.env && set +a && ../.venv/bin/python scripts/anonimizar_vencidas.py >> /var/log/deltacare-lgpd.log 2>&1
   ```
   O `backup.py` copia o banco pela API do SQLite (cópia consistente com o
   sistema no ar), confere a cópia e guarda as últimas 14. **Leve as cópias
   para fora do servidor** — backup na mesma máquina não sobrevive ao disco.
   **Para restaurar:** pare o serviço (`systemctl stop deltacare`), apague
   `deltacare.db-wal` e `deltacare.db-shm` se existirem — sobram quando o
   servidor caiu, e deixados lá o SQLite aplicaria essas escritas antigas
   sobre o banco restaurado —, copie o `deltacare.db` e a pasta `uploads/` da
   cópia escolhida por cima dos atuais e suba o serviço de novo.
   O `anonimizar_vencidas.py` anonimiza as contas cuja exclusão passou dos 45
   dias; o servidor também faz isso ao subir e quando a administração abre a
   fila, e o agendamento cobre o servidor que fica meses no ar sem ninguém
   abrir a fila.
8. **Conferir:** `https://<domínio>/saude` responde `{"status": "ok"}`, e
   `https://<domínio>/` abre a tela de login. Peça o código de recuperação de
   senha para uma conta sua: se o e-mail não chegar, o SMTP está errado (o
   log do serviço diz o motivo).

**Atualizar:** backup, `git pull`, `pip install -r backend/requirements.txt`,
`npm ci && npm run build` em `frontend/` e `systemctl restart deltacare`. O banco
migra sozinho na subida.

## Testes

```
pip install -r backend/requirements-dev.txt   # uma vez: o que só os testes usam

cd backend
python testes/rodar_testes.py      # regras e rotas, em paralelo (~50s)
python testes/testes.py            # os mesmos, em série
python scripts/contrato_front.py   # toda chamada das telas tem rota no back?

cd ../frontend
npm test                           # telas React: rotas por perfil e componentes
npm run lint                       # regras do React (hooks, componentes)
```

- **Backend (606 testes):** permissões de cada perfil, visibilidade de
  material, sessão e limite de login, senha provisória, turmas e exceções,
  atividades e correção, XP e ranking, avisos, privacidade e anonimização,
  exclusão de conta pela administração e troca de professor, dois fatores,
  força da senha, trilha de auditoria, cabeçalhos de segurança, conteúdo dos
  uploads, relatórios
  (quem vê cada turma, mês da nota e do prazo, nenhum aluno identificado),
  integridade do banco ao excluir, a entrega das telas em `/app/` e o próprio seed. Rodam
  num banco temporário e **não precisam do Ollama** — as funções que falam
  com o modelo entram como parâmetro.
- **Telas React (71 testes):** as telas são renderizadas no Node, sem
  navegador, e o teste confere o HTML que sai. Cobre quem entra em qual rota
  (visitante, aluno, professor e administração — a matriz das rotas
  públicas e privadas —, e a senha provisória, que só abre a tela de
  troca), que todo item de menu leva a uma tela que existe,
  que HTML vindo da IA aparece como texto e não vira elemento, o cartão de
  progresso, o Markdown, a leitura de datas digitadas, os links das
  notificações, o atalho "Pular para o conteúdo", o **contraste das cores
  do tema** (lido do `index.css`) e que toda janela tem nome para o leitor
  de tela.
- **Contrato front↔back:** lê as chamadas à API das telas React e confere
  com as rotas do backend, verbo incluído — inclusive as
  feitas por atalhos da tela (`chamar(...)`) e por caminho guardado em
  variável. Pega a tela que chama uma rota que não existe antes de alguém
  clicar.

## Validação de usabilidade

**Situação: piloto feito em 02/10/2026; sessões com participantes ainda não
realizadas.** Pelo menos três participantes
de fora da equipe (estudantes, de preferência da área da saúde) fazem nove
tarefas do dia a dia do aluno, pensando em voz alta. As tarefas vão do
primeiro acesso, passando por achar o aviso, ler a aula, perguntar ao
assistente e entregar o quiz, até baixar a cópia dos próprios dados. Ao final,
respondem ao questionário SUS. Antes delas, uma sessão piloto com um
integrante ensaia o roteiro e não entra na conta.

Medimos o sucesso e o tempo por tarefa, os problemas encontrados (com
gravidade de 0 a 4) e a nota SUS. As sessões rodam num banco separado
(`DELTACARE_DB=validacao.db`), com uma conta fictícia por participante.
Ninguém é identificado no registro.

Tudo em [`docs/validacao/`](docs/validacao/README.md): o plano, o
[roteiro](docs/validacao/ROTEIRO.md) com a preparação da máquina, a
[ficha de observação](docs/validacao/FICHA_DE_OBSERVACAO.md), o
[termo de consentimento](docs/validacao/TERMO_DE_CONSENTIMENTO.md), o
[questionário SUS](docs/validacao/QUESTIONARIO_SUS.md) e os
[resultados](docs/validacao/RESULTADOS.md), preenchidos depois das sessões.

## Estrutura

```
backend/                   - a API (Python). Rode tudo de dentro desta pasta:
                             o banco (deltacare.db) e uploads/ ficam aqui
  requirements.txt
  app/                     - o sistema
    main.py                  rotas, perfis e middlewares; entrega as telas em /app/

    infra/                   o que o sistema USA
      database.py              esquema, migrações e caminho único do banco
      sessoes.py               token de sessão
      security.py              hash de senha (PBKDF2)
      email.py                 envio por SMTP, em segundo plano
      arquivos.py              gravação dos uploads
      vetores.py               os vetores do chat em binário, normalizados
      cabecalhos.py            cabeçalhos de segurança (CSP, clickjacking...)

    regras/                  o que o sistema DECIDE
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
      relatorios.py            a turma ao vivo e por mês; dificuldade por disciplina
      senhas.py                a régua de toda senha nova
      auditoria.py             a trilha de auditoria
      importacao.py            planilha CSV/XLSX
      chat_ia.py               RAG: indexação, busca híbrida e resposta

  scripts/                 - o que se roda à mão ou agendado
    seed_demo.py             dados de demonstração (chama o seed_semestre.py)
    seed_semestre.py         o semestre de demonstração completo
    material_demo.py         os PDFs de exemplo: medicina de verdade, com referências
    criar_admin.py           primeiro admin numa instalação nova
    backup.py                cópia conferida do banco e dos arquivos enviados
    anonimizar_vencidas.py   LGPD: anonimiza exclusões vencidas (1x por dia)
    contrato_front.py        confere as chamadas das telas contra as rotas
    _app.py                  põe app/ no caminho de import dos scripts

  testes/
    testes.py                testes do backend
    rodar_testes.py          os mesmos testes, em paralelo

frontend/                  - as telas (React), entregues pela API em /app/
  src/App.jsx                todas as rotas, públicas e privadas
  src/rotas/                 RotaPrivada (perfil certo, ou volta ao login)
  src/sessao/, src/dialogos/ Contexts da sessão e dos diálogos
  src/hooks/                 useSessao, useApi, useDialogo, useApagarAnotacao, useTituloDaPagina, useEnvio
  src/layout/                Painel (menu, sino, perfil) e o menu de cada perfil
  src/componentes/           peças reutilizadas: Cartao, Botao, Modal, Visualizador...
  src/paginas/               aluno/, professor/, admin/, comum/ (as telas que
                             dois perfis dividem) e publicas/ (login, privacidade)
  src/lib/                   o que não é tela: API, datas, Markdown, formatos
  src/index.css              o tema do Tailwind (o design system)
  testes/                    as telas renderizadas no Node, sem navegador

docs/                      - tutorial, arquitetura, roteiro da apresentação,
                             entregas das Sprints 3 e 4 e validacao/ (teste de
                             usabilidade: plano, roteiro, ficha, termo, SUS e
                             resultados)

deploy/                    - serviço systemd, Caddyfile e modelo de configuração
```

A pasta de páginas da administração chama-se `admin`, mas o `tipo` no banco é
`adm` — os dois já estiveram trocados no front antigo e quebraram o
redirecionamento do login. No React, a ligação entre os dois fica num lugar
só (`INICIO_DO_PERFIL`, em `frontend/src/lib/usuario.js`).

## Limitações conhecidas

- **SQLite aceita um escritor por vez:** aguenta uma faculdade (60 entregas
  simultâneas se enfileiram em ~2s), não uma rede de faculdades.
- **HTTPS depende do Caddy.** Rodando o uvicorn direto numa rede, o token
  viaja em texto claro.
- **A implantação (systemd e Caddy) ainda não rodou num servidor real.**
- Arquivos enviados ficam no disco do servidor, não num serviço de storage.
- O chat indexa só PDF (vídeo e link ficam de fora).
- **A busca do chat percorre todos os trechos** a cada pergunta, em Python:
  190 ms com 30 PDFs, 570 ms com 100 (medido, vetores de 768 dimensões). No
  modo automático, são os trechos de todas as disciplinas do aluno. Serve a um
  curso; um acervo muito maior pediria um índice vetorial (`sqlite-vec` ou
  `pgvector`).
- **No modo automático, a pergunta que nenhum material respondeu não vai para
  as Lacunas de professor nenhum** — não há como saber de qual disciplina ela
  era sem chutar. Quem quer que o professor veja escolhe a disciplina.
- Professor e administração não têm a tela Meus dados: os pedidos deles sobre
  dados pessoais seguem pela secretaria.

## Documentos relacionados

- [`docs/SPRINT_4.md`](docs/SPRINT_4.md) — entrega da Sprint 4: requisitos e onde
  estão, backlog, decisões de experiência, validação de usabilidade e
  retrospectiva.
- [`docs/SPRINT_3.md`](docs/SPRINT_3.md) — entrega da Sprint 3: backlog com as user
  stories e critérios de aceite, decisões de experiência, incremento e
  retrospectiva.
- [`docs/validacao/`](docs/validacao/README.md) — teste de usabilidade da Sprint 4:
  plano, roteiro, ficha, termo, SUS e resultados.
- [`docs/TUTORIAL.md`](docs/TUTORIAL.md) — como usar a plataforma, perfil por perfil.
- [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) — diagramas, fluxo de autenticação, RAG,
  modelo de dados e matriz de permissões.
- [`docs/ROTEIRO_DEMO.md`](docs/ROTEIRO_DEMO.md) — passo a passo da apresentação, com as
  perguntas a fazer no chat e plano B se algum serviço cair.
