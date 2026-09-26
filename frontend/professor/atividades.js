/**
 * Atividades na visão do professor: criar, acompanhar e corrigir.
 *
 * Espelha a tela de materiais de propósito — mesma casca, mesmo seletor de
 * turma, mesmos três estados (rascunho, agendado, publicado). Quem já sabe
 * publicar material não precisa reaprender nada aqui.
 *
 * O que é diferente: a atividade tem **prazo** e tem **entregas**, e por isso
 * ganhou o painel de correção.
 */

const usuario = exigirAcesso("professor");

let turmas = [];
let turmaSelecionadaId = null;
let editandoId = null;
// Espelho do que está no formulário de questões. O DOM é a interface; a
// verdade fica aqui, senão ler o estado vira varredura de inputs.
let questoes = [];
// Seletores de data montados uma vez; guardados para ler e preencher depois.
let seletorLiberacao = null;
let seletorPrazo = null;

const ROTULOS_STATUS = {
    rascunho: "Rascunho",
    agendado: "Agendado",
    publicado: "Publicado",
};

const ROTULOS_TIPO = {
    objetiva: "Objetiva",
    dissertativa: "Dissertativa",
};

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    ligarFormulario();
    ligarPainelEntregas();
    carregarTurmas();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = `Prof. ${nome}`;
}

