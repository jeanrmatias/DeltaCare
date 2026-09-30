/**
 * O caderno do aluno: todas as anotações, de todos os materiais.
 *
 * Agrupadas por material e com busca, porque o uso real é "onde foi que eu
 * escrevi sobre o forame magno?" — e aí ninguém lembra em que material foi.
 * A busca é na própria tela: são as anotações de uma pessoa, e cabem inteiras
 * na memória do navegador.
 */

const usuario = exigirAcesso("aluno");

let todas = [];

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    document.querySelector("#campoBuscaAnotacoes").addEventListener("input", desenhar);
    carregar();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

async function carregar() {
    const vazio = document.querySelector("#vazio");
    try {
        const resposta = await api("/aluno/anotacoes");
        const dados = await resposta.json();
        todas = dados.anotacoes || [];
        desenhar();
    } catch (erro) {
        console.error("Erro ao carregar anotações:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

/** Minúsculas e sem acento: "forame" acha "Forâme" e "FORAME". */
function normalizar(texto) {
    return String(texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function desenhar() {
    const lista = document.querySelector("#listaAnotacoes");
    const vazio = document.querySelector("#vazio");
    const busca = normalizar(document.querySelector("#campoBuscaAnotacoes").value.trim());

    const visiveis = busca
        ? todas.filter((a) => normalizar(`${a.texto} ${a.trecho} ${a.material_titulo}`).includes(busca))
        : todas;

    lista.textContent = "";
    vazio.hidden = visiveis.length > 0;
    vazio.textContent = todas.length
        ? "Nenhuma anotação com esse termo."
        : "Nenhuma anotação ainda. Em Materiais, use o botão Anotar de qualquer material.";

    // Agrupa por material, na ordem em que o material apareceu primeiro (a
    // lista já vem da mais recente para a mais antiga).
    const grupos = new Map();
    visiveis.forEach((anotacao) => {
        const chave = anotacao.material_id ?? `removido:${anotacao.material_titulo}`;
        if (!grupos.has(chave)) grupos.set(chave, []);
        grupos.get(chave).push(anotacao);
    });

    grupos.forEach((anotacoes) => {
        const primeira = anotacoes[0];
        const cartao = document.createElement("section");
        cartao.className = "cartao";

        const titulo = document.createElement("h2");
        titulo.className = "cartao-titulo";
        titulo.textContent = primeira.material_disponivel
            ? primeira.material_titulo
            : `${primeira.material_titulo} (material removido pelo professor)`;
        cartao.appendChild(titulo);

        const itens = document.createElement("div");
        itens.className = "anotacoes-lista";
        anotacoes.forEach((anotacao) => itens.appendChild(montarAnotacao(anotacao, {
            aoEditar: async (alvo) => {
                const material = { id: alvo.material_id, titulo: alvo.material_titulo };
                if (await formularioAnotacao({ material, anotacao: alvo })) carregar();
            },
            aoApagar: async (alvo) => {
                if (await apagarAnotacao(alvo)) carregar();
            },
        })));
        cartao.appendChild(itens);
        lista.appendChild(cartao);
    });
}
