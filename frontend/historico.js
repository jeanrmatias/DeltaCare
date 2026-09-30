/**
 * Semestres anteriores: o material das disciplinas que já terminaram.
 *
 * Um arquivo para aluno e professor, como mensagens.js: a tela é a mesma, e o
 * servidor já devolve só o que cada um pode ver — o aluno, as disciplinas que
 * cursou; o professor, as que deu. A diferença aqui é só a rota.
 *
 * A busca vai até dentro dos PDFs. Para quem vai prestar residência, o que se
 * procura raramente está no título ("Aula 7"): está no texto ("forame
 * magno"). O servidor devolve o trecho onde a palavra apareceu, e é ele que
 * diz ao aluno por que aquele material veio.
 */

const perfil = window.location.pathname.includes("/professor/") ? "professor" : "aluno";
const usuario = exigirAcesso(perfil);

const ROTA_HISTORICO = perfil === "aluno" ? "/aluno/historico" : "/historico";

const ROTULOS_TIPO = {
    pdf: "PDF",
    video: "Vídeo",
    documento: "Documento",
    link: "Link",
};

if (usuario) {
    montarRodape(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    ligarBusca();
    carregar("");
}

function montarRodape(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent =
        usuario.tipo === "professor" ? `Prof. ${nome}` : nome;
}

/** Rota autenticada do arquivo, conforme o perfil (a mesma das telas de material). */
function rotaDoArquivo(material) {
    return perfil === "aluno"
        ? `/aluno/materiais/${material.id}/arquivo`
        : `/materiais/${material.id}/arquivo`;
}

function ligarBusca() {
    const formulario = document.querySelector("#formularioBusca");
    const campo = document.querySelector("#campoBusca");

    formulario.addEventListener("submit", (evento) => {
        evento.preventDefault();
        carregar(campo.value);
    });

    // Apagar a busca volta à lista inteira sem precisar de outro clique.
    campo.addEventListener("input", () => {
        if (!campo.value.trim()) carregar("");
    });
}

async function carregar(busca) {
    const lista = document.querySelector("#listaHistorico");
    const vazio = document.querySelector("#vazio");
    const resumo = document.querySelector("#resumoBusca");

    lista.innerHTML = "";
    vazio.hidden = true;
    resumo.textContent = "";

    try {
        const consulta = busca.trim() ? `?busca=${encodeURIComponent(busca.trim())}` : "";
        const resposta = await api(`${ROTA_HISTORICO}${consulta}`);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            vazio.hidden = false;
            vazio.textContent = dados.mensagem || "Não foi possível carregar o histórico.";
            return;
        }

        document.querySelector("#semestreVigente").textContent = dados.semestre_vigente;

        // O servidor ignora busca com menos de 3 letras (casaria com quase
        // todo PDF). Avisar evita o aluno achar que a busca "não funciona".
        if (busca.trim() && !dados.busca) {
            resumo.textContent = "Digite pelo menos 3 letras para buscar. Mostrando tudo.";
        } else if (dados.busca) {
            const total = contarMateriais(dados.semestres);
            resumo.textContent = total === 1
                ? `1 material com "${dados.busca}".`
                : `${total} materiais com "${dados.busca}".`;
        }

        if (!dados.semestres.length) {
            vazio.hidden = false;
            vazio.textContent = dados.busca
                ? `Nada com "${dados.busca}" nos semestres anteriores.`
                : perfil === "aluno"
                    ? "Você ainda não tem semestres anteriores. As disciplinas aparecem aqui quando o semestre virar."
                    : "Você ainda não tem disciplinas de semestres anteriores.";
            return;
        }

        dados.semestres.forEach((semestre) => lista.appendChild(montarSemestre(semestre)));
    } catch (erro) {
        console.error("Erro ao carregar o histórico:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function contarMateriais(semestres) {
    return semestres.reduce(
        (soma, s) => soma + s.disciplinas.reduce((parcial, d) => parcial + d.materiais.length, 0),
        0
    );
}

function montarSemestre(semestre) {
    const bloco = document.createElement("section");
    bloco.className = "historico-semestre";

    const titulo = document.createElement("h2");
    titulo.className = "historico-semestre-titulo";
    titulo.textContent = semestre.semestre;
    bloco.appendChild(titulo);

    semestre.disciplinas.forEach((disciplina) => bloco.appendChild(montarDisciplina(disciplina)));
    return bloco;
}

function montarDisciplina(disciplina) {
    // <details>: com oito disciplinas por semestre e dezenas de materiais em
    // cada, tudo aberto vira uma parede. Fechado, o semestre cabe numa tela e o
    // aluno abre só a que procura. Na busca, vem aberto: ali ele já disse o
    // que quer.
    const cartao = document.createElement("details");
    cartao.className = "cartao historico-disciplina";
    if (document.querySelector("#campoBusca").value.trim().length >= 3) cartao.open = true;

    const cabecalho = document.createElement("summary");
    const nome = document.createElement("strong");
    nome.textContent = disciplina.nome;
    const detalhe = document.createElement("span");
    detalhe.className = "historico-disciplina-detalhe";
    const quantos = disciplina.materiais.length;
    detalhe.textContent = `Prof. ${disciplina.professor_nome} · ` +
        (quantos === 1 ? "1 material" : `${quantos} materiais`);
    cabecalho.appendChild(nome);
    cabecalho.appendChild(detalhe);
    cartao.appendChild(cabecalho);

    if (!quantos) {
        const p = document.createElement("p");
        p.className = "estado-vazio";
        p.textContent = "Nenhum material publicado nesta disciplina.";
        cartao.appendChild(p);
        return cartao;
    }

    disciplina.materiais.forEach((material) => cartao.appendChild(montarMaterial(material)));
    return cartao;
}

function montarMaterial(material) {
    const linha = document.createElement("article");
    linha.className = "material-linha";

    const info = document.createElement("div");
    info.className = "material-linha-info";

    const topo = document.createElement("div");
    topo.className = "material-linha-topo";
    const badge = document.createElement("span");
    badge.className = "badge-tipo";
    badge.textContent = ROTULOS_TIPO[material.tipo] || material.tipo;
    topo.appendChild(badge);
    info.appendChild(topo);

    const titulo = document.createElement("h3");
    titulo.textContent = material.titulo;
    info.appendChild(titulo);

    if (material.classificacao) {
        const p = document.createElement("p");
        p.className = "material-classificacao";
        p.textContent = material.classificacao;
        info.appendChild(p);
    }

    // O trecho do PDF onde a busca casou. textContent: é texto extraído de um
    // arquivo enviado por professor, e nunca deve ser interpretado como HTML.
    if (material.trecho) {
        const trecho = document.createElement("blockquote");
        trecho.className = "historico-trecho";
        trecho.textContent = material.trecho;
        info.appendChild(trecho);
    } else if (material.descricao) {
        const p = document.createElement("p");
        p.className = "material-descricao";
        p.textContent = material.descricao;
        info.appendChild(p);
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
    } else if (material.arquivo_nome) {
        if (podeVisualizar(material)) {
            const ver = document.createElement("button");
            ver.type = "button";
            ver.className = "acao acao--primaria";
            ver.textContent = "Visualizar";
            ver.addEventListener("click", () => abrirVisualizador(material, rotaDoArquivo(material)));
            acoes.appendChild(ver);
        }

        const baixar = document.createElement("button");
        baixar.type = "button";
        baixar.className = podeVisualizar(material) ? "acao" : "acao acao--primaria";
        baixar.textContent = "Baixar";
        baixar.addEventListener("click", () => baixarArquivo(baixar, material));
        acoes.appendChild(baixar);
    }

    linha.appendChild(info);
    linha.appendChild(acoes);
    return linha;
}

/**
 * Baixa pela rota autenticada. Não pode ser link direto: a navegação do
 * navegador não envia o header Authorization, e token na URL fica no
 * histórico e nos logs.
 */
async function baixarArquivo(botao, material) {
    const texto = botao.textContent;
    botao.disabled = true;
    botao.textContent = "Baixando...";

    try {
        const resposta = await api(rotaDoArquivo(material));
        if (!resposta.ok) {
            await avisarErro("Não foi possível baixar este material.");
            return;
        }

        const url = URL.createObjectURL(await resposta.blob());
        const ancora = document.createElement("a");
        ancora.href = url;
        ancora.download = material.arquivo_nome || "material";
        document.body.appendChild(ancora);
        ancora.click();
        ancora.remove();
        setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (erro) {
        console.error("Erro ao baixar material:", erro);
    } finally {
        botao.disabled = false;
        botao.textContent = texto;
    }
}
