# Roteiro de demonstração — Delta Care

Passo a passo fixo para a apresentação. A ideia é não improvisar: cada tela
tem um objetivo, e a ordem foi montada para a banca ver o ciclo inteiro — a
administração organiza, o professor publica, o aluno estuda com o assistente,
e o que o assistente não soube responder volta para o professor.

**Duração estimada:** 12 a 15 minutos.

---

## Antes de começar (20 minutos antes)

### Um banco só para a apresentação

O banco do dia a dia acumula testes e perguntas soltas. Para a banca ver
exatamente o que este roteiro descreve, use um banco novo. No PowerShell, na
pasta `backend`:

```
$env:DELTACARE_DB = "apresentacao.db"
$env:DELTACARE_UPLOADS = "uploads/apresentacao"
python seed_demo.py
uvicorn main:app
```

As variáveis valem só nessa janela: deixe-a aberta. O seed monta o semestre
inteiro (turma MED 3A, três disciplinas, professores, oito alunos, atividades,
entregas, avisos, uma denúncia e um pedido de LGPD).

### Conferir

- [ ] O Ollama está no ar: `ollama list` mostra `gpt-oss:20b` e
      `nomic-embed-text`.
- [ ] As telas estão compiladas com a versão atual: `cd web` e
      `npm run build` (a API entrega o que está em `web/dist`).
- [ ] <http://127.0.0.1:8000/saude> responde `{"status":"ok"}`.
- [ ] <http://127.0.0.1:8000/> abre a tela de login (redireciona para
      `/app/`).

### Preparar a tela de Lacunas

A tela **Lacunas do material** só mostra um assunto quando **dois alunos
diferentes** perguntaram sobre ele (para não expor ninguém). Na apresentação,
só a Marina pergunta; então dois colegas dela perguntam antes:

1. Entre como `lucas.martins@deltacare.com` / `demo123` → **Chat de estudos**
   → **Cardiologia I** → pergunte *Quando usar a dobutamina e qual a dose?* Saia.
2. Mesma coisa com `ana.rocha@deltacare.com`.
3. Entre como `professor@deltacare.com` → **Lacunas do material**. Deve
   aparecer **dobutamina** com 2 alunos. Saia.

Isso também tira o tempo de carregar o modelo da frente da banca: a primeira
resposta do dia demora mais (o modelo sobe para a memória); as seguintes
levam de 10 a 30 segundos.

Se a dobutamina não aparecer em Lacunas, o modelo considerou a resposta
completa nas duas vezes. Pergunte de novo com um terceiro aluno
(`gabriel.teixeira@deltacare.com`).

**Contas** (senha `demo123`): `adm@deltacare.com` (Helena Prado),
`professor@deltacare.com` (Ricardo Salles, Cardiologia I),
`aluno@deltacare.com` (Marina Duarte).

Use uma **janela anônima** do navegador e deixe-a em tela cheia.

---

## Parte 1 — Administração (2 min)

**Objetivo:** mostrar que existe controle institucional, não é um app solto.

1. Login como `adm@deltacare.com`.
2. No início, aponte **Esperando a administração**: uma denúncia de conteúdo e
   um pedido de correção de dados. "Nada aqui é dado de exemplo: são registros
   do banco."
3. **Turmas → MED 3A.** Mostre os alunos e as três disciplinas. Aponte o
   **Pedro Albuquerque**, fora de Fisiologia.
   **Frase-chave:** "Quem entra na turma é matriculado em todas as
   disciplinas dela. O Pedro já cursou Fisiologia em outra faculdade: é uma
   exceção, um clique, e ele sai só dessa."
4. **Usuários → Nova conta.** Mostre o formulário e o campo **Senha
   provisória** (não precisa criar).
   **Frase-chave:** "Toda conta nasce aqui ou pela planilha; não existe
   cadastro público. E a senha que a secretaria define é provisória: no
   primeiro acesso, a pessoa é obrigada a trocar, e o servidor não deixa usar
   nada antes disso."
