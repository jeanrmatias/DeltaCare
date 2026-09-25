# Relatório de implementação

Resposta ao documento *Apontamentos e melhorias — Delta Care* (23/09/2026).
Todos os itens de alta, média e baixa prioridade foram implementados, exceto o
que o próprio documento marcou como fora de escopo.

| # | Item | Prioridade | Situação |
|---|---|---|---|
| 1 | Notificações do professor | Alta | ✅ |
| 2 | Botão "Parar" no chat | Alta | ✅ |
| 3 | Campo nome no cadastro | Alta | ✅ |
| 4 | Seleção múltipla de turmas | Média | ✅ |
| 5 | XP e acompanhamento | Média | ✅ |
| 6 | Visualizador interno | Média | ✅ |
| 7 | Filtros na lista de materiais | Baixa | ✅ |
| 8 | Importação em massa (CSV/XLSX) | Baixa | ✅ |
| 9 | Autosserviço de perfil | Futura | Fora de escopo, conforme o documento |

Além dos itens do documento, os `alert()`, `confirm()` e `prompt()` do
navegador foram substituídos por diálogos próprios (ver item 10).

**Cobertura:** 107 testes automatizados — 80 no backend (contra 43 antes desta
rodada) e 27 no JavaScript, que não tinha nenhum.

---

## 1. Notificações do professor

**O que havia:** o contador era um `<span class="badge">5</span>` escrito à
mão no HTML, e o clique não tinha tratador nenhum. Não existia tabela, rota
nem evento — o "5" nunca significou coisa alguma.

**O que foi feito:** notificações passam a ser geradas por eventos reais.

- A administração matricula um aluno → o professor daquela turma é avisado.
- O professor publica um material → os alunos matriculados são avisados.
- Um material **agendado** chega na data → o aluno é avisado.

O caso do agendado tem uma particularidade: o material se torna visível sozinho
quando a data passa, sem nenhum código rodar naquele instante. Em vez de criar
uma tarefa periódica só para isso, a verificação acontece quando o usuário abre
o sino — o custo é uma consulta, e o aviso chega no momento em que ele olharia
de qualquer forma. A coluna `materiais.notificado` impede avisar duas vezes.

**Arquivos:**
`backend/regras/notificacoes.py` (novo) · `backend/infra/database.py` (tabela
`notificacoes`, coluna `materiais.notificado`) · `backend/main.py` (3 rotas) ·
`backend/regras/matriculas.py` e `backend/regras/materiais.py` (disparo) ·
`frontend/notificacoes.js` (novo) · sino adicionado aos 9 painéis.

**Como testar:** entre como admin, matricule um aluno numa turma; entre como
professor e abra o sino — o aviso está lá. Publique um material e entre como
aluno para ver o outro lado. Clicar numa notificação a marca como lida.

**Detalhe de segurança:** `marcar_como_lida` filtra por `user_id` além do id da
notificação. Sem isso, saber o id bastaria para marcar a notificação de outra
pessoa — há teste cobrindo exatamente isso.

---

## 2. Botão "Parar" no chat

**O que havia:** durante os 10 a 20 segundos de geração, a única saída era F5.

**O que foi feito:** a requisição passou a ser feita com `AbortController`. O
botão "Enviar" é **substituído** pelo "Parar" durante o processamento — não
colocado ao lado — porque enviar outra pergunta enquanto a primeira gera não é
uma ação válida. O campo de texto também é desabilitado.

Ao cancelar, o navegador lança `AbortError` pelo mesmo caminho de uma falha de
rede; o código distingue os dois e mostra *"Resposta interrompida"* em vez de
uma mensagem de erro.

**Arquivos:** `frontend/aluno/aluno.js` · `frontend/aluno/aluno.html` ·
`frontend/style_aluno.css`.

**Como testar:** faça uma pergunta e clique em Parar antes de a resposta
chegar. A interface volta ao estado normal e o campo recebe o foco.

---

## 3. Campo nome no cadastro

**O que foi feito:** `users` ganhou as colunas `nome`, `disciplinas` e
`matricula`, por migração automática — bancos existentes são atualizados na
primeira execução, sem perder dados.

A coluna `nome` aceita `NULL` de propósito. Torná-la `NOT NULL` quebraria as
contas que já existem, que não têm esse dado. A obrigatoriedade está na criação
da conta; para contas antigas, a interface cai no e-mail formatado
("ana.paula@x" → "Ana Paula").

`disciplinas` só é gravada para professor e `matricula` só para aluno. Os
outros perfis ignoram o campo em vez de dar erro, para o formulário poder
enviar sempre o mesmo corpo.

**Extra além do pedido:** o formulário aceita matricular o aluno numa turma já
na criação, evitando cadastrar e depois matricular um a um.

