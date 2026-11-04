# Delta Care — Sprint 4 · Edge Computing & Computer Systems

**Disciplina:** Edge Computing & Computer Systems (ECCS)
**Opção escolhida:** 2 — parte do backend em C++, com a cpp-httplib e CMake
**Grupo / Projeto:** Delta Care — Challenge Hospital Moinhos de Vento
**Integrantes:** Arthur Veiga Demétrio (RM570056) · Jean Rodrigues Matias (RM571284) · Matheus Marques De Souza (RM573203)
**Repositório:** https://github.com/jeanrmatias/DeltaCare
**Código desta entrega:** [`backend/busca_cpp/`](../backend/busca_cpp) (o serviço) e [`backend/app/infra/busca_cpp.py`](../backend/app/infra/busca_cpp.py) (o Python que o consome)

---

## 1. O que foi feito

A busca do assistente de estudos do Delta Care virou um **serviço HTTP em
C++**. A cada pergunta de um aluno no chat, o backend (Python/FastAPI)
precisa achar, entre todos os trechos de material publicados nas disciplinas
do aluno, os mais parecidos com a pergunta. É o pedaço mais pesado do
backend. Agora ele roda num programa em C++ separado, que:

- guarda os vetores dos trechos **na memória** e só volta ao banco quando um
  professor publica ou apaga material;
- faz a conta da similaridade com instruções **SIMD (SSE2)** do processador;
- responde por uma **API HTTP** (cpp-httplib), que o backend em Python chama
  e que pode ser testada pelo Postman;
- é compilado pelo **CMake**, que baixa as bibliotecas de terceiros com
  versão presa e hash conferido.

Com 18 mil trechos, a busca inteira caiu de **821 ms para 18 ms**, cerca de 46
vezes mais rápida (seção 8). O resultado é **idêntico** ao da busca em Python,
até o último bit, e há teste que garante isso. Se o serviço estiver
desligado ou fora do ar, o chat continua funcionando, com a busca em Python.

---

## 2. Por que a busca do chat

O assistente responde **só com base no material dos professores** (RAG,
geração aumentada por recuperação). Cada PDF publicado é dividido em trechos
de cerca de 800 caracteres, e cada trecho vira um vetor de 768 números (o
*embedding*, gerado pelo modelo `nomic-embed-text`). Trechos sobre o mesmo
assunto têm vetores que apontam para direções parecidas. A cada pergunta:

1. a pergunta vira um vetor do mesmo jeito;
2. a busca calcula o **cosseno** entre esse vetor e o de **cada** trecho que o
   aluno pode ver;
3. os 10 mais parecidos vão para o modelo de linguagem, que redige a resposta.

O passo 2 percorre todos os trechos, a cada pergunta. Em Python, eram duas
coisas caras: **ler do banco** o vetor de todos os trechos (com 18 mil
trechos, 55 MB por pergunta) e **fazer a conta** no interpretador (768
multiplicações e somas por trecho, uma de cada vez). Um curso de medicina
tem muitas disciplinas e muitos PDFs por disciplina, e no modo automático o
chat busca em todas as disciplinas do aluno de uma vez. Era o ponto do
sistema que piorava conforme o material crescia.

**Onde entra o *edge*.** O Delta Care já divide o trabalho entre a borda e a
nuvem. O vetor da pergunta é gerado no servidor da própria instituição
(Ollama local), e a busca também roda lá, ao lado do banco. Só a pergunta e
os 10 trechos escolhidos seguem para a nuvem (Ollama Cloud), que redige a
resposta. Nenhum outro material e nenhum dado de aluno sai da máquina. O
serviço em C++ é a parte da borda que mais trabalhava, agora feita com o
hardware aproveitado de perto: memória em vez de disco, e SIMD em vez de
uma conta por vez.

---

## 3. Arquitetura

