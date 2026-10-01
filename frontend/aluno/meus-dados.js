/**
 * Meus dados: os direitos do titular, na tela do próprio aluno.
 *
 * A cópia sai na hora. Correção e exclusão viram pedido para a administração
 * (backend/regras/privacidade.py tem o porquê de cada um).
 */

const usuario = exigirAcesso("aluno");

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    document.querySelector("#botaoExportar").addEventListener("click", baixarCopia);
    document.querySelector("#formularioCorrecao").addEventListener("submit", pedirCorrecao);
    document.querySelector("#botaoExcluir").addEventListener("click", pedirExclusao);
    carregarPedidos();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

function mostrar(seletor, texto, sucesso = false) {
    const elemento = document.querySelector(seletor);
    elemento.textContent = texto;
    elemento.classList.toggle("formulario-mensagem--sucesso", sucesso);
}

async function baixarCopia() {
    const botao = document.querySelector("#botaoExportar");
    botao.disabled = true;
    mostrar("#mensagemExportar", "Preparando a cópia...");

    try {
        const resposta = await api("/aluno/privacidade/exportar");
        const resultado = await resposta.json();

        if (!resultado.sucesso) {
            mostrar("#mensagemExportar", resultado.mensagem || "Não foi possível gerar a cópia.");
            return;
        }

        // O arquivo nasce no próprio navegador: os dados já vieram na resposta,
        // e uma segunda rota só para o download seria outra porta a proteger.
        const arquivo = new Blob([JSON.stringify(resultado.dados, null, 2)], { type: "application/json" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(arquivo);
        link.download = nomeArquivoDaCopia(resultado.dados.gerado_em);
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(link.href);

        mostrar("#mensagemExportar", "Cópia baixada.", true);
        carregarPedidos();
    } catch (erro) {
        console.error("Erro ao exportar:", erro);
        mostrar("#mensagemExportar", "Não foi possível conectar ao servidor. Tente novamente.");
    } finally {
        botao.disabled = false;
    }
}

async function enviarPedido(corpo) {
    const resposta = await api("/aluno/privacidade/solicitacoes", {
        method: "POST",
        body: JSON.stringify(corpo),
    });
    return resposta.json();
}

async function pedirCorrecao(evento) {
    evento.preventDefault();

    try {
        const resultado = await enviarPedido({
            tipo: "correcao",
            campo: document.querySelector("#correcaoCampo").value,
            valor_novo: document.querySelector("#correcaoValor").value,
            motivo: document.querySelector("#correcaoMotivo").value,
        });

        mostrar("#mensagemCorrecao", resultado.mensagem, resultado.sucesso);
        if (resultado.sucesso) {
            document.querySelector("#formularioCorrecao").reset();
            carregarPedidos();
        }
    } catch (erro) {
        console.error("Erro ao pedir correção:", erro);
        mostrar("#mensagemCorrecao", "Não foi possível conectar ao servidor. Tente novamente.");
    }
}

async function pedirExclusao() {
    const motivo = await perguntar(
        { nome: "motivo", rotulo: "Motivo (opcional)", obrigatorio: false },
        {
            titulo: "Excluir minha conta",
            mensagem:
                "Aprovado o pedido, você não entra mais na plataforma. Antes, vale baixar a cópia dos seus dados.",
            rotulo: "Enviar pedido",
        }
    );
    if (motivo === null) return;

    try {
        const resultado = await enviarPedido({ tipo: "exclusao", motivo });
        mostrar("#mensagemExclusao", resultado.mensagem, resultado.sucesso);
        if (resultado.sucesso) carregarPedidos();
    } catch (erro) {
        console.error("Erro ao pedir exclusão:", erro);
        mostrar("#mensagemExclusao", "Não foi possível conectar ao servidor. Tente novamente.");
    }
}

async function carregarPedidos() {
    const lista = document.querySelector("#listaPedidos");
    const vazio = document.querySelector("#vazio");

    try {
        const resposta = await api("/aluno/privacidade/solicitacoes");
        const dados = await resposta.json();
        const pedidos = dados.solicitacoes || [];

        document.querySelector("#prazoAnonimizacao").textContent = dados.prazo_anonimizacao_dias;
        lista.textContent = "";
        vazio.hidden = pedidos.length > 0;
        vazio.textContent = "Nenhum pedido ainda.";
        pedidos.forEach((pedido) => lista.appendChild(montarPedido(pedido)));
    } catch (erro) {
        console.error("Erro ao carregar pedidos:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function montarPedido(pedido) {
    const linha = document.createElement("article");
    linha.className = "material-linha";

    const info = document.createElement("div");
    info.className = "material-linha-info";

    const topo = document.createElement("div");
    topo.className = "material-linha-topo";
    const quando = document.createElement("span");
    quando.className = "material-turma";
    quando.textContent = dataCurta(pedido.criado_em);
    topo.appendChild(quando);
    topo.appendChild(seloDeStatus(pedido.status));
    info.appendChild(topo);

    const titulo = document.createElement("h3");
    titulo.textContent = pedido.campo_rotulo
        ? `${pedido.tipo_rotulo}: ${pedido.campo_rotulo}`
        : pedido.tipo_rotulo;
    info.appendChild(titulo);

    const detalhes = [];
    if (pedido.valor_novo) detalhes.push(`Pedido: ${pedido.valor_novo}`);
    if (pedido.resposta) detalhes.push(`Resposta da administração: ${pedido.resposta}`);
    if (pedido.status === "agendada" && pedido.anonimizar_em) {
        detalhes.push(`Os dados pessoais serão anonimizados em ${dataCurta(pedido.anonimizar_em)}.`);
    }
    detalhes.forEach((texto) => {
        const paragrafo = document.createElement("p");
        paragrafo.className = "material-descricao";
        paragrafo.textContent = texto;
        info.appendChild(paragrafo);
    });

    linha.appendChild(info);

    if (pedido.status === "pendente") {
        const acoes = document.createElement("div");
        acoes.className = "material-linha-acoes";
        const cancelar = document.createElement("button");
        cancelar.type = "button";
        cancelar.className = "acao";
        cancelar.textContent = "Cancelar pedido";
        cancelar.addEventListener("click", () => cancelarPedido(pedido));
        acoes.appendChild(cancelar);
        linha.appendChild(acoes);
    }

    return linha;
}

async function cancelarPedido(pedido) {
    if (!(await confirmar("Cancelar este pedido?", { titulo: pedido.tipo_rotulo, rotulo: "Cancelar pedido" }))) {
        return;
    }

    try {
        const resposta = await api(`/aluno/privacidade/solicitacoes/${pedido.id}`, { method: "DELETE" });
        const resultado = await resposta.json();
        if (!resultado.sucesso) await avisarErro(resultado.mensagem);
        carregarPedidos();
    } catch (erro) {
        console.error("Erro ao cancelar pedido:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
