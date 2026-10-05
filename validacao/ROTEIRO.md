# Roteiro da sessão

Para o facilitador. O que está em *itálico e entre aspas* é para ser lido em
voz alta, do jeito que está: todos os participantes ouvem a mesma coisa.

---

## 1. Preparar a máquina (uma vez, antes das sessões)

O teste roda num **banco separado**, para as contas dos participantes não
aparecerem no ranking nem nos números da demonstração. No PowerShell, na pasta
`backend`:

```
$env:DELTACARE_DB = "validacao.db"
$env:DELTACARE_UPLOADS = "uploads/validacao"
python seed_demo.py
```

Depois, **na mesma janela** (as variáveis só valem nela):

```
uvicorn main:app
```

E em outra janela, uma vez, para a API entregar as telas atualizadas:

```
cd web
npm run build
```

Conferir:

- [ ] <http://127.0.0.1:8000/saude> responde `{"status":"ok"}`.
- [ ] O Ollama está no ar. Entre como `aluno@deltacare.com` / `demo123`, abra o
      chat em **Cardiologia I** e pergunte *em que situação se usa a dobutamina?*
      A resposta deve citar a pressão sistólica abaixo de 90 mmHg e a Aula 3. Se não responder, as
      tarefas 4 e 5 não podem ser aplicadas: resolva antes ou remarque.
- [ ] Saia da conta da Marina.

## 2. Criar a conta do participante (antes de cada sessão)

Uma conta nova por participante, para ninguém herdar o que o anterior fez.

1. Entre como `adm@deltacare.com` / `demo123`.
2. **Usuários → Nova conta.** Nome `Participante 1`, perfil Aluno, e-mail
   `p1@validacao.deltacare.com`, senha provisória `boasvindas`. Criar conta.
   (P2 e P3: mesmo padrão, `p2@…`, `p3@…`.)
3. **Turmas → MED 3A → Adicionar aluno à turma:** escolha o participante. Ele
   passa a cursar Cardiologia I, Anatomia e Fisiologia.
4. Saia da conta de administração.
5. Abra uma **janela anônima** do navegador em <http://127.0.0.1:8000/app/>, na
   tela de login, em tela cheia. Feche outras abas.
6. Escreva num papel, para entregar ao participante:
   `p1@validacao.deltacare.com` · senha `boasvindas`.

Com o observador: ficha nova ([FICHA_DE_OBSERVACAO.md](FICHA_DE_OBSERVACAO.md))
com o código do participante, e cronômetro à mão.

## 3. Abertura (5 minutos)

> *"Obrigado por topar. Estamos desenvolvendo o Delta Care, uma plataforma de
> estudo para uma faculdade de medicina, e queremos ver como alguém que nunca
> usou se sai com ela.*
>
> *Uma coisa importante: quem está sendo testado é o sistema, não você. Se
> algo der errado, é um problema que a gente precisa consertar, e é exatamente
> o que viemos procurar. Não existe resposta errada.*
>
> *Vou te pedir algumas tarefas, uma de cada vez. Enquanto faz, fale em voz
> alta o que está pensando: o que está procurando, o que esperava que
> acontecesse, o que te confundiu. Eu não vou poder te ajudar nem explicar a
> tela, porque quero ver o que acontece quando você está sozinho com ela. Se
> travar, pode desistir da tarefa a qualquer momento e a gente passa para a
> próxima.*
>
> *Antes de começar, leia este termo, por favor."*

Entregue o [termo](TERMO_DE_CONSENTIMENTO.md). Só siga com ele assinado (ou com
o "concordo" registrado, se for à distância). Pergunte e anote na ficha:

- curso e semestre (ou ocupação);
- se já usou alguma plataforma de ensino, e qual;
- se já usou algum assistente de IA (ChatGPT ou parecido) para estudar.

## 4. Tarefas (20 a 25 minutos)

Leia cada cenário em voz alta e entregue-o escrito, se puder. Comece o
cronômetro ao terminar de ler. **Limite de 5 minutos por tarefa:** passou
disso, ou a pessoa desistiu, anote "não concluiu" e siga.

