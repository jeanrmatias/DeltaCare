/**
 * Desempenho na visão do professor.
 *
 * A tela existe por causa de um número só: **o índice de erro por tópico**.
 * Média de turma diz que foi mal; erro por tópico diz onde foi mal, que é o
 * que muda a aula seguinte. O resto da tela é contexto para ele.
 *
 * Tudo vem de `/desempenho`. Turma sem atividade corrigida mostra o estado
 * vazio, não um gráfico de zeros — número inventado aqui levaria o professor
 * a retrabalhar o assunto errado.
 */

const usuario = exigirAcesso("professor");

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
    document.querySelector("#nomeRodape").textContent = `Prof. ${nome}`;
}

function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function formatarData(iso) {
    if (!iso) return "—";

    // Data sem hora ("2026-09-26") é lida como meia-noite UTC, e em UTC-3 isso
    // volta um dia. Lendo como data local o dia fica o que está escrito.
    const somenteData = /^\d{4}-\d{2}-\d{2}$/.test(iso);
    const data = somenteData
        ? new Date(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)))
        : new Date(iso);

    if (Number.isNaN(data.getTime())) return "—";
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

/** Número com uma casa, ou travessão quando não existe. */
function numero(valor, sufixo = "") {
    if (valor === null || valor === undefined) return "—";
    return `${valor}${sufixo}`;
}

async function carregarTurmas() {
    try {
        const resposta = await api("/turmas");
        const dados = await resposta.json();
        turmas = dados.turmas || [];

        const seletor = document.querySelector("#seletorTurma");

        if (turmas.length === 0) {
            document.querySelector("#semTurmas").hidden = false;
            document.querySelector("#seletorTurmaCampo").hidden = true;
            return;
        }

        seletor.innerHTML = "";
        turmas.forEach((turma) => {
            const opcao = document.createElement("option");
            opcao.value = turma.id;
            opcao.textContent = `${turma.nome} · ${turma.semestre}`;
            seletor.appendChild(opcao);
        });

        turmaSelecionadaId = turmas[0].id;
        seletor.value = turmaSelecionadaId;
        seletor.onchange = () => {
            turmaSelecionadaId = Number(seletor.value);
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
    ["#resumo", "#cartaoTopicos", "#cartaoAtividades", "#cartaoAlunos"].forEach((id) => {
        document.querySelector(id).hidden = true;
    });
}

async function carregar() {
    try {
        const caminho = `/desempenho?turma_id=${turmaSelecionadaId}` +
                        (periodo ? `&dias=${periodo}` : "");
        const resposta = await api(caminho);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            mostrarVazio(dados.mensagem || "Não foi possível carregar o desempenho.");
            return;
        }

        if (!dados.atividades.length) {
            mostrarVazio("Nenhuma atividade publicada nesta turma no período escolhido.");
            return;
        }

        document.querySelector("#vazio").hidden = true;
        desenharResumo(dados.resumo);
        desenharTopicos(dados.topicos);
        desenharAtividades(dados.atividades);
        desenharAlunos(dados.alunos);
    } catch (erro) {
        console.error("Erro ao carregar desempenho:", erro);
        mostrarVazio("Não foi possível conectar ao servidor. Tente novamente.");
    }
}

function desenharResumo(resumo) {
    document.querySelector("#resumo").hidden = false;
    document.querySelector("#statAlunos").textContent = resumo.total_alunos;
    document.querySelector("#statAtividades").textContent = resumo.atividades;
    document.querySelector("#statMedia").textContent = numero(resumo.media_percentual, "%");
    document.querySelector("#statEntrega").textContent = numero(resumo.taxa_entrega, "%");
}

function desenharTopicos(topicos) {
    const cartao = document.querySelector("#cartaoTopicos");
    const lista = document.querySelector("#listaTopicos");

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
            <span class="barra-detalhe">${t.erros} erro(s) em ${t.total} questão(ões) respondidas</span>
        </div>
    `).join("");
}

function desenharAtividades(atividades) {
    document.querySelector("#cartaoAtividades").hidden = false;

    const linhas = atividades.map((a) => `
        <tr>
            <td>
                ${esc(a.titulo)}
                <span class="tabela-secundario">${a.tipo === "objetiva" ? "Objetiva" : "Dissertativa"} · vale ${a.pontos}</span>
            </td>
            <td class="n">${a.entregues}</td>
            <td class="n">${a.pendentes}</td>
            <td class="n">${numero(a.media)}</td>
            <td class="n">${numero(a.menor)} – ${numero(a.maior)}</td>
        </tr>
    `).join("");

    document.querySelector("#tabelaAtividades").innerHTML = `
        <thead>
            <tr><th>Atividade</th><th>Entregues</th><th>Pendentes</th><th>Média</th><th>Menor – maior</th></tr>
        </thead>
        <tbody>${linhas}</tbody>
    `;
}

function desenharAlunos(alunos) {
    document.querySelector("#cartaoAlunos").hidden = false;

    const linhas = alunos.map((a) => `
        <tr>
            <td>
                ${esc(a.aluno_nome)}
                <span class="tabela-secundario">${esc(a.aluno_email)}</span>
            </td>
            <td class="n">${a.entregues}</td>
            <td class="n">${a.atrasadas > 0 ? `<span class="atividade-pendencia">${a.atrasadas}</span>` : "0"}</td>
            <td class="n">${numero(a.aproveitamento, "%")}</td>
            <td class="n">${formatarData(a.ultima_entrega)}</td>
        </tr>
    `).join("");

    document.querySelector("#tabelaAlunos").innerHTML = `
        <thead>
            <tr><th>Aluno</th><th>Entregues</th><th>Atrasadas</th><th>Aproveitamento</th><th>Última entrega</th></tr>
        </thead>
        <tbody>${linhas}</tbody>
    `;
}
