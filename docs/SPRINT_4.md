# Delta Care — Sprint 4

> **Situação em 05/10/2026:** desenvolvimento da sprint concluído; a
> **validação de usabilidade com participantes externos ainda não aconteceu**.
> Só o piloto, com um integrante da equipe, foi feito. A seção 6 fica com os
> campos de resultado vazios até as sessões acontecerem — nenhum número aqui é
> estimado. Este aviso sai quando o documento for fechado para a entrega.

**Disciplinas:** Web Development · Front-End Design (entrega conjunta)
**Grupo / Projeto:** Delta Care — Challenge Hospital Moinhos de Vento
**Integrantes:** Arthur Veiga Demétrio · Jean Rodrigues Matias · Matheus Marques De Souza
**Repositório:** https://github.com/jeanrmatias/DeltaCare
**Entrega:** 25/10/2026 · commits da sprint a partir de 26/09/2026

---

## 1. O produto, em um parágrafo

Delta Care é uma plataforma de ensino para uma faculdade de medicina: a
administração organiza turmas, disciplinas e professores; o professor publica
material, atividades e avisos; o aluno estuda, entrega, acompanha o próprio
desempenho e tira dúvidas com um assistente de IA que responde **apenas com
base no material publicado pelos professores**. Quando o material não cobre a
pergunta, o assistente diz isso — e o que ficou sem resposta vira pauta para o
professor, sem identificar quem perguntou. O assistente roda na
infraestrutura da instituição (Ollama), sem mandar dado de aluno para fora.

---

## 2. O que a Sprint 4 pede, e onde está

| Requisito | Onde está |
|---|---|
| React com componentes, props e hooks nativos | Todas as 34 telas, em [`frontend/src/`](../frontend/src). Vite 8, React 19, React Router 8. |
| Ao menos um hook próprio | Cinco, em [`frontend/src/hooks/`](../frontend/src/hooks): `useSessao`, `useApi`, `useDialogo`, `useApagarAnotacao`, `useTituloDaPagina`. |
| Rotas públicas e privadas | [`App.jsx`](../frontend/src/App.jsx) e [`RotaPrivada.jsx`](../frontend/src/rotas/RotaPrivada.jsx): o login (com a recuperação de senha), a privacidade e os termos são públicos; cada área só abre para o próprio perfil, e a senha provisória só abre a tela de troca. A regra é repetida no servidor, que é quem de fato barra. |
| Tailwind CSS | O tema inteiro em [`index.css`](../frontend/src/index.css), como tokens do Tailwind 4; nenhum CSS solto por tela. |
| Validação de usabilidade com no mínimo 3 participantes | Material completo em [`validacao/`](validacao/README.md); piloto feito; sessões externas pendentes (seção 6). |
| Evolução do projeto, não proposta nova | O mesmo produto das Sprints 1 a 3, com o front reescrito e os módulos que estavam no roadmap. |

---

## 3. Objetivo da sprint

> Trocar a base do front para React e Tailwind sem perder nada do que já
> funcionava, completar os módulos que o produto prometia e validar com
> pessoas de fora se ele é usável.

A Sprint 3 terminou com um front em HTML e JavaScript sem framework e uma
lista de módulos "em breve" (atividades, desempenho, denúncias, mensagens,
calendário, relatórios). A Sprint 4 pediu React e Tailwind. Fizemos as duas
coisas na ordem que reduzia o risco: primeiro o backend dos módulos que
faltavam (com testes), depois a migração das telas, com um verificador
automático de que toda chamada do front tem rota no back — o que permitiu os
dois fronts conviverem até o React cobrir tudo e o antigo sair do repositório.

---

## 4. Sprint Backlog

### US-01 — Telas em React

**Critérios de aceite**
- Todas as telas dos três perfis reescritas em React, entregues pela própria
  API em `/app/` (tela e API na mesma origem).
- F5 numa tela interna não dá 404; arquivo inexistente dá 404 de verdade.
- Sessão por token, compartilhada entre as telas por Context.
- Nenhuma chamada do front sem rota no back (verificado por
  [`contrato_front.py`](../backend/scripts/contrato_front.py), que roda nos
  testes).

