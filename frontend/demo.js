/**
 * Modo demonstração: a plataforma inteira rodando sem servidor.
 *
 * Por que existe: o backend é FastAPI + SQLite + Ollama local. Nada disso roda
 * num deploy estático (Vercel), e sem backend a tela de login não sai do lugar.
 * Em vez de publicar uma casca que não funciona, o front detecta que a API não
 * respondeu e passa a responder a si mesmo, com dados fictícios.
 *
 * Como funciona: `responder()` recebe o mesmo caminho que iria para a API e
 * devolve um `Response` de verdade, no mesmo formato que o backend devolveria.
 * Quem chama (`api()` em auth.js) não sabe a diferença — por isso nenhuma tela
 * precisou ser reescrita.
 *
 * Onde ficam os dados:
 *   - `dados-demo.json`  o conjunto inicial, fictício, versionado no repositório;
 *   - `localStorage`     o que o visitante fizer em cima dele (material criado,
 *                        notificação lida, pergunta ao assistente, XP ganho).
 *
 * Essa separação é proposital: o JSON é o ponto de partida e não muda; o
 * localStorage é o progresso de quem está navegando, e sobrevive ao recarregar
 * a página. O botão "Reiniciar demonstração" no aviso do topo apaga só a
 * segunda parte.
 *
 * O que NÃO é simulado: a verificação de permissão continua acontecendo aqui
 * (aluno não enxerga rascunho, professor não mexe em turma que não é dele),
 * porque uma demonstração que mostra o aluno vendo tudo não demonstra o
 * produto. O que não dá para simular é a garantia: no modo demonstração ela é
 * de fachada, já que o código roda no navegador de quem usa. A garantia de
 * verdade é a do backend, em `backend/main.py`.
 */