```
 Navegador (React)
      │  POST /chat/perguntar
      ▼
 Backend em Python (FastAPI) ─────────────┐
   1. confere sessão e matrícula          │
   2. gera o vetor da pergunta  ──────────┼──▶ Ollama local (nomic-embed-text)
   3. decide quais materiais o            │
      aluno pode ver (publicados,         │
      já liberados)                       │
   4. POST /busca ──────────────┐         │
                                ▼         │
            Serviço em C++ (127.0.0.1:8090)
              índice na memória ◀── lê o banco (SQLite) só quando
              conta com SSE2         algum trecho entra ou sai
                                │
   5. ◀── ids + similaridades ──┘
   6. lê do banco só o texto desses trechos
   7. bônus para termos literais e top 10 ─┼──▶ Ollama Cloud (gpt-oss:20b)
   8. resposta com as fontes              │       redige a resposta
      ◀────────────────────────────────────┘
```

**Quem decide o quê.** O serviço em C++ **só calcula**. A regra de quem vê o
quê (rascunho, material agendado, matrícula) fica no Python, num lugar só:
o backend manda ao serviço a lista dos materiais que o aluno pode ver, e o
serviço não tem como devolver trecho de outro material. O serviço também não
escreve no banco: abre o arquivo só para leitura.

**Quando o serviço falha.** O cliente em Python
([`infra/busca_cpp.py`](../backend/app/infra/busca_cpp.py)) trata como "use
o Python" qualquer uma destas situações: serviço desligado
(`DELTACARE_BUSCA_URL` vazio, o padrão), fora do ar, mais de 2 s sem
responder, resposta que não é o JSON esperado, ou trecho que o serviço não
sabe calcular (linha antiga do banco, ainda em JSON). Depois de uma falha, o
backend espera 30 s antes de tentar de novo, para o aluno não pagar a
tentativa a cada pergunta.

**Os arquivos:**

| Arquivo | O que faz |
|---|---|
| [`busca_cpp/CMakeLists.txt`](../backend/busca_cpp/CMakeLists.txt) | Compilação: baixa e confere as bibliotecas, define as opções de ponto flutuante, cria o serviço e o teste |
| [`busca_cpp/src/servidor.cpp`](../backend/busca_cpp/src/servidor.cpp) | A API HTTP (cpp-httplib): rotas, validação da entrada, erros em JSON |
| [`busca_cpp/src/indice.hpp`](../backend/busca_cpp/src/indice.hpp), [`indice.cpp`](../backend/busca_cpp/src/indice.cpp) | Os vetores do banco na memória; percebe quando o banco mudou e recarrega; a busca e o corte |
| [`busca_cpp/src/similaridade.hpp`](../backend/busca_cpp/src/similaridade.hpp), [`similaridade.cpp`](../backend/busca_cpp/src/similaridade.cpp) | A conta: produto escalar com soma compensada, em SSE2 |
| [`busca_cpp/testes/teste_similaridade.cpp`](../backend/busca_cpp/testes/teste_similaridade.cpp) | Teste da conta em C++ (ctest) |
| [`busca_cpp/postman_busca_cpp.json`](../backend/busca_cpp/postman_busca_cpp.json) | Coleção do Postman com as rotas |
| [`busca_cpp/medir.py`](../backend/busca_cpp/medir.py) | Cronometra a busca com e sem o serviço |
| [`app/infra/busca_cpp.py`](../backend/app/infra/busca_cpp.py) | O cliente em Python, com a volta para a busca em Python |
| [`app/regras/chat_ia.py`](../backend/app/regras/chat_ia.py) | `buscar_trechos_relevantes`: onde o backend chama o serviço |

---

## 4. As APIs

O serviço escuta em `http://127.0.0.1:8090` (porta em `DELTACARE_BUSCA_PORTA`).
Só em 127.0.0.1, de propósito: quem chama é o backend, na mesma máquina, e o
navegador do aluno nunca fala com o serviço. Por isso não há login nas
rotas: a sessão e a permissão são conferidas no backend, antes. Todas as
respostas são JSON em UTF-8.

