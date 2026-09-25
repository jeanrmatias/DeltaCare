/**
 * Gestão de usuários (admin).
 *
 * Fecha o caminho pelo qual professores e administradores entram no sistema.
 * A rota `POST /admin/usuarios` já existia no backend, mas nenhuma tela a
 * chamava — na prática, criar uma conta de professor exigia rodar um script.
 *
 * A administração cria conta de qualquer perfil, inclusive aluno — uma
 * instituição precisa poder cadastrar a turma inteira sem depender de cada
 * aluno se inscrever. O que continua restrito é o caminho contrário: o
 * cadastro público (`/cadastro`) só aceita o tipo "aluno", então ninguém de
 * fora consegue criar para si uma conta de confiança.
 */

const usuario = exigirAcesso("adm");

let usuariosCarregados = [];

if (usuario) {
    montarRodapePerfil(usuario);
    carregarUsuarios();
    ligarFormulario();
    ligarImportacao();
    ligarPlaceholders();
    ligarNotificacoes();
    ligarRodapePerfil();
    document.querySelector("#campoBusca").addEventListener("input", desenharLista);
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

const ROTULOS_PERFIL = {
    adm: "Administrador",
    professor: "Professor",
    aluno: "Aluno",
};

async function carregarUsuarios() {
    const vazio = document.querySelector("#estadoVazio");

    try {
        const resposta = await api("/admin/usuarios");
        const dados = await resposta.json();

        if (!dados.sucesso) {
            vazio.hidden = false;
            vazio.textContent = dados.mensagem || "Não foi possível carregar os usuários.";
            return;
        }

        usuariosCarregados = dados.usuarios || [];
        preencherEstatisticas();
        desenharLista();
    } catch (erro) {
        console.error("Erro ao carregar usuários:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function preencherEstatisticas() {
    const contar = (tipo) => usuariosCarregados.filter((u) => u.tipo === tipo).length;

    document.querySelector("#statAdmins").textContent = contar("adm");
    document.querySelector("#statProfessores").textContent = contar("professor");
    document.querySelector("#statAlunos").textContent = contar("aluno");
}

function desenharLista() {
    const lista = document.querySelector("#listaUsuarios");
    const cartao = document.querySelector("#cartaoLista");
    const vazio = document.querySelector("#estadoVazio");

    const termo = document.querySelector("#campoBusca").value.trim().toLowerCase();
    const filtrados = usuariosCarregados.filter((u) => !termo || u.email.toLowerCase().includes(termo));

    if (filtrados.length === 0) {
        cartao.hidden = true;
        vazio.hidden = false;
        vazio.textContent = usuariosCarregados.length === 0
            ? "Nenhuma conta cadastrada."
            : "Nenhuma conta corresponde à sua busca.";
        return;
    }

    vazio.hidden = true;
    cartao.hidden = false;
    lista.innerHTML = "";

    filtrados.forEach((u) => lista.appendChild(montarLinha(u)));
}

function montarLinha(dados) {
    const linha = document.createElement("article");
    linha.className = "material-linha";

    const info = document.createElement("div");
    info.className = "material-linha-info";

    const topo = document.createElement("div");
    topo.className = "material-linha-topo";

    const badge = document.createElement("span");
    badge.className = `badge-tipo badge-perfil badge-perfil--${dados.tipo}`;
    badge.textContent = ROTULOS_PERFIL[dados.tipo] || dados.tipo;
    topo.appendChild(badge);

    // A conta em uso fica marcada: ajuda a não confundir na demonstração e,
    // no futuro, a impedir que o admin remova o próprio acesso.
    if (dados.email === usuario.email) {
        const marca = document.createElement("span");
        marca.className = "material-turma";
        marca.textContent = "você";
        topo.appendChild(marca);
    }

    const titulo = document.createElement("h3");
    titulo.textContent = dados.nome || dados.email;

    info.appendChild(topo);
    info.appendChild(titulo);

    // O e-mail é a credencial de acesso: fica visível mesmo quando há nome.
    const email = document.createElement("p");
    email.className = "material-descricao";
    email.textContent = dados.email;
    info.appendChild(email);

    const vinculo = descreverVinculo(dados);
    if (vinculo) {
        const p = document.createElement("p");
        p.className = "material-classificacao";
        p.textContent = vinculo;
        info.appendChild(p);
    }

    linha.appendChild(info);
    return linha;
}

function descreverVinculo(dados) {
    if (dados.tipo === "professor") {
        const n = dados.total_turmas || 0;
        const turmas = n === 0
            ? "Nenhuma turma atribuída"
            : `${n} turma${n > 1 ? "s" : ""} atribuída${n > 1 ? "s" : ""}`;
        return dados.disciplinas ? `${turmas} · ${dados.disciplinas}` : turmas;
    }

    if (dados.tipo === "aluno") {
        const n = dados.total_matriculas || 0;
        const partes = [];
        if (dados.matricula) partes.push(`Matrícula ${dados.matricula}`);
        partes.push(n === 0 ? "Sem turma" : `Em ${n} turma${n > 1 ? "s" : ""}`);
        return partes.join(" · ");
    }

    return "Acesso completo à administração";
}

/**
 * Mostra só os campos do perfil escolhido.
 *
 * Pedir matrícula a um administrador ou disciplina a um aluno não é apenas
 * ruído: o campo vazio dá a entender que o dado existe e ficou faltando.
 */
function alternarCamposPorPerfil() {
    const tipo = document.querySelector("#usuarioTipo").value;

    document.querySelector("#camposAluno").hidden = tipo !== "aluno";
    document.querySelector("#camposProfessor").hidden = tipo !== "professor";
}

/** Popula um seletor de turma (usado no cadastro e na importação). */
async function carregarTurmasDoSeletor(alvo = "#usuarioTurma") {
    const seletor = document.querySelector(alvo);
    if (!seletor || seletor.dataset.carregado) return;
    seletor.dataset.carregado = "1";

    try {
        const resposta = await api("/admin/turmas");
        const dados = await resposta.json();

        (dados.turmas || []).forEach((turma) => {
            const opcao = document.createElement("option");
            opcao.value = turma.id;
            opcao.textContent = `${turma.nome} · ${turma.semestre}`;
            seletor.appendChild(opcao);
        });
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
    }
}

function ligarFormulario() {
    const cartao = document.querySelector("#cartaoFormulario");
    const formulario = document.querySelector("#formularioUsuario");
    const mensagem = document.querySelector("#mensagemFormulario");

    document.querySelector("#usuarioTipo").addEventListener("change", alternarCamposPorPerfil);
    alternarCamposPorPerfil();
    carregarTurmasDoSeletor();

    document.querySelector("#botaoNovoUsuario").addEventListener("click", () => {
        cartao.hidden = !cartao.hidden;
        mensagem.textContent = "";
        mensagem.classList.remove("formulario-mensagem--sucesso");
        if (!cartao.hidden) document.querySelector("#usuarioEmail").focus();
    });

    document.querySelector("#botaoCancelar").addEventListener("click", () => {
        cartao.hidden = true;
        formulario.reset();
        mensagem.textContent = "";
    });

    formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const corpo = {
            nome: document.querySelector("#usuarioNome").value.trim(),
            email: document.querySelector("#usuarioEmail").value.trim(),
            senha: document.querySelector("#usuarioSenha").value,
            tipo: document.querySelector("#usuarioTipo").value,
            matricula: document.querySelector("#usuarioMatricula").value.trim(),
            disciplinas: document.querySelector("#usuarioDisciplinas").value.trim(),
        };

        const turmaEscolhida = document.querySelector("#usuarioTurma").value;
        if (corpo.tipo === "aluno" && turmaEscolhida) {
            corpo.turma_id = Number(turmaEscolhida);
        }

        mensagem.textContent = "";
        mensagem.classList.remove("formulario-mensagem--sucesso");

        try {
            const resposta = await api("/admin/usuarios", {
                method: "POST",
                body: JSON.stringify(corpo),
            });
            const dados = await resposta.json();

            mensagem.textContent = dados.mensagem || "";

            if (dados.sucesso) {
                mensagem.classList.add("formulario-mensagem--sucesso");
                formulario.reset();
                alternarCamposPorPerfil();
                await carregarUsuarios();
            }
        } catch (erro) {
            console.error("Erro ao criar conta:", erro);
            mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
        }
    });
}

function ligarPlaceholders() {
    document.querySelectorAll("[data-em-breve]").forEach((elemento) => {
        elemento.addEventListener("click", async (evento) => {
            evento.preventDefault();
            avisar(
                `${elemento.dataset.emBreve} ainda não faz parte desta versão.`,
                "Módulo em construção"
            );
        });
    });
}

/**
 * Importação de alunos em massa.
 *
 * O fluxo tem duas etapas de propósito: primeiro "Conferir planilha", que lê e
 * valida sem gravar nada, e só então "Importar". Uma planilha com metade das
 * linhas erradas não deve criar metade das contas para o admin descobrir
 * depois.
 */
function ligarImportacao() {
    const cartao = document.querySelector("#cartaoImportacao");
    const formulario = document.querySelector("#formularioImportacao");
    const mensagem = document.querySelector("#mensagemImportacao");
    const relatorio = document.querySelector("#relatorioImportacao");
    const botaoImportar = document.querySelector("#botaoImportar");

    if (!cartao) return;

    document.querySelector("#botaoImportarPlanilha").addEventListener("click", () => {
        cartao.hidden = !cartao.hidden;
        document.querySelector("#cartaoFormulario").hidden = true;
        if (!cartao.hidden) carregarTurmasDoSeletor("#importTurma");
    });

    // Trocar o arquivo invalida a conferência anterior.
    document.querySelector("#importArquivo").addEventListener("change", () => {
        botaoImportar.disabled = true;
        relatorio.hidden = true;
        mensagem.textContent = "";
    });

    document.querySelector("#botaoAnalisar").addEventListener("click", async () => {
        const dados = await lerPlanilhaEscolhida();
        if (!dados) return;

        mensagem.textContent = "Conferindo...";
        mensagem.classList.remove("formulario-mensagem--sucesso");

        try {
            const resposta = await api("/admin/importar/analisar", {
                method: "POST",
                body: JSON.stringify(dados),
            });
            const resultado = await resposta.json();

            if (!resultado.sucesso) {
                mensagem.textContent = resultado.mensagem;
                botaoImportar.disabled = true;
                relatorio.hidden = true;
                return;
            }

            mensagem.textContent = "";
            mostrarRelatorio(resultado, false);
            botaoImportar.disabled = resultado.validos.length === 0;
        } catch (erro) {
            console.error("Erro ao conferir planilha:", erro);
            mensagem.textContent = "Não foi possível conferir a planilha.";
        }
    });

    formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const dados = await lerPlanilhaEscolhida();
        if (!dados) return;

        const senha = document.querySelector("#importSenha").value;
        if (senha.length < 6) {
            mensagem.textContent = "A senha provisória precisa ter pelo menos 6 caracteres.";
            return;
        }

        dados.senha_padrao = senha;
        const turma = document.querySelector("#importTurma").value;
        if (turma) dados.turma_id = Number(turma);

        botaoImportar.disabled = true;
        mensagem.textContent = "Importando...";

        try {
            const resposta = await api("/admin/importar", {
                method: "POST",
                body: JSON.stringify(dados),
            });
            const resultado = await resposta.json();

            mensagem.textContent = resultado.mensagem || "";
            if (resultado.sucesso) {
                mensagem.classList.add("formulario-mensagem--sucesso");
                mostrarRelatorio(resultado, true);
                await carregarUsuarios();
            }
        } catch (erro) {
            console.error("Erro ao importar:", erro);
            mensagem.textContent = "Não foi possível importar a planilha.";
        } finally {
            botaoImportar.disabled = false;
        }
    });
}