**Arquivos:** `backend/infra/database.py` · `backend/regras/autenticacao.py` ·
`backend/regras/turmas.py` · `backend/main.py` · `backend/seed_demo.py` ·
`frontend/administracao/usuarios.html` e `.js` · `frontend/auth.js`
(`nomeExibicao()` e `iniciaisDe()` centralizados, removendo cópias em 12
arquivos).

**Como testar:** crie uma conta sem nome — é recusada. Crie com nome e entre:
o nome aparece na saudação e no rodapé, não mais o e-mail.

---

## 4. Seleção múltipla de turmas

**O que foi feito:** a rota `POST /materiais` passou a aceitar `turma_ids[]`,
mantendo `turma_id` para não quebrar integrações. A interface mostra as turmas
do professor com checkbox e um "Selecionar todas" (que só aparece com mais de
uma turma).

**Decisão de modelagem:** o schema guarda `turma_id` na própria linha do
material, então cada turma recebe um registro. Migrar para muitos-para-muitos
quebraria a listagem por turma do professor e a busca por turma do chat, sem
ganho para o caso real — o professor edita e despublica turma a turma.

**Mas o arquivo é gravado uma única vez** e o caminho é compartilhado: um PDF
de 15 MB em cinco turmas ocuparia 75 MB à toa. Como consequência,
`excluir_material` passou a contar referências e só apaga o arquivo do disco
quando o último registro que aponta para ele é excluído. Há teste que cria o
material em duas turmas, exclui de uma e verifica que o arquivo **continua** no
disco — e que some quando a segunda é excluída.

**Validação antes de criar:** se uma das turmas não for do professor, nada é
criado. Publicação parcial deixaria o professor sem saber em quais turmas o
material entrou.

**Arquivos:** `backend/regras/materiais.py` · `backend/main.py` ·
`frontend/professor/materiais.html` e `.js` · `frontend/style_dashboard.css`.

---

## 5. XP e acompanhamento no painel do aluno

**O que foi feito:** o painel inicial ganhou nível, barra de XP, sequência de
dias consecutivos e um gráfico dos últimos 14 dias.

**Todo número vem de atividade registrada, nenhum é estimado.** O módulo de
Atividades ainda não existe, então o XP vem do que o sistema de fato observa:

| Ação | XP |
|---|---|
| Pergunta ao assistente | 10 |
| Material consultado (distinto) | 15 |
| Dia com atividade | 25 |

Para que "materiais consultados" existisse, foi criada a tabela
`acessos_material`, alimentada quando o aluno abre ou baixa um material — e
**só depois** da checagem de permissão, para que material que ele não pode ver
não entre no acompanhamento dele.

A composição do XP fica visível na tela. Um total de pontos sem explicação de
origem não engaja, irrita. Quando o módulo de Atividades existir, entrega e
nota entram na mesma conta.

**Dois detalhes de comportamento:** reabrir o mesmo PDF cinco vezes conta como
um material (`COUNT(DISTINCT)`), e a sequência de dias começa a contar de
ontem quando hoje ainda não teve atividade — senão zeraria toda manhã.

**Arquivos:** `backend/regras/aluno.py` · `backend/infra/database.py` ·
`backend/main.py` · `frontend/aluno/inicio.html` e `.js` ·
`frontend/style_aluno.css`.

---

## 6. Visualizador interno de materiais

**O que foi feito:** materiais abrem num modal dentro da plataforma. PDF e
texto usam o visualizador nativo do navegador (com busca, zoom e navegação por
página de graça); imagem, vídeo e áudio ganham o elemento correspondente.

**Por que blob e não `<iframe src="/aluno/materiais/1/arquivo">`:** a navegação
do iframe não envia o header `Authorization`, e passar o token na URL o
deixaria gravado no histórico do navegador e nos logs do servidor. O arquivo é
buscado autenticado, vira um blob local e é exibido a partir dele. O blob é
liberado ao fechar — sem isso, cada abertura deixaria o arquivo inteiro na
memória.

**Formatos que o navegador não renderiza (.docx, .xlsx) não oferecem o botão
"Visualizar"** — prometer visualização e entregar uma tela cinza é pior do que
dizer que não dá. Para esses, resta o download.

**Arquivos:** `frontend/visualizador.js` (novo) ·
`frontend/aluno/materiais.js` · `frontend/professor/materiais.js` ·
`frontend/style_dashboard.css`.

---

## 7. Filtros na lista de materiais

**O que foi feito:** a lista do aluno ganhou filtros combinados de assunto,
tópico, tipo e período (7 / 30 / 90 dias), somados à busca por texto que já
existia, com um botão para limpar tudo.

As opções de assunto e tópico são montadas a partir dos materiais que o aluno
realmente tem. Uma lista fixa ofereceria filtros que não retornam nada — e
esconderia assuntos que o professor cadastrou.

**Arquivos:** `frontend/aluno/materiais.html` e `.js` ·
`frontend/style_dashboard.css`.

---

## 8. Importação em massa

