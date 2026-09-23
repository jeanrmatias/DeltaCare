/**
 * Turmas — visão do professor: somente leitura. Quem cria/edita/exclui
 * turmas é o administrador (tela adm-turmas.html).
 */

const usuario = exigirAcesso("professor");

if (usuario) {
    montarRodapePerfil(usuario);
    carregarTurmas();
    ligarPlaceholders();
    document.querySelector("#botaoSair").addEventListener("click", sair);
}

function montarRodapePerfil(usuario) {
    const nome = nomeAPartirDoEmail(usuario.email);
    document.querySelector("#avatarRodape").textContent = iniciais(nome);
    document.querySelector("#nomeRodape").textContent = `Prof. ${nome}`;
}

function nomeAPartirDoEmail(email) {
    return email.split("@")[0]
        .split(/[.\-_]/)
        .filter(Boolean)
        .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
        .join(" ") || email;
}

function iniciais(nome) {
    const partes = nome.trim().split(/\s+/);
    const primeira = partes[0]?.[0] ?? "";
    const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
    return (primeira + ultima).toUpperCase();
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
        elemento.addEventListener("click", (evento) => {
            evento.preventDefault();
            alert(`${elemento.dataset.emBreve} ainda não está disponível — chega em uma próxima sprint.`);
        });
    });
}
