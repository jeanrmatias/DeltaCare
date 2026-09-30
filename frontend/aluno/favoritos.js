/**
 * Favoritos: o material que o aluno marcou para reencontrar rápido.
 *
 * Inclui os de semestres passados (regras/favoritos.py): o que foi marcado no
 * 3º período continua aqui no 6º, quando a matéria volta na revisão.
 */

const usuario = exigirAcesso("aluno");

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    carregar();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

async function carregar() {
    const lista = document.querySelector("#listaFavoritos");
    const vazio = document.querySelector("#vazio");

    try {
        const resposta = await api("/aluno/favoritos");
        const dados = await resposta.json();
        const favoritos = dados.favoritos || [];

        lista.textContent = "";
        vazio.hidden = favoritos.length > 0;
        vazio.textContent = "Nenhum favorito ainda. Toque na estrela ☆ de um material para guardá-lo aqui.";

        favoritos.forEach((material) => lista.appendChild(montarLinha(material)));
    } catch (erro) {
        console.error("Erro ao carregar favoritos:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function montarLinha(material) {
    const linha = document.createElement("article");
    linha.className = "material-linha";

    const info = document.createElement("div");
    info.className = "material-linha-info";

    const topo = document.createElement("div");
    topo.className = "material-linha-topo";
    const disciplina = document.createElement("span");
    disciplina.className = "material-turma";
    disciplina.textContent = `${material.turma_nome} · ${material.semestre}`;
    topo.appendChild(disciplina);

    // Tirar a estrela tira da lista na hora: esta tela é só de favoritos.
    topo.appendChild(botaoFavorito(material, (atualizado) => {
        if (!atualizado.favorito) {
            linha.remove();
            if (!document.querySelector("#listaFavoritos").children.length) carregar();
        }
    }));
    info.appendChild(topo);

    const titulo = document.createElement("h3");
    titulo.textContent = material.titulo;
    info.appendChild(titulo);

    if (material.descricao) {
        const descricao = document.createElement("p");
        descricao.className = "material-descricao";
        descricao.textContent = material.descricao;
        info.appendChild(descricao);
    }

    const acoes = document.createElement("div");
    acoes.className = "material-linha-acoes";

    if (material.tipo === "link" && material.link_url) {
        const link = document.createElement("a");
        link.className = "acao acao--primaria";
        link.href = material.link_url;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = "Abrir link";
        acoes.appendChild(link);
    } else if (material.arquivo_nome && podeVisualizar(material)) {
        const ver = document.createElement("button");
        ver.type = "button";
        ver.className = "acao acao--primaria";
        ver.textContent = "Visualizar";
        ver.addEventListener("click", () =>
            abrirVisualizador(material, `/aluno/materiais/${material.id}/arquivo`)
        );
        acoes.appendChild(ver);
    }

    const anotar = document.createElement("button");
    anotar.type = "button";
    anotar.className = "acao";
    anotar.textContent = "Anotações";
    anotar.addEventListener("click", () => abrirAnotacoes(material));
    acoes.appendChild(anotar);

    linha.appendChild(info);
    linha.appendChild(acoes);
    return linha;
}
