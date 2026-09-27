/**
 * Calendário do professor.
 *
 * As telas de Materiais e Atividades respondem "o que eu publiquei". Esta
 * responde "o que acontece na semana que vem" — e é a única que mostra os
 * **prazos** fora de dentro da atividade.
 *
 * Daí o aviso de conflito no topo: dois prazos no mesmo dia é a informação que
 * o professor hoje só descobre quando os alunos reclamam.
 *
 * O nome do arquivo é `calendario-tela.js` e não `calendario.js` porque já
 * existe um `frontend/calendario.js` — o seletor de data, carregado em outras
 * páginas. Dois arquivos de mesmo nome em pastas diferentes é confusão
 * garantida na hora de depurar.
 */

const usuario = exigirAcesso("professor");

let turmas = [];
let turmaSelecionadaId = null;
let referencia = new Date();
let eventosPorDia = {};
let diaSelecionado = null;

const MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

const DIAS_CURTOS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

const COR_DO_TIPO = {
    material: "azul",
    material_agendado: "azul",
    atividade: "verde",
    atividade_agendada: "verde",
    prazo: "ambar",
};

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();

    document.querySelector("#mesAnterior").addEventListener("click", () => mudarMes(-1));
    document.querySelector("#mesSeguinte").addEventListener("click", () => mudarMes(1));

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

/** "2026-09-26" como data local — sem isto o dia volta um em UTC-3. */
function dataLocal(dia) {
    return new Date(Number(dia.slice(0, 4)), Number(dia.slice(5, 7)) - 1, Number(dia.slice(8, 10)));
}

function rotuloLongo(dia) {
    return dataLocal(dia).toLocaleDateString("pt-BR", {
        weekday: "long", day: "2-digit", month: "long",
    });
}

function chaveDoDia(data) {
    const dois = (n) => String(n).padStart(2, "0");
    return `${data.getFullYear()}-${dois(data.getMonth() + 1)}-${dois(data.getDate())}`;
}

// =========================================================================
// Turmas e carga
// =========================================================================

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

        document.querySelector("#painel").hidden = false;
        carregar();
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
        document.querySelector("#semTurmas").hidden = false;
        document.querySelector("#semTurmas").textContent =
            "Não foi possível conectar ao servidor. Verifique se o backend está no ar.";
    }
}

function mudarMes(passo) {
    referencia = new Date(referencia.getFullYear(), referencia.getMonth() + passo, 1);
    diaSelecionado = null;
    carregar();
}

async function carregar() {
    const ano = referencia.getFullYear();
    const mes = referencia.getMonth() + 1;

    document.querySelector("#tituloMes").textContent = `${MESES[mes - 1]} de ${ano}`;

    try {
        const parametros = [`ano=${ano}`, `mes=${mes}`];
        if (turmaSelecionadaId) parametros.push(`turma_id=${turmaSelecionadaId}`);

        const resposta = await api(`/calendario?${parametros.join("&")}`);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            desenharGrade();
            return;
        }

        eventosPorDia = {};
        dados.eventos.forEach((evento) => {
            (eventosPorDia[evento.dia] = eventosPorDia[evento.dia] || []).push(evento);
        });

        mostrarConflitos(dados.resumo.dias_com_dois_prazos || []);
        desenharGrade();

        // Abre no dia de hoje quando ele está no mês visível; senão, no
        // primeiro dia que tem alguma coisa. Abrir vazio desperdiçaria a tela.
        const hoje = chaveDoDia(new Date());
        const diasComEvento = Object.keys(eventosPorDia).sort();
        const alvo = eventosPorDia[hoje] ? hoje : diasComEvento[0];
        if (alvo) selecionarDia(alvo);
        else mostrarDiaVazio();
    } catch (erro) {
        console.error("Erro ao carregar calendário:", erro);
        desenharGrade();
    }
}

function mostrarConflitos(dias) {
    const aviso = document.querySelector("#avisoConflito");

    if (!dias.length) {
        aviso.hidden = true;
        return;
    }

    const lista = dias.map((d) => rotuloLongo(d)).join(", ");
    aviso.hidden = false;
    aviso.textContent = dias.length === 1
        ? `Atenção: há mais de uma entrega marcada para ${lista}.`
        : `Atenção: há mais de uma entrega marcada nestes dias — ${lista}.`;
}

// =========================================================================
// Grade
// =========================================================================

function desenharGrade() {
    const grade = document.querySelector("#grade");
    const ano = referencia.getFullYear();
    const mes = referencia.getMonth();

    const primeiro = new Date(ano, mes, 1);
    const diasNoMes = new Date(ano, mes + 1, 0).getDate();
    const hoje = chaveDoDia(new Date());

    const celulas = DIAS_CURTOS.map((d) => `<span class="calendario-cabecalho">${d}</span>`);

    for (let vazio = 0; vazio < primeiro.getDay(); vazio += 1) {
        celulas.push('<span class="calendario-dia calendario-dia--vazio"></span>');
    }

    for (let dia = 1; dia <= diasNoMes; dia += 1) {
        const chave = chaveDoDia(new Date(ano, mes, dia));
        const eventos = eventosPorDia[chave] || [];

        // Um ponto por tipo presente, não por evento: cinco materiais no mesmo
        // dia viram cinco pontos iguais e nenhuma informação.
        const cores = [...new Set(eventos.map((e) => COR_DO_TIPO[e.tipo]).filter(Boolean))];
        const pontos = cores.map((cor) => `<i class="ponto ponto--${cor}"></i>`).join("");

        const classes = ["calendario-dia", "calendario-dia--clicavel"];
        if (chave === hoje) classes.push("calendario-dia--hoje");
        if (chave === diaSelecionado) classes.push("calendario-dia--selecionado");

        celulas.push(
            `<button type="button" class="${classes.join(" ")}" data-dia="${chave}">` +
            `${dia}<span class="calendario-pontos">${pontos}</span></button>`
        );
    }

    grade.innerHTML = celulas.join("");

    grade.querySelectorAll("[data-dia]").forEach((botao) => {
        botao.addEventListener("click", () => selecionarDia(botao.dataset.dia));
    });
}

// =========================================================================
// Painel do dia
// =========================================================================

function mostrarDiaVazio() {
    document.querySelector("#tituloDia").textContent = "Nada neste mês";
    document.querySelector("#listaDia").innerHTML =
        '<p class="estado-vazio">Nenhum material, atividade ou prazo neste mês.</p>';
}

function selecionarDia(dia) {
    diaSelecionado = dia;
    desenharGrade();

    document.querySelector("#tituloDia").textContent = rotuloLongo(dia);

    const eventos = eventosPorDia[dia] || [];
    const lista = document.querySelector("#listaDia");

    if (!eventos.length) {
        lista.innerHTML = '<p class="estado-vazio">Nada marcado para este dia.</p>';
        return;
    }

    lista.innerHTML = eventos.map((evento) => `
        <article class="evento">
            <span class="ponto ponto--${COR_DO_TIPO[evento.tipo] || "azul"}"></span>
            <div class="evento-info">
                <strong>${esc(evento.titulo)}</strong>
                <span>${esc(evento.detalhe)}${evento.hora ? ` · ${esc(evento.hora)}` : ""}</span>
                <span class="evento-turma">${esc(evento.turma_nome)}</span>
            </div>
            <a class="acao" href="${esc(evento.link)}">Abrir</a>
        </article>
    `).join("");
}
