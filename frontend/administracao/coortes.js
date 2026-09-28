/**
 * Turmas de alunos (coortes) e as exceções por disciplina.
 *
 * Vocabulário: esta tela cuida da **turma** (MED 3A, o grupo que cursa junto).
 * A tela de Disciplinas cuida de Anatomia, Fisiologia, e de qual professor dá
 * cada uma. No código a disciplina se chama `turma` por herança — a nota está
 * em backend/regras/coortes.py.
 *
 * O desenho da exceção: cada aluno aparece com uma fileira de chips, uma por
 * disciplina da turma. Chip aceso = cursa; chip apagado = está fora. Um toque
 * alterna. Foi escolhido em cima de uma matriz aluno × disciplina porque a
 * matriz não cabe num celular, e o admin de uma faculdade mexe nisso do
 * telefone tanto quanto do computador.
 */

const usuario = exigirAcesso("adm");

if (usuario) {
    montarRodapePerfil(usuario);
    carregarCoortes();
    ligarFormularioCoorte();
    ligarPlaceholders();
    ligarNotificacoes();
    ligarRodapePerfil();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

/** "1 aluno" / "4 alunos" — plural errado numa tela de gestão irrita. */
function contar(quantidade, singular, plural) {
    return `${quantidade} ${quantidade === 1 ? singular : plural}`;
}

// =========================================================================
// Lista de turmas
// =========================================================================

async function carregarCoortes() {
    const lista = document.querySelector("#listaCoortes");
    const vazio = document.querySelector("#coortesVazio");

    try {
        const resposta = await api("/admin/coortes");
        const dados = await resposta.json();
        const coortes = dados.coortes || [];

        lista.innerHTML = "";

        if (coortes.length === 0) {
            vazio.hidden = false;
            vazio.textContent = 'Nenhuma turma criada ainda. Clique em "Nova turma" para começar.';
            return;
        }
        vazio.hidden = true;

        coortes.forEach((coorte) => {
            const linha = document.createElement("article");
            linha.className = "cartao material-linha";
            linha.innerHTML = `
                <div class="material-linha-info">
                    <h3>${esc(coorte.nome)} · ${esc(coorte.semestre)}</h3>
                    <p class="material-classificacao">
                        ${contar(coorte.total_alunos, "aluno", "alunos")} ·
                        ${contar(coorte.total_disciplinas, "disciplina", "disciplinas")}
                    </p>
                </div>
                <div class="material-linha-acoes">
                    <button type="button" class="acao" data-acao-abrir>Alunos</button>
                    <button type="button" class="acao acao--perigo" data-acao-desfazer>Desfazer</button>
                </div>
            `;

            linha.querySelector("[data-acao-desfazer]").addEventListener("click", () => desfazerCoorte(coorte));

            const painel = montarPainel(coorte);
            linha.querySelector("[data-acao-abrir]").addEventListener("click", () => {
                painel.hidden = !painel.hidden;
                if (!painel.hidden) carregarPainel(coorte, painel);
            });

            lista.appendChild(linha);
            lista.appendChild(painel);
        });
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function ligarFormularioCoorte() {
    const cartao = document.querySelector("#formularioCoorteCartao");
    const formulario = document.querySelector("#formularioCoorte");
    const mensagem = document.querySelector("#coorteMensagem");

    document.querySelector("#botaoNovaCoorte").addEventListener("click", () => {
        cartao.hidden = false;
        mensagem.textContent = "";
    });

    document.querySelector("#botaoCancelarCoorte").addEventListener("click", () => {
        cartao.hidden = true;
        formulario.reset();
        mensagem.textContent = "";
    });

    formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const nome = document.querySelector("#coorteNome").value.trim();
        const semestre = document.querySelector("#coorteSemestre").value.trim();

        try {
            const resposta = await api("/admin/coortes", {
                method: "POST",
                body: JSON.stringify({ nome, semestre }),
            });
            const dados = await resposta.json();

            mensagem.textContent = dados.mensagem;
            mensagem.classList.toggle("formulario-mensagem--sucesso", !!dados.sucesso);

            if (dados.sucesso) {
                formulario.reset();
                cartao.hidden = true;
                carregarCoortes();
            }
        } catch (erro) {
            console.error("Erro ao criar turma:", erro);
            mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
        }
    });
}

async function desfazerCoorte(coorte) {
    const confirmou = await confirmar(
        `Desfazer a turma "${coorte.nome} · ${coorte.semestre}"?\n\n` +
        "As disciplinas e as matrículas continuam — o aluno cursou, e isso não deixa " +
        "de ter acontecido. Elas só voltam a ser disciplinas soltas, e matricular " +
        "passa a ser uma por uma.",
        { titulo: "Desfazer turma", rotulo: "Desfazer", perigo: true }
    );
    if (!confirmou) return;

    try {
        const resposta = await api(`/admin/coortes/${coorte.id}`, { method: "DELETE" });
        const dados = await resposta.json();

        if (dados.sucesso) {
            carregarCoortes();
        } else {
            await avisarErro(dados.mensagem);
        }
    } catch (erro) {
        console.error("Erro ao desfazer turma:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}

// =========================================================================
// Painel: disciplinas da turma e alunos com as exceções
// =========================================================================

function montarPainel(coorte) {
    const painel = document.createElement("section");
    painel.className = "cartao";
    painel.hidden = true;
    painel.innerHTML = `
        <h3 class="cartao-titulo">${esc(coorte.nome)} · alunos e disciplinas</h3>
        <p class="campo-dica" data-resumo-disciplinas></p>
        <div class="formulario--linha">
            <div class="campo">
                <label>Adicionar aluno à turma</label>
                <select data-seletor-aluno></select>
            </div>
            <div class="campo campo--acoes">
                <button type="button" class="acao acao--primaria" data-acao-adicionar>Adicionar</button>
            </div>
        </div>
        <p class="formulario-mensagem" data-mensagem></p>
        <ul class="lista-entregas" data-lista-alunos style="margin-top: 12px;"></ul>
    `;
    return painel;
}

async function carregarPainel(coorte, painel) {
    const lista = painel.querySelector("[data-lista-alunos]");
    const seletor = painel.querySelector("[data-seletor-aluno]");
    const mensagem = painel.querySelector("[data-mensagem]");
    const resumo = painel.querySelector("[data-resumo-disciplinas]");

    try {
        const [rAlunos, rDisciplinas, rTodos] = await Promise.all([
            api(`/admin/coortes/${coorte.id}/alunos`),
            api(`/admin/coortes/${coorte.id}/disciplinas`),
            api("/admin/alunos"),
        ]);

        const alunos = (await rAlunos.json()).alunos || [];
        const disciplinas = (await rDisciplinas.json()).disciplinas || [];
        const todos = (await rTodos.json()).alunos || [];

        if (disciplinas.length === 0) {
            resumo.innerHTML =
                'Esta turma ainda não tem disciplinas. Crie uma em ' +
                '<a href="adm-turmas.html">Disciplinas</a> apontando para esta turma — ' +
                'os alunos que já estiverem aqui entram nela automaticamente.';
        } else {
            resumo.textContent =
                "Disciplinas: " + disciplinas.map((d) => `${d.nome} (Prof. ${d.professor_nome})`).join(", ");
        }

        desenharAlunos({ coorte, painel, lista, alunos, disciplinas });

        // Só quem ainda não está na turma pode ser adicionado; deixar todos na
        // lista convidaria ao erro que o servidor recusaria depois.
        const jaEstao = new Set(alunos.map((a) => a.email));
        const disponiveis = todos.filter((email) => !jaEstao.has(email));

        seletor.innerHTML = disponiveis.length
            ? disponiveis.map((email) => `<option value="${esc(email)}">${esc(email)}</option>`).join("")
            : '<option value="">Nenhum aluno disponível</option>';
    } catch (erro) {
        console.error("Erro ao carregar o painel da turma:", erro);
        mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
        return;
    }

    painel.querySelector("[data-acao-adicionar]").onclick = async () => {
        const alunoEmail = seletor.value;
        if (!alunoEmail) return;

        try {
            const resposta = await api(`/admin/coortes/${coorte.id}/alunos`, {
                method: "POST",
                body: JSON.stringify({ aluno_email: alunoEmail }),
            });
            const dados = await resposta.json();

            mensagem.textContent = dados.mensagem;
            mensagem.classList.toggle("formulario-mensagem--sucesso", !!dados.sucesso);

            if (dados.sucesso) {
                carregarPainel(coorte, painel);
                // O contador da linha de cima envelheceu junto.
                carregarCoortes();
            }
        } catch (erro) {
            console.error("Erro ao adicionar aluno:", erro);
            mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
        }
    };
}

function desenharAlunos({ coorte, painel, lista, alunos, disciplinas }) {
    lista.innerHTML = "";

    if (alunos.length === 0) {
        const item = document.createElement("li");
        item.textContent = "Nenhum aluno nesta turma ainda.";
        lista.appendChild(item);
        return;
    }

    alunos.forEach((aluno) => {
        const fora = new Set(aluno.fora_de.map((d) => d.turma_id));

        const item = document.createElement("li");
        item.className = "aluno-coorte";

        const info = document.createElement("div");
        info.className = "aluno-coorte-info";

        const nome = document.createElement("strong");
        nome.textContent = aluno.nome;
        info.appendChild(nome);

        if (aluno.email !== aluno.nome) {
            const email = document.createElement("span");
            email.className = "aluno-coorte-email";
            email.textContent = aluno.email;
            info.appendChild(email);
        }

        if (disciplinas.length > 0) {
            const chips = document.createElement("div");
            chips.className = "disciplina-chips";

            disciplinas.forEach((disciplina) => {
                const estaFora = fora.has(disciplina.id);

                const chip = document.createElement("button");
                chip.type = "button";
                chip.className = "disciplina-chip" + (estaFora ? " disciplina-chip--fora" : "");
                chip.textContent = disciplina.nome;
                chip.title = estaFora
                    ? `${aluno.nome} está fora de ${disciplina.nome}. Clique para devolver.`
                    : `${aluno.nome} cursa ${disciplina.nome}. Clique para tirar.`;
                chip.setAttribute("aria-pressed", String(!estaFora));
                chip.addEventListener("click", () =>
                    alternarExcecao({ coorte, painel, aluno, disciplina, estaFora })
                );

                chips.appendChild(chip);
            });

            info.appendChild(chips);
        }

        item.appendChild(info);

        const remover = document.createElement("button");
        remover.type = "button";
        remover.className = "botao-corrigir";
        remover.textContent = "Remover da turma";
        remover.addEventListener("click", () => removerDaCoorte(coorte, aluno, painel));
        item.appendChild(remover);

        lista.appendChild(item);
    });
}

/**
 * Tira ou devolve o aluno de uma disciplina.
 *
 * Sem confirmação de propósito: é reversível no mesmo clique, e um diálogo a
 * cada toque tornaria insuportável ajustar a grade de uma turma inteira. O que
 * precisa de confirmação é o irreversível — desfazer a turma, excluir.
 */
async function alternarExcecao({ coorte, painel, aluno, disciplina, estaFora }) {
    const mensagem = painel.querySelector("[data-mensagem]");

    try {
        const resposta = await api("/admin/excecoes", {
            method: estaFora ? "DELETE" : "POST",
            body: JSON.stringify({ aluno_email: aluno.email, turma_id: disciplina.id }),
        });
        const dados = await resposta.json();

        mensagem.textContent = dados.mensagem;
        mensagem.classList.toggle("formulario-mensagem--sucesso", !!dados.sucesso);

        if (dados.sucesso) carregarPainel(coorte, painel);
    } catch (erro) {
        console.error("Erro ao mudar a disciplina do aluno:", erro);
        mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

async function removerDaCoorte(coorte, aluno, painel) {
    const confirmou = await confirmar(
        `Remover ${aluno.nome} da turma "${coorte.nome}"?\n\n` +
        "Sai também de todas as disciplinas dela, e perde o acesso ao material.",
        { titulo: "Remover da turma", rotulo: "Remover", perigo: true }
    );
    if (!confirmou) return;

    try {
        const resposta = await api(`/admin/coortes/${coorte.id}/alunos`, {
            method: "DELETE",
            body: JSON.stringify({ aluno_email: aluno.email }),
        });
        const dados = await resposta.json();

        if (dados.sucesso) {
            carregarPainel(coorte, painel);
            carregarCoortes();
        } else {
            await avisarErro(dados.mensagem);
        }
    } catch (erro) {
        console.error("Erro ao remover aluno da turma:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
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
