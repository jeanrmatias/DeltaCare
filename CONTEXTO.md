# Contexto do projeto Delta Care

Resumo do que foi decidido até aqui, pra continuar em outra ferramenta sem perder o fio.

## Estrutura de pastas do front
- Raiz (`/`): arquivos globais — `index.html` (login), `script.js`, `auth.js`, `config.js`, `markdown.js`, `servir.py`, `tokens.css`, `style_index.css`, `style_dashboard.css`, `style_aluno.css`.
- `professor/`: `prof.html` (dashboard), `materiais.html`, `turmas.html` (+ .js de cada).
- `administracao/`: `adm.html`, `adm-turmas.html`, `usuarios.html` (+ .js de cada). **A pasta chama-se `administracao`, mas o valor de `tipo` no banco é `adm`** — os dois já estiveram trocados e quebraram o redirecionamento do login.
- `aluno/`: `inicio.html` (tela inicial), `aluno.html` (chat de estudos), `materiais.html` (+ .js de cada).
- Páginas dentro de subpasta referenciam os arquivos globais com `../` (ex.: `../auth.js`).
- Os `<script>` e `<link>` levam `?v=N`. Ao mexer em .js/.css compartilhado, subir esse número evita o navegador usar a versão antiga.

## Autenticação (feita)
- O login devolve um token opaco (`secrets.token_urlsafe`), guardado na tabela `sessoes` com validade de 12h.
- O front guarda o token e envia em `Authorization: Bearer <token>`; o helper `api()` em `auth.js` centraliza isso e trata 401 mandando de volta ao login.
- Em `main.py`, as dependências `usuario_logado` e `exigir_perfil(...)` são o **único** caminho pelo qual uma rota descobre quem está chamando. Nenhuma rota protegida aceita e-mail vindo do cliente.
- Exceção proposital: `professor_email` em `TurmaRequest` e `aluno_email` em `MatriculaRequest` continuam existindo — ali são o **alvo** da ação (quem recebe a turma, quem é matriculado), não a identidade de quem faz a requisição. Ambas são rotas só de admin.
- Token opaco no banco em vez de JWT: dá pra revogar na hora e não exige gerenciar chave de assinatura. JWT faria sentido com vários serviços validando sem consultar o banco, que não é o caso.
- O primeiro admin nasce só pelo `seed_demo.py`, inserido direto no banco: o cadastro público só cria aluno e `criar_conta_staff` exige um admin já existente.

## Testes
`python backend/testes.py` roda 43 testes num banco temporário (variável `DELTACARE_DB`), sem precisar do Ollama. O foco é o que dá prejuízo se quebrar em silêncio: permissão, visibilidade de material, sessão e integridade do banco ao excluir. Interface e formatação ficam de fora — erro de CSS aparece na tela, erro de permissão não.

## Regras de permissão (todas validadas no backend, não só escondidas na UI)
- Só **admin** cria/exclui turma e matricula/desmatricula aluno.
- Professor só vê as turmas atribuídas a ele (leitura) e gerencia materiais dentro delas.
- Cadastro público (`/cadastro`) só cria conta **aluno**. Professor/admin só são criados por um admin já existente (`POST /admin/usuarios`).
- Aluno só acessa (e só pergunta no chat sobre) turmas em que está matriculado.
- A visão do aluno mora em `regras/aluno.py`, separada de `regras/materiais.py`: lá toda consulta parte do professor dono e **inclui rascunho e agendado**. Misturar as duas na mesma função convidaria a um erro de filtro que vazaria material não liberado.

## Chat de IA do aluno (`regras/chat_ia.py`)
- RAG restrito ao material: só indexa PDF (por enquanto — vídeo/link/doc ficaram de fora do escopo inicial).
- Fluxo: upload de PDF pelo professor → extrai texto (`pypdf`) → divide em chunks → gera embedding → salva.
- Pergunta do aluno → embedding da pergunta → busca por similaridade de cosseno só nos materiais **publicados** (nunca rascunho/agendado) da turma → monta prompt que restringe a resposta ao contexto encontrado → chama o modelo de chat.
- As duas únicas chamadas ao modelo (`gerar_embedding` e `gerar_resposta_chat`) ficam isoladas de propósito no topo do arquivo, recebendo as demais funções como parâmetro (`gerar_embedding_fn`/`gerar_resposta_fn`), pra poder trocar de provedor sem mexer no resto.
- **Hoje roda em Ollama local**: `gpt-oss:20b` (chat) e `nomic-embed-text` (embeddings). Configurável por `OLLAMA_URL`, `MODELO_CHAT`, `MODELO_EMBEDDING` e `ESFORCO_RACIOCINIO`.
- `think: low` no gpt-oss cortou o tempo de resposta pela metade (31s → 13s) sem perder qualidade nos testes — a tarefa é responder a partir de trechos já selecionados, não precisa de raciocínio longo.
- **As fontes citadas vêm de structured output, não de regex.** O schema JSON passado ao Ollama restringe o decodificador, e o `enum` limita as fontes aos títulos reais dos materiais recuperados — o modelo não consegue inventar fonte nem grafar o título diferente. Antes disso a instrução ficava no prompt e o modelo desobedecia de formas variadas (`**FONTES_USADAS:**` em negrito, como item de lista), o que exigia ~90 linhas de regex e limpeza.
- Histórico de chat (pergunta + resposta + fontes citadas) é salvo por aluno/turma e recarregado ao abrir a página.

