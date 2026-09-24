/**
 * Materiais liberados para o aluno.
 *
 * Usa `/aluno/materiais`, que é uma rota diferente da do professor: ela nunca
 * devolve rascunho nem material agendado para o futuro (ver backend/logica_aluno.py).
 * A tela confia nisso e não faz filtro de visibilidade por conta própria —
 * filtro de permissão em JavaScript não protege nada.
 */

const usuario = exigirAcesso("aluno");

let materiaisCarregados = [];
let turmaSelecionada = null;

if (usuario) {
    montarRodapePerfil(usuario);
    iniciar();
    ligarPlaceholders();
    ligarNotificacoes();
    document.querySelector("#botaoSair").addEventListener("click", sair);
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
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
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

async function iniciar() {
    await carregarTurmas();
    await carregarMateriais();

    document.querySelector("#campoBusca").addEventListener("input", desenharLista);

    ["#filtroAssunto", "#filtroTopico", "#filtroTipo", "#filtroPeriodo"].forEach((seletor) => {
        document.querySelector(seletor).addEventListener("change", desenharLista);
    });

    document.querySelector("#botaoLimparFiltros").addEventListener("click", () => {
        ["#filtroAssunto", "#filtroTopico", "#filtroTipo", "#filtroPeriodo"].forEach((seletor) => {
            document.querySelector(seletor).value = "";
        });
        document.querySelector("#campoBusca").value = "";
        desenharLista();
    });
}

/**
 * Preenche os seletores com os valores que existem nos materiais carregados.
 *
 * Uma lista fixa de assuntos ofereceria filtros que não retornam nada — e
 * esconderia assuntos que o professor cadastrou.
 */
function montarOpcoesDeFiltro() {
    const filtros = document.querySelector("#filtrosMateriais");
    if (!filtros) return;

    if (materiaisCarregados.length === 0) {
        filtros.hidden = true;
        return;
    }

    filtros.hidden = false;

    const preencher = (seletor, valores, formatar) => {
        const campo = document.querySelector(seletor);
        const escolhido = campo.value;

        campo.innerHTML = '<option value="">Todos</option>';

        Array.from(valores)
            .filter(Boolean)
            .sort((a, b) => a.localeCompare(b, "pt-BR"))
            .forEach((valor) => {
                const opcao = document.createElement("option");
                opcao.value = valor;
                opcao.textContent = formatar ? formatar(valor) : valor;
                campo.appendChild(opcao);
            });

        // Mantém a escolha do usuário se ela ainda existir na lista nova.
        if (escolhido && Array.from(valores).includes(escolhido)) {
            campo.value = escolhido;
        }
    };

    preencher("#filtroAssunto", new Set(materiaisCarregados.map((m) => m.assunto)));
    preencher("#filtroTopico", new Set(materiaisCarregados.map((m) => m.topico)));
    preencher(
        "#filtroTipo",
        new Set(materiaisCarregados.map((m) => m.tipo)),
        (valor) => ROTULOS_TIPO[valor] || valor
    );
}

async function carregarTurmas() {
    const campo = document.querySelector("#seletorTurmaCampo");
    const seletor = document.querySelector("#seletorTurma");

    try {
        const resposta = await api("/aluno/turmas");
        const dados = await resposta.json();
        const turmas = dados.turmas || [];

        if (turmas.length === 0) return;

        // A tela inicial linka para cá com ?turma=N; respeitamos essa escolha.
        const parametros = new URLSearchParams(window.location.search);
        const turmaDaUrl = Number(parametros.get("turma")) || null;

        const opcoes = ['<option value="">Todas as turmas</option>'].concat(
            turmas.map((t) => `<option value="${t.id}">${t.nome} · ${t.semestre}</option>`)
        );
        seletor.innerHTML = opcoes.join("");

        if (turmaDaUrl && turmas.some((t) => t.id === turmaDaUrl)) {
            seletor.value = String(turmaDaUrl);
            turmaSelecionada = turmaDaUrl;
        }

        campo.hidden = false;

        seletor.addEventListener("change", async () => {
            turmaSelecionada = seletor.value ? Number(seletor.value) : null;
            await carregarMateriais();
        });
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
    }
}

async function carregarMateriais() {
    const vazio = document.querySelector("#estadoVazio");
    const cartao = document.querySelector("#cartaoMateriais");

    try {
        const caminho = turmaSelecionada
            ? `/aluno/materiais?turma_id=${turmaSelecionada}`
            : "/aluno/materiais";

        const resposta = await api(caminho);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            vazio.hidden = false;
            cartao.hidden = true;
            vazio.textContent = dados.mensagem || "Não foi possível carregar os materiais.";
            return;
        }

        materiaisCarregados = dados.materiais || [];
        montarOpcoesDeFiltro();
        desenharLista();
    } catch (erro) {
        console.error("Erro ao carregar materiais:", erro);
        vazio.hidden = false;
        cartao.hidden = true;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function desenharLista() {
    const vazio = document.querySelector("#estadoVazio");
    const cartao = document.querySelector("#cartaoMateriais");
    const lista = document.querySelector("#listaMateriais");

    const termo = document.querySelector("#campoBusca").value.trim().toLowerCase();

    const assunto = document.querySelector("#filtroAssunto").value;
    const topico = document.querySelector("#filtroTopico").value;
    const tipo = document.querySelector("#filtroTipo").value;
    const periodo = document.querySelector("#filtroPeriodo").value;

    const limite = periodo
        ? Date.now() - Number(periodo) * 24 * 60 * 60 * 1000
        : null;

    const filtrados = materiaisCarregados.filter((material) => {
        if (assunto && material.assunto !== assunto) return false;
        if (topico && material.topico !== topico) return false;
        if (tipo && material.tipo !== tipo) return false;

        if (limite) {
            const criado = new Date(material.criado_em).getTime();
            if (Number.isNaN(criado) || criado < limite) return false;
        }

        if (!termo) return true;

        const alvo = [material.titulo, material.assunto, material.topico, material.aula, material.descricao]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();
        return alvo.includes(termo);
    });

    if (filtrados.length === 0) {
        cartao.hidden = true;
        vazio.hidden = false;
        vazio.textContent = materiaisCarregados.length === 0
            ? "Nenhum material liberado até agora. Assim que o professor publicar, aparece aqui."
            : "Nenhum material corresponde à sua busca.";
        return;
    }

    vazio.hidden = true;
    cartao.hidden = false;
    lista.innerHTML = "";

    filtrados.forEach((material) => lista.appendChild(montarLinha(material)));
}

function montarLinha(material) {
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

    const turma = document.createElement("span");
    turma.className = "material-turma";
    turma.textContent = material.turma_nome;
    topo.appendChild(turma);

    const titulo = document.createElement("h3");
    titulo.textContent = material.titulo;

    info.appendChild(topo);
    info.appendChild(titulo);

    const classificacao = [material.assunto, material.topico, material.aula]
        .filter(Boolean)
        .join(" · ");

    if (classificacao) {
        const p = document.createElement("p");
        p.className = "material-classificacao";
        p.textContent = classificacao;
        info.appendChild(p);
    }

    if (material.descricao) {
        const p = document.createElement("p");
        p.className = "material-descricao";
        p.textContent = material.descricao;
        info.appendChild(p);
    }

    const data = formatarData(material.criado_em);
    if (data) {
        const p = document.createElement("p");
        p.className = "material-data";
        p.textContent = `Publicado em ${data}`;
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
        // Visualizar vem antes de Baixar: ver na plataforma é o caminho
        // esperado, e baixar passa a ser a alternativa.
        if (podeVisualizar(material)) {
            const ver = document.createElement("button");
            ver.type = "button";
            ver.className = "acao acao--primaria";
            ver.textContent = "Visualizar";
            ver.addEventListener("click", () =>
                abrirVisualizador(material, `/aluno/materiais/${material.id}/arquivo`)
            );
            acoes.appendChild(ver);
        }

        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = podeVisualizar(material) ? "acao" : "acao acao--primaria";
        botao.textContent = "Baixar";
        botao.addEventListener("click", () => baixarArquivo(botao, material));
        acoes.appendChild(botao);
    }

    linha.appendChild(info);
    linha.appendChild(acoes);

    return linha;
}

/**
 * Baixa o material pela rota autenticada.
 *
 * Não pode ser um link direto: navegação do navegador não envia o header
 * Authorization, e colocar o token na URL o deixaria no histórico e nos logs.
 */
async function baixarArquivo(botao, material) {
    const textoOriginal = botao.textContent;
    botao.disabled = true;
    botao.textContent = "Baixando...";

    try {
        const resposta = await api(`/aluno/materiais/${material.id}/arquivo`);

        if (!resposta.ok) {
            await avisarErro("Não foi possível baixar este material.");
            return;
        }

        const blob = await resposta.blob();
        const url = URL.createObjectURL(blob);

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
        botao.textContent = textoOriginal;
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