**Decisão.** Migrar com os dois fronts no ar e o contrato conferindo os dois
deu segurança para trocar tela por tela. Quando o React passou a cobrir tudo,
o front antigo saiu do repositório (fica no histórico do git): o contrato
mostrou que ele não usava nenhuma rota que o React não use.

### US-02 — Tema em Tailwind, com as cores do hospital

**Critérios de aceite**
- Cores, tipografia, cantos e sombras definidos uma vez, como tokens.
- As cores da marca não mudam: o produto é vendido para quem já as usa.
- Todo par de texto e fundo usado nas telas passa no WCAG AA (4,5:1; 3:1
  para contorno e ícone) — conferido por teste, lido do próprio `index.css`.

**Decisão.** Onde a cor exata da marca não alcança 4,5:1 com texto pequeno, ela
fica nas superfícies (barras, ícones, anel de foco) e o texto usa o mesmo matiz
escurecido até passar. O teste trava as cores da marca: mudar uma delas
quebra a suíte.

### US-03 — Uso no celular

**Critérios de aceite**
- As 34 telas sem rolagem horizontal em 360, 390, 768 e 1280 px.
- No celular, o menu é uma gaveta lateral que se puxa com o dedo, fechada
  fora do alcance do Tab, e fecha com Esc ou tocando fora.
- A logo leva ao início do perfil.

### US-04 — Atividades e correção

**Critérios de aceite**
- Objetiva (corrigida na hora) e dissertativa (com ou sem arquivo), com prazo,
  publicação em várias disciplinas, rascunho e correção com devolutiva.
- A nota vira XP proporcional aos pontos da atividade.

**O XP era farmável** e a sprint fechou isso: pergunta ao chat só pontua se o
material respondeu, se é distinta das anteriores e dentro de um teto por dia.

### US-05 — Desempenho, denúncias e mensagens

**Critérios de aceite**
- Desempenho por disciplina: notas, evolução e o tópico com mais erro.
- Denúncia de conteúdo pelo aluno, tratada pela administração, que avisa
  quem reportou; quem reportou pode retirar.
- Conversa entre aluno e professor por disciplina.

### US-06 — Calendário

**Critérios de aceite**
- Prazos e liberações do mês, para aluno e professor.
- O professor marca uma atividade ou agenda um material a partir do dia.
- As datas seguem o fuso da instituição.

**Defeito achado em uso:** um prazo às 23:59 aparecia no dia seguinte, porque
o calendário agrupava pela data em UTC. Corrigido com o fuso configurável
(`DELTACARE_FUSO_HORAS`). Na revisão do código, o mesmo erro apareceu fora do
calendário — dias de estudo, sequência, teto diário de XP, ranking da semana
e mês dos relatórios — e a regra virou uma só para o sistema todo
([`infra/fuso.py`](../backend/app/infra/fuso.py)).

### US-07 — Turma de alunos, semestres e ranking

**Critérios de aceite**
- A turma (ex.: MED 3A) é entidade própria: matricular na turma matricula em
  todas as disciplinas dela, com exceção por aluno (aproveitamento de estudos).
- Semestres anteriores ficam consultáveis, sem misturar com os atuais.
- Ranking do semestre por faixas (bronze, prata, ouro, platina); só o topo
  aparece, e o aluno pode escolher não aparecer.

### US-08 — Chat de estudos que admite o que não sabe

**Critérios de aceite**
- A resposta diz se o material cobriu a pergunta por inteiro, em parte ou
  nada; na parcial, mostra "O material não traz:" com o que faltou.
- Toda resposta cita de qual material saiu; fonte que não corresponde a
  material recuperado é descartada.
- **Modo automático**, o padrão: o aluno não escolhe a disciplina; o chat
  procura em todas as dele e mostra de qual veio a resposta.
- O aluno apaga a conversa quando quiser.

**Lacunas do material.** O que os alunos perguntam e o material não responde
chega ao professor agrupado por assunto, sem o texto da pergunta e sem quem
perguntou, e só quando pelo menos dois alunos diferentes perguntaram.

