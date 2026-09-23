/**
 * Dashboard do professor.
 *
 * Autenticação, saudação, turmas e o card "Materiais agendados" usam
 * dados reais da API. O resto (entregas, calendário, gráfico de tópicos,
 * mensagens, e os cards de Entregas pendentes/Atividades ativas/Média da
 * turma) ainda é exemplo (mock) — os módulos de Atividades, Chat e
 * Desempenho ainda não existem (Sprints 3, 4 e 7 do backlog).
 */

const usuario = exigirAcesso("professor");

if (usuario) {
    montarSaudacao(usuario);
    montarCalendario();
    montarEntregas();
    montarGrafico();
    montarMensagens();
    ligarMenuAvatar();
    ligarPlaceholders();
    carregarResumoTurmas();

    document.querySelector("#botaoSair").addEventListener("click", sair);
}

async function carregarResumoTurmas() {
    const seletor = document.querySelector("#seletorTurma");

    try {
        const resposta = await fetch(`${API_URL}/turmas?professor_email=${encodeURIComponent(usuario.email)}`);
        const dados = await resposta.json();
        const turmas = dados.turmas || [];

        if (turmas.length === 0) {
            seletor.textContent = "Criar turma";
            seletor.onclick = () => { window.location.href = "turmas.html"; };
            return;
        }

        const rotulo = turmas.length === 1
            ? `${turmas[0].nome} · ${turmas[0].semestre}`
            : `${turmas[0].nome} · ${turmas[0].semestre} (+${turmas.length - 1})`;

        seletor.innerHTML = `
            ${rotulo}
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
        `;
        seletor.onclick = () => { window.location.href = "turmas.html"; };

        const respostaMateriais = await fetch(
            `${API_URL}/materiais?professor_email=${encodeURIComponent(usuario.email)}`
        );
        const dadosMateriais = await respostaMateriais.json();
        const agendados = (dadosMateriais.materiais || []).filter((m) => m.status === "agendado").length;

        document.querySelector("#statMateriaisAgendados").textContent = agendados;
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
    }
}

function nomeAPartirDoEmail(email) {
    const usuarioParte = email.split("@")[0];
    const nome = usuarioParte
        .split(/[.\-_]/)
        .filter(Boolean)
        .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
        .join(" ");
    return nome || email;
}

function iniciais(nome) {
    const partes = nome.trim().split(/\s+/);
    const primeira = partes[0]?.[0] ?? "";
    const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
    return (primeira + ultima).toUpperCase();
}

function montarSaudacao(usuario) {
    const nome = nomeAPartirDoEmail(usuario.email);
    const primeiroNome = nome.split(" ")[0];

    document.querySelector("#saudacao").textContent = `Olá, Prof. ${primeiroNome}`;

    const hoje = new Date();
    const dataFormatada = hoje.toLocaleDateString("pt-BR", {
        weekday: "long",
        day: "2-digit",
        month: "long",
        year: "numeric",
    });
    document.querySelector("#dataHoje").textContent =
        dataFormatada.charAt(0).toUpperCase() + dataFormatada.slice(1);

    const sigla = iniciais(nome);
    document.querySelector("#avatarRodape").textContent = sigla;
    document.querySelector("#nomeRodape").textContent = `Prof. ${nome}`;
    document.querySelector("#botaoAvatar").textContent = sigla;
    document.querySelector("#menuNome").textContent = `Prof. ${nome}`;
    document.querySelector("#menuEmail").textContent = usuario.email;
}

