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
    ligarPlaceholders();
    ligarNotificacoes();
    document.querySelector("#botaoSair").addEventListener("click", sair);
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
function montarProgresso(progresso) {
    const cartao = document.querySelector("#cartaoProgresso");
    if (!cartao || !progresso) return;

    cartao.hidden = false;

    document.querySelector("#progressoNivel").textContent = progresso.nivel;
    document.querySelector("#progressoXp").textContent = `${progresso.xp} XP`;

    const faltam = progresso.xp_para_proximo_nivel - progresso.xp_no_nivel;
    document.querySelector("#progressoFaltam").textContent =
        `faltam ${faltam} XP para o nível ${progresso.nivel + 1}`;

    const percentual = Math.round((progresso.xp_no_nivel / progresso.xp_para_proximo_nivel) * 100);
    document.querySelector("#progressoBarra").style.width = `${percentual}%`;

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
