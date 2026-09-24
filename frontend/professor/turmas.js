/**
 * Turmas — visão do professor: somente leitura. Quem cria/edita/exclui
 * turmas é o administrador (tela adm-turmas.html).
 */

const usuario = exigirAcesso("professor");

if (usuario) {
    montarRodapePerfil(usuario);
    carregarTurmas();
    ligarPlaceholders();
    ligarNotificacoes();
    document.querySelector("#botaoSair").addEventListener("click", sair);
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = `Prof. ${nome}`;
}

async function carregarTurmas() {
    const lista = document.querySelector("#listaTurmas");
    const vazio = document.querySelector("#turmasVazio");

    try {
        const resposta = await api("/turmas");
        const dados = await resposta.json();

        lista.innerHTML = "";

        if (!dados.turmas || dados.turmas.length === 0) {
            vazio.hidden = false;
            return;
        }

        vazio.hidden = true;

        dados.turmas.forEach((turma) => {
            const cartao = document.createElement("article");
            cartao.className = "cartao turma-cartao";
            cartao.innerHTML = `
                <h2>${turma.nome}</h2>
                <span class="turma-semestre">${turma.semestre}</span>
                <p>${turma.materiais_publicados} material(is) publicado(s)</p>
            `;
            const botao = document.createElement("a");
            botao.href = `materiais.html?turma=${turma.id}`;
            botao.className = "acao";
            botao.textContent = "Ver materiais";
            cartao.appendChild(botao);
            lista.appendChild(cartao);
        });
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
        lista.innerHTML = "";
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
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
