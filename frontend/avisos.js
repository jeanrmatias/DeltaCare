/**
 * Avisos: escrever para as turmas, e ver o que chegou.
 *
 * Um arquivo para professor e administração, como mensagens.js. A diferença de
 * quem pode o quê é do servidor (regras/avisos.py); aqui muda só o que a tela
 * oferece — a administração tem a opção "instituição inteira" e escolhe entre
 * todas as disciplinas, o professor entre as dele.
 */

const perfil = window.location.pathname.includes("/professor/") ? "professor" : "adm";
const usuario = exigirAcesso(perfil);

let disciplinas = [];

if (usuario) {
    montarRodape(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    ligarFormulario();
    carregarDisciplinas();
    carregarEnviados();
    carregarRecebidos();
}

function montarRodape(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent =
        usuario.tipo === "professor" ? `Prof. ${nome}` : nome;
}

function quando(iso) {
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

// =========================================================================
// Destino
// =========================================================================

async function carregarDisciplinas() {
    const rota = perfil === "professor" ? "/turmas" : "/admin/turmas";
    const caixa = document.querySelector("#listaDisciplinas");

    try {
        const resposta = await api(rota);
        const dados = await resposta.json();
        disciplinas = dados.turmas || [];

        // A administração vê a lista inteira, e ela cresce semestre a
        // semestre. Só as do semestre vigente entram na escolha: aviso para
        // disciplina encerrada não chega a ninguém que ainda esteja lá.
        if (perfil === "adm") {
            const vigente = await semestreVigente();
            if (vigente) disciplinas = disciplinas.filter((d) => d.semestre === vigente);
        } else {
            disciplinas = disciplinas.filter((d) => d.vigente !== false);
        }

        caixa.textContent = "";
        if (!disciplinas.length) {
            caixa.textContent = "Nenhuma disciplina neste semestre.";
            return;
        }

        disciplinas.forEach((disciplina) => {
            const rotulo = document.createElement("label");
            rotulo.className = "aviso-disciplina";
            const marca = document.createElement("input");
            marca.type = "checkbox";
            marca.value = disciplina.id;
            marca.name = "disciplina";
            rotulo.appendChild(marca);
            rotulo.appendChild(document.createTextNode(
                perfil === "adm" && disciplina.professor_email
                    ? ` ${disciplina.nome} · ${disciplina.professor_email}`
                    : ` ${disciplina.nome}`
            ));
            caixa.appendChild(rotulo);
        });
    } catch (erro) {
        console.error("Erro ao carregar disciplinas:", erro);
        caixa.textContent = "Não foi possível carregar as disciplinas.";
    }
}

async function semestreVigente() {
    try {
        const resposta = await api("/semestre");
        return (await resposta.json()).semestre;
    } catch (erro) {
        return null;
    }
}

function marcadas() {
    return [...document.querySelectorAll('#listaDisciplinas input[name="disciplina"]:checked')]
        .map((caixa) => Number(caixa.value));
}

function ehGeral() {
    const geral = document.querySelector("#destinoGeral");
    return Boolean(geral && geral.checked);
}

/**
 * A opção "instituição inteira" só existe para a administração, e é criada
 * aqui em vez de estar no HTML: assim as duas páginas têm a mesma marcação, e
 * o professor não recebe um controle escondido que o servidor recusaria.
 */
function montarOpcaoGeral() {
    if (perfil !== "adm") return;

    const rotulo = document.createElement("label");
    rotulo.className = "aviso-marca";
    const caixa = document.createElement("input");
    caixa.type = "checkbox";
    caixa.id = "destinoGeral";
    rotulo.appendChild(caixa);
    rotulo.appendChild(document.createTextNode(" Para a instituição inteira"));
    document.querySelector("#blocoDestino").prepend(rotulo);
}

function ligarFormulario() {
    const formulario = document.querySelector("#formularioAviso");
    const mensagem = document.querySelector("#avisoMensagem");

    montarOpcaoGeral();

    document.querySelector("#marcarTodas").addEventListener("click", () => {
        const caixas = document.querySelectorAll('#listaDisciplinas input[name="disciplina"]');
        const todasMarcadas = [...caixas].every((c) => c.checked);
        caixas.forEach((c) => { c.checked = !todasMarcadas; });
    });

    // "Instituição inteira" desliga a escolha de disciplina: as duas coisas
    // ao mesmo tempo deixariam em dúvida para quem o aviso foi.
    const geral = document.querySelector("#destinoGeral");
    if (geral) {
        geral.addEventListener("change", () => {
            document.querySelector("#blocoDisciplinas").hidden = geral.checked;
        });
    }

    formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();
        mensagem.textContent = "";

        const titulo = document.querySelector("#avisoTitulo").value.trim();
        const conteudo = document.querySelector("#avisoConteudo").value.trim();
        const urgente = document.querySelector("#avisoUrgente").checked;
        const turmaIds = ehGeral() ? [] : marcadas();

        if (!ehGeral() && !turmaIds.length) {
            mensagem.textContent = "Escolha pelo menos uma disciplina.";
            return;
        }

        // Aviso não tem desfazer para quem já recebeu no sino. Confirmar com o
        // destino por extenso é o que evita mandar para a turma errada.
        const destino = ehGeral()
            ? "a instituição inteira"
            : disciplinas.filter((d) => turmaIds.includes(d.id)).map((d) => d.nome).join(", ");
        const confirmou = await confirmar(
            `Enviar${urgente ? " como URGENTE" : ""} para ${destino}?\n\n"${titulo}"`,
            { titulo: "Enviar aviso", rotulo: "Enviar" }
        );
        if (!confirmou) return;

        try {
            const resposta = await api("/avisos", {
                method: "POST",
                body: JSON.stringify({ titulo, conteudo, urgente, geral: ehGeral(), turma_ids: turmaIds }),
            });
            const dados = await resposta.json();

            mensagem.textContent = dados.mensagem;
            mensagem.classList.toggle("formulario-mensagem--sucesso", !!dados.sucesso);

            if (dados.sucesso) {
                formulario.reset();
                const bloco = document.querySelector("#blocoDisciplinas");
                if (bloco) bloco.hidden = false;
                carregarEnviados();
            }
        } catch (erro) {
            console.error("Erro ao enviar aviso:", erro);
            mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
        }
    });
}

