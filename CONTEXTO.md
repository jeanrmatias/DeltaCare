# Contexto do projeto Delta Care

Resumo do que foi decidido até aqui, pra continuar em outra ferramenta sem perder o fio.

## Estrutura de pastas do front
- Raiz (`/`): arquivos globais — `index.html` (login), `script.js`, `auth.js`, `config.js`, `tokens.css`, `style_index.css`, `style_dashboard.css`, `style_aluno.css`.
- `professor/`: `prof.html`, `materiais.html`, `turmas.html` (+ .js de cada).
- `adm/`: `adm.html`, `adm-turmas.html` (+ .js de cada).
- `aluno/`: `aluno.html` (chat de estudos) + `aluno.js`.
- Páginas dentro de subpasta referenciam os arquivos globais com `../` (ex.: `../auth.js`).

## Regras de permissão (todas validadas no backend, não só escondidas na UI)
- Só **admin** cria/exclui turma e matricula/desmatricula aluno.
- Professor só vê as turmas atribuídas a ele (leitura) e gerencia materiais dentro delas.
- Cadastro público (`/cadastro`) só cria conta **aluno**. Professor/admin só são criados por um admin já existente (`POST /admin/usuarios`).
- Aluno só acessa (e só pergunta no chat sobre) turmas em que está matriculado.

## Chat de IA do aluno (`chat_ia.py`)
- RAG restrito ao material: só indexa PDF (por enquanto — vídeo/link/doc ficaram de fora do escopo inicial).
- Fluxo: upload de PDF pelo professor → extrai texto (`pypdf`) → divide em chunks → gera embedding → salva.
- Pergunta do aluno → embedding da pergunta → busca por similaridade de cosseno só nos materiais **publicados** (nunca rascunho/agendado) da turma → monta prompt que restringe a resposta ao contexto encontrado → chama o modelo de chat.
- As duas únicas chamadas a uma API externa (`gerar_embedding` e `gerar_resposta_chat`) ficam isoladas de propósito no topo de `chat_ia.py`, recebendo as demais funções como parâmetro (`gerar_embedding_fn`/`gerar_resposta_fn`). Isso foi pensado pra poder trocar de provedor sem mexer no resto da lógica.
- Hoje está configurado pra OpenAI (`text-embedding-3-small` + `gpt-4o-mini`, lendo `OPENAI_API_KEY` do ambiente). **Se for trocar por Ollama local**: só reescrever essas duas funções pra chamar `http://localhost:11434/api/...` (embeddings com algo como `nomic-embed-text`, chat com `llama3`/outro modelo local) em vez do SDK da OpenAI — o resto (chunking, busca, prompt, permissões) não muda.
- Histórico de chat (pergunta + resposta + fontes citadas) é salvo por aluno/turma e recarregado ao abrir a página.

## O que falta pra virar produto de verdade (não só pitch)
- **Autenticação real (JWT)** — hoje o backend confia no e-mail que o front manda em cada requisição, sem validar de novo depois do login. É o item mais crítico antes de qualquer dado real de aluno.
- Trocar SQLite por Postgres (concorrência).
- Storage de arquivo em nuvem (hoje é disco local).
- Serviço de e-mail de verdade pra recuperação de senha (hoje só imprime no console).
- Rate limiting no login/recuperação de senha.
- Indexar outros tipos de material pro chat (vídeo precisa de transcrição; link precisa de scraping).
- Módulo de Atividades (Sprint 3 do backlog) e o resto do dashboard do professor, que ainda é mockado (entregas, gráfico, mensagens).
- LGPD: política de privacidade e termo de uso.

## Ambiente de teste usado nesta conversa
Não existe aqui — é só uma referência caso apareça algo estranho em código morto: as funções de negócio (`logica*.py`, `chat_ia.py`) foram testadas com scripts Python direto e com um servidor stub de `http.server` (não FastAPI) porque o sandbox não tinha internet para instalar `fastapi`/`openai`. Isso não faz parte do projeto entregue — só rodou aqui pra validar antes de mandar os arquivos.