function montarCalendario() {
    const grade = document.querySelector("#calendarioGrade");
    const cabecalhos = ["D", "S", "T", "Q", "Q", "S", "S"];
    const nomesMeses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ];

    const agora = new Date();
    const ano = agora.getFullYear();
    const mes = agora.getMonth();
    const hoje = agora.getDate();

    document.querySelector("#calendarioMes").textContent = `${nomesMeses[mes]} ${ano}`;

    const primeiroDiaSemana = new Date(ano, mes, 1).getDay();
    const diasNoMes = new Date(ano, mes + 1, 0).getDate();

    const celulas = [];
    for (let i = 0; i < primeiroDiaSemana; i++) celulas.push(0);
    for (let dia = 1; dia <= diasNoMes; dia++) celulas.push(dia);

    // Exemplo (mock) de dias com evento, só pra ilustrar o layout do
    // calendário. Quando o módulo existir de verdade, isso vira dados
    // vindos da API em vez de datas fixas.
    const cores = ["azul", "ambar", "azul", "ambar", "verde"];
    const eventos = {};
    [2, 8, 12, 23, 26].forEach((dia, indice) => {
        if (dia <= diasNoMes) eventos[dia] = cores[indice];
    });

    let selecionado = hoje;

    function desenhar() {
        grade.innerHTML = "";

        cabecalhos.forEach((letra) => {
            const celula = document.createElement("span");
            celula.className = "calendario-cabecalho";
            celula.textContent = letra;
            grade.appendChild(celula);
        });

        celulas.forEach((dia) => {
            const celula = document.createElement("button");
            celula.type = "button";
            celula.className = "calendario-dia";

            if (dia === 0) {
                celula.classList.add("calendario-dia--vazio");
                celula.disabled = true;
                grade.appendChild(celula);
                return;
            }

            if (dia === hoje) celula.classList.add("calendario-dia--hoje");
            if (dia === selecionado) celula.classList.add("calendario-dia--selecionado");

            const numero = document.createElement("span");
            numero.textContent = dia;
            celula.appendChild(numero);

            if (eventos[dia]) {
                const ponto = document.createElement("i");
                ponto.className = `ponto ponto--${eventos[dia]}`;
                celula.appendChild(ponto);
            }

            celula.addEventListener("click", () => {
                selecionado = dia;
                desenhar();
            });

            grade.appendChild(celula);
        });
    }

    desenhar();
}

function montarEntregas() {
    const entregas = [
        { nome: "Lucas Martins", detalhe: "Redação · Meio ambiente" },
        { nome: "Beatriz Costa", detalhe: "Lista de exercícios · Frações" },
        { nome: "Rafael Souza", detalhe: "Trabalho · Verbos irregulares" },
    ];

    const lista = document.querySelector("#listaEntregas");
    lista.innerHTML = "";

    entregas.forEach((entrega) => {
        const item = document.createElement("li");
        item.innerHTML = `
            <span class="avatar">${iniciais(entrega.nome)}</span>
            <span class="entrega-info">
                <strong>${entrega.nome}</strong>
                <span>${entrega.detalhe}</span>
            </span>
        `;

        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "botao-corrigir";
        botao.textContent = "Corrigir";
        botao.addEventListener("click", () => avisoEmBreve("Correção de atividades"));

        item.appendChild(botao);
        lista.appendChild(item);
    });
}

function montarGrafico() {
    const topicos = [
        { rotulo: "Frações", valor: 82 },
        { rotulo: "Equações", valor: 65 },
        { rotulo: "Verbos irregulares", valor: 58 },
        { rotulo: "Interpretação de texto", valor: 45 },
    ];

    const grafico = document.querySelector("#grafico");
    grafico.innerHTML = "";

    topicos.forEach((topico) => {
        const barra = document.createElement("div");
        barra.className = "grafico-barra";
        barra.innerHTML = `
            <span class="grafico-barra-valor">${topico.valor}%</span>
            <div class="grafico-barra-coluna" style="height: ${topico.valor}%; opacity: ${topico.valor / 100 + 0.25}"></div>
            <span class="grafico-barra-rotulo">${topico.rotulo}</span>
        `;
        grafico.appendChild(barra);
    });
}

function montarMensagens() {
    const mensagens = [
        { nome: "João Pedro", texto: "Professora, posso entregar a atividade amanhã?" },
        { nome: "Mariana Alves", texto: "Não entendi o exercício 4, pode me ajudar?" },
    ];

    const lista = document.querySelector("#listaMensagens");
    lista.innerHTML = "";

    mensagens.forEach((mensagem) => {
        const item = document.createElement("li");
        item.innerHTML = `
            <span class="avatar">${iniciais(mensagem.nome)}</span>
            <span class="mensagem-info">
                <strong>${mensagem.nome}</strong>
                <span>${mensagem.texto}</span>
            </span>
        `;
        item.addEventListener("click", () => avisoEmBreve("Chat"));
        lista.appendChild(item);
    });
}

function ligarMenuAvatar() {
    const botao = document.querySelector("#botaoAvatar");
    const lista = document.querySelector("#listaAvatar");

    botao.addEventListener("click", (evento) => {
        evento.stopPropagation();
        lista.hidden = !lista.hidden;
    });

    document.addEventListener("click", () => {
        lista.hidden = true;
    });
}

function ligarPlaceholders() {
    document.querySelectorAll("[data-em-breve]").forEach((elemento) => {
        elemento.addEventListener("click", (evento) => {
            evento.preventDefault();
            avisoEmBreve(elemento.dataset.emBreve);
        });
    });
}

function avisoEmBreve(nomeFuncionalidade) {
    alert(`${nomeFuncionalidade} ainda não está disponível — chega em uma próxima sprint.`);
}
