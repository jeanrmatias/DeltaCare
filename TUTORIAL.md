# Como usar o Delta Care

Guia de uso da plataforma, perfil por perfil. Para instalar e rodar o sistema,
veja o [README](README.md).

**Contas de demonstração** (criadas pelo `backend/seed_demo.py`, senha
`demo123`):

| Perfil | E-mail | Quem é |
|---|---|---|
| Administração | `adm@deltacare.com` | Helena Prado |
| Professor | `professor@deltacare.com` | Ricardo Salles, Cardiologia I |
| Aluno | `aluno@deltacare.com` | Marina Duarte, turma MED 3A |

O seed cria também outros professores e alunos (`beatriz.lemos@`,
`lucas.martins@`…, todos `@deltacare.com`).

---

## Antes de tudo

### Turma e disciplina

- **Turma** é o grupo de alunos que cursa o semestre junto (ex.: MED 3A).
- **Disciplina** é a matéria (ex.: Cardiologia I): um professor, o material
  dele e um chat de estudos próprio.

Uma turma tem várias disciplinas. Quem entra na turma é matriculado em todas
elas, menos nas que a administração marcar como exceção.

### Quem faz o quê

Cada perfil enxerga só o que lhe cabe, e não é a tela que esconde: o servidor
confere a permissão a cada requisição.

| | Administração | Professor | Aluno |
|---|---|---|---|
| Criar contas, turmas e disciplinas | ✅ | — | — |
| Matricular aluno | ✅ | — | — |
| Publicar material e atividade | — | ✅ nas disciplinas dele | — |
| Ver material publicado | ✅ supervisão | ✅ os próprios | ✅ das disciplinas dele |
| Perguntar ao assistente de IA | — | — | ✅ |
| Escrever aviso | ✅ instituição ou disciplinas | ✅ as disciplinas dele | — |
| Ler anotações, entregas e conversas do aluno | ❌ nunca | só as entregas, para corrigir | ✅ as próprias |

A ordem natural de uso é: **a administração prepara → o professor alimenta →
o aluno estuda.** É essa ordem que este tutorial segue.

### Primeiro acesso

A conta chega com uma **senha provisória**, definida pela secretaria. No
primeiro login, a plataforma pede uma senha nova antes de mostrar qualquer
outra tela: a provisória às vezes é a mesma para a turma inteira e não pode
continuar valendo.

Depois disso, a senha se troca no perfil — **Ver perfil**, embaixo do menu
lateral → **Alterar senha**. A troca pede a senha atual e encerra as outras sessões
abertas da conta.

**Esqueci minha senha:** na tela de login. Chega um código por e-mail, válido
por 15 minutos.

---

## 1. Administração

Entre com `adm@deltacare.com`.

### Início

Os números da instituição (professores, disciplinas, materiais) e o que está
**esperando a administração**: denúncias abertas e pedidos de alunos sobre
dados pessoais.

### Turmas

Menu → **Turmas**.

1. **Nova turma:** nome e semestre (ex.: MED 3A, 2026/2).
2. Abra a turma e **adicione os alunos**. Cada um entra em todas as
   disciplinas da turma.
3. **Exceções:** cada aluno tem uma fileira com as disciplinas da turma. Um
   clique tira o aluno de uma delas (aproveitamento de estudos, por exemplo) e
   outro devolve.

Na mesma tela fica o **semestre vigente**. Virar o semestre muda o que conta
como "atual" no XP, no ranking e nas listas; o que passou vai para
**Semestres anteriores**, sem apagar nada.

### Disciplinas

Menu → **Disciplinas**. Cada disciplina tem um professor e um semestre. Ao
apontá-la para uma turma, os alunos dessa turma já entram matriculados.

**Trocar professor** passa a disciplina para outro professor (licença, saída,
redistribuição), com o material e as atividades dela — inclusive as entregas
por corrigir. O professor anterior perde o acesso; o novo é avisado pelo sino.

> **Excluir uma disciplina apaga junto** o material dela, os trechos
> indexados para o assistente, as matrículas, as atividades e entregas, as
> mensagens com o professor, as conversas com o assistente e as lacunas. Não
> há como desfazer.

### Usuários

Menu → **Usuários** → **Nova conta**: nome, perfil, e-mail e senha
provisória. Para aluno, dá para informar a matrícula e já matricular numa
disciplina; para professor, as disciplinas que ele leciona.

**Importar planilha** (.csv ou .xlsx) cria várias contas de uma vez. Precisa
de uma coluna de nome e uma de e-mail; matrícula é opcional, e o cabeçalho pode
estar escrito de vários jeitos ("Nome Completo", "Aluno", "E-mail", "RA").

1. **Conferir planilha:** lê e valida **sem gravar nada**, e mostra quantas
   linhas estão prontas e quais foram recusadas, com o motivo.
