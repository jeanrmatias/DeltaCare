# Roteiro de demonstração — Delta Care

Passo a passo fixo para a apresentação. A ideia é não improvisar: cada tela
tem um objetivo, e a ordem foi montada para a última coisa que a banca vê ser
a mais forte.

**Duração estimada:** 8 a 12 minutos.

---

## Antes de começar (15 minutos antes)

Três serviços precisam estar no ar. Abra três terminais e deixe rodando:

```
# 1. Ollama (o modelo de IA)
ollama serve

# 2. Backend
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# 3. Frontend
cd frontend
python servir.py
```

Confira nesta ordem:

- [ ] `ollama list` mostra `gpt-oss:20b` e `nomic-embed-text`
- [ ] <http://127.0.0.1:8000> responde `{"mensagem": "Backend funcionando :)"}`
- [ ] <http://127.0.0.1:5500> abre a tela de login
- [ ] **Faça uma pergunta de teste no chat antes da banca entrar.** A primeira
      resposta carrega o modelo na memória e demora ~30s; as seguintes caem
      para 13-20s. Não gaste esse tempo na frente de ninguém.

Se o banco estiver vazio ou bagunçado:

```
cd backend
python seed_demo.py
```

**Contas** (senha `demo123` nas três): `adm@deltacare.com`,
`professor@deltacare.com`, `aluno@deltacare.com`.

---

## Parte 1 — Administração (2 min)

**Objetivo:** mostrar que existe controle institucional, não é um app solto.

1. Login como `adm@deltacare.com`.
2. Na visão geral, aponte os números: professores, turmas e materiais — todos
   vindos do banco.
3. Vá em **Usuários**. Mostre a lista com os três perfis e abra **Nova conta**.
   Vale criar uma conta de professor ao vivo: é rápido e responde antes de ser
   perguntado como alguém entra no sistema.
4. **Frase-chave:** "Professor e administrador só nascem aqui. Pela tela de
   login existe cadastro público, mas ele só cria conta de aluno — ninguém de
   fora consegue criar para si uma conta de confiança."
5. Vá em **Turmas**. Mostre a turma Cardiologia I, o professor responsável e
   os alunos matriculados.
6. **Frase-chave:** "Quem cria turma e matricula aluno é só a administração.
   O professor não consegue, nem que tente pela API — a regra está no backend."

---

## Parte 2 — Professor (3 min)

**Objetivo:** mostrar o fluxo de trabalho de quem alimenta a plataforma.

1. Saia e entre como `professor@deltacare.com`.
2. No dashboard, aponte: turmas, alunos matriculados, materiais publicados e
   agendados. Se alguém perguntar sobre os cartões tracejados ("Atividades e
   desempenho", "Mensagens"), essa é uma boa hora para dizer: "esses módulos
   ainda não existem, e preferimos declarar isso a preencher a tela com dado
   de exemplo."
3. Vá em **Materiais**. Mostre o PDF já publicado.
4. Abra o formulário de novo material e mostre os três estados:
   **rascunho**, **agendado** e **publicado**.
5. **Frase-chave:** "O aluno só enxerga o que está publicado. Rascunho e
   agendado são invisíveis para ele — e isso vale também para o assistente de
   IA, que não indexa material não liberado."

---

## Parte 3 — Aluno (4 min, é o ponto alto)

**Objetivo:** o diferencial do produto.

1. Saia e entre como `aluno@deltacare.com`.
2. A **tela inicial** abre com os números dele: turmas, materiais disponíveis,
   perguntas já feitas.
3. Vá em **Materiais**: só aparece o material publicado. Se você criou um
   rascunho na Parte 2, mostre que ele **não** está aqui.
4. Abra o **Chat de estudos** e faça as três perguntas na ordem:

   **a) Pergunta que o material responde**
   > Quais são os quatro estágios da Escala DCM-4 e a conduta de cada um?

   Costuma vir como tabela formatada. Aponte a fonte citada no rodapé.

   **b) Pergunta de detalhe**
   > Quando o Cardiolex deve ser interrompido?

   Resposta: pressão sistólica abaixo de 92 mmHg ou frequência acima de
   130 bpm. Esses números só existem no PDF.

   **c) Pergunta fora do material — a mais importante**
   > Qual o tratamento cirúrgico da apendicite?

   Ele **recusa** e sugere perguntar ao professor. Repare que nenhuma fonte
   aparece no rodapé.

5. **Frase-chave (guarde para depois da recusa):** "O modelo sabe responder
   sobre apendicite. Ele se recusou porque não está no material que o
   professor liberou. É isso que separa esta ferramenta de um ChatGPT
   genérico: o aluno não estuda por uma fonte que o professor não validou."

---

## Se perguntarem

**"Os dados vão para a OpenAI?"**
Não. O modelo roda localmente, via Ollama. Nenhum material de aula e nenhuma
pergunta de aluno sai da infraestrutura da instituição — o que importa para
LGPD.

**"E se ele inventar uma resposta?"**
Duas travas. O prompt restringe ao material, e as fontes citadas são validadas
pelo sistema: o modelo só consegue citar um material que realmente foi
recuperado na busca, porque o formato da resposta é imposto no decodificador,
não pedido em texto.

**"Isso escala para a faculdade inteira?"**
A arquitetura sim, com trabalho conhecido: trocar Ollama por vLLM (que atende
várias requisições em paralelo), SQLite por Postgres e o disco local por
storage em nuvem. O README tem o levantamento completo, em "Limitações
conhecidas".

**"Por que demora alguns segundos?"**
Porque o modelo roda numa GPU de desenvolvimento que não comporta ele inteiro.
Em servidor adequado, cai para poucos segundos.

**"É seguro?"**
O login emite um token de sessão, e toda rota deduz quem está chamando a partir
dele. Nenhuma rota aceita identidade informada pelo cliente. O que ainda falta
antes de uso real: HTTPS e limite de tentativas de login.

---

## Se precisar consultar

O [TUTORIAL.md](TUTORIAL.md) descreve cada tela em detalhe, perfil por perfil —
útil se a banca pedir para ver algo fora do roteiro.

## Plano B

**O Ollama caiu ou está muito lento:** o chat mostra "O assistente de IA está
indisponível no momento" em vez de quebrar. Siga para as telas de materiais e
administração, que não dependem dele, e mostre o histórico de conversa já
salvo na turma.

**Alguma tela não carrega:** dê `Ctrl+Shift+R`. Se persistir, confira se os
três serviços continuam rodando.

**A resposta veio sem tabela:** é variação normal do modelo, não é erro. O
conteúdo está correto do mesmo jeito.