async function lerPlanilhaEscolhida() {
    const entrada = document.querySelector("#importArquivo");
    const arquivo = entrada.files[0];

    if (!arquivo) {
        await avisar("Escolha uma planilha primeiro.", "Nenhum arquivo");
        return null;
    }

    const base64 = await new Promise((resolver, rejeitar) => {
        const leitor = new FileReader();
        leitor.onload = () => resolver(String(leitor.result).split(",")[1]);
        leitor.onerror = rejeitar;
        leitor.readAsDataURL(arquivo);
    });

    return { arquivo_base64: base64, arquivo_nome: arquivo.name };
}

/**
 * Mostra o que entrou e o que foi recusado, linha a linha.
 *
 * O relatório de rejeição é o ponto do recurso: sem ele, o admin sabe que
 * "faltaram 3" mas não quais nem por quê.
 */
function mostrarRelatorio(resultado, jaImportou) {
    const area = document.querySelector("#relatorioImportacao");
    area.hidden = false;
    area.innerHTML = "";

    const resumo = document.createElement("div");
    resumo.className = "importacao-resumo";

    const aprovados = jaImportou ? (resultado.criados || []).length : (resultado.validos || []).length;
    const recusados = (resultado.rejeitados || []).length;

    const okBloco = document.createElement("span");
    okBloco.className = "importacao-contagem importacao-contagem--ok";
    okBloco.textContent = jaImportou
        ? `${aprovados} conta(s) criada(s)`
        : `${aprovados} linha(s) pronta(s) para importar`;
    resumo.appendChild(okBloco);

    if (recusados > 0) {
        const erroBloco = document.createElement("span");
        erroBloco.className = "importacao-contagem importacao-contagem--erro";
        erroBloco.textContent = `${recusados} rejeitada(s)`;
        resumo.appendChild(erroBloco);
    }

    area.appendChild(resumo);

    if (recusados > 0) {
        const titulo = document.createElement("h3");
        titulo.className = "importacao-titulo";
        titulo.textContent = "Linhas rejeitadas";
        area.appendChild(titulo);

        const lista = document.createElement("ul");
        lista.className = "importacao-rejeitados";

        (resultado.rejeitados || []).forEach((item) => {
            const linha = document.createElement("li");

            const numero = document.createElement("strong");
            numero.textContent = `Linha ${item.linha}`;

            const motivo = document.createElement("span");
            motivo.textContent = [item.email || item.nome, item.motivo].filter(Boolean).join(" — ");

            linha.appendChild(numero);
            linha.appendChild(motivo);
            lista.appendChild(linha);
        });

        area.appendChild(lista);
    }
}
