# Como usar o Delta Care

Guia de uso da plataforma, perfil por perfil. Para instalar e rodar o sistema,
veja o [README](README.md).

**Contas de demonstração** (senha `demo123` nas três):

| Perfil | E-mail |
|---|---|
| Administração | `adm@deltacare.com` |
| Professor | `professor@deltacare.com` |
| Aluno | `aluno@deltacare.com` |

---

## Antes de tudo: quem faz o quê

A plataforma tem três perfis, e cada um enxerga apenas o que lhe cabe. Essa
divisão não é só visual — o servidor confere a permissão a cada requisição.

| | Administração | Professor | Aluno |
|---|---|---|---|
| Criar contas | ✅ qualquer perfil | — | — |
| Criar turma | ✅ | — | — |
| Matricular aluno | ✅ | — | — |
| Publicar material | — | ✅ nas turmas dele | — |
| Ver rascunho | — | ✅ os próprios | — |
| Ver material publicado | — | ✅ os próprios | ✅ das turmas dele |
| Perguntar ao assistente | — | — | ✅ |

A ordem natural de uso é: **administração prepara → professor alimenta →
aluno consome.** É essa ordem que este tutorial segue.

---

## 1. Administração

Entre com `adm@deltacare.com`.

### Criar contas

Menu lateral → **Usuários**.

A tela lista todas as contas separadas por perfil, mostrando o que cada uma
tem vinculado (quantas turmas o professor leciona, em quantas o aluno está
matriculado).

Para criar uma conta, clique em **Nova conta** e preencha e-mail, perfil e uma
senha provisória. A pessoa deve trocá-la no primeiro acesso, usando "Esqueci
minha senha" na tela de login.

Ao criar um aluno, dá para informar a matrícula e já escolher a turma — evita
cadastrar e depois matricular um a um. Para professor, o campo é a lista de
disciplinas que ele leciona.

### Importar uma turma inteira

Menu lateral → **Usuários** → **Importar planilha**.

Aceita **.csv** e **.xlsx**. A planilha precisa de uma coluna de nome e uma de
e-mail; matrícula é opcional. O cabeçalho pode estar escrito de várias formas
("Nome Completo", "Aluno", "E-mail", "RA") — não é preciso renomear nada.

O fluxo tem dois passos:

1. **Conferir planilha** — lê e valida **sem gravar nada**, e mostra quantas
   linhas estão prontas e quais foram recusadas, com o motivo de cada uma.
2. **Importar** — cria as contas. Escolha uma senha provisória (a mesma para
   todos) e, se quiser, a turma em que todos serão matriculados.

Linhas com problema são puladas individualmente; as demais entram normalmente.

> **Por que o aluno também pode se cadastrar sozinho?**
> Pela tela de login existe um cadastro público, mas ele **só cria conta de
> aluno** — nunca professor ou administrador. A instituição escolhe: cadastrar
> a turma inteira de uma vez por aqui, ou deixar cada aluno se inscrever.
> Contas de confiança só nascem nesta tela.

### Criar turma e matricular

Menu lateral → **Turmas**.

1. Clique em **Nova turma**, dê um nome e o semestre, e escolha o professor
   responsável na lista.
2. Com a turma criada, clique nela para abrir o painel de alunos.
3. Escolha o aluno na lista e clique em **Matricular**.

O aluno passa a ver essa turma — e só a partir daí consegue acessar o material
dela e perguntar sobre ela ao assistente.

Para desmatricular, use o botão ao lado do nome do aluno no mesmo painel.

> **Excluir uma turma apaga junto** os materiais dela, os trechos indexados
> para o assistente, as matrículas e o histórico de conversa daquela turma.
> Não há como desfazer.

---

## 2. Professor

Entre com `professor@deltacare.com`.

### O painel inicial

Mostra quantas turmas você leciona, quantos alunos estão matriculados nelas e
quantos materiais você já publicou ou deixou agendados. Abaixo ficam suas
turmas e os materiais mais recentes.

Você não cria turmas: isso é da administração. Se o painel disser que você não
tem turmas atribuídas, fale com a coordenação.

### Publicar material

Menu lateral → **Materiais** → **Novo material**.

Marque em **quais turmas** o material deve entrar. Dá para escolher várias de
uma vez, e há um "Selecionar todas" quando você leciona em mais de uma.

Preencha o título e escolha o tipo:

| Tipo | O que enviar |
|---|---|
| **PDF** | Arquivo, até 15 MB |
| Documento | Arquivo |
| Vídeo | Arquivo |
| Link | Endereço começando com `http://` ou `https://` |

Os campos **assunto, tópico, aula e semestre** são opcionais, mas é o que
permite ao aluno filtrar depois — vale preencher.

No fim do formulário você decide quando o material fica visível:

- **Salvar como rascunho** — só você vê. Serve para preparar com antecedência.
- **Publicar** — o aluno vê na hora.
- **Publicar com data de liberação** — preencha a data e hora. O material fica
  invisível para o aluno até aquele momento e aparece sozinho quando a data
  chega. Não é preciso voltar aqui para liberar.