**Decisão do modo automático.** A pergunta fica na disciplina de onde veio a
resposta; quando nenhum material respondeu, fica sem disciplina. Chutar a
disciplina mais parecida foi exatamente o erro que o piloto achou (seção 6).

### US-09 — LGPD

**Critérios de aceite**
- O aluno baixa uma cópia de tudo o que a plataforma guarda sobre ele, na hora.
- Correção e exclusão são pedidas pelo aluno e decididas pela administração,
  que é a encarregada pelo tratamento de dados.
- Exclusão desativa a conta na hora e anonimiza em 45 dias, com volta atrás
  possível nesse prazo; notas e entregas ficam no registro acadêmico, sem
  identificação.
- A administração exclui quem deixou a instituição, com motivo registrado;
  professor só sai com alguém para assumir as disciplinas.
- Política de privacidade e termos de uso públicos.

### US-10 — Relatórios da turma

**Critérios de aceite**
- Painel ao vivo e relatório mensal por turma (notas, entregas, engajamento,
  uso do chat), para administração e professor, exportável em CSV.
- Para a administração, em quais disciplinas os alunos têm mais dificuldade.
- Nenhum número com nome de aluno.

### US-11 — Segurança

**Critérios de aceite**
- Código por e-mail no login de professor e administração.
- Senha provisória trocada no primeiro acesso; senha nova com 8 ou mais
  caracteres, fora da lista das mais usadas.
- Trilha de auditoria das ações sensíveis, consultável pela administração.
- Cabeçalhos de segurança (CSP, proteção contra clickjacking) e upload
  conferido pelo conteúdo do arquivo, não pela extensão.

### US-12 — Material de demonstração verdadeiro

**Critérios de aceite**
- Dez PDFs, em todas as disciplinas, com medicina real e as referências no
  fim (diretrizes da ESC, AHA e SBC; Guyton, Junqueira, Moore).
- Quizzes, caso clínico e mensagens da demonstração coerentes com eles.

**Decisão revista.** Até esta sprint, o exemplo era inventado de propósito (um
remédio e uma escala que não existem), para provar que o assistente lia o
material. Para um produto vendido a um hospital, conteúdo falso na
demonstração é um risco maior do que o benefício. A prova continua de outro
jeito: cada resposta mostra de onde saiu, e o que não está no material ele
recusa.

---

## 5. Decisões de experiência (Front-End Design)

**Nenhum dado de demonstração na interface.** Tela sem backend mostra que não
conseguiu carregar, e não números de exemplo. Um painel com dado falso
quando o servidor cai é pior que um painel vazio, porque parece funcionar.

**A escolha fica junto de onde se usa.** O seletor de disciplina do chat ficava
no topo da página, longe da pergunta — apontado como pouco intuitivo por quem
usou. Foi para junto do campo de pergunta, numa frase: "Perguntando sobre o
material de [disciplina ▾]". Depois veio o modo automático, que dispensa a
escolha.

**As duas falas do chat com o mesmo peso visual.** A resposta do assistente era
texto solto na página, com um filete na margem; ao lado do balão azul do
aluno, parecia desamarrada. Virou balão também, espelhado, com as fontes como
nota de rodapé numerada e o "O material não traz:" como anotação dentro dele.

**Não apontar um caminho que pode estar errado.** Quando o material não
responde, a plataforma oferece levar a dúvida a um professor, sem dizer qual
(seção 6).

**Contar antes o que acontece depois.** Apagar a conversa avisa, antes, o que
some e o que continua contando. O chat avisa, antes da pergunta, o que o
professor vê.

**Identidade editorial.** Literata nos títulos e números, Source Sans 3 no
texto; contorno fino no lugar de sombra; números da tela inicial como uma
faixa. As cores são as da marca, intocadas.

**Acessibilidade.** Contraste AA verificado por teste; anel de foco visível em
todo elemento; atalho "Pular para o conteúdo"; toda janela com nome para o
leitor de tela; a resposta do chat é anunciada sozinha quando chega (região
`log`), e o cronômetro de espera não é lido a cada segundo. O teste completo
com o NVDA tem roteiro pronto
([TESTE_LEITOR_DE_TELA.md](validacao/TESTE_LEITOR_DE_TELA.md)) e ainda não foi
feito.