### Busca híbrida: semântica + literal
Medido com uma apostila de 18 trechos e fatos únicos por seção:

- `TOP_K = 5` perdia informação em 8% das perguntas; com 10, recuperou todas. Dez trechos ocupam ~2,5 mil dos 4096 tokens, deixando folga para a resposta. Catorze deixariam ~570 e arriscariam cortar o texto.
- Só similaridade de cosseno **não basta**. Um trecho de 800 caracteres em que apenas 80 respondem à pergunta tem o embedding dominado pelos outros 720, que costumam ser texto genérico. O trecho que definia o "escore ARR-7" caía para a 7ª posição, atrás de trechos que não respondiam nada, e o modelo dizia que o material não cobria o assunto.
- A correção foi somar um bônus pequeno (`PESO_BUSCA_LITERAL = 0.12`) para trechos que contêm literalmente os termos distintivos da pergunta — siglas, códigos e números, que é o que identifica assunto em texto médico. O trecho do ARR-7 foi para a 1ª posição e nenhuma outra pergunta piorou. Quatro perguntas fora do material (incluindo um "escore XYZ-99" inventado, justamente para tentar enganar o bônus) continuaram sendo recusadas.

**Prefixos do nomic-embed-text foram testados e descartados.** A documentação do modelo sugere `search_query:` e `search_document:`, mas medindo no caso difícil eles pioraram o resultado (posição 4 → 9) sem melhorar os fáceis.

### Por que não dá pra tirar o julgamento do modelo
Medimos os scores de similaridade: pergunta válida deu 0,70 e pergunta fora do material deu 0,65. A margem é estreita demais pra um corte por limiar — qualquer valor que barrasse a pergunta fora do material também barraria uma legítima. Quem decide se o material responde à pergunta é o modelo, e ele acertou em todos os testes. O que é **forma** (formato, validação, limpeza) fica no código; o que é **significado** fica com o modelo.

## O que falta pra virar produto de verdade (não só pitch)
- Sem HTTPS: o token viaja em texto claro. Aceitável em rede local de demonstração, obrigatório antes de qualquer dado real.
- Rate limiting no login/recuperação de senha.
- Trocar SQLite por Postgres (concorrência).
- Storage de arquivo em nuvem (hoje é disco local).
- Serviço de e-mail de verdade pra recuperação de senha (hoje só imprime no console).
- Indexar outros tipos de material pro chat (vídeo precisa de transcrição; link precisa de scraping).
- Contexto de 4096 tokens limita o `TOP_K` a 10 (ver abaixo). Para apostilas muito maiores, o caminho é aumentar o contexto — o que custa VRAM numa GPU já cheia — ou reordenar os trechos com um reranker.
- Módulo de Atividades (Sprint 3 do backlog), chat professor↔aluno, notificações, favoritos e anotações.
- LGPD: política de privacidade e termo de uso.

## Serviço de IA em produção (se for além da demonstração)
- Ollama serializa requisições por padrão; pra vários alunos ao mesmo tempo, o caminho é **vLLM** ou **SGLang**, que fazem *continuous batching*.
- A GPU de desenvolvimento (RX 6750 XT, 12GB) não comporta o gpt-oss:20b inteiro: ~10,5GB cabem na VRAM e o resto (~2,6GB) vai pra CPU, o que explica os 13-20s por resposta. Não há configuração que feche essa diferença.
- A indexação de PDF roda dentro do request em `POST /materiais`, com um embedding sequencial por chunk. Com um PDF grande isso segura a requisição por minutos — precisa virar job em background.
- A busca vetorial carrega todos os chunks da turma e calcula cosseno em Python a cada pergunta. Com material acumulado, precisa de `sqlite-vec` ou `pgvector`.

## Armadilhas já encontradas (pra não repetir)
- **Não usar `uvicorn --reload`**: o reloader deixou um worker órfão segurando a porta 8000 e servindo código antigo; os restarts falhavam com `Errno 10048` em silêncio enquanto o processo fantasma respondia. Depois de reiniciar, conferir o log do bind.
- **`python -m http.server` não manda `Cache-Control`**, só `Last-Modified`. O navegador aplica cache heurístico e serve .js antigo sem revalidar. Use `frontend/servir.py`, que envia `no-store`.
- Ao escrever `servir.py`, usar `ThreadingHTTPServer` e não `socketserver.TCPServer`: o servidor de uma requisição por vez trava na primeira conexão keep-alive do navegador e a página pendura.
- Excluir material ou turma precisa apagar também os trechos indexados (`material_chunks`), as matrículas e o histórico de chat. Sem isso sobram registros órfãos apontando para algo que não existe mais — foram 18 trechos órfãos encontrados de uma vez. Não chega a vazar conteúdo porque a busca usa `JOIN` com `materiais` e o id é `AUTOINCREMENT` (nunca reaproveitado), mas acumula lixo.
- O download de arquivo não pode ser `<a href>`: navegação do navegador não envia o header `Authorization`, e token na URL fica no histórico e nos logs. As telas buscam o arquivo autenticado e abrem via blob.