Se o participante perguntar algo, devolva a pergunta: *"O que você acha?"*,
*"Onde você procuraria?"*. Se ficar mudo, lembre: *"O que está pensando
agora?"*. Ajuda direta só para destravar uma tarefa da qual a seguinte depende,
e isso vira "concluiu com ajuda".

O que conta como sucesso está ao lado de cada tarefa, **só para o observador**:
não leia em voz alta.

| # | Cenário (ler em voz alta) | Conta como sucesso |
|---|---|---|
| 1 | *"A secretaria da faculdade te mandou este e-mail e esta senha para o primeiro acesso. Entre na plataforma."* | Entrou e definiu a própria senha |
| 2 | *"Um colega comentou que uma prova mudou de data. Descubra qual prova e para quando."* | Diz: prova de Cardiologia I, próxima quarta-feira |
| 3 | *"Você vai estudar insuficiência cardíaca para Cardiologia. Encontre a aula sobre isso e abra para ler. Depois, deixe-a guardada de um jeito que dê para achar rápido da próxima vez."* | Abriu a Aula 3 e marcou como favorita |
| 4 | *"Na aula de insuficiência cardíaca aparece a dobutamina. Use o assistente da plataforma para descobrir em que situação ela é usada. Depois me diga de onde veio a resposta."* | Diz hipotensão (sistólica abaixo de 90 mmHg) com sinais de hipoperfusão **e** aponta o material citado (Aula 3) |
| 5 | *"Agora pergunte ao assistente como se trata uma pneumonia."* — quando a resposta chegar: *"O que aconteceu? Por que você acha que ele respondeu assim?"* | Entende que o assistente só responde com o material da disciplina. "Não funcionou" ou "deu erro" contam como não concluiu |
| 6 | *"Tem um quiz de insuficiência cardíaca valendo nota. Responda e entregue. Pode consultar o que quiser."* | Entregou o quiz |
| 7 | *"A plataforma dá pontos para quem estuda. Quanto falta para você subir para o próximo nível?"* | Diz um número de XP ou de faixa coerente com a tela |
| 8 | *"Você ficou com uma dúvida sobre o relatório de caso clínico. Mande uma pergunta para o professor de Cardiologia."* | Mensagem enviada na conversa de Cardiologia I |
| 9 | *"Você quer uma cópia de todos os dados que a plataforma guarda sobre você. Consiga essa cópia."* | Baixou o arquivo |

**Por que estas tarefas:** seguem o caminho do aluno numa semana de aula
(entrar, ver o que mudou, estudar, perguntar, entregar, acompanhar o próprio
progresso, falar com o professor) e passam pelas funções que o backlog trata
como centrais. A 5 testa o diferencial do assistente; a 9 testa uma função de
LGPD que fica dentro do perfil, e por isso pode estar escondida demais.

## 5. Questionário e conversa final (5 minutos)

Entregue o [questionário SUS](QUESTIONARIO_SUS.md):

> *"Para fechar, dez afirmações sobre o sistema. Marque o quanto concorda com
> cada uma. Responda rápido, com a primeira impressão."*

Depois, três perguntas abertas (anote as respostas na ficha):

1. *"O que foi mais difícil?"*
2. *"Teve alguma coisa que te surpreendeu, para bem ou para mal?"*
3. *"Se você fosse aluno desta faculdade, usaria o assistente para estudar?
   Por quê?"*

> *"Muito obrigado. Era isso."*

## 6. Logo depois (sem o participante)

- [ ] Facilitador e observador repassam a ficha juntos e dão a gravidade de
      cada problema (escala na ficha) enquanto a memória está fresca.
- [ ] Calcule a nota SUS (instruções no próprio questionário).
- [ ] Guarde a ficha e o questionário fora do repositório se tiverem qualquer
      dado pessoal (o termo assinado tem o nome: **não** vai para o GitHub).