### `GET /saude`

Responde enquanto o processo está de pé.

```
$ curl http://127.0.0.1:8090/saude
{"status":"ok"}
```

### `GET /indice`

O que está na memória. Serve para conferir que o serviço leu o banco certo.

```
$ curl http://127.0.0.1:8090/indice
{"banco":"deltacare.db","bytes_na_memoria":125952,"carregado_em":"2026-11-04T02:47:26Z",
 "dimensao":768,"fora_do_indice":0,"recargas":1,"trechos":41}
```

| Campo | Significado |
|---|---|
| `trechos` | Trechos de material no índice |
| `dimensao` | Números por vetor (768 com o `nomic-embed-text`) |
| `bytes_na_memoria` | Memória dos vetores: 41 × 768 × 4 bytes = 125.952 |
| `fora_do_indice` | Trechos sem vetor binário (linhas antigas, em JSON). Com algum, a busca desses materiais é feita em Python |
| `recargas` | Quantas vezes o índice foi lido do banco desde que o serviço subiu |
| `carregado_em` | Hora da última leitura, em UTC |

### `POST /busca`

A busca. O corpo:

| Campo | Tipo | Obrigatório | Significado |
|---|---|---|---|
| `pergunta` | lista de números | sim | O vetor da pergunta, já normalizado (1 a 4096 números finitos) |
| `materiais` | lista de inteiros | sim | Os ids dos materiais que o aluno pode ver. Trecho de outro material nunca volta |
| `top_k` | inteiro | não (10) | Quantos trechos a busca quer no fim (1 a 100) |
| `folga` | número | não (0) | O bônus máximo que o Python ainda pode somar a um trecho (ver abaixo) |

A resposta:

| Campo | Significado |
|---|---|
| `trechos` | `[{"id", "similaridade"}]`, em ordem de id: os candidatos ao top-k |
| `considerados` | Trechos dos materiais pedidos |
| `fora_do_indice` | Desses, quantos o serviço não calculou. Se for maior que 0, o backend refaz a busca em Python |
| `milissegundos` | Tempo da busca dentro do serviço |

**Por que volta mais que `top_k`.** O backend dá um pequeno bônus ao trecho
que contém, ao pé da letra, um termo raro da pergunta (o nome de um remédio,
uma sigla). Com o bônus, o 15º trecho por similaridade pode subir para o
top 10. O serviço devolve todo trecho com similaridade ≥ (a `top_k`-ésima
melhor − `folga`), que são exatamente os que ainda podem chegar ao top-k. O
Python soma o bônus e escolhe os 10. Com `folga` 0, voltam só os `top_k`
melhores (mais os empates).

Exemplo real, no banco de demonstração, com a pergunta igual ao vetor de um
trecho da "Aula 3 - Insuficiência cardíaca aguda" (id 75). O vetor tem 768
números e está abreviado aqui:

```
$ curl -X POST http://127.0.0.1:8090/busca -H "Content-Type: application/json" \
       -d '{"pergunta": [0.0067, 0.103, ...], "materiais": [1, 2, ..., 14], "top_k": 3, "folga": 0}'
{"considerados":41,"fora_do_indice":0,"milissegundos":0.0508,
 "trechos":[{"id":73,"similaridade":0.7957140262664726},
            {"id":74,"similaridade":0.828609716650849},
            {"id":75,"similaridade":1.0000000042202486}]}
```

Os três vêm da mesma aula, e o próprio trecho vem com similaridade 1, como
deveria. (O 1,0000000042 em vez de 1 exato é a precisão do float32 em que o
vetor é guardado: 7 casas.)

**Erros.** Pedido malformado recebe **400**, com o motivo:

```
$ curl -X POST http://127.0.0.1:8090/busca -d '{"pergunta": []}'
{"erro":"\"pergunta\" precisa ser uma lista de 1 a 4096 números"}

$ curl -X POST http://127.0.0.1:8090/busca -d 'lixo'
{"erro":"o corpo precisa ser um objeto JSON"}

$ curl -X POST http://127.0.0.1:8090/busca -d '{"pergunta":[1,0],"materiais":[1],"top_k":0}'
{"erro":"\"top_k\" precisa ser um inteiro de 1 a 100"}
```

