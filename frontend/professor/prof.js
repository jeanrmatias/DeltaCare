/**
 * Dashboard do professor.
 *
 * Todos os números desta tela vêm da API, e só do semestre vigente. Nada é
 * exemplo: sem dado, cada bloco diz que está vazio. Num sistema que uma
 * faculdade vai avaliar, tela com dado falso levanta a dúvida de o que mais
 * ali não é real — e tela dizendo que um módulo "ainda não existe" quando
 * ele existe é o mesmo problema, ao contrário.
 */

const usuario = exigirAcesso("professor");

if (usuario) {
    montarSaudacao(usuario);
    ligarMenuAvatar();
    ligarNotificacoes();
    carregarResumoTurmas();
    ligarRodapePerfil();
}

const ROTULOS_TIPO = {
    pdf: "PDF",
    documento: "Documento",
    video: "Vídeo",
    link: "Link",
};

const ROTULOS_STATUS = {
    publicado: "Publicado",
    rascunho: "Rascunho",
    agendado: "Agendado",
};

function formatarData(iso) {
    if (!iso) return "";
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

/**
 * Tudo da tela inicial, do semestre vigente.
 *
 * As disciplinas de semestres passados ficam em Semestres anteriores: somá-las
 * aqui faria "Alunos matriculados" crescer a cada semestre sem que o professor
 * tivesse mais aluno nenhum.
 *
 * Cada bloco carrega independente: um erro em mensagens não pode apagar as
 * disciplinas da tela.
 */
async function carregarResumoTurmas() {
    const seletor = document.querySelector("#seletorTurma");

    try {
        const [respostaTurmas, respostaMateriais] = await Promise.all([
            api("/turmas"),
            api("/materiais"),
        ]);

        const todas = (await respostaTurmas.json()).turmas || [];
        const turmas = todas.filter((t) => t.vigente !== false);
        const vigentes = new Set(turmas.map((t) => t.id));
        const materiais = ((await respostaMateriais.json()).materiais || [])
            .filter((m) => vigentes.has(m.turma_id));

        preencherEstatisticas(turmas, materiais);
        montarTurmas(turmas);
        montarMateriaisRecentes(materiais);

        // textContent, e não innerHTML: o nome da disciplina é digitado pela
        // administração e não pode ser interpretado como HTML.
        seletor.textContent = turmas.length === 0
            ? "Nenhuma disciplina"
            : turmas.length === 1
                ? `${turmas[0].nome} · ${turmas[0].semestre}`
                : `${turmas[0].nome} · ${turmas[0].semestre} (+${turmas.length - 1})`;
        seletor.onclick = () => { window.location.href = "turmas.html"; };
    } catch (erro) {
        console.error("Erro ao carregar o resumo:", erro);
        seletor.textContent = "Disciplinas";
    }

    carregarParaCorrigir();
    carregarMensagens();
    carregarAvisos();
}

function preencherEstatisticas(turmas, materiais) {
    const totalAlunos = turmas.reduce((soma, turma) => soma + (turma.total_alunos || 0), 0);
    const publicados = materiais.filter((m) => m.status === "publicado").length;
    const agendados = materiais.filter((m) => m.status === "agendado").length;

    document.querySelector("#statTurmas").textContent = turmas.length;
    document.querySelector("#statAlunos").textContent = totalAlunos;
    document.querySelector("#statMateriaisPublicados").textContent = publicados;
    document.querySelector("#statMateriaisAgendados").textContent = agendados;
}

/** Um item de lista com um número à esquerda e duas linhas de texto. */
function itemComContador(numero, titulo, detalhe, link) {
    const item = document.createElement("li");

    const contador = document.createElement("span");
    contador.className = "contador-nao-lidas";
    contador.textContent = numero;

    const info = document.createElement("div");
    info.className = "recente-info";
    const forte = document.createElement("strong");
    forte.textContent = titulo;
    const linha = document.createElement("span");
    linha.textContent = detalhe;
    info.appendChild(forte);
    info.appendChild(linha);

    item.appendChild(contador);
    item.appendChild(info);

    if (link) {
        item.classList.add("lista-recentes-link");
        item.addEventListener("click", () => { window.location.href = link; });
    }
    return item;
}

function itemVazio(texto) {
    const item = document.createElement("li");
    item.className = "lista-recentes-vazio";
    item.textContent = texto;
    return item;
}

async function carregarParaCorrigir() {
    const lista = document.querySelector("#listaParaCorrigir");
    try {
        const resposta = await api("/atividades");
        const atividades = (await resposta.json()).atividades || [];
        const esperando = atividades
            .filter((a) => a.a_corrigir > 0)
            .sort((a, b) => b.a_corrigir - a.a_corrigir);

        const total = esperando.reduce((soma, a) => soma + a.a_corrigir, 0);
        document.querySelector("#statParaCorrigir").textContent = total;

        lista.textContent = "";
        if (!esperando.length) {
            lista.appendChild(itemVazio("Nada esperando correção."));
            return;
        }
        esperando.slice(0, 5).forEach((atividade) => lista.appendChild(itemComContador(
            atividade.a_corrigir,
            atividade.titulo,
            atividade.turma_nome,
            "atividades.html"
        )));
    } catch (erro) {
        console.error("Erro ao carregar correções:", erro);
        lista.textContent = "";
        lista.appendChild(itemVazio("Não foi possível carregar."));
    }
}

async function carregarMensagens() {
    const lista = document.querySelector("#listaMensagens");
    try {
        const resposta = await api("/mensagens/conversas");
        const conversas = (await resposta.json()).conversas || [];
        const novas = conversas.filter((c) => c.nao_lidas > 0);

        lista.textContent = "";
        if (!novas.length) {
            lista.appendChild(itemVazio("Nenhuma mensagem nova."));
            return;
        }
        novas.slice(0, 4).forEach((conversa) => lista.appendChild(itemComContador(
            conversa.nao_lidas,
            conversa.titulo,
            conversa.ultima_mensagem || conversa.subtitulo,
            "mensagens.html"
        )));
    } catch (erro) {
        console.error("Erro ao carregar mensagens:", erro);
        lista.textContent = "";
        lista.appendChild(itemVazio("Não foi possível carregar."));
    }
}

/** Só aparece quando há aviso: um cartão vazio na tela inicial não diz nada. */
async function carregarAvisos() {
    const cartao = document.querySelector("#cartaoAvisosProfessor");
    const lista = document.querySelector("#listaAvisosProfessor");
    try {
        const resposta = await api("/avisos/recebidos");
        const avisos = ((await resposta.json()).avisos || []).slice(0, 3);
        cartao.hidden = !avisos.length;
        lista.textContent = "";

        avisos.forEach((aviso) => {
            const item = document.createElement("article");
            item.className = "aviso" + (aviso.em_destaque ? " aviso--urgente" : "");
            const titulo = document.createElement("h3");
            titulo.textContent = aviso.urgente ? `Urgente: ${aviso.titulo}` : aviso.titulo;
            const texto = document.createElement("p");
            texto.className = "aviso-conteudo";
            texto.textContent = aviso.conteudo;
            item.appendChild(titulo);
            item.appendChild(texto);
            lista.appendChild(item);
        });
    } catch (erro) {
        console.error("Erro ao carregar avisos:", erro);
    }
}

function montarTurmas(turmas) {
    const lista = document.querySelector("#listaTurmas");
    const vazio = document.querySelector("#semTurmas");

    lista.innerHTML = "";

    if (turmas.length === 0) {
        vazio.hidden = false;
        return;
    }

    vazio.hidden = true;

    turmas.forEach((turma) => {
        const cartao = document.createElement("article");
        cartao.className = "cartao turma-cartao";

        const titulo = document.createElement("h2");
        titulo.textContent = turma.nome;

        const semestre = document.createElement("span");
        semestre.className = "turma-semestre";
        semestre.textContent = turma.semestre;

        const detalhe = document.createElement("p");
        const alunos = turma.total_alunos || 0;
        const publicados = turma.materiais_publicados || 0;
        detalhe.textContent =
            `${alunos} aluno${alunos === 1 ? "" : "s"} · ${publicados} material${publicados === 1 ? "" : "is"}`;

        const link = document.createElement("a");
        link.className = "acao";
        link.href = `materiais.html?turma=${turma.id}`;
        link.textContent = "Ver materiais";

        cartao.appendChild(titulo);
        cartao.appendChild(semestre);
        cartao.appendChild(detalhe);
        cartao.appendChild(link);
        lista.appendChild(cartao);
    });
}

function montarMateriaisRecentes(materiais) {
    const lista = document.querySelector("#listaRecentes");
    lista.innerHTML = "";

    if (materiais.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "lista-recentes-vazio";
        vazio.textContent = "Você ainda não publicou nenhum material.";
        lista.appendChild(vazio);
        return;
    }

    materiais.slice(0, 5).forEach((material) => {
        const item = document.createElement("li");

        const badge = document.createElement("span");
        badge.className = `badge-status badge-status--${material.status}`;
        badge.textContent = ROTULOS_STATUS[material.status] || material.status;

        const info = document.createElement("div");
        info.className = "recente-info";

        const titulo = document.createElement("strong");
        titulo.textContent = material.titulo;

        const detalhe = document.createElement("span");
        const partes = [
            ROTULOS_TIPO[material.tipo] || material.tipo,
            material.turma_nome,
            formatarData(material.criado_em),
        ].filter(Boolean);
        detalhe.textContent = partes.join(" · ");

        info.appendChild(titulo);
        info.appendChild(detalhe);

        item.appendChild(badge);
        item.appendChild(info);
        lista.appendChild(item);
    });
}

function montarSaudacao(usuario) {
    const nome = nomeExibicao(usuario);
    const primeiroNome = nome.split(" ")[0];

    document.querySelector("#saudacao").textContent = `Olá, Prof. ${primeiroNome}`;

    const hoje = new Date();
    const dataFormatada = hoje.toLocaleDateString("pt-BR", {
        weekday: "long",
        day: "2-digit",
        month: "long",
        year: "numeric",
    });
    document.querySelector("#dataHoje").textContent =
        dataFormatada.charAt(0).toUpperCase() + dataFormatada.slice(1);

    const sigla = iniciaisDe(nome);
    document.querySelector("#avatarRodape").textContent = sigla;
    document.querySelector("#nomeRodape").textContent = `Prof. ${nome}`;
    document.querySelector("#botaoAvatar").textContent = sigla;
    document.querySelector("#menuNome").textContent = `Prof. ${nome}`;
    document.querySelector("#menuEmail").textContent = usuario.email;
}

function ligarMenuAvatar() {
    const botao = document.querySelector("#botaoAvatar");
    const lista = document.querySelector("#listaAvatar");

    botao.addEventListener("click", (evento) => {
        evento.stopPropagation();
        lista.hidden = !lista.hidden;
    });

    document.addEventListener("click", () => {
        lista.hidden = true;
    });
}