/** Escapa texto que vai para innerHTML. Título e enunciado são digitados. */
function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function formatarData(iso) {
    if (!iso) return "";
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleString("pt-BR", {
        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
}

// =========================================================================
// Turmas
// =========================================================================

async function carregarTurmas() {
    try {
        const resposta = await api("/turmas");
        const dados = await resposta.json();
        turmas = dados.turmas || [];

        const seletor = document.querySelector("#seletorTurma");
        const semTurmas = document.querySelector("#semTurmas");

        if (turmas.length === 0) {
            semTurmas.hidden = false;
            document.querySelector("#seletorTurmaCampo").hidden = true;
            document.querySelector("#botaoNova").disabled = true;
            document.querySelector("#lista").innerHTML = "";
            document.querySelector("#vazio").hidden = true;
            return;
        }

        semTurmas.hidden = true;
        document.querySelector("#seletorTurmaCampo").hidden = false;
        document.querySelector("#botaoNova").disabled = false;

        seletor.innerHTML = "";
        turmas.forEach((turma) => {
            const opcao = document.createElement("option");
            opcao.value = turma.id;
            opcao.textContent = `${turma.nome} · ${turma.semestre}`;
            seletor.appendChild(opcao);
        });

        if (!turmaSelecionadaId || !turmas.some((t) => t.id === turmaSelecionadaId)) {
            turmaSelecionadaId = turmas[0].id;
        }
        seletor.value = turmaSelecionadaId;

        seletor.onchange = () => {
            turmaSelecionadaId = Number(seletor.value);
            carregarAtividades();
        };

        carregarAtividades();
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
        document.querySelector("#vazio").hidden = false;
        document.querySelector("#vazio").textContent =
            "Não foi possível conectar ao servidor. Verifique se o backend está no ar.";
    }
}

// =========================================================================
// Listagem
// =========================================================================

async function carregarAtividades() {
    const lista = document.querySelector("#lista");
    const vazio = document.querySelector("#vazio");

    try {
        const resposta = await api(`/atividades?turma_id=${turmaSelecionadaId}`);
        const dados = await resposta.json();
        const atividades = dados.atividades || [];

        lista.innerHTML = "";
        vazio.hidden = atividades.length > 0;

        atividades.forEach((atividade) => lista.appendChild(criarLinha(atividade)));
    } catch (erro) {
        console.error("Erro ao carregar atividades:", erro);
        lista.innerHTML = "";
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function criarLinha(atividade) {
    const linha = document.createElement("article");
    linha.className = "cartao material-linha";

    const classificacao = [atividade.assunto, atividade.topico]
        .filter(Boolean).join(" · ");

    const detalhes = [];
    if (atividade.tipo === "objetiva") {
        detalhes.push(`${atividade.total_questoes} questão(ões)`);
    }
    detalhes.push(`vale ${atividade.pontos}`);
    if (atividade.prazo) detalhes.push(`prazo ${formatarData(atividade.prazo)}`);

    // Só faz sentido falar de entrega no que o aluno já pode ver.
    const acompanhamento = atividade.status === "publicado"
        ? `<p class="atividade-acompanhamento">
               <strong>${atividade.entregues}</strong> de ${atividade.total_alunos} entregaram
               ${atividade.a_corrigir > 0 ? ` · <span class="atividade-pendencia">${atividade.a_corrigir} a corrigir</span>` : ""}
           </p>`
        : "";

    linha.innerHTML = `
        <div class="material-linha-info">
            <div class="material-linha-topo">
                <span class="badge-tipo">${ROTULOS_TIPO[atividade.tipo] ?? atividade.tipo}</span>
                <span class="badge-status badge-status--${atividade.status}">${ROTULOS_STATUS[atividade.status]}</span>
            </div>
            <h3>${esc(atividade.titulo)}</h3>
            ${classificacao ? `<p class="material-classificacao">${esc(classificacao)}</p>` : ""}
            <p class="material-descricao">${esc(detalhes.join(" · "))}</p>
            ${acompanhamento}
        </div>
        <div class="material-linha-acoes">
            ${atividade.status === "publicado" ? `<button type="button" class="acao" data-acao-entregas>Entregas</button>` : ""}
            <button type="button" class="acao" data-acao-editar>Editar</button>
            <button type="button" class="acao acao--perigo" data-acao-excluir>Excluir</button>
        </div>
    `;

    const botaoEntregas = linha.querySelector("[data-acao-entregas]");
    if (botaoEntregas) {
        botaoEntregas.addEventListener("click", () => abrirEntregas(atividade));
    }
    linha.querySelector("[data-acao-editar]").addEventListener("click", () => abrirFormulario(atividade));
    linha.querySelector("[data-acao-excluir]").addEventListener("click", () => excluir(atividade));

    return linha;
}

// =========================================================================
// Formulário
// =========================================================================

function ligarFormulario() {
    seletorLiberacao = criarSeletorDataHora(document.querySelector("#campoLiberacao"));
    seletorPrazo = criarSeletorDataHora(document.querySelector("#campoPrazo"));

    document.querySelector("#botaoNova").addEventListener("click", () => abrirFormulario(null));
    document.querySelector("#botaoCancelar").addEventListener("click", fecharFormulario);
    document.querySelector("#botaoAddQuestao").addEventListener("click", () => {
        questoes.push({ enunciado: "", alternativas: ["", ""], correta: 0 });
        desenharQuestoes();
    });

    document.querySelector("#campoTipo").addEventListener("change", aplicarTipo);

    document.querySelector("#formulario").addEventListener("submit", async (evento) => {
        evento.preventDefault();
        const rascunho = evento.submitter?.dataset.acao === "rascunho";
        await salvar(rascunho);
    });
}

function aplicarTipo() {
    const objetiva = document.querySelector("#campoTipo").value === "objetiva";
    document.querySelector("#blocoQuestoes").hidden = !objetiva;
}

function abrirFormulario(atividade) {
    const cartao = document.querySelector("#formularioCartao");
    const titulo = document.querySelector("#formularioTitulo");
    const campoTurmas = document.querySelector("#campoTurmasPublicacao");

    editandoId = atividade ? atividade.id : null;
    limparMensagem();

    if (atividade) {
        titulo.textContent = "Editar atividade";
        document.querySelector("#campoTitulo").value = atividade.titulo;
        document.querySelector("#campoEnunciado").value = atividade.enunciado || "";
        document.querySelector("#campoTipo").value = atividade.tipo;
        document.querySelector("#campoPontos").value = atividade.pontos;
        document.querySelector("#campoAssunto").value = atividade.assunto || "";
        document.querySelector("#campoTopico").value = atividade.topico || "";
        seletorLiberacao.definir(atividade.data_liberacao);
        seletorPrazo.definir(atividade.prazo);

        // Edição vale para o registro daquela turma, como nos materiais. E as
        // questões não são editáveis depois de criadas: mudar o gabarito com
        // entregas já corrigidas bagunçaria as notas que o aluno já viu.
        campoTurmas.hidden = true;
        document.querySelector("#campoTipo").disabled = true;
        document.querySelector("#blocoQuestoes").hidden = true;
        questoes = [];
    } else {
        titulo.textContent = "Nova atividade";
        document.querySelector("#formulario").reset();
        // O reset() não alcança os seletores de data: eles não são campos do
        // formulário, são componentes com estado próprio.
        seletorLiberacao.limpar();
        seletorPrazo.limpar();
        document.querySelector("#campoPontos").value = 10;
        document.querySelector("#campoTipo").disabled = false;
        campoTurmas.hidden = false;
        montarTurmasCheck();
        questoes = [{ enunciado: "", alternativas: ["", ""], correta: 0 }];
        desenharQuestoes();
        aplicarTipo();
    }

    cartao.hidden = false;
    cartao.scrollIntoView({ behavior: "smooth", block: "start" });
    document.querySelector("#campoTitulo").focus();
}

function fecharFormulario() {
    document.querySelector("#formularioCartao").hidden = true;
    document.querySelector("#campoTipo").disabled = false;
    editandoId = null;
    questoes = [];
    limparMensagem();
}

function montarTurmasCheck() {
    const caixa = document.querySelector("#listaTurmasCheck");
    const dica = document.querySelector("#dicaTurmas");
    caixa.innerHTML = "";

    if (turmas.length > 1) {
        const rotuloTodas = document.createElement("label");
        rotuloTodas.className = "turma-check turma-check--todas";
        rotuloTodas.innerHTML = `<input type="checkbox" id="turmasTodas"> Selecionar todas`;
        caixa.appendChild(rotuloTodas);
    }

    turmas.forEach((turma) => {
        const rotulo = document.createElement("label");
        rotulo.className = "turma-check";
        rotulo.innerHTML =
            `<input type="checkbox" name="turma" value="${turma.id}"` +
            `${turma.id === turmaSelecionadaId ? " checked" : ""}> ` +
            `${esc(turma.nome)} <span class="turma-semestre">${esc(turma.semestre)}</span>`;
        caixa.appendChild(rotulo);
    });

    const todas = caixa.querySelector("#turmasTodas");
    if (todas) {
        todas.addEventListener("change", () => {
            caixa.querySelectorAll('input[name="turma"]').forEach((c) => {
                c.checked = todas.checked;
            });
        });
    }

    dica.textContent = turmas.length > 1
        ? "A mesma atividade entra em cada turma marcada."
        : "";
}

function turmasMarcadas() {
    return [...document.querySelectorAll('#listaTurmasCheck input[name="turma"]:checked')]
        .map((c) => Number(c.value));
}

// -------------------------------------------------------------- questões

function desenharQuestoes() {
    const caixa = document.querySelector("#listaQuestoes");
    caixa.innerHTML = "";

    questoes.forEach((questao, indice) => {
        const bloco = document.createElement("div");
        bloco.className = "questao-editor";

        const alternativas = questao.alternativas.map((texto, posicao) => `
            <div class="questao-alternativa">
                <input type="radio" name="correta-${indice}" ${questao.correta === posicao ? "checked" : ""}
                       data-correta="${posicao}" aria-label="Marcar como correta">
                <input type="text" value="${esc(texto)}" data-alternativa="${posicao}"
                       placeholder="Alternativa ${posicao + 1}">
                ${questao.alternativas.length > 2
                    ? `<button type="button" class="acao acao--perigo" data-remover-alternativa="${posicao}">×</button>`
                    : ""}
            </div>
        `).join("");

        bloco.innerHTML = `
            <div class="questao-topo">
                <strong>Questão ${indice + 1}</strong>
                ${questoes.length > 1
                    ? `<button type="button" class="acao acao--perigo" data-remover-questao>Remover</button>`
                    : ""}
            </div>
            <input type="text" class="questao-enunciado" value="${esc(questao.enunciado)}"
                   placeholder="Enunciado da questão">
            <div class="questao-alternativas">${alternativas}</div>
            <button type="button" class="acao" data-add-alternativa>+ Alternativa</button>
        `;

        bloco.querySelector(".questao-enunciado").addEventListener("input", (e) => {
            questao.enunciado = e.target.value;
        });

        bloco.querySelectorAll("[data-alternativa]").forEach((campo) => {
            campo.addEventListener("input", (e) => {
                questao.alternativas[Number(campo.dataset.alternativa)] = e.target.value;
            });
        });

        bloco.querySelectorAll("[data-correta]").forEach((radio) => {
            radio.addEventListener("change", () => {
                questao.correta = Number(radio.dataset.correta);
            });
        });

        bloco.querySelector("[data-add-alternativa]").addEventListener("click", () => {
            questao.alternativas.push("");
            desenharQuestoes();
        });

        bloco.querySelectorAll("[data-remover-alternativa]").forEach((botao) => {
            botao.addEventListener("click", () => {
                const posicao = Number(botao.dataset.removerAlternativa);
                questao.alternativas.splice(posicao, 1);
                if (questao.correta >= questao.alternativas.length) {
                    questao.correta = 0;
                }
                desenharQuestoes();
            });
        });

        const removerQuestao = bloco.querySelector("[data-remover-questao]");
        if (removerQuestao) {
            removerQuestao.addEventListener("click", () => {
                questoes.splice(indice, 1);
                desenharQuestoes();
            });
        }

        caixa.appendChild(bloco);
    });
}

// -------------------------------------------------------------- salvar

function limparMensagem() {
    const mensagem = document.querySelector("#mensagem");
    mensagem.textContent = "";
    mensagem.className = "formulario-mensagem";
}

function mostrarMensagem(texto, sucesso = false) {
    const mensagem = document.querySelector("#mensagem");
    mensagem.textContent = texto;
    mensagem.className = "formulario-mensagem" + (sucesso ? " formulario-mensagem--sucesso" : "");
}

async function salvar(rascunho) {
    const titulo = document.querySelector("#campoTitulo").value.trim();

    if (!titulo) {
        mostrarMensagem("Informe o título da atividade.");
        return;
    }

    const corpo = {
        titulo,
        enunciado: document.querySelector("#campoEnunciado").value.trim(),
        assunto: document.querySelector("#campoAssunto").value.trim(),
        topico: document.querySelector("#campoTopico").value.trim(),
        pontos: Number(document.querySelector("#campoPontos").value) || 10,
        rascunho,
        data_liberacao: seletorLiberacao.valor(),
        prazo: seletorPrazo.valor(),
    };

    try {
        let resposta;

        if (editandoId) {
            resposta = await api(`/atividades/${editandoId}`, {
                method: "PUT",
                body: JSON.stringify(corpo),
            });
        } else {
            const alvos = turmasMarcadas();
            if (alvos.length === 0) {
                mostrarMensagem("Escolha pelo menos uma turma.");
                return;
            }

            corpo.turma_ids = alvos;
            corpo.tipo = document.querySelector("#campoTipo").value;

            if (corpo.tipo === "objetiva") {
                corpo.questoes = questoes.map((q) => ({
                    enunciado: q.enunciado.trim(),
                    alternativas: q.alternativas.map((a) => a.trim()).filter(Boolean),
                    correta: q.correta,
                }));
            }

            resposta = await api("/atividades", {
                method: "POST",
                body: JSON.stringify(corpo),
            });
        }

        const dados = await resposta.json();

        if (dados.sucesso) {
            mostrarMensagem(dados.mensagem, true);
            fecharFormulario();
            carregarAtividades();
        } else {
            mostrarMensagem(dados.mensagem || dados.detail || "Não foi possível salvar.");
        }
    } catch (erro) {
        console.error("Erro ao salvar atividade:", erro);
        mostrarMensagem("Não foi possível conectar ao servidor. Tente novamente.");
    }
}

async function excluir(atividade) {
    const confirmou = await confirmar(
        `Excluir "${atividade.titulo}"?\n\nAs entregas e as notas dos alunos saem junto. Não há como desfazer.`,
        { titulo: "Excluir atividade", rotulo: "Excluir", perigo: true }
    );
    if (!confirmou) return;

    try {
        const resposta = await api(`/atividades/${atividade.id}`, { method: "DELETE" });
        const dados = await resposta.json();

        if (dados.sucesso) {
            carregarAtividades();
        } else {
            await avisarErro(dados.mensagem);
        }
    } catch (erro) {
        console.error("Erro ao excluir atividade:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}

// =========================================================================
// Entregas e correção
// =========================================================================

function ligarPainelEntregas() {
    document.querySelector("#fecharEntregas").addEventListener("click", () => {
        document.querySelector("#painelEntregas").close();
    });
}

async function abrirEntregas(atividade) {
    const painel = document.querySelector("#painelEntregas");
    const corpo = document.querySelector("#entregasCorpo");

    document.querySelector("#entregasTitulo").textContent = atividade.titulo;
    document.querySelector("#entregasDetalhe").textContent =
        [atividade.turma_nome, `vale ${atividade.pontos}`,
         atividade.prazo ? `prazo ${formatarData(atividade.prazo)}` : ""]
            .filter(Boolean).join(" · ");

    corpo.innerHTML = "<p class='visualizador-carregando'>Carregando entregas...</p>";
    painel.showModal();

    try {
        const resposta = await api(`/atividades/${atividade.id}/entregas`);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            corpo.innerHTML = `<p class="estado-vazio">${esc(dados.mensagem)}</p>`;
            return;
        }

        corpo.innerHTML = "";
        dados.entregas.forEach((entrega) => {
            corpo.appendChild(criarLinhaEntrega(entrega, dados.atividade, dados.questoes || []));
        });
    } catch (erro) {
        console.error("Erro ao carregar entregas:", erro);
        corpo.innerHTML = "<p class='estado-vazio'>Não foi possível carregar as entregas.</p>";
    }
}

/**
 * O que o aluno marcou em cada questão, com acerto e erro visíveis.
 *
 * A nota da objetiva sai sozinha, mas o professor precisa **ver onde** a turma
 * errou — é isso que diz qual tópico precisa ser retomado em aula. Um número
 * de acertos sozinho não conta essa história.
 */
function gabaritoDoAluno(questoes, escolhas) {
    if (!questoes.length || !Array.isArray(escolhas)) return "";

    const linhas = questoes.map((questao, indice) => {
        const marcada = escolhas[indice];
        const respondeu = marcada !== null && marcada !== undefined;
        const acertou = respondeu && marcada === questao.correta;

        const textoMarcado = respondeu
            ? esc(questao.alternativas[marcada] ?? "—")
            : "não respondeu";

        const esperado = acertou
            ? ""
            : `<span class="gabarito-certo">correta: ${esc(questao.alternativas[questao.correta])}</span>`;

        return `
            <li class="gabarito-item ${acertou ? "gabarito-item--certo" : "gabarito-item--errado"}">
                <span class="gabarito-marca">${acertou ? "✓" : "✗"}</span>
                <span class="gabarito-texto">
                    <strong>${indice + 1}.</strong> ${esc(questao.enunciado)}
                    <span class="gabarito-marcada">marcou: ${textoMarcado}</span>
                    ${esperado}
                </span>
            </li>
        `;
    });

    return `<ul class="gabarito-lista">${linhas.join("")}</ul>`;
}

function criarLinhaEntrega(entrega, atividade, questoes) {
    const linha = document.createElement("article");
    linha.className = "entrega-linha";

    let situacao;
    if (!entrega.entregue) {
        situacao = `<span class="badge-status badge-status--rascunho">Não entregou</span>`;
    } else if (entrega.nota !== null && entrega.nota !== undefined) {
        situacao = `<span class="badge-status badge-status--publicado">Nota ${entrega.nota}</span>`;
    } else {
        situacao = `<span class="badge-status badge-status--agendado">A corrigir</span>`;
    }

    const atraso = entrega.atrasada
        ? `<span class="atividade-pendencia">entregue com atraso</span>`
        : "";

    // Dissertativa mostra o texto; objetiva mostra o que foi marcado questão a
    // questão, com o gabarito ao lado.
    let resposta = "";
    if (entrega.entregue && typeof entrega.respostas === "string") {
        resposta = `<p class="entrega-resposta">${esc(entrega.respostas)}</p>`;
    } else if (entrega.entregue && Array.isArray(entrega.respostas)) {
        resposta = gabaritoDoAluno(questoes, entrega.respostas);
    }

    linha.innerHTML = `
        <div class="entrega-info">
            <strong>${esc(entrega.aluno_nome)}</strong>
            <span>${situacao} ${entrega.enviado_em ? `· ${formatarData(entrega.enviado_em)}` : ""} ${atraso}</span>
            ${resposta}
            ${entrega.devolutiva ? `<p class="entrega-devolutiva">${esc(entrega.devolutiva)}</p>` : ""}
        </div>
        ${entrega.entregue
            ? `<button type="button" class="botao-corrigir" data-corrigir>${entrega.nota !== null && entrega.nota !== undefined ? "Rever nota" : "Corrigir"}</button>`
            : ""}
    `;

    const botao = linha.querySelector("[data-corrigir]");
    if (botao) {
        botao.addEventListener("click", () => corrigir(entrega, atividade));
    }

    return linha;
}

async function corrigir(entrega, atividade) {
    const resultado = await perguntar(
        [
            {
                nome: "nota",
                rotulo: `Nota (0 a ${atividade.pontos})`,
                tipo: "number",
                // String, não número: o diálogo faz `campo.valor || ""`, e a
                // nota 0 cairia no lado falso, aparecendo em branco.
                valor: entrega.nota === null || entrega.nota === undefined
                    ? ""
                    : String(entrega.nota),
            },
            {
                nome: "devolutiva",
                rotulo: "Devolutiva para o aluno",
                valor: entrega.devolutiva ?? "",
            },
        ],
        {
            titulo: `Corrigir — ${entrega.aluno_nome}`,
            mensagem: "O aluno recebe a nota e a devolutiva, e é avisado pelo sino.",
            rotulo: "Salvar correção",
        }
    );

    if (!resultado) return;

    try {
        const resposta = await api(`/entregas/${entrega.entrega_id}/correcao`, {
            method: "POST",
            body: JSON.stringify({
                nota: Number(resultado.nota),
                devolutiva: resultado.devolutiva || "",
            }),
        });
        const dados = await resposta.json();

        if (dados.sucesso) {
            await abrirEntregas(atividade);
            carregarAtividades();
        } else {
            await avisarErro(dados.mensagem);
        }
    } catch (erro) {
        console.error("Erro ao corrigir:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
