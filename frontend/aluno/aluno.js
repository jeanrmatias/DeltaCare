/**
 * Chat de estudos do aluno. Assistente de IA restrito ao material (PDF) que
 * o professor liberou na turma selecionada — nunca sai desse escopo (isso é
 * garantido no backend, em chat_ia.py, não aqui).
 */

const usuario = exigirAcesso("aluno");

let turmaAtual = null;

if (usuario) {
    montarRodapePerfil(usuario);
    carregarTurmas();
    ligarFormularioChat();
    ligarPlaceholders();
    ligarNotificacoes();
    ligarRodapePerfil();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

async function carregarTurmas() {
    const seletorCampo = document.querySelector("#seletorTurmaCampo");
    const seletor = document.querySelector("#seletorTurma");
    const semTurmas = document.querySelector("#semTurmas");
    const chatCartao = document.querySelector("#chatCartao");

    try {
        const resposta = await api("/aluno/turmas");
        const dados = await resposta.json();
        const turmas = dados.turmas || [];

        if (turmas.length === 0) {
            seletorCampo.hidden = true;
            chatCartao.hidden = true;
            semTurmas.hidden = false;
            return;
        }

        semTurmas.hidden = true;
        seletorCampo.hidden = false;
        chatCartao.hidden = false;

        seletor.innerHTML = turmas.map((t) => `<option value="${t.id}">${t.nome} · ${t.semestre}</option>`).join("");
        turmaAtual = turmas[0].id;

        seletor.addEventListener("change", () => {
            turmaAtual = Number(seletor.value);
            carregarHistorico();
        });

        await carregarHistorico();
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
        semTurmas.hidden = false;
        semTurmas.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

async function carregarHistorico() {
    const mensagensEl = document.querySelector("#chatMensagens");
    mensagensEl.innerHTML = "";

    if (!turmaAtual) return;

    try {
        const resposta = await api(`/chat/historico?turma_id=${turmaAtual}`);
        const dados = await resposta.json();
        (dados.mensagens || []).forEach((m) => adicionarMensagem(m.papel, m.conteudo, m.fontes));

        if (!dados.mensagens || dados.mensagens.length === 0) {
            adicionarMensagem("assistant", "Oi! Pode perguntar qualquer coisa sobre o material liberado nessa turma que eu ajudo — só não saio do que o professor disponibilizou.");
        }
    } catch (erro) {
        console.error("Erro ao carregar histórico:", erro);
    }
}

function adicionarMensagem(papel, texto, fontes) {
    const mensagensEl = document.querySelector("#chatMensagens");
    const bolha = document.createElement("div");
    bolha.className = `chat-bolha chat-bolha--${papel === "user" ? "aluno" : "ia"}`;

    if (papel === "user") {
        // Pergunta do aluno é texto puro: nada a formatar, e o CSS já preserva
        // as quebras de linha que ele digitou.
        bolha.textContent = texto;
    } else {
        // Resposta da IA vem em Markdown (títulos, listas, tabelas). O
        // renderizador monta os elementos um a um, sem passar por innerHTML.
        bolha.classList.add("chat-bolha--markdown");
        renderizarMarkdown(texto, bolha);
    }

    if (fontes && fontes.length > 0) {
        const rodape = document.createElement("div");
        rodape.className = "chat-bolha-fontes";
        rodape.textContent = `Fonte(s): ${fontes.join(", ")}`;
        bolha.appendChild(rodape);
    }

    mensagensEl.appendChild(bolha);
    mensagensEl.scrollTop = mensagensEl.scrollHeight;
}

/**
 * Mostra a bolha de "pensando" enquanto a IA responde.
 *
 * O modelo roda localmente e leva de 10 a 20 segundos por resposta. Sem um
 * sinal de progresso, esse tempo parece travamento. Devolve uma função que
 * remove a bolha.
 */
function mostrarPensando() {
    const mensagensEl = document.querySelector("#chatMensagens");

    const bolha = document.createElement("div");
    bolha.className = "chat-bolha chat-bolha--ia chat-bolha--pensando";

    const pontos = document.createElement("span");
    pontos.className = "chat-pensando-pontos";
    // Três pontos animados por CSS, um atraso diferente em cada.
    for (let i = 0; i < 3; i += 1) {
        pontos.appendChild(document.createElement("span"));
    }

    const texto = document.createElement("span");
    texto.className = "chat-pensando-texto";
    texto.textContent = "Consultando o material da turma";

    const cronometro = document.createElement("span");
    cronometro.className = "chat-pensando-tempo";

    bolha.appendChild(pontos);
    bolha.appendChild(texto);
    bolha.appendChild(cronometro);

    mensagensEl.appendChild(bolha);
    mensagensEl.scrollTop = mensagensEl.scrollHeight;

    // O contador dá a sensação de que algo está acontecendo e evita que o
    // aluno clique em Enviar de novo achando que falhou.
    const inicio = Date.now();
    const intervalo = setInterval(() => {
        const segundos = Math.floor((Date.now() - inicio) / 1000);
        cronometro.textContent = segundos >= 3 ? `${segundos}s` : "";
    }, 1000);

    return function removerPensando() {
        clearInterval(intervalo);
        bolha.remove();
    };
}

// Controla a requisição em andamento para o botão "Parar" poder cancelá-la.
// Sem isso, a única saída era recarregar a página.
let geracaoEmAndamento = null;

function ligarFormularioChat() {
    const formulario = document.querySelector("#chatFormulario");
    const entrada = document.querySelector("#chatEntrada");
    const botao = document.querySelector("#chatBotaoEnviar");
    const botaoParar = document.querySelector("#chatBotaoParar");

    botaoParar.addEventListener("click", () => {
        if (geracaoEmAndamento) geracaoEmAndamento.abort();
    });

    formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const pergunta = entrada.value.trim();
        if (!pergunta || !turmaAtual) return;

        adicionarMensagem("user", pergunta);
        entrada.value = "";

        geracaoEmAndamento = new AbortController();
        alternarModoGeracao(true, { botao, botaoParar, entrada });

        const removerPensando = mostrarPensando();

        try {
            const resposta = await api("/chat/perguntar", {
                method: "POST",
                body: JSON.stringify({ turma_id: turmaAtual, pergunta: pergunta }),
                signal: geracaoEmAndamento.signal,
            });
            const dados = await resposta.json();

            removerPensando();

            if (dados.sucesso) {
                adicionarMensagem("assistant", dados.resposta, dados.fontes);
            } else {
                adicionarMensagem("assistant", dados.mensagem || "Não foi possível responder agora.");
            }
        } catch (erro) {
            removerPensando();

            // Cancelamento pedido pelo usuário não é erro: o navegador lança
            // AbortError do mesmo jeito que lançaria uma falha de rede.
            if (erro.name === "AbortError") {
                adicionarMensagem("assistant", "_Resposta interrompida._");
            } else {
                console.error("Erro ao perguntar:", erro);
                adicionarMensagem("assistant", "Não foi possível conectar ao servidor. Tente novamente.");
            }
        } finally {
            geracaoEmAndamento = null;
            alternarModoGeracao(false, { botao, botaoParar, entrada });
        }
    });
}

/** Alterna a interface entre "pronto para perguntar" e "gerando resposta". */
function alternarModoGeracao(gerando, { botao, botaoParar, entrada }) {
    botao.hidden = gerando;
    botao.disabled = gerando;
    botaoParar.hidden = !gerando;
    entrada.disabled = gerando;

    if (!gerando) entrada.focus();
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
