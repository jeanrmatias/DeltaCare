/**
 * Conversa entre professor e aluno.
 *
 * Um arquivo para os dois perfis: a tela é a mesma, e o que muda é só quem
 * aparece na lista de conversas — o servidor já devolve isso pronto conforme
 * quem está logado. Duplicar a tela por causa disso criaria dois lugares para
 * consertar o mesmo bug.
 *
 * É o canal que faltava: o assistente de IA responde o que o material cobre e
 * recusa o resto, e até agora o que ele recusava não tinha para onde ir.
 */

const usuario = exigirAcesso(perfilDaPagina());

let conversas = [];
let ativa = null;

function perfilDaPagina() {
    return window.location.pathname.includes("/professor/") ? "professor" : "aluno";
}

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    ligarFormulario();
    carregarConversas();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent =
        usuario.tipo === "professor" ? `Prof. ${nome}` : nome;
}

/** Data curta para a lista, hora para a conversa aberta. */
function quando(iso, comHora = false) {
    if (!iso) return "";
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";

    const hoje = new Date();
    const mesmoDia = data.toDateString() === hoje.toDateString();

    if (comHora) {
        return mesmoDia
            ? data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
            : data.toLocaleString("pt-BR", {
                  day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
              });
    }

    return mesmoDia
        ? data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
        : data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

// =========================================================================
// Lista de conversas
// =========================================================================

async function carregarConversas() {
    const vazio = document.querySelector("#vazio");

    try {
        const resposta = await api("/mensagens/conversas");
        const dados = await resposta.json();

        if (!dados.sucesso) {
            vazio.hidden = false;
            vazio.textContent = dados.mensagem;
            return;
        }

        conversas = dados.conversas || [];

        if (!conversas.length) {
            vazio.hidden = false;
            vazio.textContent = usuario.tipo === "professor"
                ? "Nenhum aluno matriculado nas suas turmas ainda."
                : "Você ainda não está matriculado em nenhuma turma.";
            return;
        }

        vazio.hidden = true;
        document.querySelector("#painel").hidden = false;
        desenharLista();

        // Vindo do chat de estudos com uma dúvida em mãos, abre direto na
        // conversa daquela turma — inclusive havendo mensagem por ler, porque
        // aqui a pessoa já disse aonde quer ir.
        if (!ativa && aplicarRascunho()) return;

        // Abre a primeira sozinho **só quando não há nada por ler**. Havendo
        // mensagem nova, abrir marcaria como lida antes de a pessoa olhar, e o
        // contador sumiria sem ela ter visto o aviso. Com a caixa em dia, abrir
        // sozinho não custa nada e poupa um clique.
        if (!ativa && !dados.nao_lidas) abrirConversa(conversas[0]);
    } catch (erro) {
        console.error("Erro ao carregar conversas:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

/**
 * Abre a conversa da turma que o chat de estudos indicou, com a pergunta pronta.
 *
 * O aluno chega aqui vindo de uma recusa do assistente: o material não cobria a
 * dúvida dele. Fazer ele redigitar a pergunta que acabou de escrever seria
 * atrito puro — e o mais provável é que ele desistisse no caminho.
 *
 * Consome de uma vez (`removeItem` antes de usar): se ele voltar para esta tela
 * depois, é para ver a resposta, não para reabrir o mesmo rascunho.
 *
 * Devolve `true` quando abriu algo, para quem chamou não abrir outra conversa
 * por cima.
 */
function aplicarRascunho() {
    let rascunho = null;

    try {
        const bruto = sessionStorage.getItem("deltacare_rascunho_mensagem");
        if (!bruto) return false;
        sessionStorage.removeItem("deltacare_rascunho_mensagem");
        rascunho = JSON.parse(bruto);
    } catch (erro) {
        // sessionStorage bloqueado ou JSON corrompido: a tela abre normal.
        return false;
    }

    if (!rascunho || !rascunho.turma_id) return false;

    // A turma vem do chat, mas quem manda é a lista do servidor: se ele saiu da
    // turma nesse meio tempo, não há conversa para abrir.
    const conversa = conversas.find((c) => c.turma_id === rascunho.turma_id);
    if (!conversa) return false;

    abrirConversa(conversa).then(() => {
        const campo = document.querySelector("#campoMensagem");
        if (!rascunho.texto) return;
        // Não envia sozinho: a pergunta foi escrita para uma IA, e ele pode
        // querer ajustar o tom antes de mandar para uma pessoa.
        campo.value = rascunho.texto;
        campo.focus();
    });

    return true;
}

function mesmaConversa(a, b) {
    return a && b && a.turma_id === b.turma_id && a.contraparte_email === b.contraparte_email;
}

function desenharLista() {
    const lista = document.querySelector("#listaConversas");
    lista.innerHTML = "";

    conversas.forEach((conversa) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "conversa-item" + (mesmaConversa(conversa, ativa) ? " conversa-item--ativa" : "");

        const previa = conversa.ultima_mensagem
            ? `${conversa.ultima_minha ? "Você: " : ""}${conversa.ultima_mensagem}`
            : "Nenhuma mensagem ainda";

        item.innerHTML = `
            <span class="avatar">${esc(iniciaisDe(conversa.titulo))}</span>
            <span class="conversa-item-texto">
                <strong>${esc(conversa.titulo)}</strong>
                <span class="conversa-item-turma">${esc(conversa.subtitulo)}</span>
                <span class="conversa-item-previa">${esc(previa)}</span>
            </span>
            <span class="conversa-item-lado">
                <span class="conversa-item-hora">${quando(conversa.ultima_em)}</span>
                ${conversa.nao_lidas ? `<span class="contador-nao-lidas">${conversa.nao_lidas}</span>` : ""}
            </span>
        `;

        item.addEventListener("click", () => abrirConversa(conversa));
        lista.appendChild(item);
    });
}

// =========================================================================
// Conversa aberta
// =========================================================================

async function abrirConversa(conversa) {
    ativa = conversa;
    desenharLista();

    document.querySelector("#conversaTitulo").textContent = conversa.titulo;
    document.querySelector("#conversaSubtitulo").textContent = conversa.subtitulo;
    document.querySelector("#formulario").hidden = false;
    limparMensagem();

    const caixa = document.querySelector("#mensagens");
    caixa.innerHTML = "<p class='estado-vazio'>Carregando...</p>";

    try {
        const parametros = [`turma_id=${conversa.turma_id}`];
        if (usuario.tipo === "professor") {
            parametros.push(`aluno_email=${encodeURIComponent(conversa.contraparte_email)}`);
        }

        const resposta = await api(`/mensagens?${parametros.join("&")}`);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            caixa.innerHTML = `<p class="estado-vazio">${esc(dados.mensagem)}</p>`;
            return;
        }

        desenharMensagens(dados.mensagens);

        // O contador zera porque abrir já marcou como lida no servidor.
        conversa.nao_lidas = 0;
        desenharLista();
        // O sino tem a propria carga; recarregar aqui duplicaria a chamada.
        if (typeof carregarNotificacoes === "function") carregarNotificacoes();
    } catch (erro) {
        console.error("Erro ao abrir conversa:", erro);
        caixa.innerHTML = "<p class='estado-vazio'>Não foi possível carregar a conversa.</p>";
    }
}

function desenharMensagens(mensagens) {
    const caixa = document.querySelector("#mensagens");

    if (!mensagens.length) {
        caixa.innerHTML = "<p class='estado-vazio'>Nenhuma mensagem ainda. Escreva a primeira.</p>";
        return;
    }

    caixa.innerHTML = mensagens.map((m) => `
        <div class="balao ${m.minha ? "balao--minha" : ""}">
            <p>${esc(m.conteudo)}</p>
            <span class="balao-hora">${quando(m.criado_em, true)}</span>
        </div>
    `).join("");

    // Conversa se lê de baixo para cima: a última mensagem é a que importa.
    caixa.scrollTop = caixa.scrollHeight;
}

// =========================================================================
// Envio
// =========================================================================

function ligarFormulario() {
    const formulario = document.querySelector("#formulario");
    const campo = document.querySelector("#campoMensagem");

    formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();
        await enviar();
    });

    // Enter envia, Shift+Enter quebra linha — o que se espera de um chat.
    campo.addEventListener("keydown", (evento) => {
        if (evento.key === "Enter" && !evento.shiftKey) {
            evento.preventDefault();
            enviar();
        }
    });
}

function limparMensagem() {
    const mensagem = document.querySelector("#mensagem");
    mensagem.textContent = "";
    mensagem.className = "formulario-mensagem";
}

function mostrarMensagem(texto) {
    const mensagem = document.querySelector("#mensagem");
    mensagem.textContent = texto;
    mensagem.className = "formulario-mensagem";
}

async function enviar() {
    if (!ativa) return;

    const campo = document.querySelector("#campoMensagem");
    const conteudo = campo.value.trim();

    if (!conteudo) return;

    const corpo = { turma_id: ativa.turma_id, conteudo };
    if (usuario.tipo === "professor") corpo.aluno_email = ativa.contraparte_email;

    try {
        const resposta = await api("/mensagens", {
            method: "POST",
            body: JSON.stringify(corpo),
        });
        const dados = await resposta.json();

        if (!dados.sucesso) {
            mostrarMensagem(dados.mensagem);
            return;
        }

        campo.value = "";
        limparMensagem();
        await abrirConversa(ativa);
        carregarConversas();
    } catch (erro) {
        console.error("Erro ao enviar mensagem:", erro);
        mostrarMensagem("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