---

## 6. Validação de usabilidade

**Método** ([`validacao/`](validacao/README.md)): sessões individuais de 30 a
40 minutos, com um facilitador e um observador, num banco separado do de
demonstração. Nove tarefas lidas em voz alta, do primeiro acesso à cópia dos
próprios dados; sucesso e tempo anotados por tarefa; questionário SUS no fim;
termo de consentimento antes.

**Piloto (02/10/2026, com um integrante — não conta entre os três).** As
tarefas correram sem tropeço, e o roteiro ficou como estava. O produto mudou:
uma pergunta sobre crânio, feita no chat de Anatomia, recebeu a sugestão de
procurar o material de Cardiologia, porque uma palavra aparecia num PDF de lá.
Caminho errado. A sugestão de outra disciplina foi retirada; a oferta de levar
a dúvida ao professor ficou, sem apontar qual.

**Sessões com participantes externos:** pendentes. Os resultados — sucesso por
tarefa, tempos, nota SUS, problemas encontrados por gravidade e o que mudou
por causa deles — vão em [RESULTADOS.md](validacao/RESULTADOS.md) e num
resumo aqui, só com dado das sessões.

| | P1 | P2 | P3 |
|---|---|---|---|
| Data | | | |
| Tarefas concluídas sozinho | /9 | /9 | /9 |
| Nota SUS (0–100) | | | |

---

## 7. Qualidade

| Verificação | Resultado em 05/10/2026 |
|---|---|
| Testes do backend (regras e rotas, sem o Ollama) | 587 passando |
| Testes das telas React (renderizadas no Node) | 64 passando |
| Lint do React (oxlint) | sem aviso |
| Contrato front ↔ back | 139 chamadas conferidas, nenhuma sem rota |

Na Sprint 3 eram 80 testes de backend.

**Todo teste novo é conferido falhando.** O defeito que ele deveria pegar é
reintroduzido de propósito; se o teste continua passando, ele é refeito. Nesta
sprint isso derrubou testes que pareciam bons: um limite de reenvio do código
por e-mail que o teste "provava" só porque outra regra (a espera entre envios)
mascarava a falta dele; uma cópia de índice do chat que o teste não conferia
porque a consulta não lia a coluna copiada.

**Sete testes não rodavam, e ninguém sabia.** Duas classes de teste tinham
o mesmo nome de classes posteriores (`TestesExclusao`, `TestesCorrecao`); em
Python, a segunda apaga a primeira, e os testes dela somem da suíte sem aviso.
Uma análise estática (Pyright) apontou. As classes foram renomeadas, os sete
testes voltaram a rodar e passaram, e um teste novo falha se isso se repetir.
A mesma análise não achou defeito no código do sistema: os demais avisos eram
de tipagem, em trechos já protegidos.

**Testes que dependiam da hora.** Três testes do calendário falhavam só entre
0h e 3h (horário de Brasília): montavam a data em UTC e esperavam o dia UTC,
enquanto o calendário mostra o dia local. Passaram a montar a data no fuso da
instituição.

**O teste com o modelo de verdade pega o que o falso não pega.** Os testes do
chat usam um modelo falso, para rodar sem o Ollama. Ao testar o modo automático
com o modelo real, uma resposta certa chegou sem fonte e sem disciplina: o
modelo escreveu a fonte com um prefixo ("Material: ..."), apesar do formato
imposto. O sistema passou a reconhecer a fonte com tolerância, e o caso virou
teste.

---

## 8. Arquitetura

```
frontend/   React (Vite), entregue pela API em /app/
backend/
  app/      main.py (rotas), infra/ (o que o sistema usa), regras/ (o que decide)
  scripts/  seeds, material de demonstração, backup, rotinas da LGPD
  testes/
docs/       tutorial, arquitetura, roteiro da apresentação, validação
deploy/     systemd, Caddy (HTTPS) e modelo de configuração
```

- **109 rotas**, **27 tabelas** (SQLite em modo WAL) e **26 módulos de
  regras**, nenhum deles dependente do FastAPI — é o que permite testá-los
  sem subir servidor.