2. **Importar:** cria as contas com a senha provisória escolhida (a mesma
   para todos) e, se quiser, matricula todos numa disciplina.

> **Por que o aluno não se cadastra sozinho?** Quem é aluno da faculdade é a
> secretaria que decide, não quem preenche um formulário. Toda conta nasce
> aqui ou pela planilha.

**Excluir** (em cada conta de aluno ou professor) é para quem deixou a
instituição. Peça o **motivo**, que fica registrado:

- A conta para de entrar na hora, e a pessoa recebe um e-mail.
- Em **45 dias** os dados pessoais são anonimizados; notas, entregas e o
  material publicado ficam, sem identificação.
- Até lá, **Desfazer exclusão** devolve a conta (a pessoa entra com a senha de
  antes). A exclusão também aparece em **Privacidade**.
- **Professor com disciplina** só sai com alguém para assumi-las: escolha o
  professor na própria janela. As disciplinas não voltam sozinhas se a
  exclusão for desfeita — use **Trocar professor** em Disciplinas.

### Avisos

Menu → **Avisos**. Escreva para a instituição inteira ou para disciplinas
específicas. Marcado como **urgente**, o aviso fica no topo do mural por 7
dias. Quem recebe é avisado pelo sino.

### Denúncias

Menu → **Denúncias**. Material reportado por alunos e professores, com o
motivo. Mude o status (em análise, concluída, arquivada) e registre o que foi
feito: **quem reportou é avisado** da resposta.

### Conteúdo

Menu → **Conteúdo**. Supervisão do que as disciplinas recebem: material e
atividades publicados ou agendados, inclusive o gabarito das objetivas. Só
leitura. Rascunho de professor não aparece, e entregas, anotações e conversas
de aluno nunca aparecem aqui.

### Privacidade

Menu → **Privacidade**. Pedidos dos alunos sobre os próprios dados (LGPD):

- **Correção** (nome, e-mail, matrícula): aprove, e o dado muda; ou recuse,
  com um motivo que o aluno vai ler.
- **Exclusão:** aprovada, a conta é desativada na hora e **anonimizada em 45
  dias**. Até lá dá para reverter (o aluno que trancou e voltou, ou foi
  transferido de turma).

A cópia dos dados não passa por aqui: o aluno baixa sozinho.

### Relatórios

Menu → **Relatórios**. Escolha a turma no topo. Nenhum número tem nome de
aluno.

- **Ao vivo:** quantos alunos estudaram na última hora e nas últimas 24 horas
  (material aberto, pergunta ao assistente, entrega), as atividades em aberto
  com quantos já entregaram, e o que acabou de acontecer. Atualiza sozinho a
  cada 30 segundos.
- **Por mês:** aproveitamento (nota sobre pontos), entregas no prazo,
  atrasadas e não entregues, alunos ativos, dias de estudo, XP médio,
  perguntas ao assistente e quanto o material respondeu. Dá para ver a turma
  inteira ou uma disciplina, e **Baixar planilha (CSV)** abre no Excel. Embaixo,
  como cada número é calculado.
- **Dificuldade por disciplina:** as disciplinas do semestre, da de menor
  aproveitamento para a de maior. Ao lado de cada uma: quantos alunos estão
  abaixo de 60%, quanto das entregas falta, quanto das perguntas o material
  não respondeu e o tópico com mais erro. Os sinais ficam separados de
  propósito — uma disciplina pode ter nota boa e metade das entregas faltando.
  Com poucas notas corrigidas, a disciplina avisa.

---

## 2. Professor

Entre com `professor@deltacare.com`.

### Início

O que você tem a fazer hoje: **entregas para corrigir**, **mensagens** de
alunos sem resposta e **o que falta no material** (ver Lacunas, abaixo). Além
das suas disciplinas e dos materiais recentes.

Você não cria disciplinas: isso é da administração. Se não aparecer nenhuma,
fale com a coordenação.

### Materiais

Menu → **Materiais** → **Novo material**.

Marque **em quais disciplinas** o material entra (dá para várias de uma vez),
preencha o título e escolha o tipo:

| Tipo | O que enviar |
|---|---|
| **PDF** | Arquivo, até 15 MB |
| Documento | Arquivo |
| Vídeo | Arquivo |
| Link | Endereço começando com `http://` ou `https://` |

**Assunto, tópico, aula e semestre** são opcionais, mas é por eles que o aluno
filtra depois.

Quando o material fica visível:

- **Rascunho:** só você vê.
- **Publicar:** o aluno vê na hora, e o sino avisa.
- **Publicar com data de liberação:** invisível até a data e hora, e aparece
  sozinho quando ela chega.