**O que foi feito:** a administração envia CSV ou XLSX e recebe um relatório
do que entrou e do que foi recusado, linha a linha, com o motivo.

**O fluxo tem duas etapas de propósito:** "Conferir planilha" lê e valida sem
gravar nada; só depois "Importar" cria as contas. Uma planilha com metade das
linhas erradas não deve criar metade das contas para o admin descobrir depois.

**Sem dependência nova.** O `.xlsx` é um ZIP com XML dentro, e `zipfile` +
`ElementTree` são da biblioteca padrão. Trazer openpyxl ou pandas para ler três
colunas seria desproporcional — o projeto já escreve o próprio gerador de PDF e
o próprio hash de senha pelo mesmo motivo. O `requirements.txt` continua com
três pacotes.

**Tolerância a planilha do mundo real:**
- separador `;` (Excel em português) ou `,`;
- codificação UTF-8, UTF-8 com BOM, cp1252 ou latin-1;
- cabeçalho em várias grafias: "Nome Completo", "Aluno", "E-mail", "Correio",
  "Matrícula", "RA", "Registro"…

**Validação:** nome vazio, e-mail malformado, e-mail repetido na própria
planilha e e-mail já cadastrado são recusados individualmente — as demais
linhas entram normalmente.

**Sobre PDF:** o documento pedia para avaliar a viabilidade. A conclusão foi
**não implementar**. O texto extraído de um PDF não tem estrutura de tabela, e
adivinhar colunas por posição no papel erra em silêncio. Um erro silencioso num
cadastro acadêmico — um aluno com a matrícula de outro — é pior do que pedir a
planilha.

**Arquivos:** `backend/regras/importacao.py` (novo) · `backend/main.py` (2
rotas) · `frontend/administracao/usuarios.html` e `.js`.

---

## 8.1 Lacuna encontrada no próprio roadmap

Ao revisar o catálogo de módulos, apareceu uma incoerência que não era de
implementação, e sim de planejamento: **o módulo de denúncias existia só do
lado de quem trata**.

A administração tinha "receber e listar denúncias", "acompanhar o status" e
"registrar a ação tomada". Mas não havia, em lugar nenhum, como uma denúncia
ser criada — nem pelo aluno, nem pelo professor. Uma caixa de entrada sem
porta de entrada.

A lacuna vinha do backlog original: os cards do Trello descrevem a gestão das
denúncias e nenhum descreve o ato de denunciar.

**Correção:** o catálogo ganhou o módulo "Denúncias" nas áreas do aluno e do
professor, descrevendo o lado de quem reporta, e os dois módulos passaram a se
referenciar explicitamente — cada tela diz que depende da outra e que as duas
fazem parte da mesma entrega. O item entrou no menu dos dois perfis, para não
virar uma página que ninguém alcança.

O teste de contagem de módulos (`length === 9`) foi substituído por duas
verificações de coerência: que os dois lados da denúncia existem, e que módulos
dependentes apontam para a contraparte.

## 9. Autosserviço de perfil

Não implementado, conforme o próprio documento
(*"Registrar como item futuro, não implementar agora"*). Fica anotado no
`CONTEXTO.md` junto dos demais itens de escopo futuro.

---

## 10. Diálogos próprios no lugar dos nativos

**Não estava no documento**, mas foi pedido junto: os 21 `alert()`,
`confirm()` e `prompt()` do navegador foram substituídos.

Os diálogos nativos travam a página inteira, não seguem a identidade visual e,
em alguns navegadores, podem ser silenciados pelo usuário — o que faria uma
confirmação de exclusão desaparecer sem aviso.

Os novos usam `<dialog>` nativo, que já entrega foco preso dentro do diálogo,
fechamento por Esc e semântica de modal para leitores de tela. Todos retornam
Promise, então o código chamador ficou praticamente igual.

Um ganho colateral: a recuperação de senha pedia e-mail, código e nova senha em
**três `prompt()` seguidos**, e quem errasse o último perdia o código. Agora
código e senha ficam no mesmo diálogo.

**Arquivos:** `frontend/dialogo.js` (novo) · `frontend/style_dashboard.css` e
`style_index.css` · 11 arquivos de JS.

---

## Como verificar tudo

```
cd backend
python testes.py          # 80 testes, não precisa do Ollama

cd ../frontend
node testes.mjs           # 27 testes do JavaScript
```

Os testes de front cobrem a lógica pura: renderização de Markdown (incluindo
que HTML vindo do modelo **não** é interpretado), nome de exibição, formatos
aceitos pelo visualizador e consistência entre os links do menu e o catálogo de
módulos. O DOM mínimo está no próprio arquivo, sem jsdom.

O roteiro de demonstração está em [`ROTEIRO_DEMO.md`](ROTEIRO_DEMO.md) e o guia
de uso em [`TUTORIAL.md`](TUTORIAL.md).