const Demo = (function () {
    "use strict";

    const CHAVE_ESTADO = "deltacare_demo_estado";
    const CHAVE_PREFERENCIAS = "deltacare_preferencias";

    // Mesmos valores de backend/regras/aluno.py. Duplicados de propósito: o
    // modo demonstração não fala com o Python, e um XP diferente do real faria
    // a demonstração mentir sobre o produto.
    const XP_POR_PERGUNTA = 10;
    const XP_POR_MATERIAL_ACESSADO = 15;
    const XP_POR_DIA_ATIVO = 25;
    const XP_POR_NIVEL = 150;
    const DIAS_ACOMPANHAMENTO = 14;

    const PAGINAS_POR_PERFIL = {
        adm: "administracao/adm.html",
        professor: "professor/prof.html",
        aluno: "aluno/inicio.html",
    };

    let ativo = false;
    let dados = null;
    let estado = null;

    // ------------------------------------------------------------------
    // Datas
    // ------------------------------------------------------------------

    function agora() {
        return new Date();
    }

    function isoComDeslocamento({ dias = 0, horas = 0 } = {}) {
        const data = agora();
        data.setDate(data.getDate() - dias);
        data.setHours(data.getHours() - horas);
        return data.toISOString();
    }

    function diaDe(iso) {
        return String(iso).slice(0, 10);
    }

    function hoje() {
        return diaDe(agora().toISOString());
    }

    // ------------------------------------------------------------------
    // Carga dos dados e do estado
    // ------------------------------------------------------------------

    /** Caminho do JSON relativo a este arquivo — as páginas ficam em subpastas. */
    function caminhoDosDados() {
        const script = document.querySelector('script[src*="demo.js"]');
        const src = (script && script.getAttribute("src")) || "demo.js";
        return src.replace(/demo\.js.*$/, "dados-demo.json");
    }

    async function carregarDados() {
        if (dados) return dados;

        const resposta = await fetch(caminhoDosDados(), { cache: "no-store" });
        if (!resposta.ok) {
            throw new Error("Não foi possível carregar os dados de demonstração.");
        }

        dados = await resposta.json();
        return dados;
    }

    /** Estado inicial, derivado do JSON. Datas relativas viram datas reais. */
    function estadoInicial() {
        const materiais = dados.materiais.map((material) => {
            const copia = Object.assign({}, material);

            if (material.dias_frente !== undefined) {
                copia.criado_em = isoComDeslocamento({ dias: 0 });
                copia.data_liberacao = diaDe(
                    new Date(Date.now() + material.dias_frente * 86400000).toISOString()
                );
            } else {
                copia.criado_em = isoComDeslocamento({ dias: material.dias_atras || 0 });
                copia.data_liberacao = null;
            }

            copia.atualizado_em = copia.criado_em;
            delete copia.dias_atras;
            delete copia.dias_frente;
            return copia;
        });

        const turmas = dados.turmas.map((turma) => {
            const copia = Object.assign({}, turma);
            copia.criado_em = isoComDeslocamento({ dias: turma.dias_atras || 0 });
            delete copia.dias_atras;
            return copia;
        });

        const notificacoes = dados.notificacoes.map((aviso) => {
            const copia = Object.assign({}, aviso);
            copia.criado_em = isoComDeslocamento({ horas: aviso.horas_atras || 0 });
            delete copia.horas_atras;
            return copia;
        });

        const chat = dados.chat.map((mensagem) => {
            const copia = Object.assign({}, mensagem);
            copia.criado_em = isoComDeslocamento({ horas: mensagem.horas_atras || 0 });
            delete copia.horas_atras;
            return copia;
        });

        const atividade = dados.atividade_aluno || {};
        const acessos = (atividade.materiais_acessados || []).map((item) => ({
            aluno_email: atividade.aluno_email,
            material_id: item.material_id,
            dia: diaDe(isoComDeslocamento({ dias: item.dias_atras })),
        }));
        const perguntas = (atividade.perguntas || []).map((item) => ({
            aluno_email: atividade.aluno_email,
            dia: diaDe(isoComDeslocamento({ dias: item.dias_atras })),
        }));

        return {
            usuarios: dados.usuarios.map((u) => Object.assign({}, u)),
            turmas: turmas,
            materiais: materiais,
            matriculas: dados.matriculas.map((m) => Object.assign({}, m)),
            notificacoes: notificacoes,
            chat: chat,
            acessos: acessos,
            perguntas: perguntas,
            sessoes: {},
            proximoId: 1000,
        };
    }

    function carregarEstado() {
        try {
            const salvo = localStorage.getItem(CHAVE_ESTADO);
            if (salvo) return JSON.parse(salvo);
        } catch (erro) {
            /* localStorage indisponível ou conteúdo inválido: recomeça do JSON */
        }
        return null;
    }

    function salvarEstado() {
        try {
            localStorage.setItem(CHAVE_ESTADO, JSON.stringify(estado));
        } catch (erro) {
            /* modo privado ou cota estourada: a demonstração segue sem persistir */
        }
    }

    async function prepararEstado() {
        await carregarDados();
        if (estado) return;

        estado = carregarEstado() || estadoInicial();
        // Sessão nunca é restaurada do localStorage: quem recarrega a página
        // continua logado pelo sessionStorage do auth.js, e um token órfão aqui
        // deixaria a demonstração num estado que o backend real não teria.
        estado.sessoes = estado.sessoes || {};
    }

    function reiniciar() {
        try {
            localStorage.removeItem(CHAVE_ESTADO);
            localStorage.removeItem(CHAVE_PREFERENCIAS);
        } catch (erro) {
            /* nada a limpar */
        }
        estado = null;
    }

    // ------------------------------------------------------------------
    // Preferências do visitante (filtros, últimas escolhas)
    // ------------------------------------------------------------------
    // Ficam separadas do estado da demonstração porque valem também com o
    // backend real rodando: são do navegador de quem usa, não do servidor.

    function lerPreferencias() {
        try {
            return JSON.parse(localStorage.getItem(CHAVE_PREFERENCIAS) || "{}");
        } catch (erro) {
            return {};
        }
    }

    function gravarPreferencia(chave, valor) {
        try {
            const atuais = lerPreferencias();
            atuais[chave] = valor;
            localStorage.setItem(CHAVE_PREFERENCIAS, JSON.stringify(atuais));
        } catch (erro) {
            /* sem localStorage: a preferência simplesmente não é lembrada */
        }
    }

    function lerPreferencia(chave, padrao) {
        const valor = lerPreferencias()[chave];
        return valor === undefined ? padrao : valor;
    }

    // ------------------------------------------------------------------
    // Consultas auxiliares
    // ------------------------------------------------------------------

    function usuarioPorEmail(email) {
        return estado.usuarios.find((u) => u.email === String(email).toLowerCase().trim()) || null;
    }

    function usuarioDoToken(token) {
        const email = estado.sessoes[token];
        return email ? usuarioPorEmail(email) : null;
    }

    function turmaPorId(id) {
        return estado.turmas.find((t) => t.id === Number(id)) || null;
    }

    function materialPorId(id) {
        return estado.materiais.find((m) => m.id === Number(id)) || null;
    }

    function turmasDoAluno(email) {
        const ids = estado.matriculas
            .filter((m) => m.aluno_email === email)
            .map((m) => m.turma_id);
        return estado.turmas.filter((t) => ids.includes(t.id));
    }

    function statusDoMaterial(material) {
        if (material.rascunho) return "rascunho";
        if (material.data_liberacao && material.data_liberacao > hoje()) return "agendado";
        return "publicado";
    }

    function novoId() {
        estado.proximoId += 1;
        return estado.proximoId;
    }

    function nomeDe(email) {
        const usuario = usuarioPorEmail(email);
        return (usuario && usuario.nome) || email;
    }

    // ------------------------------------------------------------------
    // Respostas
    // ------------------------------------------------------------------

    function json(corpo, status = 200) {
        return new Response(JSON.stringify(corpo), {
            status: status,
            headers: { "Content-Type": "application/json" },
        });
    }

    function erro(mensagem, status = 400) {
        return json({ sucesso: false, mensagem: mensagem, detail: mensagem }, status);
    }

    // ------------------------------------------------------------------
    // Rotas
    // ------------------------------------------------------------------

    const rotas = [];

    function rota(metodo, padrao, executar, perfil) {
        rotas.push({ metodo: metodo, padrao: padrao, executar: executar, perfil: perfil });
    }

    // ----- públicas -----

    rota("POST", /^\/login$/, (ctx) => {
        const usuario = usuarioPorEmail(ctx.corpo.email);
        const senhaOk = ctx.corpo.senha === dados.senha_padrao;

        if (!usuario || !senhaOk) {
            return json({ sucesso: false, mensagem: "E-mail ou senha incorretos." });
        }

        const token = "demo-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
        estado.sessoes[token] = usuario.email;
        salvarEstado();

        return json({
            sucesso: true,
            mensagem: "Login bem-sucedido!",
            pagina: PAGINAS_POR_PERFIL[usuario.tipo],
            email: usuario.email,
            tipo: usuario.tipo,
            nome: usuario.nome,
            token: token,
        });
    });

    rota("POST", /^\/cadastro$/, (ctx) => {
        if (usuarioPorEmail(ctx.corpo.email)) {
            return json({ sucesso: false, mensagem: "Esse e-mail já está cadastrado." });
        }

        estado.usuarios.push({
            id: novoId(),
            email: String(ctx.corpo.email).toLowerCase().trim(),
            tipo: "aluno",
            nome: ctx.corpo.nome || "",
            disciplinas: "",
            matricula: "",
        });
        salvarEstado();

        return json({
            sucesso: true,
            mensagem: "Conta criada! Na demonstração, entre com a senha " + dados.senha_padrao + ".",
        });
    });

    rota("POST", /^\/recuperar-senha$/, () =>
        json({
            sucesso: true,
            mensagem:
                "No modo demonstração não há envio de e-mail. Todas as contas usam a senha " +
                dados.senha_padrao + ".",
        })
    );

    rota("POST", /^\/redefinir-senha$/, () =>
        json({
            sucesso: false,
            mensagem:
                "A troca de senha depende do servidor. No modo demonstração as contas usam a senha " +
                dados.senha_padrao + ".",
        })
    );

    rota("POST", /^\/logout$/, (ctx) => {
        delete estado.sessoes[ctx.token];
        salvarEstado();
        return json({ sucesso: true, mensagem: "Sessão encerrada." });
    });

    // ----- sessão -----

    rota("GET", /^\/eu$/, (ctx) => {
        const turmas =
            ctx.usuario.tipo === "professor"
                ? estado.turmas
                      .filter((t) => t.professor_email === ctx.usuario.email)
                      .map((t) => ({ nome: t.nome, semestre: t.semestre }))
                : ctx.usuario.tipo === "aluno"
                ? turmasDoAluno(ctx.usuario.email).map((t) => ({ nome: t.nome, semestre: t.semestre }))
                : [];

        return json({
            sucesso: true,
            email: ctx.usuario.email,
            tipo: ctx.usuario.tipo,
            nome: ctx.usuario.nome,
            disciplinas: ctx.usuario.disciplinas || "",
            matricula: ctx.usuario.matricula || "",
            turmas: turmas,
        });
    }, "logado");

    // ----- notificações -----

    rota("GET", /^\/notificacoes$/, (ctx) => {
        const minhas = estado.notificacoes
            .filter((n) => n.user_email === ctx.usuario.email)
            .sort((a, b) => (a.criado_em < b.criado_em ? 1 : -1))
            .map((n) => ({
                id: n.id,
                tipo: n.tipo,
                titulo: n.titulo,
                mensagem: n.mensagem,
                link: n.link,
                lida: n.lida,
                criado_em: n.criado_em,
            }));

        return json({
            sucesso: true,
            notificacoes: minhas,
            nao_lidas: minhas.filter((n) => !n.lida).length,
        });
    }, "logado");

    rota("POST", /^\/notificacoes\/(\d+)\/lida$/, (ctx) => {
        const aviso = estado.notificacoes.find(
            (n) => n.id === Number(ctx.partes[1]) && n.user_email === ctx.usuario.email
        );
        if (aviso) {
            aviso.lida = true;
            salvarEstado();
        }
        return json({ sucesso: true });
    }, "logado");

    rota("POST", /^\/notificacoes\/lidas$/, (ctx) => {
        estado.notificacoes
            .filter((n) => n.user_email === ctx.usuario.email)
            .forEach((n) => {
                n.lida = true;
            });
        salvarEstado();
        return json({ sucesso: true });
    }, "logado");

    // ----- professor -----

    rota("GET", /^\/turmas$/, (ctx) => {
        const turmas = estado.turmas
            .filter((t) => t.professor_email === ctx.usuario.email)
            .map((t) => ({
                id: t.id,
                nome: t.nome,
                semestre: t.semestre,
                criado_em: t.criado_em,
                materiais_publicados: estado.materiais.filter(
                    (m) => m.turma_id === t.id && statusDoMaterial(m) === "publicado"
                ).length,
                total_alunos: estado.matriculas.filter((m) => m.turma_id === t.id).length,
            }));

        return json({ sucesso: true, turmas: turmas });
    }, "professor");

    rota("GET", /^\/materiais$/, (ctx) => {
        const turmasDoProfessor = estado.turmas
            .filter((t) => t.professor_email === ctx.usuario.email)
            .map((t) => t.id);

        const filtro = ctx.parametros.get("turma_id");
        const materiais = estado.materiais
            .filter((m) => turmasDoProfessor.includes(m.turma_id))
            .filter((m) => !filtro || m.turma_id === Number(filtro))
            .sort((a, b) => (a.criado_em < b.criado_em ? 1 : -1))
            .map((m) => {
                const turma = turmaPorId(m.turma_id);
                return Object.assign({}, m, {
                    status: statusDoMaterial(m),
                    turma_nome: turma ? turma.nome : "",
                    link_url: m.link_url || null,
                    arquivo_nome: m.arquivo_nome || null,
                });
            });

        return json({ sucesso: true, materiais: materiais });
    }, "professor");

    rota("POST", /^\/materiais$/, (ctx) => {
        const alvos = ctx.corpo.turma_ids || (ctx.corpo.turma_id ? [ctx.corpo.turma_id] : []);

        if (!alvos.length) {
            return erro("Escolha pelo menos uma turma.");
        }

        // Mesma regra do backend: se uma das turmas não for do professor, nada
        // é criado. Publicação parcial deixaria o professor sem saber onde o
        // material entrou.
        const invalida = alvos.find((id) => {
            const turma = turmaPorId(id);
            return !turma || turma.professor_email !== ctx.usuario.email;
        });

        if (invalida) {
            return erro("Uma das turmas escolhidas não é sua.", 403);
        }

        const ids = [];

        alvos.forEach((turmaId) => {
            const id = novoId();
            ids.push(id);
            estado.materiais.push({
                id: id,
                turma_id: Number(turmaId),
                titulo: ctx.corpo.titulo,
                descricao: ctx.corpo.descricao || "",
                tipo: ctx.corpo.tipo,
                link_url: ctx.corpo.link_url || null,
                arquivo_nome: ctx.corpo.arquivo_nome || null,
                assunto: ctx.corpo.assunto || "",
                topico: ctx.corpo.topico || "",
                aula: ctx.corpo.aula || "",
                semestre: ctx.corpo.semestre || "",
                rascunho: Boolean(ctx.corpo.rascunho),
                data_liberacao: ctx.corpo.data_liberacao || null,
                criado_em: agora().toISOString(),
                atualizado_em: agora().toISOString(),
            });

            if (!ctx.corpo.rascunho) {
                avisarAlunosDaTurma(Number(turmaId), ctx.corpo.titulo);
            }
        });

        salvarEstado();

        return json({
            sucesso: true,
            mensagem: "Material salvo.",
            material_ids: ids,
            aviso_demonstracao:
                ctx.corpo.arquivo_base64 && ctx.corpo.tipo === "pdf"
                    ? "No modo demonstração o arquivo não é indexado para o assistente de IA: a indexação depende do servidor."
                    : undefined,
        });
    }, "professor");

    rota("PUT", /^\/materiais\/(\d+)$/, (ctx) => {
        const material = materialPorId(ctx.partes[1]);
        const turma = material && turmaPorId(material.turma_id);

        if (!material || !turma || turma.professor_email !== ctx.usuario.email) {
            return erro("Material não encontrado.", 404);
        }

        const eraRascunho = material.rascunho;
        Object.keys(ctx.corpo).forEach((campo) => {
            if (ctx.corpo[campo] !== null && ctx.corpo[campo] !== undefined) {
                material[campo] = ctx.corpo[campo];
            }
        });
        material.atualizado_em = agora().toISOString();

        if (eraRascunho && !material.rascunho) {
            avisarAlunosDaTurma(material.turma_id, material.titulo);
        }

        salvarEstado();
        return json({ sucesso: true, mensagem: "Material atualizado." });
    }, "professor");

    rota("DELETE", /^\/materiais\/(\d+)$/, (ctx) => {
        const material = materialPorId(ctx.partes[1]);
        const turma = material && turmaPorId(material.turma_id);

        if (!material || !turma || turma.professor_email !== ctx.usuario.email) {
            return erro("Material não encontrado.", 404);
        }

        estado.materiais = estado.materiais.filter((m) => m.id !== material.id);
        estado.acessos = estado.acessos.filter((a) => a.material_id !== material.id);
        salvarEstado();

        return json({ sucesso: true, mensagem: "Material excluído." });
    }, "professor");

    rota("GET", /^\/materiais\/(\d+)\/arquivo$/, (ctx) => {
        const material = materialPorId(ctx.partes[1]);
        const turma = material && turmaPorId(material.turma_id);

        if (!material || !turma || turma.professor_email !== ctx.usuario.email) {
            return erro("Arquivo não encontrado.", 404);
        }

        return arquivoDoMaterial(material);
    }, "professor");

    // ----- aluno -----

    rota("GET", /^\/aluno\/turmas$/, (ctx) =>
        json({
            sucesso: true,
            turmas: turmasDoAluno(ctx.usuario.email).map((t) => ({
                id: t.id,
                nome: t.nome,
                semestre: t.semestre,
            })),
        }),
    "aluno");

    rota("GET", /^\/aluno\/materiais$/, (ctx) => {
        const filtro = ctx.parametros.get("turma_id");
        return json({
            sucesso: true,
            materiais: materiaisVisiveisAoAluno(ctx.usuario.email, filtro),
        });
    }, "aluno");

    rota("GET", /^\/aluno\/materiais\/(\d+)\/arquivo$/, (ctx) => {
        const id = Number(ctx.partes[1]);
        const visiveis = materiaisVisiveisAoAluno(ctx.usuario.email, null);
        const material = visiveis.find((m) => m.id === id);

        if (!material) {
            return erro("Arquivo não encontrado.", 404);
        }

        // Registrado só depois da checagem de permissão, como no backend: o que
        // o aluno não pode ver não entra no acompanhamento dele.
        registrarAcesso(ctx.usuario.email, id);
        return arquivoDoMaterial(material);
    }, "aluno");

    rota("GET", /^\/aluno\/resumo$/, (ctx) => json(resumoDoAluno(ctx.usuario.email)), "aluno");

    rota("GET", /^\/chat\/historico$/, (ctx) => {
        const turmaId = Number(ctx.parametros.get("turma_id"));
        const mensagens = estado.chat
            .filter((m) => m.aluno_email === ctx.usuario.email && m.turma_id === turmaId)
            .map((m) => ({
                papel: m.papel,
                conteudo: m.conteudo,
                fontes: m.fontes || [],
                criado_em: m.criado_em,
            }));

        return json({ sucesso: true, mensagens: mensagens });
    }, "aluno");

    rota("POST", /^\/chat\/perguntar$/, (ctx) => {
        const turmaId = Number(ctx.corpo.turma_id);
        const pergunta = String(ctx.corpo.pergunta || "").trim();

        const matriculado = estado.matriculas.some(
            (m) => m.aluno_email === ctx.usuario.email && m.turma_id === turmaId
        );

        if (!matriculado) {
            return json({ sucesso: false, mensagem: "Você não está matriculado nessa turma." });
        }

        const titulosDaTurma = materiaisVisiveisAoAluno(ctx.usuario.email, turmaId).map(
            (m) => m.titulo
        );

        const escolhida = escolherResposta(pergunta, titulosDaTurma);

        estado.chat.push({
            aluno_email: ctx.usuario.email,
            turma_id: turmaId,
            papel: "user",
            conteudo: pergunta,
            fontes: [],
            criado_em: agora().toISOString(),
        });
        estado.chat.push({
            aluno_email: ctx.usuario.email,
            turma_id: turmaId,
            papel: "assistant",
            conteudo: escolhida.resposta,
            fontes: escolhida.fontes,
            criado_em: agora().toISOString(),
        });
        estado.perguntas.push({ aluno_email: ctx.usuario.email, dia: hoje() });
        salvarEstado();

        return json({ sucesso: true, resposta: escolhida.resposta, fontes: escolhida.fontes });
    }, "aluno");

    // ----- administração -----

    rota("GET", /^\/admin\/turmas$/, () =>
        json({
            sucesso: true,
            turmas: estado.turmas.map((t) => ({
                id: t.id,
                nome: t.nome,
                semestre: t.semestre,
                criado_em: t.criado_em,
                professor_email: t.professor_email,
                total_materiais: estado.materiais.filter((m) => m.turma_id === t.id).length,
            })),
        }),
    "adm");

    rota("POST", /^\/admin\/turmas$/, (ctx) => {
        const professor = usuarioPorEmail(ctx.corpo.professor_email);

        if (!professor || professor.tipo !== "professor") {
            return json({ sucesso: false, mensagem: "Professor não encontrado." });
        }
        if (!ctx.corpo.nome) {
            return json({ sucesso: false, mensagem: "Informe o nome da turma." });
        }
        if (!ctx.corpo.semestre) {
            return json({ sucesso: false, mensagem: "Informe o semestre (ex.: 2026/2)." });
        }

        const repetida = estado.turmas.some(
            (t) =>
                t.professor_email === professor.email &&
                t.nome === ctx.corpo.nome &&
                t.semestre === ctx.corpo.semestre
        );

        if (repetida) {
            return json({
                sucesso: false,
                mensagem: "Esse professor já tem uma turma com esse nome nesse semestre.",
            });
        }

        estado.turmas.push({
            id: novoId(),
            nome: ctx.corpo.nome,
            semestre: ctx.corpo.semestre,
            professor_email: professor.email,
            criado_em: agora().toISOString(),
        });
        salvarEstado();

        return json({ sucesso: true, mensagem: "Turma criada." });
    }, "adm");

    rota("DELETE", /^\/admin\/turmas\/(\d+)$/, (ctx) => {
        const id = Number(ctx.partes[1]);

        if (!turmaPorId(id)) {
            return json({ sucesso: false, mensagem: "Turma não encontrada." });
        }

        // Como no backend: apagar a turma apaga o que depende dela, senão
        // sobram registros órfãos apontando para algo que não existe mais.
        estado.turmas = estado.turmas.filter((t) => t.id !== id);
        estado.materiais = estado.materiais.filter((m) => m.turma_id !== id);
        estado.matriculas = estado.matriculas.filter((m) => m.turma_id !== id);
        estado.chat = estado.chat.filter((m) => m.turma_id !== id);
        salvarEstado();

        return json({ sucesso: true, mensagem: "Turma excluída." });
    }, "adm");

    rota("GET", /^\/admin\/turmas\/(\d+)\/alunos$/, (ctx) =>
        json({
            sucesso: true,
            alunos: estado.matriculas
                .filter((m) => m.turma_id === Number(ctx.partes[1]))
                .map((m) => m.aluno_email),
        }),
    "adm");

    rota("GET", /^\/admin\/professores$/, () =>
        json({
            sucesso: true,
            professores: estado.usuarios.filter((u) => u.tipo === "professor").map((u) => u.email),
        }),
    "adm");

    rota("GET", /^\/admin\/alunos$/, () =>
        json({
            sucesso: true,
            alunos: estado.usuarios.filter((u) => u.tipo === "aluno").map((u) => u.email),
        }),
    "adm");

    rota("GET", /^\/admin\/usuarios$/, () =>
        json({
            sucesso: true,
            usuarios: estado.usuarios.map((u) => ({
                id: u.id,
                email: u.email,
                tipo: u.tipo,
                nome: u.nome || "",
                disciplinas: u.disciplinas || "",
                matricula: u.matricula || "",
                total_turmas: estado.turmas.filter((t) => t.professor_email === u.email).length,
                total_matriculas: estado.matriculas.filter((m) => m.aluno_email === u.email).length,
            })),
        }),
    "adm");

    rota("POST", /^\/admin\/usuarios$/, (ctx) => {
        if (!ctx.corpo.nome || !String(ctx.corpo.nome).trim()) {
            return json({ sucesso: false, mensagem: "Informe o nome." });
        }
        if (usuarioPorEmail(ctx.corpo.email)) {
            return json({ sucesso: false, mensagem: "Esse e-mail já está cadastrado." });
        }

        const tipo = ctx.corpo.tipo;
        const email = String(ctx.corpo.email).toLowerCase().trim();

        estado.usuarios.push({
            id: novoId(),
            email: email,
            tipo: tipo,
            nome: String(ctx.corpo.nome).trim(),
            disciplinas: tipo === "professor" ? ctx.corpo.disciplinas || "" : "",
            matricula: tipo === "aluno" ? ctx.corpo.matricula || "" : "",
        });

        if (tipo === "aluno" && ctx.corpo.turma_id) {
            matricular(email, Number(ctx.corpo.turma_id));
        }

        salvarEstado();
        return json({ sucesso: true, mensagem: "Conta criada." });
    }, "adm");

    rota("POST", /^\/admin\/matriculas$/, (ctx) => {
        const aluno = usuarioPorEmail(ctx.corpo.aluno_email);
        const turma = turmaPorId(ctx.corpo.turma_id);

        if (!aluno || aluno.tipo !== "aluno") {
            return json({ sucesso: false, mensagem: "Aluno não encontrado." });
        }
        if (!turma) {
            return json({ sucesso: false, mensagem: "Turma não encontrada." });
        }

        const resultado = matricular(aluno.email, turma.id);
        salvarEstado();
        return json(resultado);
    }, "adm");

    rota("DELETE", /^\/admin\/matriculas$/, (ctx) => {
        const antes = estado.matriculas.length;
        estado.matriculas = estado.matriculas.filter(
            (m) =>
                !(m.aluno_email === ctx.corpo.aluno_email && m.turma_id === Number(ctx.corpo.turma_id))
        );
        salvarEstado();

        return json(
            antes === estado.matriculas.length
                ? { sucesso: false, mensagem: "Matrícula não encontrada." }
                : { sucesso: true, mensagem: "Aluno desmatriculado." }
        );
    }, "adm");

    rota("POST", /^\/admin\/importar\/analisar$/, (ctx) => json(analisarPlanilha(ctx.corpo)), "adm");

    rota("POST", /^\/admin\/importar$/, (ctx) => {
        const analise = analisarPlanilha(ctx.corpo);

        if (!analise.sucesso) return json(analise);

        let criados = 0;
        analise.validos.forEach((linha) => {
            estado.usuarios.push({
                id: novoId(),
                email: linha.email,
                tipo: "aluno",
                nome: linha.nome,
                disciplinas: "",
                matricula: linha.matricula || "",
            });
            if (ctx.corpo.turma_id) {
                matricular(linha.email, Number(ctx.corpo.turma_id));
            }
            criados += 1;
        });

        salvarEstado();

        return json({
            sucesso: true,
            mensagem: criados + " conta(s) criada(s).",
            criados: criados,
            validos: analise.validos,
            recusados: analise.recusados,
            total: analise.total,
        });
    }, "adm");

    // ------------------------------------------------------------------
    // Regras auxiliares
    // ------------------------------------------------------------------

    function matricular(alunoEmail, turmaId) {
        const jaTem = estado.matriculas.some(
            (m) => m.aluno_email === alunoEmail && m.turma_id === turmaId
        );

        if (jaTem) {
            return { sucesso: false, mensagem: "Esse aluno já está nessa turma." };
        }

        estado.matriculas.push({ aluno_email: alunoEmail, turma_id: turmaId });

        const turma = turmaPorId(turmaId);
        if (turma) {
            estado.notificacoes.push({
                id: novoId(),
                user_email: turma.professor_email,
                tipo: "matricula",
                titulo: "Novo aluno na turma",
                mensagem: nomeDe(alunoEmail) + " foi matriculado(a) em " + turma.nome + ".",
                link: "turmas.html",
                lida: false,
                criado_em: agora().toISOString(),
            });
        }

        return { sucesso: true, mensagem: "Aluno matriculado." };
    }

    function avisarAlunosDaTurma(turmaId, tituloMaterial) {
        const turma = turmaPorId(turmaId);
        if (!turma) return;

        estado.matriculas
            .filter((m) => m.turma_id === turmaId)
            .forEach((matricula) => {
                estado.notificacoes.push({
                    id: novoId(),
                    user_email: matricula.aluno_email,
                    tipo: "material",
                    titulo: "Novo material disponível",
                    mensagem: '"' + tituloMaterial + '" foi publicado em ' + turma.nome + ".",
                    link: "materiais.html",
                    lida: false,
                    criado_em: agora().toISOString(),
                });
            });
    }

    function materiaisVisiveisAoAluno(email, filtroTurma) {
        const ids = turmasDoAluno(email).map((t) => t.id);

        return estado.materiais
            .filter((m) => ids.includes(m.turma_id))
            .filter((m) => statusDoMaterial(m) === "publicado")
            .filter((m) => !filtroTurma || m.turma_id === Number(filtroTurma))
            .sort((a, b) => (a.criado_em < b.criado_em ? 1 : -1))
            .map((m) => {
                const turma = turmaPorId(m.turma_id);
                return {
                    id: m.id,
                    titulo: m.titulo,
                    descricao: m.descricao,
                    tipo: m.tipo,
                    link_url: m.link_url || null,
                    arquivo_nome: m.arquivo_nome || null,
                    assunto: m.assunto,
                    topico: m.topico,
                    aula: m.aula,
                    semestre: m.semestre,
                    criado_em: m.criado_em,
                    turma_id: m.turma_id,
                    turma_nome: turma ? turma.nome : "",
                    professor_email: turma ? turma.professor_email : "",
                };
            });
    }

    function registrarAcesso(email, materialId) {
        estado.acessos.push({ aluno_email: email, material_id: materialId, dia: hoje() });
        salvarEstado();
    }

    function resumoDoAluno(email) {
        const turmas = turmasDoAluno(email);
        const materiais = materiaisVisiveisAoAluno(email, null);

        const perguntas = estado.perguntas.filter((p) => p.aluno_email === email);
        const acessos = estado.acessos.filter((a) => a.aluno_email === email);

        // COUNT(DISTINCT): reabrir o mesmo material cinco vezes conta como um.
        const materiaisAcessados = new Set(acessos.map((a) => a.material_id)).size;
        const diasComAtividade = new Set(
            perguntas.map((p) => p.dia).concat(acessos.map((a) => a.dia))
        );

        const xp =
            perguntas.length * XP_POR_PERGUNTA +
            materiaisAcessados * XP_POR_MATERIAL_ACESSADO +
            diasComAtividade.size * XP_POR_DIA_ATIVO;

        const acompanhamento = [];
        for (let i = DIAS_ACOMPANHAMENTO - 1; i >= 0; i -= 1) {
            const dia = diaDe(isoComDeslocamento({ dias: i }));
            acompanhamento.push({ dia: dia, ativo: diasComAtividade.has(dia) });
        }

        return {
            sucesso: true,
            total_turmas: turmas.length,
            total_materiais: materiais.length,
            perguntas_feitas: perguntas.length,
            turmas: turmas.map((t) => ({
                id: t.id,
                nome: t.nome,
                semestre: t.semestre,
                total_materiais: materiais.filter((m) => m.turma_id === t.id).length,
            })),
            materiais_recentes: materiais.slice(0, 5),
            progresso: {
                xp: xp,
                nivel: Math.floor(xp / XP_POR_NIVEL) + 1,
                xp_no_nivel: xp % XP_POR_NIVEL,
                xp_para_proximo_nivel: XP_POR_NIVEL,
                perguntas: perguntas.length,
                materiais_acessados: materiaisAcessados,
                dias_ativos: diasComAtividade.size,
                sequencia: calcularSequencia(diasComAtividade),
                acompanhamento: acompanhamento,
            },
        };
    }

    /** Dias seguidos com atividade. Começa de ontem quando hoje ainda não teve. */
    function calcularSequencia(dias) {
        let inicio = 0;
        if (!dias.has(hoje())) {
            if (!dias.has(diaDe(isoComDeslocamento({ dias: 1 })))) return 0;
            inicio = 1;
        }

        let sequencia = 0;
        for (let i = inicio; i < 365; i += 1) {
            if (!dias.has(diaDe(isoComDeslocamento({ dias: i })))) break;
            sequencia += 1;
        }
        return sequencia;
    }

    /**
     * Escolhe a resposta do assistente.
     *
     * No modo demonstração não há modelo de linguagem: as respostas são escritas
     * à mão em `dados-demo.json` e casadas por termo. O comportamento que importa
     * demonstrar é outro — que a resposta vem com a fonte, e que pergunta fora do
     * material é **recusada** em vez de respondida por fora.
     */
    function escolherResposta(pergunta, titulosDaTurma) {
        const texto = pergunta.toLowerCase();

        const encontrada = (dados.respostas_ia || []).find((item) =>
            item.termos.some((termo) => texto.includes(termo))
        );

        if (!encontrada) {
            return { resposta: dados.resposta_sem_cobertura, fontes: [] };
        }

        // A fonte só é citada se o material estiver mesmo nas turmas do aluno.
        const fontes = encontrada.fontes.filter((titulo) => titulosDaTurma.includes(titulo));

        if (!fontes.length) {
            return { resposta: dados.resposta_sem_cobertura, fontes: [] };
        }

        return { resposta: encontrada.resposta, fontes: fontes };
    }

    function analisarPlanilha(corpo) {
        const nome = String(corpo.arquivo_nome || "").toLowerCase();

        if (nome.endsWith(".xlsx")) {
            return {
                sucesso: false,
                mensagem:
                    "No modo demonstração a leitura de .xlsx não está disponível — ela é feita no servidor. Envie um CSV para ver o relatório de importação.",
            };
        }

        let texto = "";
        try {
            texto = decodeURIComponent(escape(atob(String(corpo.arquivo_base64 || ""))));
        } catch (erro) {
            try {
                texto = atob(String(corpo.arquivo_base64 || ""));
            } catch (outroErro) {
                return { sucesso: false, mensagem: "Não consegui ler o arquivo enviado." };
            }
        }

        const linhas = texto.split(/\r?\n/).filter((l) => l.trim());
        if (!linhas.length) {
            return { sucesso: false, mensagem: "A planilha está vazia." };
        }

        const separador = linhas[0].includes(";") ? ";" : ",";
        const cabecalho = linhas[0].split(separador).map((c) => c.trim().toLowerCase());

        const indiceDe = (nomes) =>
            cabecalho.findIndex((coluna) => nomes.some((n) => coluna.includes(n)));

        const iNome = indiceDe(["nome", "aluno"]);
        const iEmail = indiceDe(["mail", "correio"]);
        const iMatricula = indiceDe(["matr", "ra", "registro"]);

        if (iNome === -1 || iEmail === -1) {
            return {
                sucesso: false,
                mensagem: "A planilha precisa de uma coluna de nome e uma de e-mail.",
            };
        }

        const validos = [];
        const recusados = [];
        const vistos = new Set();

        linhas.slice(1).forEach((linha, indice) => {
            const colunas = linha.split(separador).map((c) => c.trim());
            const nomeAluno = colunas[iNome] || "";
            const email = (colunas[iEmail] || "").toLowerCase();
            const matricula = iMatricula > -1 ? colunas[iMatricula] || "" : "";
            const numero = indice + 2;

            if (!nomeAluno) {
                recusados.push({ linha: numero, email: email, motivo: "Nome vazio." });
            } else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
                recusados.push({ linha: numero, email: email, motivo: "E-mail inválido." });
            } else if (vistos.has(email)) {
                recusados.push({ linha: numero, email: email, motivo: "E-mail repetido na planilha." });
            } else if (usuarioPorEmail(email)) {
                recusados.push({ linha: numero, email: email, motivo: "E-mail já cadastrado." });
            } else {
                vistos.add(email);
                validos.push({ linha: numero, nome: nomeAluno, email: email, matricula: matricula });
            }
        });

        return {
            sucesso: true,
            total: validos.length + recusados.length,
            validos: validos,
            recusados: recusados,
        };
    }

    // ------------------------------------------------------------------
    // Arquivos
    // ------------------------------------------------------------------

    function arquivoDoMaterial(material) {
        const texto =
            (dados.arquivos && dados.arquivos[String(material.id)]) ||
            "Este material foi criado durante a demonstração.\n\n" +
                "O conteúdo dos arquivos enviados não é guardado no modo demonstração:\n" +
                "o upload depende do servidor. Os materiais que já vêm na demonstração\n" +
                "têm conteúdo de exemplo e podem ser abertos normalmente.\n";

        const nome = material.arquivo_nome || "material.txt";

        if (nome.toLowerCase().endsWith(".pdf")) {
            return new Response(gerarPdf(texto), {
                status: 200,
                headers: { "Content-Type": "application/pdf" },
            });
        }

        return new Response(new Blob([texto], { type: "text/plain;charset=utf-8" }), {
            status: 200,
            headers: { "Content-Type": "text/plain" },
        });
    }

    /**
     * Gera um PDF de verdade a partir de texto.
     *
     * Porte do gerador que o projeto já tem em `backend/seed_demo.py`, escrito à
     * mão pelo mesmo motivo: trazer uma biblioteca de PDF só para exibir um
     * arquivo de exemplo seria desproporcional. Sem isso o visualizador teria de
     * abrir um .txt onde o produto mostra um .pdf, e a demonstração deixaria de
     * mostrar o visualizador nativo do navegador, que é o ponto da tela.
     */
    function gerarPdf(texto, linhasPorPagina = 46) {
        const bytes = [];
        const escrever = (s) => {
            for (let i = 0; i < s.length; i += 1) {
                const codigo = s.charCodeAt(i);
                bytes.push(codigo > 255 ? 63 : codigo); // fora do latin-1 vira "?"
            }
        };

        const escapar = (linha) =>
            linha.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");

        const linhas = texto.split("\n");
        const paginas = [];
        for (let i = 0; i < linhas.length; i += linhasPorPagina) {
            paginas.push(linhas.slice(i, i + linhasPorPagina));
        }

        const idFonte = 1;
        const idCatalogo = 2;
        const idPages = 3;
        const idsPaginas = paginas.map((_, i) => 4 + i * 2);

        const objetos = [
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            "<< /Type /Catalog /Pages " + idPages + " 0 R >>",
            "<< /Type /Pages /Count " + paginas.length + " /Kids [" +
                idsPaginas.map((id) => id + " 0 R").join(" ") + "] >>",
        ];

        paginas.forEach((linhasDaPagina, indice) => {
            const idConteudo = idsPaginas[indice] + 1;
            objetos.push(
                "<< /Type /Page /Parent " + idPages + " 0 R /MediaBox [0 0 595 842] " +
                    "/Resources << /Font << /F1 " + idFonte + " 0 R >> >> " +
                    "/Contents " + idConteudo + " 0 R >>"
            );

            let fluxo = "BT\n/F1 11 Tf\n16 TL\n50 792 Td\n";
            linhasDaPagina.forEach((linha) => {
                fluxo += "(" + escapar(linha) + ") Tj T*\n";
            });
            fluxo += "ET";

            objetos.push("<< /Length " + fluxo.length + " >>\nstream\n" + fluxo + "\nendstream");
        });

        escrever("%PDF-1.4\n");
        const deslocamentos = [];

        objetos.forEach((corpo, indice) => {
            deslocamentos.push(bytes.length);
            escrever(indice + 1 + " 0 obj\n" + corpo + "\nendobj\n");
        });

        const inicioXref = bytes.length;
        escrever("xref\n0 " + (objetos.length + 1) + "\n0000000000 65535 f \n");
        deslocamentos.forEach((deslocamento) => {
            escrever(String(deslocamento).padStart(10, "0") + " 00000 n \n");
        });
        escrever(
            "trailer\n<< /Size " + (objetos.length + 1) + " /Root " + idCatalogo + " 0 R >>\n" +
                "startxref\n" + inicioXref + "\n%%EOF\n"
        );

        return new Blob([new Uint8Array(bytes)], { type: "application/pdf" });
    }

    // ------------------------------------------------------------------
    // Entrada
    // ------------------------------------------------------------------

    async function responder(caminho, opcoes = {}) {
        await prepararEstado();

        const metodo = (opcoes.method || "GET").toUpperCase();
        const [semQuery, query] = String(caminho).split("?");
        const parametros = new URLSearchParams(query || "");

        let corpo = {};
        if (opcoes.body) {
            try {
                corpo = JSON.parse(opcoes.body);
            } catch (erro) {
                corpo = {};
            }
        }

        const cabecalhos = opcoes.headers || {};
        const autorizacao = cabecalhos["Authorization"] || cabecalhos["authorization"] || "";
        const token = autorizacao.toLowerCase().startsWith("bearer ")
            ? autorizacao.slice(7).trim()
            : "";

        for (const item of rotas) {
            if (item.metodo !== metodo) continue;

            const partes = semQuery.match(item.padrao);
            if (!partes) continue;

            const usuario = usuarioDoToken(token);

            if (item.perfil) {
                if (!usuario) {
                    return erro("Sessão inválida ou expirada. Faça login de novo.", 401);
                }
                if (item.perfil !== "logado" && usuario.tipo !== item.perfil) {
                    return erro("Você não tem permissão para esta ação.", 403);
                }
            }

            return item.executar({
                partes: partes,
                parametros: parametros,
                corpo: corpo,
                token: token,
                usuario: usuario,
            });
        }

        return erro("Rota não disponível no modo demonstração: " + metodo + " " + semQuery, 404);
    }

    // ------------------------------------------------------------------
    // Aviso no topo da página
    // ------------------------------------------------------------------

    function mostrarAviso() {
        if (document.querySelector("#avisoDemonstracao")) return;

        const estilo = document.createElement("style");
        estilo.textContent = [
            "#avisoDemonstracao{position:sticky;top:0;z-index:999;display:flex;flex-wrap:wrap;",
            "align-items:center;gap:8px 14px;padding:10px 16px;background:#102542;color:#E7ECFB;",
            "font:500 13px/1.45 'Inter',system-ui,sans-serif;}",
            "#avisoDemonstracao b{color:#FFD79A;font-weight:600;}",
            "#avisoDemonstracao span{flex:1 1 260px;min-width:0;}",
            "#avisoDemonstracao button{background:transparent;color:inherit;border:1px solid rgba(231,236,251,.45);",
            "border-radius:6px;padding:5px 12px;font:inherit;cursor:pointer;}",
            "#avisoDemonstracao button:hover{background:rgba(231,236,251,.12);}",
            "@media (max-width:520px){#avisoDemonstracao{font-size:12px;padding:9px 14px;}}",
        ].join("");

        const barra = document.createElement("div");
        barra.id = "avisoDemonstracao";
        barra.setAttribute("role", "status");

        const texto = document.createElement("span");
        const rotulo = document.createElement("b");
        rotulo.textContent = "Modo demonstração. ";
        texto.appendChild(rotulo);
        texto.appendChild(
            document.createTextNode(
                "O servidor não está rodando, então os dados são fictícios e ficam salvos no seu navegador."
            )
        );

        const botao = document.createElement("button");
        botao.type = "button";
        botao.textContent = "Reiniciar demonstração";
        botao.addEventListener("click", () => {
            reiniciar();
            window.location.reload();
        });

        barra.appendChild(texto);
        barra.appendChild(botao);

        document.head.appendChild(estilo);
        document.body.insertBefore(barra, document.body.firstChild);
    }

    function ativar() {
        if (ativo) return;
        ativo = true;

        if (document.body) {
            mostrarAviso();
        } else {
            document.addEventListener("DOMContentLoaded", mostrarAviso);
        }
    }

    return {
        ativo: () => ativo,
        ativar: ativar,
        responder: responder,
        reiniciar: reiniciar,
        lerPreferencia: lerPreferencia,
        gravarPreferencia: gravarPreferencia,
        // exposto para os testes
        _gerarPdf: gerarPdf,
        _analisarPlanilha: analisarPlanilha,
    };
})();

if (typeof module !== "undefined" && module.exports) {
    module.exports = { Demo };
}
