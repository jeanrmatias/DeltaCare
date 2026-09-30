/**
 * Tela inicial do aluno.
 *
 * Tudo aqui vem da API (`/aluno/resumo`): números, turmas e materiais recentes.
 * Nada é exemplo fixo — se não houver dado, a tela mostra o estado vazio em vez
 * de preencher com conteúdo inventado.
 */

const usuario = exigirAcesso("aluno");

if (usuario) {
    montarRodapePerfil(usuario);
    carregarResumo();
    carregarAvisos();
    ligarPlaceholders();
    ligarNotificacoes();
    ligarRodapePerfil();
}

/**
 * O mural de avisos, na tela em que o aluno entra — e não numa página à
 * parte, que ele teria que lembrar de abrir. O sino já avisou; aqui o aviso
 * fica para ser relido. Urgente recente vem no topo (o servidor ordena).
 */
async function carregarAvisos() {
    const cartao = document.querySelector("#cartaoAvisos");
    const lista = document.querySelector("#listaAvisos");

    try {
        const resposta = await api("/avisos/recebidos");
        const dados = await resposta.json();
        const avisos = (dados.avisos || []).slice(0, 5);

        // Sem aviso, sem cartão: um "Nenhum aviso" fixo na tela inicial
        // ocuparia espaço para dizer nada.
        cartao.hidden = !avisos.length;
        lista.textContent = "";

        avisos.forEach((aviso) => {
            const item = document.createElement("article");
            item.className = "aviso" + (aviso.em_destaque ? " aviso--urgente" : "");

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

            const texto = document.createElement("p");
            texto.className = "aviso-conteudo";
            texto.textContent = aviso.conteudo;

            const rodape = document.createElement("p");
            rodape.className = "aviso-rodape";
            const autor = aviso.autor_e_administracao ? "Coordenação" : `Prof. ${aviso.autor}`;
            const data = new Date(aviso.criado_em).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
            rodape.textContent = `${autor} · ${data}` + (aviso.disciplinas.length ? ` · ${aviso.disciplinas.join(", ")}` : "");

            item.appendChild(topo);
            item.appendChild(texto);
            item.appendChild(rodape);
            lista.appendChild(item);
        });
    } catch (erro) {
        // O mural é complemento da tela inicial: falhar aqui não pode
        // derrubar o resto dela.
        console.error("Erro ao carregar avisos:", erro);
    }
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#saudacao").textContent = `Olá, ${nome}`;
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

const ROTULOS_TIPO = {
    pdf: "PDF",
    documento: "Documento",
    video: "Vídeo",
    link: "Link",
};

function formatarData(iso) {
    if (!iso) return "";
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

async function carregarResumo() {
    const semTurmas = document.querySelector("#semTurmas");
    const painel = document.querySelector("#painelConteudo");

    try {
        const resposta = await api("/aluno/resumo");
        const dados = await resposta.json();

        if (!dados.sucesso) {
            semTurmas.hidden = false;
            semTurmas.textContent = dados.mensagem || "Não foi possível carregar seus dados.";
            return;
        }

        document.querySelector("#statTurmas").textContent = dados.total_turmas;
        document.querySelector("#statMateriais").textContent = dados.total_materiais;
        document.querySelector("#statPerguntas").textContent = dados.perguntas_feitas;

        if ((dados.turmas || []).length === 0) {
            semTurmas.hidden = false;
            painel.hidden = true;
            return;
        }

        semTurmas.hidden = true;
        painel.hidden = false;

        montarProgresso(dados.progresso);
        montarTurmas(dados.turmas || []);
        montarRecentes(dados.materiais_recentes || []);
    } catch (erro) {
        console.error("Erro ao carregar o resumo:", erro);
        semTurmas.hidden = false;
        semTurmas.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

/**
 * Desenha o cartão de progresso.
 *
 * Todo número aqui vem do servidor, calculado sobre o que o aluno realmente
 * fez (perguntas ao assistente, materiais abertos, dias com atividade). A
 * composição fica visível de propósito: XP sem explicação de origem não
 * engaja, irrita.
 */
/**
 * Pinta o escudo com a cor da faixa e escreve o nome dela.
 *
 * Bronze, Prata, Ouro, Platina. A faixa vem pronta do servidor
 * (regras/aluno.faixa_do_nivel) — aqui não há nenhum limite de nível escrito,
 * de propósito: os limites são regra de produto, e se a tela também os
 * soubesse, mudar a regra exigiria mudar os dois e lembrar dos dois.
 *
 * O `faltam N níveis` importa mais do que o nome: uma faixa sem próximo degrau
 * visível é só um adjetivo. Em Platina o servidor manda `proxima: null`, e a
 * frase muda em vez de prometer um degrau que não existe.
 */
function montarFaixa(progresso, anel) {
    const faixa = progresso.faixa;
    const nome = document.querySelector("#progressoFaixa");
    if (!faixa || !nome) return;

    anel.dataset.faixa = faixa.chave;
    nome.textContent = faixa.nome;

    const rodape = document.querySelector("#progressoFaixaMeta");
    if (!rodape) return;

    if (!faixa.proxima) {
        rodape.textContent = "Faixa máxima — e o nível continua subindo.";
        return;
    }

    const faltam = faixa.nivel_da_proxima - progresso.nivel;
    rodape.textContent = faltam === 1
        ? `Falta 1 nível para ${faixa.proxima}.`
        : `Faltam ${faltam} níveis para ${faixa.proxima}.`;
}

function montarProgresso(progresso) {
    const cartao = document.querySelector("#cartaoProgresso");
    if (!cartao || !progresso) return;

    cartao.hidden = false;

    document.querySelector("#progressoNivel").textContent = progresso.nivel;
    document.querySelector("#progressoXp").textContent = `${progresso.xp} XP`;

    // Nível e faixa são do semestre (ver regras/aluno._calcular_progresso). Sem
    // dizer isso, a virada de semestre pareceria o sistema perdendo o XP do
    // aluno — o total acumulado vai junto para mostrar que não perdeu.
    const semestre = document.querySelector("#progressoSemestre");
    if (semestre && progresso.semestre) {
        const total = progresso.xp_total ?? progresso.xp;
        semestre.textContent = total > progresso.xp
            ? `Semestre ${progresso.semestre} · ${total} XP desde o início`
            : `Semestre ${progresso.semestre}`;
    }

    const faltam = progresso.xp_para_proximo_nivel - progresso.xp_no_nivel;
    document.querySelector("#progressoFaltam").textContent =
        `faltam ${faltam} XP para o nível ${progresso.nivel + 1}`;

    const percentual = Math.round((progresso.xp_no_nivel / progresso.xp_para_proximo_nivel) * 100);
    document.querySelector("#progressoBarra").style.width = `${percentual}%`;

    // O anel do escudo mostra o mesmo avanço, e é o que faz a forma informar em
    // vez de enfeitar. Vai por variável CSS: o conic-gradient lê daqui, e assim
    // o desenho fica todo no CSS e o JS só entrega o número.
    const anel = document.querySelector("#progressoAnel");
    anel.style.setProperty("--avanco", `${percentual}%`);

    montarFaixa(progresso, anel);

    // A sequência só aparece quando existe: "0 dias seguidos" é um lembrete
    // de fracasso, não um incentivo.
    const sequencia = document.querySelector("#progressoSequencia");
    if (progresso.sequencia > 0) {
        sequencia.hidden = false;
        document.querySelector("#progressoSequenciaDias").textContent = progresso.sequencia;
    } else {
        sequencia.hidden = true;
    }

    montarComposicao(progresso.composicao || []);
    montarFrequencia(progresso.acompanhamento || [], progresso.dias_ativos || 0);
}

function montarComposicao(itens) {
    const area = document.querySelector("#progressoComposicao");
    area.innerHTML = "";

    itens.forEach((item) => {
        const linha = document.createElement("div");
        linha.className = "composicao-linha";

        const rotulo = document.createElement("span");
        rotulo.className = "composicao-rotulo";
        rotulo.textContent = item.rotulo;

        const valor = document.createElement("span");
        valor.className = "composicao-valor";
        valor.textContent = `${item.quantidade} · ${item.xp} XP`;

        linha.appendChild(rotulo);
        linha.appendChild(valor);
        area.appendChild(linha);
    });
}

function montarFrequencia(dias, totalDiasAtivos) {
    const grade = document.querySelector("#frequenciaGrade");
    const resumo = document.querySelector("#frequenciaResumo");

    grade.innerHTML = "";

    dias.forEach((entrada) => {
        const quadrado = document.createElement("span");
        quadrado.className = `frequencia-dia${entrada.ativo ? " frequencia-dia--ativo" : ""}`;

        // title e aria-label: o quadradinho sozinho não diz que dia é.
        const data = new Date(`${entrada.dia}T12:00:00`);
        const rotulo = data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
        const estado = entrada.ativo ? "com estudo" : "sem registro";

        quadrado.title = `${rotulo} — ${estado}`;
        quadrado.setAttribute("aria-label", `${rotulo}, ${estado}`);

        grade.appendChild(quadrado);
    });

    const ativosNaJanela = dias.filter((d) => d.ativo).length;
    resumo.textContent = ativosNaJanela === 0
        ? "Nenhum estudo registrado nas últimas duas semanas."
        : `${ativosNaJanela} de ${dias.length} dias com estudo · ${totalDiasAtivos} no total`;
}

function montarTurmas(turmas) {
    const lista = document.querySelector("#listaTurmas");
    lista.innerHTML = "";

    turmas.forEach((turma) => {
        const cartao = document.createElement("article");
        cartao.className = "cartao turma-cartao";

        const titulo = document.createElement("h2");
        titulo.textContent = turma.nome;

        const semestre = document.createElement("span");
        semestre.className = "turma-semestre";
        semestre.textContent = turma.semestre;

        const contagem = document.createElement("p");
        const total = turma.total_materiais || 0;
        contagem.textContent =
            total === 0
                ? "Nenhum material liberado ainda"
                : `${total} material${total > 1 ? "is" : ""} liberado${total > 1 ? "s" : ""}`;

        const link = document.createElement("a");
        link.className = "acao";
        link.href = `materiais.html?turma=${turma.id}`;
        link.textContent = "Ver materiais";

        cartao.appendChild(titulo);
        cartao.appendChild(semestre);
        cartao.appendChild(contagem);
        cartao.appendChild(link);
        lista.appendChild(cartao);
    });
}

function montarRecentes(materiais) {
    const lista = document.querySelector("#listaRecentes");
    lista.innerHTML = "";

    if (materiais.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "lista-recentes-vazio";
        vazio.textContent = "Nenhum material liberado ainda.";
        lista.appendChild(vazio);
        return;
    }

    materiais.forEach((material) => {
        const item = document.createElement("li");

        const badge = document.createElement("span");
        badge.className = "badge-tipo";
        badge.textContent = ROTULOS_TIPO[material.tipo] || material.tipo;

        const info = document.createElement("div");
        info.className = "recente-info";

        const titulo = document.createElement("strong");
        titulo.textContent = material.titulo;

        const detalhe = document.createElement("span");
        const partes = [material.turma_nome, formatarData(material.criado_em)].filter(Boolean);
        detalhe.textContent = partes.join(" · ");

        info.appendChild(titulo);
        info.appendChild(detalhe);

        item.appendChild(badge);
        item.appendChild(info);
        lista.appendChild(item);
    });
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
