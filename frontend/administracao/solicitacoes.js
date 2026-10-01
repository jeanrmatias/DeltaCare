/**
 * Privacidade na visão da administração: os pedidos dos alunos sobre os
 * próprios dados.
 *
 * O outro lado é aluno/meus-dados.js. Aqui só chega o que precisa de decisão
 * — correção e exclusão. A cópia dos dados o aluno baixa sozinho.
 *
 * A fila vem com os pendentes primeiro, depois as contas desativadas (que
 * ainda podem ser revertidas), depois o histórico.
 */

const usuario = exigirAcesso("adm");

let filtroStatus = "";

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

async function carregar() {
    const lista = document.querySelector("#lista");
    const vazio = document.querySelector("#vazio");

    try {
        const consulta = filtroStatus ? `?status=${encodeURIComponent(filtroStatus)}` : "";
        const resposta = await api(`/admin/privacidade/solicitacoes${consulta}`);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            vazio.hidden = false;
            vazio.textContent = dados.mensagem || "Não foi possível carregar os pedidos.";
            return;
        }

        const contagem = dados.contagem || {};
        document.querySelector("#statPendentes").textContent = contagem.pendente || 0;
        document.querySelector("#statAgendadas").textContent = contagem.agendada || 0;
        document.querySelector("#statConcluidas").textContent = contagem.concluida || 0;
        document.querySelector("#resumo").hidden = false;
        document.querySelector("#prazoAnonimizacao").textContent = dados.prazo_anonimizacao_dias;

        const pedidos = dados.solicitacoes || [];
        lista.textContent = "";
        vazio.hidden = pedidos.length > 0;
        vazio.textContent = "Nenhum pedido por aqui.";
        pedidos.forEach((pedido) => lista.appendChild(montarPedido(pedido)));
    } catch (erro) {
        console.error("Erro ao carregar pedidos:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function paragrafo(texto) {
    const p = document.createElement("p");
    p.className = "material-descricao";
    p.textContent = texto;
    return p;
}

function montarPedido(pedido) {
    const linha = document.createElement("article");
    linha.className = "material-linha";

    const info = document.createElement("div");
    info.className = "material-linha-info";

    const topo = document.createElement("div");
    topo.className = "material-linha-topo";
    const quem = document.createElement("span");
    quem.className = "material-turma";
    const aluno = pedido.aluno || {};
    quem.textContent = aluno.anonimizado
        ? `Aluno removido · pedido de ${dataCurta(pedido.criado_em)}`
        : `${aluno.nome || aluno.email} · ${aluno.email} · ${dataCurta(pedido.criado_em)}`;
    topo.appendChild(quem);
    topo.appendChild(seloDeStatus(pedido.status));
    info.appendChild(topo);

    const titulo = document.createElement("h3");
    titulo.textContent = pedido.campo_rotulo
        ? `${pedido.tipo_rotulo}: ${pedido.campo_rotulo}`
        : pedido.tipo_rotulo;
    info.appendChild(titulo);

    // Correção: o valor de hoje ao lado do pedido. Aprovar sem ver o que vai
    // ser trocado é aprovar no escuro.
    if (pedido.tipo === "correcao" && pedido.valor_novo) {
        info.appendChild(paragrafo(`Hoje: ${pedido.valor_atual || "(vazio)"} → Pedido: ${pedido.valor_novo}`));
    }
    if (pedido.motivo) info.appendChild(paragrafo(`Motivo do aluno: ${pedido.motivo}`));
    if (pedido.resposta) info.appendChild(paragrafo(`Resposta: ${pedido.resposta}`));
    if (pedido.status === "agendada" && pedido.anonimizar_em) {
        info.appendChild(paragrafo(`Anonimização em ${dataCurta(pedido.anonimizar_em)}.`));
    }

    linha.appendChild(info);

    const acoes = document.createElement("div");
    acoes.className = "material-linha-acoes";

    if (pedido.status === "pendente") {
        acoes.appendChild(botao("Aprovar", "acao acao--primaria", () => aprovar(pedido)));
        acoes.appendChild(botao("Recusar", "acao", () => recusar(pedido)));
    } else if (pedido.status === "agendada") {
        acoes.appendChild(botao("Reverter exclusão", "acao", () => reverter(pedido)));
    }

    if (acoes.children.length) linha.appendChild(acoes);
    return linha;
}

function botao(texto, classe, acao) {
    const elemento = document.createElement("button");
    elemento.type = "button";
    elemento.className = classe;
    elemento.textContent = texto;
    elemento.addEventListener("click", acao);
    return elemento;
}

async function decidir(pedido, aprovar, resposta = "") {
    try {
        const retorno = await api(`/admin/privacidade/solicitacoes/${pedido.id}`, {
            method: "PUT",
            body: JSON.stringify({ aprovar, resposta }),
        });
        const resultado = await retorno.json();
        if (resultado.sucesso) {
            await avisar(resultado.mensagem, "Pronto");
        } else {
            await avisarErro(resultado.mensagem);
        }
        carregar();
    } catch (erro) {
        console.error("Erro ao decidir pedido:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}

async function aprovar(pedido) {
    const nome = pedido.aluno.nome || pedido.aluno.email;
    const exclusao = pedido.tipo === "exclusao";
    const mensagem = exclusao
        ? `A conta de ${nome} será desativada agora, e os dados pessoais anonimizados ao fim do prazo. Até lá, dá para reverter.`
        : `Trocar ${pedido.campo_rotulo.toLowerCase()} de ${nome} para "${pedido.valor_novo}"?`;

    if (await confirmar(mensagem, { titulo: pedido.tipo_rotulo, rotulo: "Aprovar", perigo: exclusao })) {
        decidir(pedido, true);
    }
}

async function recusar(pedido) {
    const resposta = await perguntar(
        { nome: "resposta", rotulo: "Motivo da recusa (o aluno vai ler)" },
        { titulo: `Recusar: ${pedido.tipo_rotulo}`, rotulo: "Recusar" }
    );
    if (resposta) decidir(pedido, false, resposta);
}

async function reverter(pedido) {
    const nome = pedido.aluno.nome || pedido.aluno.email;
    if (!(await confirmar(`A conta de ${nome} volta a entrar normalmente.`, {
        titulo: "Reverter exclusão",
        rotulo: "Reverter",
    }))) {
        return;
    }

    try {
        const retorno = await api(`/admin/privacidade/solicitacoes/${pedido.id}/reverter`, { method: "POST" });
        const resultado = await retorno.json();
        if (!resultado.sucesso) await avisarErro(resultado.mensagem);
        carregar();
    } catch (erro) {
        console.error("Erro ao reverter:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
