# Validação de usabilidade — plano

**Sprint 4 · Front-End Design.** O enunciado pede uma validação com no mínimo
três participantes, registrada no README. Este é o plano; o que aconteceu de
fato vai em [RESULTADOS.md](RESULTADOS.md).

| Documento | Para quê | Quem usa |
|---|---|---|
| [ROTEIRO.md](ROTEIRO.md) | Preparar a máquina, conduzir a sessão e as nove tarefas | Facilitador |
| [FICHA_DE_OBSERVACAO.md](FICHA_DE_OBSERVACAO.md) | Anotar o que aconteceu em cada tarefa (uma ficha por participante) | Observador |
| [TERMO_DE_CONSENTIMENTO.md](TERMO_DE_CONSENTIMENTO.md) | O participante concorda antes de começar | Participante |
| [QUESTIONARIO_SUS.md](QUESTIONARIO_SUS.md) | Dez afirmações ao final, e como calcular a nota | Participante, depois o facilitador |
| [RESULTADOS.md](RESULTADOS.md) | Os números, os problemas achados e o que mudou por causa deles | Equipe |
| [TESTE_LEITOR_DE_TELA.md](TESTE_LEITOR_DE_TELA.md) | A plataforma usada só pelo teclado e pelo leitor de tela NVDA | Equipe, ou um usuário de leitor de tela |

## O que queremos descobrir

O aluno é quem mais usa a plataforma, e é por ele que o teste começa. Três
perguntas:

1. **Alguém que nunca viu o Delta Care consegue fazer o que o aluno faz no dia
   a dia** — entrar pela primeira vez, achar o aviso, ler o material, perguntar
   ao assistente, entregar uma atividade — sem ajuda?
2. **O participante entende o assistente?** É o diferencial do produto: ele só
   responde com o material do professor e diz de onde tirou. Se o participante
   acha que o assistente "não funcionou" quando ele recusa uma pergunta fora do
   material, a interface está explicando mal.
3. **O que está escondido?** Funções que existem mas ninguém acha (a cópia dos
   dados, por exemplo, fica dentro do perfil).

## Participantes

- **Três pessoas de fora da equipe, no mínimo, reais.** Arthur, Jean e Matheus
  não contam: conhecem o sistema e sabem onde cada coisa fica.
- **Perfil desejado:** estudante da área da saúde (medicina, enfermagem,
  fisioterapia…). Na falta, estudante universitário de qualquer curso, que usa
  plataforma de ensino (Moodle, Canvas, a da própria faculdade). O perfil de
  cada um vai anotado na ficha, sem nome.
- **Sessão piloto com o Matheus**, antes das três. Serve para ensaiar o
  roteiro, cronometrar e achar tarefa mal escrita. **Não conta como
  participante** e os números dela não entram no resultado.
- Ninguém é identificado no registro: os participantes são P1, P2 e P3, e as
  contas usadas no teste são fictícias (`p1@validacao.deltacare.com`).

## Como

- **Teste de tarefas com pensamento em voz alta.** O participante recebe um
  cenário ("ouviu falar que uma prova mudou de data…"), tenta resolver e vai
  falando o que pensa. O facilitador não ajuda nem explica a tela.
- **As tarefas não usam o nome dos botões.** "Descubra qual prova mudou" em vez
  de "abra o mural de avisos": o que se testa é se a pessoa encontra, não se
  ela lê.
- **Presencial ou à distância** (chamada de vídeo com compartilhamento de
  tela, o participante controlando o navegador no computador do facilitador
  por controle remoto, ou com o servidor exposto na rede local).
- **Duração:** de 30 a 40 minutos por pessoa — 5 de abertura, 20 a 25 de
  tarefas, 5 de questionário e conversa final.
- **Papéis:** um facilitador (conduz e fala) e um observador (só anota). Com
  uma pessoa só, ela faz as duas coisas e grava a tela, **se** o participante
  autorizar no termo.

## O que medimos

| Medida | Como | Por quê |
|---|---|---|
| **Sucesso por tarefa** | Concluiu sozinho / com ajuda / não concluiu | É a pergunta 1 |
| **Tempo por tarefa** | Cronômetro, da leitura do cenário até a conclusão ou desistência | Aponta onde a pessoa se perdeu, mesmo quando conseguiu |
| **Problemas observados** | Descrição + gravidade de 0 a 4 (escala de Nielsen, na ficha) | É o que vira correção |
| **Falas do participante** | Frases literais, quando dizem algo sobre a tela ("achei que isso era um botão") | Explicam o porquê do problema |
| **Nota SUS** | Questionário de 10 itens ao final, nota de 0 a 100 | Satisfação, comparável com outros sistemas |

**Sobre a nota SUS com três pessoas:** é indicativa, não estatística. A média
de referência de mercado fica em torno de 68; com três participantes, a nota
serve para ver se alguém saiu muito insatisfeito, não para afirmar que o
sistema "é bom". O peso da validação está nos problemas observados — com
cinco pessoas costuma-se achar a maior parte dos problemas graves, e com três
já aparecem os mais frequentes.

## Depois das sessões

1. Juntar as fichas em [RESULTADOS.md](RESULTADOS.md): sucesso e tempo por
   tarefa, nota SUS de cada um, lista de problemas com gravidade.
2. Corrigir os de gravidade 3 e 4 ainda nesta sprint; registrar os demais.
3. No README do projeto, a seção **Validação de usabilidade** resume o
   resultado e aponta para cá.

**Nenhum dado é inventado.** Se só duas sessões acontecerem, o registro diz
duas. Tarefa que não deu para aplicar (o modelo de IA fora do ar, por
exemplo) aparece como não aplicada, com o motivo.
