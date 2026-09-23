/**
 * Tela inicial do aluno.
 *
 * Tudo aqui vem da API (`/aluno/resumo`): números, turmas e materiais recentes.
 * Nada é exemplo fixo — se não houver dado, a tela mostra o estado vazio em vez
 * de preencher com conteúdo inventado.
 */

const usuario = exigirAcesso("aluno");

if (usuario) {
    montarRodapePerfil(usuario);
    carregarResumo();
    ligarPlaceholders();
    document.querySelector("#botaoSair").addEventListener("click", sair);
}

function nomeAPartirDoEmail(email) {
    const apelido = (email || "").split("@")[0].replace(/[._-]+/g, " ");
    return apelido
        .split(" ")
        .filter(Boolean)
        .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
        .join(" ");
}

function iniciais(nome) {
    const partes = (nome || "").trim().split(/\s+/).filter(Boolean);
    if (partes.length === 0) return "--";
    if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
    return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function montarRodapePerfil(usuario) {
    const nome = nomeAPartirDoEmail(usuario.email);
    document.querySelector("#saudacao").textContent = `Olá, ${nome}`;
    document.querySelector("#avatarRodape").textContent = iniciais(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

const ROTULOS_TIPO = {
    pdf: "PDF",
    documento: "Documento",
    video: "Vídeo",
    link: "Link",
};

function formatarData(iso) {
    if (!iso) return "";
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

async function carregarResumo() {
    const semTurmas = document.querySelector("#semTurmas");
    const painel = document.querySelector("#painelConteudo");

    try {
        const resposta = await api("/aluno/resumo");
        const dados = await resposta.json();

        if (!dados.sucesso) {
            semTurmas.hidden = false;
            semTurmas.textContent = dados.mensagem || "Não foi possível carregar seus dados.";
            return;
        }

        document.querySelector("#statTurmas").textContent = dados.total_turmas;
        document.querySelector("#statMateriais").textContent = dados.total_materiais;
        document.querySelector("#statPerguntas").textContent = dados.perguntas_feitas;

        if ((dados.turmas || []).length === 0) {
            semTurmas.hidden = false;
            painel.hidden = true;
            return;
        }

        semTurmas.hidden = true;
        painel.hidden = false;

        montarTurmas(dados.turmas || []);
        montarRecentes(dados.materiais_recentes || []);
    } catch (erro) {
        console.error("Erro ao carregar o resumo:", erro);
        semTurmas.hidden = false;
        semTurmas.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function montarTurmas(turmas) {
    const lista = document.querySelector("#listaTurmas");
    lista.innerHTML = "";

    turmas.forEach((turma) => {
        const cartao = document.createElement("article");
        cartao.className = "cartao turma-cartao";

        const titulo = document.createElement("h2");
        titulo.textContent = turma.nome;

        const semestre = document.createElement("span");
        semestre.className = "turma-semestre";
        semestre.textContent = turma.semestre;

        const contagem = document.createElement("p");
        const total = turma.total_materiais || 0;
        contagem.textContent =
            total === 0
                ? "Nenhum material liberado ainda"
                : `${total} material${total > 1 ? "is" : ""} liberado${total > 1 ? "s" : ""}`;

        const link = document.createElement("a");
        link.className = "acao";
        link.href = `materiais.html?turma=${turma.id}`;
        link.textContent = "Ver materiais";

        cartao.appendChild(titulo);
        cartao.appendChild(semestre);
        cartao.appendChild(contagem);
        cartao.appendChild(link);
        lista.appendChild(cartao);
    });
}

function montarRecentes(materiais) {
    const lista = document.querySelector("#listaRecentes");
    lista.innerHTML = "";

    if (materiais.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "lista-recentes-vazio";
        vazio.textContent = "Nenhum material liberado ainda.";
        lista.appendChild(vazio);
        return;
    }

    materiais.forEach((material) => {
        const item = document.createElement("li");

        const badge = document.createElement("span");
        badge.className = "badge-tipo";
        badge.textContent = ROTULOS_TIPO[material.tipo] || material.tipo;

        const info = document.createElement("div");
        info.className = "recente-info";

        const titulo = document.createElement("strong");
        titulo.textContent = material.titulo;

        const detalhe = document.createElement("span");
        const partes = [material.turma_nome, formatarData(material.criado_em)].filter(Boolean);
        detalhe.textContent = partes.join(" · ");

        info.appendChild(titulo);
        info.appendChild(detalhe);

        item.appendChild(badge);
        item.appendChild(info);
        lista.appendChild(item);
    });
}

function ligarPlaceholders() {
    document.querySelectorAll("[data-em-breve]").forEach((elemento) => {
        elemento.addEventListener("click", (evento) => {
            evento.preventDefault();
            alert(`${elemento.dataset.emBreve} ainda não está disponível nesta versão.`);
        });
    });
}
