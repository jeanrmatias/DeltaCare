/**
 * Desempenho na visão do aluno.
 *
 * A pergunta que a tela responde não é "quanto eu tirei" — isso já está na
 * tela de Atividades. É **"o que eu reviso primeiro"**, e quem responde isso é
 * a lista de tópicos ordenada por erro.
 *
 * O aproveitamento é ponderado pelos pontos, não média das notas: uma
 * atividade que vale 30 pesa mais que uma que vale 10. Média simples daria um
 * número mais bonito e menos verdadeiro.
 */

const usuario = exigirAcesso("aluno");

let turmas = [];
let turmaSelecionadaId = null;
let periodo = "";

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();

    document.querySelector("#seletorPeriodo").addEventListener("change", (evento) => {
        periodo = evento.target.value;
        carregar();
    });

    carregarTurmas();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function formatarData(iso) {
    if (!iso) return "—";

    // "2026-09-26" sozinho é interpretado como meia-noite UTC, e em UTC-3 isso
    // volta um dia: a entrega de 26 aparecia como 25. Data sem hora é lida
    // como data local; com hora, o fuso já vem no próprio texto.
    const somenteData = /^\d{4}-\d{2}-\d{2}$/.test(iso);
    const data = somenteData
        ? new Date(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)))
        : new Date(iso);

    if (Number.isNaN(data.getTime())) return "—";
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function numero(valor, sufixo = "") {
    if (valor === null || valor === undefined) return "—";
    return `${valor}${sufixo}`;
}

async function carregarTurmas() {
    try {
        const resposta = await api("/aluno/turmas");
        const dados = await resposta.json();
        turmas = dados.turmas || [];

        const seletor = document.querySelector("#seletorTurma");

        if (turmas.length === 0) {
            document.querySelector("#seletorTurmaCampo").hidden = true;
            mostrarVazio("Você ainda não está matriculado em nenhuma turma.");
            return;
        }

        seletor.innerHTML = "";

        const todas = document.createElement("option");
        todas.value = "";
        todas.textContent = "Todas as turmas";
        seletor.appendChild(todas);

        turmas.forEach((turma) => {
            const opcao = document.createElement("option");
            opcao.value = turma.id;
            opcao.textContent = `${turma.nome} · ${turma.semestre}`;
            seletor.appendChild(opcao);
        });

        seletor.onchange = () => {
            turmaSelecionadaId = seletor.value ? Number(seletor.value) : null;
            carregar();
        };

        carregar();
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
        mostrarVazio("Não foi possível conectar ao servidor. Verifique se o backend está no ar.");
    }
}

function mostrarVazio(texto) {
    const vazio = document.querySelector("#vazio");
    vazio.hidden = false;
    vazio.textContent = texto;
    ["#resumo", "#cartaoTopicos", "#cartaoEvolucao", "#cartaoNotas"].forEach((id) => {
        document.querySelector(id).hidden = true;
    });
}

async function carregar() {
    try {
        const parametros = [];
        if (turmaSelecionadaId) parametros.push(`turma_id=${turmaSelecionadaId}`);
        if (periodo) parametros.push(`dias=${periodo}`);
        const caminho = "/aluno/desempenho" + (parametros.length ? `?${parametros.join("&")}` : "");

        const resposta = await api(caminho);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            mostrarVazio(dados.mensagem || "Não foi possível carregar seu desempenho.");
            return;
        }

        if (!dados.notas.length) {
            mostrarVazio("Você ainda não entregou nenhuma atividade no período escolhido.");
            return;
        }

        document.querySelector("#vazio").hidden = true;
        desenharResumo(dados.resumo);
        desenharTopicos(dados.topicos);
        desenharEvolucao(dados.evolucao);
        desenharNotas(dados.notas);
    } catch (erro) {
        console.error("Erro ao carregar desempenho:", erro);
        mostrarVazio("Não foi possível conectar ao servidor. Tente novamente.");
    }
}

function desenharResumo(resumo) {
    document.querySelector("#resumo").hidden = false;
    document.querySelector("#statAproveitamento").textContent = numero(resumo.aproveitamento, "%");
    document.querySelector("#statEntregues").textContent = resumo.entregues;
    document.querySelector("#statAguardando").textContent = resumo.aguardando;
    document.querySelector("#statAtrasadas").textContent = resumo.atrasadas;
}

function desenharTopicos(topicos) {
    const cartao = document.querySelector("#cartaoTopicos");
    const lista = document.querySelector("#listaTopicos");

    // Sem objetiva respondida não há de onde tirar tópico. Melhor sumir com o
    // cartão do que mostrar uma lista vazia sem explicação.
    if (!topicos.length) {
        cartao.hidden = true;
        return;
    }

    cartao.hidden = false;
    lista.innerHTML = topicos.map((t) => `
        <div class="barra-linha">
            <div class="barra-rotulo">
                <span>${esc(t.topico)}</span>
                <strong>${t.percentual_erro}% de erro</strong>
            </div>
            <div class="barra-trilho">
                <div class="barra-preenchida ${t.percentual_erro >= 50 ? "barra-preenchida--alta" : ""}"
                     style="width: ${Math.max(t.percentual_erro, 2)}%"></div>
            </div>
            <span class="barra-detalhe">${t.erros} de ${t.total} questão(ões) você errou</span>
        </div>
    `).join("");
}

function desenharEvolucao(evolucao) {
    const cartao = document.querySelector("#cartaoEvolucao");
    const caixa = document.querySelector("#evolucao");

    if (evolucao.length < 2) {
        // Com uma nota só não existe evolução para mostrar.
        cartao.hidden = true;
        return;
    }

    cartao.hidden = false;
    caixa.innerHTML = evolucao.map((ponto) => {
        const altura = Math.max(ponto.percentual ?? 0, 3);
        const classe = (ponto.percentual ?? 0) >= 60 ? "evolucao-coluna--boa" : "evolucao-coluna--baixa";
        return `
            <div class="evolucao-item" title="${esc(ponto.titulo)}: ${ponto.percentual}%">
                <div class="evolucao-trilho">
                    <div class="evolucao-coluna ${classe}" style="height: ${altura}%"></div>
                </div>
                <span class="evolucao-valor">${ponto.percentual}%</span>
                <span class="evolucao-data">${formatarData(ponto.data)}</span>
            </div>
        `;
    }).join("");
}

function desenharNotas(notas) {
    document.querySelector("#cartaoNotas").hidden = false;

    const linhas = [...notas].reverse().map((n) => {
        const nota = n.nota === null || n.nota === undefined
            ? `<span class="tabela-secundario">aguardando correção</span>`
            : `<strong>${n.nota}</strong> de ${n.pontos}`;

        return `
            <tr>
                <td>
                    ${esc(n.titulo)}
                    <span class="tabela-secundario">${esc(n.turma_nome)}${n.topico ? ` · ${esc(n.topico)}` : ""}</span>
                </td>
                <td class="n">${nota}</td>
                <td class="n">${numero(n.percentual, "%")}</td>
                <td class="n">
                    ${formatarData(n.enviado_em)}
                    ${n.atrasada ? `<span class="atividade-pendencia">atrasada</span>` : ""}
                </td>
            </tr>
        `;
    }).join("");

    document.querySelector("#tabelaNotas").innerHTML = `
        <thead><tr><th>Atividade</th><th>Nota</th><th>%</th><th>Entregue em</th></tr></thead>
        <tbody>${linhas}</tbody>
    `;
}