Erro dentro do serviço (o banco travado por mais de 2 s, por exemplo) recebe **500** com
`{"erro": "..."}`, em vez de derrubar o processo. Corpo acima de 4 MB é
recusado pela própria cpp-httplib.

**No Postman:** importe
[`backend/busca_cpp/postman_busca_cpp.json`](../backend/busca_cpp/postman_busca_cpp.json).
Ela traz as quatro chamadas acima, com a variável `base` apontando para
`http://127.0.0.1:8090`.

---

## 5. Como compilar

**Precisa de:** CMake 3.16 ou mais novo, um compilador C++17 e internet na
primeira configuração (o CMake baixa as bibliotecas de terceiros).

```
cd backend/busca_cpp
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
ctest --test-dir build -C Release
```

O executável sai em `build/busca_cpp` (Linux, MinGW, Ninja) ou em
`build/Release/busca_cpp.exe` (Visual Studio).

| Sistema | Compilador |
|---|---|
| Windows | Visual Studio 2022 com "Desenvolvimento para desktop com C++", ou MinGW-w64 |
| Linux | `sudo apt install cmake g++` |
| macOS | `xcode-select --install` e `brew install cmake` |

**Sem compilador instalado no Windows**, foi assim que compilamos, só com
pacotes do Python, sem instalar nada no sistema. O zig traz um Clang
completo:

```
python -m venv ferramentas
ferramentas\Scripts\pip install cmake ninja ziglang
```

O CMake precisa de um programa para o compilador e outro para o
arquivador. Crie `zig-ar.cmd` com a linha
`@"<caminho>\ferramentas\Lib\site-packages\ziglang\zig.exe" ar %*` e
`zig-ranlib.cmd` com o mesmo `zig.exe`, trocando `ar` por `ranlib`. Depois:

```
set ZIG=<caminho>\ferramentas\Lib\site-packages\ziglang\zig.exe
ferramentas\Scripts\cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_MAKE_PROGRAM=<caminho>\ferramentas\Scripts\ninja.exe ^
  -DCMAKE_C_COMPILER=%ZIG% -DCMAKE_C_COMPILER_ARG1=cc ^
  -DCMAKE_CXX_COMPILER=%ZIG% -DCMAKE_CXX_COMPILER_ARG1=c++ ^
  -DCMAKE_AR=<caminho>\zig-ar.cmd -DCMAKE_RANLIB=<caminho>\zig-ranlib.cmd
ferramentas\Scripts\cmake --build build -j 2
```

**O que foi testado:** Windows 11 com o Clang 21.1 do zig 0.16 (compila sem
nenhum aviso com `-Wall -Wextra`; serviço, ctest e suíte do backend
rodados), e compilação cruzada para Linux x86-64 com o mesmo Clang (gera o
executável; não foi executado num Linux). Visual Studio e GCC não foram
testados nesta máquina; o CMakeLists já traz as opções de cada um.

**As bibliotecas de terceiros**, todas com versão presa e SHA-256 conferido
pelo CMake:

