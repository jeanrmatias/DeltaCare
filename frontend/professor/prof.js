/**
 * Dashboard do professor.
 *
 * Todos os números desta tela vêm da API. Antes havia calendário, entregas,
 * gráfico de erros e mensagens preenchidos com dados de exemplo (alunos e
 * disciplinas inventados, de outra área que não medicina). Foram removidos:
 * num sistema que uma faculdade vai avaliar, tela com dado falso levanta a
 * dúvida de o que mais ali não é real. Os módulos que ainda não existem
 * aparecem declarados como indisponíveis, não simulados.
 */

const usuario = exigirAcesso("professor");

if (usuario) {
    montarSaudacao(usuario);
    ligarMenuAvatar();
    ligarNotificacoes();
    ligarPlaceholders();
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

async function carregarResumoTurmas() {
    const seletor = document.querySelector("#seletorTurma");

    try {
        const [respostaTurmas, respostaMateriais] = await Promise.all([
            api("/turmas"),
            api("/materiais"),
        ]);

        const turmas = (await respostaTurmas.json()).turmas || [];
        const materiais = (await respostaMateriais.json()).materiais || [];

        preencherEstatisticas(turmas, materiais);
        montarTurmas(turmas);
        montarMateriaisRecentes(materiais);

        if (turmas.length === 0) {
            seletor.textContent = "Nenhuma turma";
            seletor.onclick = () => { window.location.href = "turmas.html"; };
            return;
        }

        const rotulo = turmas.length === 1
            ? `${turmas[0].nome} · ${turmas[0].semestre}`
            : `${turmas[0].nome} · ${turmas[0].semestre} (+${turmas.length - 1})`;

        seletor.innerHTML = `
            ${rotulo}
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
        `;
        seletor.onclick = () => { window.location.href = "turmas.html"; };
    } catch (erro) {
        console.error("Erro ao carregar o resumo:", erro);
    }
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

function ligarPlaceholders() {
    document.querySelectorAll("[data-em-breve]").forEach((elemento) => {
        elemento.addEventListener("click", (evento) => {
            evento.preventDefault();
            avisoEmBreve(elemento.dataset.emBreve);
        });
    });
}

async function avisoEmBreve(nomeFuncionalidade) {
    await avisar(`${nomeFuncionalidade} ainda não faz parte desta versão.`, "Módulo em construção");
}