> **Só o PDF alimenta o assistente de IA.** Ao publicar um PDF, o texto é
> extraído e indexado, e o aluno já pode perguntar sobre ele. Vídeo e link o
> assistente não lê. Disciplina que só tem link e vídeo não tem como ter
> resposta do assistente — a tela de Lacunas avisa quando isso acontece.

**Fora do chat:** se o PDF não pôde ser indexado (o assistente estava fora do
ar na publicação, ou o PDF é escaneado e não tem texto), a plataforma avisa na
hora, e o material aparece na lista com o selo **Fora do chat** e o botão
**Indexar para o chat**. Escaneado continua fora: o assistente só lê PDF com
texto.

Você só edita e exclui o material que você mesmo criou.

### Atividades

Menu → **Atividades** → **Nova atividade**.

- **Objetiva:** questões de múltipla escolha. A nota sai na hora, comparando
  com o gabarito — que nunca é enviado ao navegador do aluno.
- **Dissertativa:** o aluno escreve a resposta e, se você permitir, anexa um
  arquivo (nenhum, opcional ou obrigatório). A nota e a devolutiva são suas.

Prazo, pontos, assunto e tópico são da atividade. **Entrega atrasada é aceita
e marcada como atrasada**, não recusada: quem decide o que fazer com ela é
você.

Para corrigir: abra a atividade, escolha a entrega, dê a nota e escreva a
devolutiva. O aluno é avisado.

### Calendário

O semestre por data: material publicado, material agendado, atividade
liberada e **prazo de entrega**. Serve para ver, antes dos alunos reclamarem,
que duas entregas caíram no mesmo dia.

### Chat

Menu → **Chat**. As conversas com os alunos, uma por aluno e disciplina. É
para cá que vêm as dúvidas que o assistente não respondeu.

### Desempenho

Como a turma está indo e, principalmente, **qual tópico** ela mais erra nas
atividades corrigidas — a informação que muda a próxima aula. Disciplina sem
atividade corrigida mostra isso, em vez de gráfico de zeros.

### Lacunas do material

O que os alunos perguntam ao assistente e o seu material **não responde**, ou
responde só em parte, agrupado por assunto. Por exemplo: *"Cardiolex — o
material cita, mas não diz o que é; 4 alunos"*.

- Você **nunca** vê o texto da pergunta nem quem perguntou.
- Um assunto só aparece quando **pelo menos dois alunos diferentes**
  perguntaram, para ninguém ser identificado.
- Depois de completar o material, marque **Já tratei**: o assunto sai da
  lista e só volta se alguém perguntar de novo.

Perguntas feitas numa disciplina sem nenhum PDF aparecem à parte, com um aviso
para publicar material.

### Relatórios

O mesmo da administração (ao vivo e por mês), só com as **suas** disciplinas
dentro da turma. A dificuldade por disciplina é da administração; para saber
de um aluno, use **Desempenho**.

### Avisos, Denúncias e Semestres anteriores

- **Avisos:** escreva para uma, várias ou todas as suas disciplinas.
- **Denúncias:** reporte um material com problema e acompanhe a resposta da
  administração.
- **Semestres anteriores:** o material das disciplinas que já terminaram.

---

## 3. Aluno

Entre com `aluno@deltacare.com`.

### Início

Seu progresso no semestre: **nível**, **faixa** (Bronze, Prata, Ouro,
Platina) e quanto falta para a próxima, sequência de dias estudando e o
gráfico dos últimos 14 dias. Abaixo, o mural de avisos, suas disciplinas e os
materiais recentes.

**De onde vem o XP** (150 XP por nível):

| Ação | XP |
|---|---|
| Pergunta ao assistente respondida pelo material | 5 (até 5 por dia; repetir a mesma não conta) |
| Abrir um material pela primeira vez | 15 |
| Dia com atividade na plataforma | 25 |
| Entregar uma atividade | 20 |
| Nota da atividade | até 30, proporcional ao acerto |

O nível e a faixa são do **semestre**: no seguinte, todo mundo recomeça, e o
XP dos semestres anteriores aparece como total.

### Sino e avisos

O sino avisa material e atividade novos, nota lançada, mensagem do professor,
resposta de denúncia ou de pedido sobre seus dados, e avisos dos professores e
da coordenação. Clicar leva até o que mudou. Os avisos ficam no
mural da tela inicial; os urgentes, no topo.

### Materiais

Tudo que os professores liberaram nas suas disciplinas, com filtros por
disciplina, assunto, tópico, tipo e período.

- **Visualizar** abre o material dentro da plataforma (PDF, imagem, vídeo,
  áudio). Formato que o navegador não exibe, como .docx, só com **Baixar**.
- **Favoritar** (a estrela) guarda o material em **Favoritos**, que valem
  entre semestres.