| Biblioteca | Versão | Para quê | Licença |
|---|---|---|---|
| [cpp-httplib](https://github.com/yhirose/cpp-httplib) | 0.18.1 | Servidor HTTP, só um cabeçalho | MIT |
| [nlohmann/json](https://github.com/nlohmann/json) | 3.11.3 | Ler e escrever JSON, só um cabeçalho | MIT |
| [SQLite](https://www.sqlite.org) | 3.46.1 | Ler o banco do backend; compilado junto (a "amalgamation", o SQLite inteiro num `.c`) | Domínio público |

Se o arquivo baixado não for byte a byte o esperado, a configuração para com
erro, em vez de compilar outra coisa.

---

## 6. Como rodar localmente

Três terminais, todos a partir da raiz do repositório. Os passos do backend e
das telas são os do [README](../README.md#como-rodar); o que muda é o
serviço e uma variável.

**1. O serviço em C++**, de dentro de `backend/`, para ele achar o
`deltacare.db`:

```
cd backend
busca_cpp/build/busca_cpp              (Windows com VS: busca_cpp\build\Release\busca_cpp.exe)
```

Ele mostra `Busca em C++ no ar: http://127.0.0.1:8090  (41 trechos de deltacare.db)`.
O banco pode ser outro: `busca_cpp/build/busca_cpp caminho/do/banco.db`.

**2. O backend, dizendo onde está o serviço:**

```
cd backend
set DELTACARE_BUSCA_URL=http://127.0.0.1:8090          (Linux/macOS: export DELTACARE_BUSCA_URL=...)
uvicorn main:app --app-dir app
```

**3. As telas:** `cd frontend && npm run dev`, e o chat do aluno já usa o
serviço. Para conferir: <http://127.0.0.1:8090/indice> mostra os trechos
carregados, e o campo `recargas` sobe quando um professor publica um PDF.

A ordem não importa. Se o backend subir antes do serviço, as primeiras
perguntas usam a busca em Python, e o backend passa a usar o serviço até 30
s depois de ele subir.

---

## 7. Testes

**Em C++** (`ctest --test-dir build`): o
[`teste_similaridade.cpp`](../backend/busca_cpp/testes/teste_similaridade.cpp)
confere a conta com valores feitos à mão. São 13 verificações, entre elas:
vetor igual dá 1; perpendicular dá 0; oposto dá −1; vetor de tamanho
diferente é comparado até o menor; vetor vazio não lê memória fora dele;
bytes desalinhados na memória são lidos certo; tamanho que não é múltiplo
de 4 é recusado; a soma compensada acerta `1e16 + 1 + 1 − 1e16 = 2` (a soma
comum daria 0); e o caminho SIMD dá o mesmo que o caminho comum, bit a bit.

**No backend** ([`backend/testes/testes.py`](../backend/testes/testes.py)):

- `TestesServicoDeBuscaCpp` sobe o **executável de verdade** num banco
  temporário e confere que a busca com o serviço devolve **exatamente** o
  mesmo que sem ele: os mesmos trechos, na mesma ordem, com a mesma
  similaridade até o último bit, com e sem termo literal na pergunta.
  Confere também que material em rascunho ou agendado nunca aparece, que
  material novo entra sem reiniciar o serviço, que linha antiga em JSON faz
  a busca cair no Python, e que pedido malformado recebe 400.
- `TestesClienteDaBuscaCpp` imita o serviço fora do ar, respondendo lixo ou
  sem saber calcular um trecho, e confere que o chat cai no Python e espera
  antes de tentar de novo. Esses rodam mesmo sem o executável compilado; os
  do serviço são pulados, com aviso, quando não há executável.

A suíte inteira tem 660 testes e passa (`python testes/testes.py`, de dentro
de `backend/`).

**Os testes pegam defeito de verdade.** Para conferir, estragamos de
propósito a comparação dentro da conta SIMD (`_mm_cmpge_pd` trocado por
`_mm_cmplt_pd`, que inverte a escolha da compensação) e recompilamos. O
ctest reprovou, e o teste do serviço reprovou as duas perguntas. Depois o
código foi restaurado, e tudo passou de novo.

---

## 8. Medidas

Feitas com [`busca_cpp/medir.py`](../backend/busca_cpp/medir.py) numa máquina
com AMD Ryzen 5 7600, Windows 11 e Python 3.14. O script cria um banco
temporário com trechos sorteados de 768 dimensões, sobe o serviço e
cronometra `buscar_trechos_relevantes`, a mesma função que o chat chama,
pelos dois caminhos (melhor de 5 repetições). Antes de anotar o tempo, ele
confere que os dois caminhos deram o mesmo resultado. Como numa disciplina
de verdade, 1% dos trechos é parecido com a pergunta e o resto não.

**A busca inteira** (banco + conta + texto dos escolhidos):

| Trechos | Situação | Python | C++ | Vezes mais rápido |
|---:|---|---:|---:|---:|
| 41 | o banco de demonstração | 2,3 ms | 3,9 ms | 0,6× |
| 3.000 | uma disciplina com uns 30 PDFs | 113,0 ms | 4,5 ms | 25× |
| 18.000 | modo automático: seis disciplinas | 820,9 ms | 17,9 ms | 46× |

Com 41 trechos o C++ **perde**: a busca toda leva 2 ms, e só a chamada HTTP
custa mais que isso. O serviço compensa quando há material de verdade, e é
aí que ele faz diferença: com 18 mil trechos, o aluno esperava quase um
segundo a mais por pergunta só na busca.

**A conta sozinha** (sem banco nem HTTP), medida durante o desenvolvimento,
com 18 mil trechos. Mostra o que cada decisão rendeu:

| Versão | Tempo da conta | O que mudou |
|---|---:|---|
| Python (`sum(map(operator.mul, ...))`) | 351 ms | — |
| C++, um trecho por vez | ≈ 14 ms | o laço vira instruções de máquina |
| C++, quatro trechos intercalados | 14,5 ms | nenhum ganho (ver seção 9) |
| C++, quatro trechos em SSE2 | 7,8 ms | duas contas por instrução |

---

## 9. Conceitos de Computer Systems aplicados

**Representação de números (IEEE 754).** Cada vetor fica no banco em
float32: 4 bytes por número, 3 KB por trecho. A pergunta chega em double (8
bytes). A conversão de float32 para double é exata, porque todo float32 cabe
num double, e é por isso que o C++ e o Python partem dos mesmos valores. Os
bytes são lidos com `memcpy` em vez de converter o ponteiro: não dependem
do alinhamento do bloco na memória (há teste com bloco desalinhado), e a
ordem dos bytes (*little-endian*) é a mesma de quem gravou, porque é a
mesma máquina.

**Por que o resultado é idêntico, e não só parecido.** Somar números de
ponto flutuante em outra ordem, ou com outro arredondamento, muda a última
casa. Três cuidados garantem o mesmo resultado do Python:
1. **A mesma soma.** Desde a versão 3.12, o `sum()` do Python usa a soma
   compensada de Neumaier: guarda à parte o que cada adição perde no
   arredondamento e devolve no fim. O C++ faz exatamente o mesmo, na mesma
   ordem. Com a soma comum, 282 de 300 trechos de teste dariam diferente na
   última casa.
2. **Sem FMA.** Processadores modernos têm uma instrução que calcula
   `a × b + c` arredondando uma vez só, em vez de duas. É mais rápida, mas
   muda o resultado. O compilador usa essa instrução sozinho quando pode
   (em ARM, sempre). O CMakeLists proíbe com `-ffp-contract=off`.
3. **Sem `-ffast-math`**, que autoriza o compilador a reordenar somas.

**SIMD.** Um registrador SSE2 tem 128 bits, ou seja, dois doubles. Uma
instrução `_mm_add_pd` soma dois pares ao mesmo tempo. A conta processa
quatro trechos juntos, em dois registradores, e cada "pista" do registrador
faz exatamente as operações da versão comum. A escolha "se a soma é maior,
compensa assim; senão, assado" não pode ser um `if`, porque cada pista pode
querer um lado. Por isso as duas expressões são calculadas, e uma máscara de
bits escolhe pista a pista. SSE2 é o mínimo de todo processador x86-64, então
não exclui nenhuma máquina desse tipo. Em ARM, o código usa a versão comum.

**Onde estava o gargalo.** A primeira tentativa foi intercalar quatro
trechos no código comum, para o processador não ficar esperando cada soma
terminar antes de começar a próxima. Não ganhou nada (cerca de 14 ms
antes e depois), e a medida mostrou o motivo: o laço não estava esperando, estava
ocupado. São cerca de 10 operações de ponto flutuante por número, e o
processador já fazia todas no ritmo máximo. O ganho só veio quando cada
instrução passou a fazer duas contas (SIMD).

**Memória × disco.** O maior ganho não foi a conta, foi não ler. Em Python,
cada pergunta lia do SQLite 55 MB de vetores (18 mil × 3 KB). O serviço lê
uma vez e guarda na memória. Para saber se precisa reler, consulta o
`PRAGMA data_version` do SQLite (custa quase nada e muda quando outra
conexão grava algo). Só se mudou, conta os trechos e pega o maior id, duas
consultas que usam índice e não tocam nos vetores. Trechos nunca são
editados no lugar (reindexar apaga e insere com id novo), então essas duas
contagens bastam para saber se mudaram.

**Concorrência.** A cpp-httplib atende cada requisição numa thread. Várias
buscas leem o índice ao mesmo tempo, com `std::shared_mutex` em modo
compartilhado. A recarga monta o índice novo fora da trava e só troca no
fim, em modo exclusivo, então uma busca nunca vê o índice pela metade. O
banco está em modo WAL, e o serviço lê enquanto o backend em Python escreve.

**Recursos (RAII).** Toda consulta ao SQLite é um objeto que se finaliza no
destrutor. Não há caminho, nem com exceção, em que uma consulta fique aberta
segurando o banco.

**Compilação.** O CMake separa o código em uma biblioteca estática (`nucleo`:
a conta e o índice), o executável do serviço e o do teste, que usa a mesma
biblioteca sem HTTP. O SQLite é compilado junto, como código C, e não
depende de o sistema ter a biblioteca instalada. No MinGW o executável é
ligado estaticamente, para não depender de DLLs fora do PATH.

**Rede.** O serviço só escuta em 127.0.0.1 (*loopback*): a requisição não
passa pela placa de rede e não é alcançável de fora da máquina. O cliente em
Python ignora `HTTP_PROXY` de propósito, para um proxy configurado no
sistema não mandar a pergunta para fora. No Windows, conectar numa porta
local fechada leva uns 2 s até desistir. Por isso o serviço é desligado por
padrão (quem não o subiu não paga a espera), e depois de uma falha o
backend espera 30 s antes de tentar de novo.

---

## 10. Limitações

- **Roda localmente, como a entrega pede; não está no servidor de produção.**
  O servidor de demonstração no Azure segue com a busca em Python. Pôr o
  serviço lá exige compilar no servidor e criar um serviço no systemd.
- **Memória:** 3 KB por trecho. 18 mil trechos são 55 MB, e 100 mil seriam
  cerca de 300 MB.
- **Sem login nas rotas:** seguro porque o serviço só escuta em 127.0.0.1. Se
  um dia rodar em outra máquina, precisa de autenticação entre o backend e
  ele.
- **Visual Studio e GCC não foram testados aqui** (seção 5).
- **Banco pequeno:** abaixo de algumas centenas de trechos, a chamada HTTP
  custa mais que a busca em Python (seção 8).

---

## 11. Uso de IA

Como no resto do projeto (ver o [README](../README.md#onde-e-como-usamos-inteligência-artificial-no-desenvolvimento)),
usamos o **Claude Code** como par de programação. A equipe definiu o que
fazer e os critérios (mesmo resultado do Python, o chat não pode parar se o
serviço cair, a regra de visibilidade fica no Python). A IA propôs e
escreveu a implementação, e a equipe revisou, testou e mediu. A primeira
versão era uma biblioteca carregada direto pelo Python (ctypes), sem HTTP.
Foi refeita como serviço HTTP com cpp-httplib e CMake quando conferimos as
instruções da opção 2 da disciplina. O teste de mutação da seção 7 foi feito
para confirmar que os testes pegam defeito.
