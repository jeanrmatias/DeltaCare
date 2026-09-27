/**
 * Denúncias na visão de quem trata: a fila da administração.
 *
 * O outro lado desta tela é `frontend/denuncias.js`, onde aluno e professor
 * reportam. Os dois são a mesma entrega — o módulo existe justamente porque o
 * backlog tinha só a metade de cá, e uma caixa de entrada sem porta de entrada
 * não serve para nada.
 *
 * A fila vem com as abertas primeiro. Ordem cronológica seria mais simples e
 * mais inútil: quem abre esta tela vem trabalhar, não ler histórico.
 */

const usuario = exigirAcesso("adm");

let filtroStatus = "";

const CLASSE_STATUS = {
    aberta: "rascunho",
    em_analise: "agendado",
    concluida: "publicado",
    arquivada: "rascunho",
    retirada: "rascunho",
};

const PROXIMOS_PASSOS = {
    aberta: [
        { status: "em_analise", rotulo: "Pôr em análise" },
        { status: "concluida", rotulo: "Concluir" },
        { status: "arquivada", rotulo: "Arquivar" },
    ],
    em_analise: [
        { status: "concluida", rotulo: "Concluir" },
        { status: "arquivada", rotulo: "Arquivar" },
    ],
    concluida: [{ status: "em_analise", rotulo: "Reabrir" }],
    arquivada: [{ status: "em_analise", rotulo: "Reabrir" }],
    // Quem reportou já voltou atrás. Não há o que concluir, só tirar da fila —
    // e reabrir continua possível caso a administração queira apurar mesmo
    // assim, porque o problema pode ser real ainda que a pessoa desista.
    retirada: [
        { status: "arquivada", rotulo: "Arquivar" },
        { status: "em_analise", rotulo: "Apurar mesmo assim" },
    ],
};

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();

    document.querySelector("#seletorStatus").addEventListener("change", (evento) => {
        filtroStatus = evento.target.value;
        carregar();
    });

    carregar();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function formatarData(iso) {
    if (!iso) return "";
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
}

async function carregar() {
    const lista = document.querySelector("#lista");
    const vazio = document.querySelector("#vazio");
    const resumo = document.querySelector("#resumo");

    try {
        const caminho = "/admin/denuncias" + (filtroStatus ? `?status=${filtroStatus}` : "");
        const resposta = await api(caminho);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            vazio.hidden = false;
            vazio.textContent = dados.mensagem;
            resumo.hidden = true;
            return;
        }

        resumo.hidden = false;
        document.querySelector("#statAbertas").textContent = dados.resumo.abertas;
        document.querySelector("#statAnalise").textContent = dados.resumo.em_analise;
        document.querySelector("#statConcluidas").textContent = dados.resumo.concluidas;
        document.querySelector("#statArquivadas").textContent = dados.resumo.arquivadas;
        document.querySelector("#statRetiradas").textContent = dados.resumo.retiradas;

        lista.innerHTML = "";
        vazio.hidden = dados.denuncias.length > 0;

        if (!dados.denuncias.length && filtroStatus) {
            vazio.textContent = "Nenhuma denúncia com esse status.";
        }

        dados.denuncias.forEach((denuncia) => lista.appendChild(criarLinha(denuncia)));
    } catch (erro) {
        console.error("Erro ao carregar denúncias:", erro);
        lista.innerHTML = "";
        resumo.hidden = true;
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function criarLinha(denuncia) {
    const linha = document.createElement("article");
    linha.className = "cartao material-linha";

    const acoes = (PROXIMOS_PASSOS[denuncia.status] || [])
        .map((passo) => `<button type="button" class="acao" data-status="${passo.status}">${passo.rotulo}</button>`)
        .join("");

    linha.innerHTML = `
        <div class="material-linha-info">
            <div class="material-linha-topo">
                <span class="badge-tipo">${esc(denuncia.motivo_rotulo)}</span>
                <span class="badge-status badge-status--${CLASSE_STATUS[denuncia.status] || "rascunho"}">${esc(denuncia.status_rotulo)}</span>
            </div>
            <h3>${esc(denuncia.material_titulo)}</h3>
            <p class="material-classificacao">
                ${esc(denuncia.autor_nome)}${denuncia.turma_nome ? ` · ${esc(denuncia.turma_nome)}` : ""}
                · ${formatarData(denuncia.criado_em)}
            </p>
            ${denuncia.descricao ? `<p class="material-descricao">${esc(denuncia.descricao)}</p>` : ""}
            ${denuncia.acao
                ? `<div class="denuncia-resposta"><strong>Ação registrada</strong><p>${esc(denuncia.acao)}</p></div>`
                : ""}
        </div>
        <div class="material-linha-acoes">${acoes}</div>
    `;

    linha.querySelectorAll("[data-status]").forEach((botao) => {
        botao.addEventListener("click", () => tratar(denuncia, botao.dataset.status));
    });

    return linha;
}

async function tratar(denuncia, status) {
    const encerra = status === "concluida" || status === "arquivada";

    // Encerrar exige dizer o que foi feito: quem reportou recebe o aviso e
    // precisa saber se algo mudou. O servidor também recusa sem isso.
    const resultado = await perguntar(
        {
            nome: "acao",
            rotulo: encerra ? "O que foi feito" : "Observação (opcional)",
            valor: denuncia.acao || "",
        },
        {
            titulo: encerra ? "Encerrar denúncia" : "Atualizar denúncia",
            mensagem: encerra
                ? "Quem reportou recebe esta resposta pelo sino."
                : "A pessoa que reportou é avisada da mudança de status.",
            rotulo: "Salvar",
        }
    );

    if (resultado === null) return;

    try {
        const resposta = await api(`/admin/denuncias/${denuncia.id}`, {
            method: "POST",
            body: JSON.stringify({ status: status, acao: resultado.acao || "" }),
        });
        const dados = await resposta.json();

        if (dados.sucesso) {
            carregar();
        } else {
            await avisarErro(dados.mensagem);
        }
    } catch (erro) {
        console.error("Erro ao tratar denúncia:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