- **Anotações:** escreva sobre o material e, se quiser, cole o trecho a que a
  nota se refere. **Só você lê** — nem o professor, nem a administração. Todas
  ficam juntas em **Anotações**.
- **Reportar:** material com erro, arquivo que não abre, conteúdo
  inadequado. Você acompanha a resposta em **Denúncias**.

> Material que o professor citou em aula e não aparece aqui ainda está como
> rascunho ou agendado para outra data.

### Chat de estudos

Escolha a disciplina no topo e escreva sua dúvida.

**O que torna esse assistente diferente:** ele responde **apenas** com base
no material que o professor publicou naquela disciplina. O que não está no
material, ele não responde — mesmo que o modelo soubesse.

A resposta pode vir de três jeitos:

- **Completa:** com a fonte (o material usado) embaixo.
- **Em parte:** o material fala do assunto, mas não responde exatamente o que
  você perguntou. Ele traz o que o material tem e mostra **"O material não
  traz:"** o que faltou.
- **Não coberta:** uma frase dizendo isso, sem fonte. A plataforma oferece
  levar a dúvida a um professor: a pergunta vai pronta para **Mensagens**, e
  você escolhe a conversa.

O que o material não cobriu chega ao professor como **lacuna** — sem o seu
nome e sem o texto da pergunta.

A resposta leva de 10 a 30 segundos, porque o modelo roda na própria
instituição. Enquanto isso, aparece um cronômetro; **Parar** interrompe. O
histórico fica salvo por disciplina.

#### Como perguntar bem

- **Pergunte na disciplina certa.** O assistente só lê o material da
  disciplina escolhida no topo.
- **Seja específico.** "Qual a dose inicial de Cardiolex?" funciona melhor que
  "fala sobre medicamentos".
- **Use o termo exato** (nome do protocolo, da escala, do medicamento): a
  busca dá peso a siglas, códigos e números.
- **Uma pergunta de cada vez.**
- **Confira a fonte.** É por onde você continua o estudo.

### Atividades

Os quizzes e trabalhos das suas disciplinas, com prazo e situação. O progresso
fica salvo: dá para fechar a aba e voltar depois. A **objetiva** mostra a nota
na hora; a **dissertativa** espera a correção do professor, e o sino avisa
quando ela sai. Entrega depois do prazo é aceita, marcada como atrasada.

### Desempenho

Suas notas, sua evolução e em que assunto você mais erra, por disciplina e
por tópico.

### Mensagens

Uma conversa com o professor de cada disciplina.

### Ranking

A sua turma, pelo XP do semestre. Só os 10 primeiros aparecem para todos; a
sua posição, só você vê, onde quer que esteja. Também tem **quem mais evoluiu**
nos últimos 7 dias. Se não quiser aparecer, desligue: você continua na sua
posição, mas como "colega que preferiu não aparecer".

### Semestres anteriores

O material das disciplinas que você já cursou, com **busca dentro dos PDFs**.

### Meus dados

**Ver perfil** (embaixo do menu lateral) → **Meus dados**:

- **Baixar uma cópia** de tudo que a plataforma guarda sobre você — na hora,
  sem pedir a ninguém.
- **Pedir correção** de nome, e-mail ou matrícula.
- **Pedir exclusão** da conta. Aprovada pela administração, a conta é
  desativada na hora e anonimizada em 45 dias.

---

## Perguntas frequentes

**Fui desconectado do nada.**
A sessão dura 12 horas. Trocar a senha também encerra as outras sessões da
conta.

**Errei a senha várias vezes e não consigo entrar.**
Depois de 5 erros em 15 minutos, o login daquele e-mail fica bloqueado por um
tempo. "Esqueci minha senha" destrava na hora.

**Minhas perguntas ao assistente são privadas?**
O histórico é seu: colegas não veem, e a administração também não. O professor
vê só os assuntos que o material não cobriu, sem nome nem texto, e só quando
dois alunos ou mais perguntaram. E nada sai da instituição: o modelo de IA
roda localmente. A política completa está em **Privacidade e uso de dados**, na
tela de login.

**O assistente pode errar?**
Pode. Restrito ao material, ele erra muito menos, mas não nunca. Confira a
fonte e leve ao professor o que parecer estranho.

**Quem é o encarregado pelos meus dados (DPO)?**
A administração acadêmica da instituição. É com ela — pela tela Meus dados ou
pela secretaria — que se pede cópia, correção ou exclusão.

---

## Para quem vai apresentar o sistema

O [ROTEIRO_DEMO.md](ROTEIRO_DEMO.md) tem o passo a passo cronometrado da
demonstração, com o preparo da máquina, as perguntas a fazer no chat,
respostas para as dúvidas mais prováveis da banca e um plano B.