5. **Auditoria.** Mostre o login que você acabou de fazer e a conta que
   abriu na tela de Usuários, se criou.
   **Frase-chave:** "Toda ação da administração e todo acesso ficam
   registrados: quem, quando, de onde. Senha nunca. E, numa conta de verdade,
   professor e administração entram com um código no e-mail — a conta da
   demonstração dispensa só para a apresentação."
6. **Privacidade.** Mostre o pedido do Rafael para corrigir o nome. Aprove.
   **Frase-chave:** "LGPD não é uma página de política: o aluno baixa uma
   cópia dos próprios dados na hora, e pede correção ou exclusão por aqui. A
   exclusão desativa a conta na hora e anonimiza em 45 dias."

---

## Parte 2 — Professor (2 min)

**Objetivo:** o fluxo de quem alimenta a plataforma.

1. Saia e entre como `professor@deltacare.com`.
2. No início, aponte **Para corrigir** (o relatório do Lucas) e **Mensagens**
   (uma pergunta da Ana sem resposta). É o que o professor tem a fazer hoje.
3. **Materiais.** Mostre a *Aula 3 - Insuficiência Cardíaca Aguda*, o PDF
   publicado. Abra **Novo material** e mostre os três estados: **rascunho**,
   **agendado** e **publicado**.
   **Frase-chave:** "O aluno só enxerga o que está publicado. Rascunho e
   agendado são invisíveis para ele — e para o assistente de IA, que não lê
   material não liberado."

Não abra Lacunas ainda: ela fecha a apresentação.

---

## Parte 3 — Aluno (5 min, o ponto alto)

**Objetivo:** o diferencial do produto.

1. Saia e entre como `aluno@deltacare.com`.
2. No início, aponte o **nível e a faixa** do semestre (bronze, prata, ouro,
   platina) e o aviso urgente **Prova antecipada**.
3. Abra o **Chat de estudos**, em **Cardiologia I**, e faça as três perguntas
   na ordem:

   **a) Pergunta que o material responde**
   > Quais são os quatro perfis de Stevenson e a conduta de cada um?

   Costuma vir em lista ou tabela. Aponte a fonte citada abaixo da resposta,
   a Aula 3.
   **Frase-chave:** "Cada resposta diz de qual aula saiu: o aluno confere no
   PDF que o professor publicou. É material de verdade, com as referências no
   fim de cada aula."

   **b) Pergunta que o material responde só em parte**
   > Quando usar a dobutamina e qual a dose?

   A Aula 3 diz quando usar (hipotensão, com sistólica abaixo de 90 mmHg, e
   sinais de hipoperfusão), mas não a dose. O assistente traz o que tem e
   mostra, abaixo, **"O material não traz:"** o que faltou.
   **Frase-chave:** "O modelo sabe uma dose de dobutamina de memória. Ele não
   a dá, porque não está no material que o professor validou — e também não
   joga fora o que o material tem. Diz o que sabe e o que falta."

   **c) Pergunta fora do material**
   > Qual o tratamento cirúrgico da apendicite?

   Ele **recusa**, sem nenhuma fonte, e a plataforma oferece levar a dúvida a
   um professor.
   **Frase-chave:** "O modelo sabe responder sobre apendicite. Ele se recusou
   porque não está no material que o professor liberou. É isso que separa
   esta ferramenta de um ChatGPT genérico: o aluno não estuda por uma fonte que
   o professor não validou."

---

## Parte 4 — De volta ao professor (2 min, o fecho)

**Objetivo:** mostrar que a recusa não é o fim da linha.

1. Saia e entre como `professor@deltacare.com`.
2. Abra **Lacunas do material**. **dobutamina** aparece com 3 alunos e, em
   "o que falta", o que eles queriam saber: a dose.
3. **Frase-chave:** "O que o assistente não soube responder vira pauta para o
   professor: o que a turma está perguntando e o material não cobre. Sem
   nome de aluno e sem o texto da pergunta — e só quando pelo menos dois
   alunos perguntaram, para ninguém ser identificado. O professor completa o
   material e marca 'Já tratei'."