// =========================================================================
// Listas
// =========================================================================

function montarAviso(aviso, { podeApagar }) {
    const cartao = document.createElement("article");
    cartao.className = "aviso" + (aviso.em_destaque ? " aviso--urgente" : "");

    const topo = document.createElement("div");
    topo.className = "aviso-topo";

    if (aviso.urgente) {
        const selo = document.createElement("span");
        selo.className = "aviso-selo";
        selo.textContent = "Urgente";
        topo.appendChild(selo);
    }

    const titulo = document.createElement("h3");
    titulo.textContent = aviso.titulo;
    topo.appendChild(titulo);
    cartao.appendChild(topo);

    const texto = document.createElement("p");
    texto.className = "aviso-conteudo";
    texto.textContent = aviso.conteudo;
    cartao.appendChild(texto);

    const rodape = document.createElement("p");
    rodape.className = "aviso-rodape";
    const destino = aviso.geral ? "Instituição inteira" : aviso.disciplinas.join(", ");
    rodape.textContent = podeApagar
        ? `${quando(aviso.criado_em)} · para ${destino}`
        : `${aviso.autor_e_administracao ? "Administração" : aviso.autor} · ${quando(aviso.criado_em)} · ${destino}`;
    cartao.appendChild(rodape);

    if (podeApagar) {
        const apagar = document.createElement("button");
        apagar.type = "button";
        apagar.className = "acao acao--discreta";
        apagar.textContent = "Apagar";
        apagar.addEventListener("click", () => apagarAviso(aviso));
        cartao.appendChild(apagar);
    }

    return cartao;
}

// `buscar` é a chamada inteira, e não só o caminho: com `api("/avisos/...")`
// escrito por extenso em quem chama, dá para achar no código quem usa cada
// rota (é o que backend/contrato_front.py confere).
async function carregarLista(buscar, seletor, vazioTexto, opcoes) {
    const lista = document.querySelector(seletor);
    try {
        const resposta = await buscar();
        const dados = await resposta.json();
        lista.textContent = "";

        if (!dados.avisos || !dados.avisos.length) {
            const vazio = document.createElement("p");
            vazio.className = "estado-vazio";
            vazio.textContent = vazioTexto;
            lista.appendChild(vazio);
            return;
        }

        dados.avisos.forEach((aviso) => lista.appendChild(montarAviso(aviso, opcoes)));
    } catch (erro) {
        console.error("Erro ao carregar avisos:", erro);
        lista.textContent = "Não foi possível carregar os avisos.";
    }
}

function carregarEnviados() {
    carregarLista(
        () => api("/avisos/enviados"),
        "#listaEnviados",
        "Você ainda não enviou nenhum aviso.",
        { podeApagar: true }
    );
}

function carregarRecebidos() {
    carregarLista(
        () => api("/avisos/recebidos"),
        "#listaRecebidos",
        perfil === "professor" ? "Nenhum aviso da administração." : "Nenhum aviso de outros administradores.",
        { podeApagar: false }
    );
}

async function apagarAviso(aviso) {
    const confirmou = await confirmar(
        `Apagar "${aviso.titulo}" do mural?\n\nQuem já foi avisado pelo sino continua com a notificação.`,
        { titulo: "Apagar aviso", rotulo: "Apagar", perigo: true }
    );
    if (!confirmou) return;

    try {
        const resposta = await api(`/avisos/${aviso.id}`, { method: "DELETE" });
        const dados = await resposta.json();
        if (dados.sucesso) {
            carregarEnviados();
        } else {
            await avisarErro(dados.mensagem);
        }
    } catch (erro) {
        console.error("Erro ao apagar aviso:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
