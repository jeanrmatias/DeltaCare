/**
 * Sino de notificações.
 *
 * Antes o contador era um "5" escrito no HTML e o clique não abria nada. Agora
 * o contador vem do servidor e o painel lista eventos que aconteceram de fato
 * (matrícula de aluno para o professor, material liberado para o aluno).
 *
 * Uso: chame `ligarNotificacoes()` depois de autenticar. A função é tolerante
 * a página sem sino — os painéis de aluno não têm um, e nesse caso ela apenas
 * não faz nada.
 */

const INTERVALO_ATUALIZACAO = 60000; // 1 min: eventos aqui não são urgentes

let _notificacoes = [];
let _painelAberto = false;

function ligarNotificacoes() {
    const botao = document.querySelector("#botaoNotificacoes");
    if (!botao) return;

    const painel = _criarPainel(botao);

    botao.addEventListener("click", async (evento) => {
        evento.stopPropagation();
        _painelAberto = !_painelAberto;
        painel.hidden = !_painelAberto;

        if (_painelAberto) {
            await carregarNotificacoes();
        }
    });

    // Clique fora fecha, como em qualquer popover.
    document.addEventListener("click", (evento) => {
        if (!_painelAberto) return;
        if (painel.contains(evento.target) || botao.contains(evento.target)) return;
        _painelAberto = false;
        painel.hidden = true;
    });

    document.addEventListener("keydown", (evento) => {
        if (evento.key === "Escape" && _painelAberto) {
            _painelAberto = false;
            painel.hidden = true;
        }
    });

    carregarNotificacoes();
    setInterval(carregarNotificacoes, INTERVALO_ATUALIZACAO);
}

function _criarPainel(botao) {
    const painel = document.createElement("div");
    painel.className = "painel-notificacoes";
    painel.id = "painelNotificacoes";
    painel.hidden = true;
    painel.setAttribute("role", "region");
    painel.setAttribute("aria-label", "Notificações");

    const topo = document.createElement("div");
    topo.className = "painel-notificacoes-topo";

    const titulo = document.createElement("strong");
    titulo.textContent = "Notificações";

    const marcarTodas = document.createElement("button");
    marcarTodas.type = "button";
    marcarTodas.className = "painel-notificacoes-marcar";
    marcarTodas.textContent = "Marcar todas como lidas";
    marcarTodas.addEventListener("click", async (evento) => {
        evento.stopPropagation();
        await api("/notificacoes/lidas", { method: "POST" });
        await carregarNotificacoes();
    });

    topo.appendChild(titulo);
    topo.appendChild(marcarTodas);

    const lista = document.createElement("ul");
    lista.className = "painel-notificacoes-lista";
    lista.id = "listaNotificacoes";

    painel.appendChild(topo);
    painel.appendChild(lista);

    // O painel fica dentro do botão-pai posicionado, para acompanhar o sino.
    botao.parentElement.style.position = botao.parentElement.style.position || "relative";
    botao.insertAdjacentElement("afterend", painel);

    return painel;
}

async function carregarNotificacoes() {
    try {
        const resposta = await api("/notificacoes");
        const dados = await resposta.json();

        if (!dados.sucesso) return;

        _notificacoes = dados.notificacoes || [];
        _atualizarContador(dados.nao_lidas || 0);

        if (_painelAberto) _desenharLista();
    } catch (erro) {
        // Falha ao buscar notificação não pode atrapalhar o resto da página.
        console.error("Erro ao carregar notificações:", erro);
    }
}

function _atualizarContador(naoLidas) {
    const botao = document.querySelector("#botaoNotificacoes");
    if (!botao) return;

    let badge = botao.querySelector(".badge");

    if (naoLidas === 0) {
        if (badge) badge.remove();
        botao.setAttribute("aria-label", "Notificações");
        return;
    }

    if (!badge) {
        badge = document.createElement("span");
        badge.className = "badge";
        botao.appendChild(badge);
    }

    badge.textContent = naoLidas > 9 ? "9+" : String(naoLidas);
    botao.setAttribute("aria-label", `Notificações: ${naoLidas} não lida(s)`);
}

function _formatarQuando(iso) {
    if (!iso) return "";

    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";

    const minutos = Math.floor((Date.now() - data.getTime()) / 60000);

    if (minutos < 1) return "agora";
    if (minutos < 60) return `há ${minutos} min`;
    if (minutos < 1440) return `há ${Math.floor(minutos / 60)} h`;
    if (minutos < 2880) return "ontem";

    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function _desenharLista() {
    const lista = document.querySelector("#listaNotificacoes");
    if (!lista) return;

    lista.innerHTML = "";

    if (_notificacoes.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "painel-notificacoes-vazio";
        vazio.textContent = "Nenhuma notificação por aqui.";
        lista.appendChild(vazio);
        return;
    }

    _notificacoes.forEach((notificacao) => {
        const item = document.createElement("li");
        item.className = `notificacao${notificacao.lida ? "" : " notificacao--nova"}`;

        const conteudo = document.createElement(notificacao.link ? "a" : "div");
        conteudo.className = "notificacao-conteudo";

        if (notificacao.link) {
            conteudo.href = notificacao.link;
        }

        const titulo = document.createElement("strong");
        titulo.textContent = notificacao.titulo;

        const mensagem = document.createElement("span");
        mensagem.textContent = notificacao.mensagem;

        const quando = document.createElement("time");
        quando.className = "notificacao-quando";
        quando.textContent = _formatarQuando(notificacao.criado_em);

        conteudo.appendChild(titulo);
        conteudo.appendChild(mensagem);
        conteudo.appendChild(quando);

        // Abrir a notificação já a marca como lida — é o comportamento que o
        // usuário espera, e evita ter que marcar manualmente uma por uma.
        conteudo.addEventListener("click", async () => {
            if (!notificacao.lida) {
                await api(`/notificacoes/${notificacao.id}/lida`, { method: "POST" });
                notificacao.lida = true;
                await carregarNotificacoes();
            }
        });

        item.appendChild(conteudo);
        lista.appendChild(item);
    });
}