> **Só o PDF alimenta o assistente de IA.** Ao publicar um PDF, o sistema
> extrai o texto e o indexa automaticamente, e o aluno já pode perguntar sobre
> ele. Vídeo e link ficam disponíveis para download e leitura, mas o assistente
> não os consulta — vídeo exigiria transcrição, e link exigiria buscar o
> conteúdo fora da plataforma.

### Editar e excluir

Na lista de materiais, cada item tem **Editar** e **Excluir**. Você só consegue
mexer nos materiais que você mesmo criou, mesmo que outro professor dê aula na
mesma turma.

Ao editar, dá para mudar de rascunho para publicado, ajustar a data de
liberação ou corrigir a classificação.

---

## 3. Aluno

Entre com `aluno@deltacare.com`.

### Tela inicial

Abre com seu progresso: nível, XP acumulado, sequência de dias estudando e um
gráfico dos últimos 14 dias. Abaixo, suas turmas e os materiais liberados mais
recentes.

**De onde vem o XP:** cada pergunta ao assistente vale 10, cada material novo
que você abre vale 15, e cada dia com atividade vale 25. A composição fica
visível no próprio cartão — reabrir o mesmo material não conta de novo.

### Notificações

O sino no topo avisa quando um professor publica material novo numa turma sua,
inclusive os que estavam agendados e chegaram na data. Clicar numa notificação
a marca como lida e leva até o material.

### Materiais

Menu lateral → **Materiais**.

Lista tudo que os professores liberaram nas suas turmas. Use o seletor no topo
para filtrar por turma, e a busca para procurar por título, assunto ou tópico.

Use os filtros de assunto, tópico, tipo e período para achar mais rápido quando
o semestre acumular material.

Clique em **Visualizar** para abrir o material **dentro da plataforma**, sem
precisar baixar — funciona para PDF, imagem, vídeo e áudio. **Baixar** salva o
arquivo no seu computador, e **Abrir link** vale para material que é um
endereço externo.

Formatos que o navegador não sabe exibir (como .docx) não têm o botão
Visualizar; para esses, use Baixar.

> Se um material que o professor mencionou em aula não aparece aqui, ele ainda
> está como rascunho ou foi agendado para uma data futura.

### Chat de estudos

Menu lateral → **Chat de estudos**. Escolha a turma no seletor do topo e
escreva sua dúvida.

**O que torna esse assistente diferente:** ele responde **apenas** com base no
material que o seu professor publicou naquela turma. Se você perguntar algo
que não está no material, ele diz isso em vez de responder por conta própria —
mesmo que sob outras circunstâncias soubesse a resposta.

Cada resposta traz embaixo qual material foi usado. Quando não aparece fonte
nenhuma, é porque a resposta não veio do material.

A resposta leva de 10 a 20 segundos, porque o modelo roda na infraestrutura da
instituição, e não em serviço externo. Enquanto processa, aparece um indicador
com o tempo decorrido — é normal, não travou.

Se mudar de ideia no meio, o botão **Parar** interrompe a geração e devolve o
campo de digitação. Não é preciso recarregar a página.

Seu histórico fica salvo por turma e volta quando você reabre a página.

#### Como perguntar bem

- **Seja específico.** "Qual a dose inicial de Cardiolex?" funciona melhor que
  "fala sobre medicamentos".
- **Cite o termo exato** quando souber (o nome do protocolo, da escala, do
  medicamento). A busca dá peso extra a siglas, códigos e números.
- **Uma pergunta de cada vez.** Perguntas com várias partes tendem a ter a
  resposta concentrada na primeira.
- **Confira a fonte.** Ela diz de qual material veio a informação, e é por onde
  você continua o estudo.

---

## Perguntas frequentes

**Esqueci minha senha.**
Na tela de login, clique em "Esqueci minha senha" e informe seu e-mail. Nesta
versão de demonstração o link de recuperação é impresso no console do servidor,
não enviado por e-mail.

**Fui desconectado do nada.**
A sessão dura 12 horas. Depois disso é preciso entrar de novo.

**Minhas perguntas ao assistente são privadas?**
Seu histórico é individual: outros alunos não o veem. E nada sai da
infraestrutura da instituição — o modelo de IA roda localmente. Veja a
[política de privacidade](frontend/privacidade.html) na tela de login.

**O assistente pode errar?**
Pode. Ele é restrito ao material do professor, o que reduz muito o risco de
inventar, mas não elimina. Confira sempre a fonte citada, e leve ao professor
o que parecer estranho.

**Alguns itens do menu não abrem uma tela funcional.**
Atividades, Desempenho, Mensagens, Calendário, Denúncias e Relatórios ainda não
foram construídos. Clicando neles você vê o que cada módulo vai permitir e em
qual etapa está previsto. Preferimos deixar isso explícito a preencher a tela
com dados de exemplo.

---

## Para quem vai apresentar o sistema

O [ROTEIRO_DEMO.md](ROTEIRO_DEMO.md) tem um passo a passo cronometrado da
demonstração, com as perguntas certas a fazer no chat, respostas para as
dúvidas mais prováveis da banca e um plano B caso algum serviço caia.
