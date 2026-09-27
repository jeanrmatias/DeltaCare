/**
 * Denúncias na visão de quem reporta — aluno e professor.
 *
 * Um arquivo só para os dois perfis: o que muda entre eles é apenas de onde
 * vem a lista de materiais, e duplicar a tela para essa diferença criaria dois
 * lugares para consertar o mesmo bug.
 *
 * A tela acompanha o que foi reportado. **Reportar mesmo acontece no material**,
 * pelo link "Reportar" que aparece em cada item da lista de materiais — uma
 * denúncia que exige o usuário lembrar o nome do arquivo e vir até aqui é uma
 * denúncia que ninguém faz.
 */

const usuario = exigirAcesso(perfilDaPagina());

let motivos = [];
let materiais = [];

/** Descobre o perfil pela pasta da página, para o arquivo servir aos dois. */
function perfilDaPagina() {
    return window.location.pathname.includes("/professor/") ? "professor" : "aluno";
}

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    ligarFormulario();
    carregar();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent =
        usuario.tipo === "professor" ? `Prof. ${nome}` : nome;
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

const CLASSE_STATUS = {
    aberta: "rascunho",
    em_analise: "agendado",
    concluida: "publicado",
    arquivada: "rascunho",
};

// =========================================================================
// Listagem
// =========================================================================

async function carregar() {
    const lista = document.querySelector("#lista");
    const vazio = document.querySelector("#vazio");

    try {
        const resposta = await api("/denuncias");
        const dados = await resposta.json();

        if (!dados.sucesso) {
            vazio.hidden = false;
            vazio.textContent = dados.mensagem;
            return;
        }

        motivos = dados.motivos || [];
        montarMotivos();

        lista.innerHTML = "";
        vazio.hidden = dados.denuncias.length > 0;

        dados.denuncias.forEach((denuncia) => lista.appendChild(criarLinha(denuncia)));
    } catch (erro) {
        console.error("Erro ao carregar denúncias:", erro);
        lista.innerHTML = "";
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function criarLinha(denuncia) {
    const linha = document.createElement("article");
    linha.className = "cartao material-linha";

    // A resposta da administração é o que a pessoa veio ver. Denúncia sem
    // desfecho visível é um buraco onde se joga o problema.
    const resposta = denuncia.acao
        ? `<div class="denuncia-resposta">
               <strong>Resposta da administração</strong>
               <p>${esc(denuncia.acao)}</p>
           </div>`
        : denuncia.status === "aberta"
            ? `<p class="material-descricao">Aguardando a administração analisar.</p>`
            : "";

    linha.innerHTML = `
        <div class="material-linha-info">
            <div class="material-linha-topo">
                <span class="badge-tipo">${esc(denuncia.motivo_rotulo)}</span>
                <span class="badge-status badge-status--${CLASSE_STATUS[denuncia.status] || "rascunho"}">${esc(denuncia.status_rotulo)}</span>
            </div>
            <h3>${esc(denuncia.material_titulo)}</h3>
            <p class="material-classificacao">
                ${denuncia.turma_nome ? esc(denuncia.turma_nome) + " · " : ""}reportado em ${formatarData(denuncia.criado_em)}
            </p>
            ${denuncia.descricao ? `<p class="material-descricao">${esc(denuncia.descricao)}</p>` : ""}
            ${resposta}
        </div>
    `;

    return linha;
}

// =========================================================================
// Formulário
// =========================================================================

function ligarFormulario() {
    document.querySelector("#botaoNova").addEventListener("click", abrirFormulario);
    document.querySelector("#botaoCancelar").addEventListener("click", fecharFormulario);
    document.querySelector("#formulario").addEventListener("submit", async (evento) => {
        evento.preventDefault();
        await enviar();
    });
}

function montarMotivos() {
    const seletor = document.querySelector("#campoMotivo");
    if (seletor.options.length || !motivos.length) return;

    motivos.forEach((motivo) => {
        const opcao = document.createElement("option");
        opcao.value = motivo.valor;
        opcao.textContent = motivo.rotulo;
        seletor.appendChild(opcao);
    });
}

async function carregarMateriais() {
    const caminho = usuario.tipo === "professor" ? "/materiais" : "/aluno/materiais";

    try {
        const resposta = await api(caminho);
        const dados = await resposta.json();
        materiais = dados.materiais || [];

        // O professor enxerga rascunho e agendado na própria lista; reportar
        // material que ainda não foi liberado não faz sentido.
        if (usuario.tipo === "professor") {
            materiais = materiais.filter((m) => m.status === "publicado");
        }

        const seletor = document.querySelector("#campoMaterial");
        seletor.innerHTML = "";

        if (!materiais.length) {
            const vazio = document.createElement("option");
            vazio.value = "";
            vazio.textContent = "Nenhum material disponível";
            seletor.appendChild(vazio);
            return;
        }

        materiais.forEach((material) => {
            const opcao = document.createElement("option");
            opcao.value = material.id;
            opcao.textContent = `${material.titulo} — ${material.turma_nome}`;
            seletor.appendChild(opcao);
        });
    } catch (erro) {
        console.error("Erro ao carregar materiais:", erro);
    }
}

async function abrirFormulario() {
    const cartao = document.querySelector("#formularioCartao");
    document.querySelector("#formulario").reset();
    limparMensagem();

    await carregarMateriais();

    cartao.hidden = false;
    cartao.scrollIntoView({ behavior: "smooth", block: "start" });
}

function fecharFormulario() {
    document.querySelector("#formularioCartao").hidden = true;
    limparMensagem();
}

function limparMensagem() {
    const mensagem = document.querySelector("#mensagem");
    mensagem.textContent = "";
    mensagem.className = "formulario-mensagem";
}

function mostrarMensagem(texto, sucesso = false) {
    const mensagem = document.querySelector("#mensagem");
    mensagem.textContent = texto;
    mensagem.className = "formulario-mensagem" + (sucesso ? " formulario-mensagem--sucesso" : "");
}

async function enviar() {
    const materialId = Number(document.querySelector("#campoMaterial").value);

    if (!materialId) {
        mostrarMensagem("Escolha o material que você quer reportar.");
        return;
    }

    try {
        const resposta = await api("/denuncias", {
            method: "POST",
            body: JSON.stringify({
                material_id: materialId,
                motivo: document.querySelector("#campoMotivo").value,
                descricao: document.querySelector("#campoDescricao").value.trim(),
            }),
        });
        const dados = await resposta.json();

        if (dados.sucesso) {
            fecharFormulario();
            await avisar(dados.mensagem, "Denúncia registrada");
            carregar();
        } else {
            mostrarMensagem(dados.mensagem || "Não foi possível registrar a denúncia.");
        }
    } catch (erro) {
        console.error("Erro ao enviar denúncia:", erro);
        mostrarMensagem("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