Se a pergunta (b) da Marina veio como resposta completa, aparecem 2 alunos em
vez de 3. A fala é a mesma.

**Se sobrar tempo (1 min):** entre como `adm@deltacare.com` →
**Relatórios** → **Dificuldade por disciplina**.
**Frase-chave:** "A coordenação vê em que disciplina a turma tem mais
dificuldade — a nota, as entregas que faltam, o que o material não respondeu
e o tópico com mais erro, cada um com o seu número. Sem nome de aluno." Na
aba **Ao vivo**, a pergunta que a Marina acabou de fazer já aparece.

---

## Se perguntarem

**"Os dados vão para a OpenAI?"**
Não. O modelo roda localmente, via Ollama. Nenhum material de aula e nenhuma
pergunta de aluno sai da infraestrutura da instituição — o que importa para a
LGPD.

**"E se ele inventar uma resposta?"**
Três travas. O prompt restringe ao material e proíbe deduzir; o assistente
declara se o material cobriu a pergunta por inteiro, em parte ou nada; e as
fontes são validadas pelo sistema: o modelo só consegue citar um material que
realmente foi recuperado na busca, porque o formato da resposta é imposto no
decodificador, não pedido em texto.

**"Por que ele não me mandou para a disciplina certa?"**
Já mandou, e errava: a plataforma adivinhava pela palavra da pergunta, e no
teste piloto mandou uma dúvida de crânio para Cardiologia. Caminho errado é
pior que nenhum. Hoje a pergunta vai pronta para Mensagens, e o aluno escolhe
o professor.

**"É seguro?"**
Toda rota descobre quem está chamando pelo token da sessão; nenhuma aceita a
identidade que o navegador informa. Professor e administração entram com a
senha e um código no e-mail (as contas da demonstração dispensam o código).
Senha de 8 caracteres ou mais, recusando as conhecidas; limite de tentativas
no login; trilha de auditoria de toda ação administrativa e de todo acesso;
Content-Security-Policy contra XSS; upload conferido pelo conteúdo; HTTPS
pelo Caddy na implantação. O que é de infraestrutura (WAF, DDoS, backup fora
do servidor) está no README, em "Segurança".

**"Isso escala para a faculdade inteira?"**
Uma faculdade, sim: o SQLite enfileira 60 entregas simultâneas em cerca de 2
segundos. Uma rede de faculdades pede trocar o SQLite por Postgres, o Ollama
por um servidor que atenda várias perguntas em paralelo (vLLM) e o disco por
storage. O README tem o levantamento em "Limitações conhecidas".

**"Por que demora alguns segundos?"**
O modelo roda numa GPU de desenvolvimento. Enquanto ele pensa, a tela mostra
um cronômetro, e as outras telas e o login continuam respondendo.

**"Por que React?"**
Exigência da Sprint 4, e ela pagou: as telas que antes se repetiam em 33
páginas viraram componentes (o menu, por exemplo, é uma lista só), e as rotas
públicas e privadas ficaram num arquivo. A validação de usabilidade com
participantes de fora está em [`validacao/`](validacao/README.md).

---

## Se precisar consultar

O [TUTORIAL.md](TUTORIAL.md) descreve cada tela, perfil por perfil — útil se a
banca pedir para ver algo fora do roteiro.

## Plano B

**O Ollama caiu ou está muito lento:** o chat responde "O assistente de IA está
indisponível no momento" em vez de quebrar. Mostre o histórico da conversa já
salvo e a tela de Lacunas preparada antes, e siga com o resto, que não depende
do modelo.

**Alguma tela não carrega:** `Ctrl+Shift+R`. Se persistir, confira se a janela
do uvicorn continua aberta e se `/saude` responde.

**A resposta veio sem tabela:** variação normal do modelo, não é erro. O
conteúdo está certo do mesmo jeito.

**Terminou a apresentação:** feche a janela do uvicorn. Na próxima vez que
subir o backend numa janela nova, ele volta ao banco do dia a dia
(`deltacare.db`).
