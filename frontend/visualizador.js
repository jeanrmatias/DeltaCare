/**
 * Visualizador de material dentro da plataforma.
 *
 * Antes, ver um material exigia baixá-lo: o aluno saía da plataforma, abria o
 * arquivo em outro programa e perdia o contexto do estudo. Aqui o arquivo é
 * buscado autenticado, vira um blob local e é exibido num modal.
 *
 * Por que blob e não um <iframe src="/aluno/materiais/1/arquivo">: a navegação
 * do iframe não envia o header Authorization, e passar o token na URL o
 * deixaria no histórico e nos logs do servidor.
 */

// Tipos que o navegador exibe sozinho. Para os demais, resta o download —
// prometer visualização de .docx e entregar uma tela cinza é pior do que
// dizer que não dá.
const VISUALIZAVEIS = {
    pdf: "application/pdf",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    gif: "image/gif",
    webp: "image/webp",
    mp4: "video/mp4",
    webm: "video/webm",
    mp3: "audio/mpeg",
    txt: "text/plain",
};

function extensaoDe(nomeArquivo) {
    const partes = String(nomeArquivo || "").split(".");
    return partes.length > 1 ? partes.pop().toLowerCase() : "";
}

/** Diz se o material pode ser aberto na plataforma. */
function podeVisualizar(material) {
    if (material.tipo === "link") return false;
    return Boolean(VISUALIZAVEIS[extensaoDe(material.arquivo_nome)]);
}

/**
 * Abre o material num modal.
 *
 * `caminhoArquivo` é a rota autenticada do arquivo; muda conforme o perfil
 * (o professor usa /materiais/{id}/arquivo e o aluno /aluno/materiais/...).
 */
async function abrirVisualizador(material, caminhoArquivo) {
    const extensao = extensaoDe(material.arquivo_nome);
    const mime = VISUALIZAVEIS[extensao];

    if (!mime) {
        await avisar(
            "Este formato não abre dentro da plataforma. Use o botão Baixar para vê-lo no seu computador.",
            "Visualização indisponível"
        );
        return;
    }

    const dialogo = document.createElement("dialog");
    dialogo.className = "visualizador";

    const cabecalho = document.createElement("div");
    cabecalho.className = "visualizador-cabecalho";

    const titulo = document.createElement("div");
    titulo.className = "visualizador-titulo";

    const nome = document.createElement("strong");
    nome.textContent = material.titulo;

    const detalhe = document.createElement("span");
    detalhe.textContent = [material.turma_nome, material.arquivo_nome].filter(Boolean).join(" · ");

    titulo.appendChild(nome);
    titulo.appendChild(detalhe);

    const acoes = document.createElement("div");
    acoes.className = "visualizador-acoes";

    const fechar = document.createElement("button");
    fechar.type = "button";
    fechar.className = "acao";
    fechar.textContent = "Fechar";
    fechar.addEventListener("click", () => dialogo.close());

    acoes.appendChild(fechar);
    cabecalho.appendChild(titulo);
    cabecalho.appendChild(acoes);

    const corpo = document.createElement("div");
    corpo.className = "visualizador-corpo";

    const carregando = document.createElement("p");
    carregando.className = "visualizador-carregando";
    carregando.textContent = "Carregando material...";
    corpo.appendChild(carregando);

    dialogo.appendChild(cabecalho);
    dialogo.appendChild(corpo);
    document.body.appendChild(dialogo);

    let url = null;

    dialogo.addEventListener("close", () => {
        // Sem revoke, cada abertura deixaria o arquivo inteiro na memória.
        if (url) URL.revokeObjectURL(url);
        dialogo.remove();
    });

    dialogo.addEventListener("click", (evento) => {
        if (evento.target === dialogo) dialogo.close();
    });

    dialogo.showModal();

    try {
        const resposta = await api(caminhoArquivo);

        if (!resposta.ok) {
            carregando.textContent = "Não foi possível carregar este material.";
            return;
        }

        const blob = await resposta.blob();
        // O tipo vem da extensão, e não do servidor: o FileResponse do FastAPI
        // devolve octet-stream para vários formatos, e o navegador então
        // ofereceria download em vez de exibir.
        url = URL.createObjectURL(new Blob([blob], { type: mime }));

        corpo.innerHTML = "";
        corpo.appendChild(_montarConteudo(extensao, mime, url, material));
    } catch (erro) {
        console.error("Erro ao abrir material:", erro);
        carregando.textContent = "Não foi possível carregar este material.";
    }
}

function _montarConteudo(extensao, mime, url, material) {
    if (mime.startsWith("image/")) {
        const imagem = document.createElement("img");
        imagem.className = "visualizador-imagem";
        imagem.src = url;
        imagem.alt = material.titulo;
        return imagem;
    }

    if (mime.startsWith("video/")) {
        const video = document.createElement("video");
        video.className = "visualizador-video";
        video.src = url;
        video.controls = true;
        return video;
    }

    if (mime.startsWith("audio/")) {
        const audio = document.createElement("audio");
        audio.className = "visualizador-audio";
        audio.src = url;
        audio.controls = true;
        return audio;
    }

    // PDF e texto: o visualizador nativo do navegador dá conta, com busca,
    // zoom e navegação por página de graça.
    const quadro = document.createElement("iframe");
    quadro.className = "visualizador-quadro";
    quadro.src = url;
    quadro.title = material.titulo;
    return quadro;
}