- **Identidade nunca vem do cliente:** toda rota protegida lê o usuário do
  token de sessão, e o perfil é conferido no servidor.
- **RAG local:** PDFs divididos em trechos, embeddings com `nomic-embed-text`,
  busca híbrida (cosseno e termos literais) e resposta do `gpt-oss:20b` em
  JSON com formato imposto.

Diagramas, fluxo de autenticação, RAG e matriz de permissões:
[ARQUITETURA.md](ARQUITETURA.md).

---

## 9. Fora de escopo e débito técnico

- **SQLite aceita um escritor por vez:** aguenta uma faculdade, não uma rede.
- **A implantação (systemd e Caddy) não rodou num servidor real.** O professor
  roda o projeto na própria máquina, e o README traz o passo a passo dos dois
  jeitos.
- **O chat lê só PDF**; vídeo e link ficam de fora.
- **A busca percorre todos os trechos a cada pergunta**: rápida para um curso,
  pediria um índice vetorial para um acervo muito maior.
- **No modo automático, a pergunta que nenhum material respondeu não vai para
  as lacunas de professor nenhum**, por decisão (seção 4, US-08).
- Professor e administração não têm a tela Meus dados; seguem pela
  secretaria.
- A política de privacidade e os termos de uso precisam da aprovação formal
  da instituição.

---

## 10. Retrospectiva

**Funcionou**
- **Migrar com uma rede embaixo.** O contrato front↔back conferindo as duas
  versões das telas deixou trocar o front inteiro sem uma rota quebrada
  chegar ao navegador.
- **Testar com quem usa, mesmo antes do teste oficial.** O piloto achou um
  erro que nenhum teste automatizado acharia, porque cada parte estava certa
  sozinha: a sugestão de disciplina errada.
- **Reintroduzir o defeito para ver o teste falhar.** Pegou testes que
  passavam pelo motivo errado (seção 7).

**Não funcionou, e o que aprendemos**
- **Conteúdo de exemplo inventado.** Fazia sentido para provar o RAG e deixou
  de fazer quando ficou claro que a demonstração é para um hospital. Trocar
  custou reescrever PDFs, quizzes, mensagens e roteiros. Aprendizado:
  conteúdo de demonstração é parte do produto, e decide-se com o cliente em
  mente desde o começo.
- **Data em UTC numa tela de calendário.** O prazo das 23:59 mudava de dia.
  Toda data que a pessoa lê tem fuso, e o teste precisa de um caso perto da
  meia-noite.
- **Confiar no formato imposto ao modelo.** O schema reduz os erros do modelo,
  mas não os elimina. O que vem do modelo é conferido contra o que o sistema
  sabe ser verdade (os materiais recuperados).
- **Dois fronts por tempo demais.** Conviver deu segurança à migração, mas
  dobrou o que conferir. Quando o React cobriu tudo, devíamos ter tirado o
  antigo logo, em vez de esperar.

**O que levamos para a próxima**
- Toda funcionalidade de IA testada também com o modelo de verdade, não só
  com o falso.
- A validação com pessoas de fora marcada no começo da sprint, não no fim.

---

## 11. Como executar

```
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..

cd backend
python scripts/seed_demo.py           # dados de demonstração
uvicorn main:app --app-dir app        # http://127.0.0.1:8000/app/
```

Contas de demonstração (senha `demo123`): `adm@deltacare.com`,
`professor@deltacare.com`, `aluno@deltacare.com`. O assistente de IA exige o
Ollama com `gpt-oss:20b` (ou um modelo menor, via `MODELO_CHAT`) e
`nomic-embed-text`; o resto da plataforma funciona sem ele.

**Documentação:** [README](../README.md) (visão geral e instalação) ·
[TUTORIAL.md](TUTORIAL.md) (uso, perfil por perfil) ·
[ARQUITETURA.md](ARQUITETURA.md) (diagramas) ·
[ROTEIRO_DEMO.md](ROTEIRO_DEMO.md) (apresentação) ·
[SPRINT_3.md](SPRINT_3.md) (entrega anterior).
