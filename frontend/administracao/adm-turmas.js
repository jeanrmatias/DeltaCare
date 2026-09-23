const usuario = exigirAcesso("adm");

if (usuario) {
    montarRodapePerfil(usuario);
    carregarProfessoresETurmas();
    ligarFormularioTurma();
    ligarPlaceholders();
    document.querySelector("#botaoSair").addEventListener("click", sair);
}

function montarRodapePerfil(usuario) {
    const nome = nomeAPartirDoEmail(usuario.email);
    document.querySelector("#avatarRodape").textContent = iniciais(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

function nomeAPartirDoEmail(email) {
    return email.split("@")[0]
        .split(/[.\-_]/)
        .filter(Boolean)
        .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
        .join(" ") || email;
}

function iniciais(nome) {
    const partes = nome.trim().split(/\s+/);
    const primeira = partes[0]?.[0] ?? "";
    const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
    return (primeira + ultima).toUpperCase();
}

async function carregarProfessoresETurmas() {
    try {
        const respostaProfessores = await fetch(
            `${API_URL}/admin/professores?admin_email=${encodeURIComponent(usuario.email)}`
        );
        const dadosProfessores = await respostaProfessores.json();
        const professores = dadosProfessores.professores || [];

        const seletor = document.querySelector("#turmaProfessor");
        const semProfessores = document.querySelector("#semProfessores");
        const botaoNovaTurma = document.querySelector("#botaoNovaTurma");

        if (professores.length === 0) {
            semProfessores.hidden = false;
            botaoNovaTurma.disabled = true;
        } else {
            semProfessores.hidden = true;
            botaoNovaTurma.disabled = false;
            seletor.innerHTML = professores.map((email) => `<option value="${email}">${email}</option>`).join("");
        }

        await carregarTurmas();
    } catch (erro) {
        console.error("Erro ao carregar professores:", erro);
    }
}

async function carregarTurmas() {
    const lista = document.querySelector("#listaTurmas");
    const vazio = document.querySelector("#turmasVazio");

    try {
        const resposta = await fetch(`${API_URL}/admin/turmas?admin_email=${encodeURIComponent(usuario.email)}`);
        const dados = await resposta.json();
        const turmas = dados.turmas || [];

        lista.innerHTML = "";

        if (turmas.length === 0) {
            vazio.hidden = false;
            return;
        }
        vazio.hidden = true;

        turmas.forEach((turma) => {
            const linha = document.createElement("article");
            linha.className = "cartao material-linha";
            linha.innerHTML = `
                <div class="material-linha-info">
                    <h3>${turma.nome} · ${turma.semestre}</h3>
                    <p class="material-classificacao">Professor: ${turma.professor_email}</p>
                    <p class="material-classificacao">${turma.total_materiais} material(is) cadastrado(s)</p>
                </div>
                <div class="material-linha-acoes">
                    <button type="button" class="acao" data-acao-alunos>Alunos</button>
                    <button type="button" class="acao acao--perigo" data-acao-excluir>Excluir</button>
                </div>
            `;
            linha.querySelector("[data-acao-excluir]").addEventListener("click", () => excluirTurma(turma));

            const painelAlunos = montarPainelAlunos(turma);
            linha.querySelector("[data-acao-alunos]").addEventListener("click", () => {
                painelAlunos.hidden = !painelAlunos.hidden;
                if (!painelAlunos.hidden) {
                    carregarAlunosDaTurma(turma, painelAlunos);
                }
            });

            lista.appendChild(linha);
            lista.appendChild(painelAlunos);
        });
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function ligarFormularioTurma() {
    const cartaoFormulario = document.querySelector("#formularioTurmaCartao");
    const formulario = document.querySelector("#formularioTurma");
    const mensagem = document.querySelector("#turmaMensagem");

    document.querySelector("#botaoNovaTurma").addEventListener("click", () => {
        cartaoFormulario.hidden = false;
        mensagem.textContent = "";
    });

    document.querySelector("#botaoCancelarTurma").addEventListener("click", () => {
        cartaoFormulario.hidden = true;
        formulario.reset();
        mensagem.textContent = "";
    });

    formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const professorEmail = document.querySelector("#turmaProfessor").value;
        const nome = document.querySelector("#turmaNome").value.trim();
        const semestre = document.querySelector("#turmaSemestre").value.trim();

        try {
            const resposta = await fetch(`${API_URL}/admin/turmas`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    admin_email: usuario.email,
                    professor_email: professorEmail,
                    nome: nome,
                    semestre: semestre,
                }),
            });

            const dados = await resposta.json();
            mensagem.textContent = dados.mensagem;

            if (dados.sucesso) {
                mensagem.classList.add("formulario-mensagem--sucesso");
                formulario.reset();
                cartaoFormulario.hidden = true;
                carregarTurmas();
            }
        } catch (erro) {
            console.error("Erro ao criar turma:", erro);
            mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
        }
    });
}

async function excluirTurma(turma) {
    if (!confirm(`Excluir a turma "${turma.nome} · ${turma.semestre}" de ${turma.professor_email}? Os materiais dela também serão excluídos.`)) {
        return;
    }

    try {
        const resposta = await fetch(`${API_URL}/admin/turmas/${turma.id}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ admin_email: usuario.email }),
        });
        const dados = await resposta.json();

        if (dados.sucesso) {
            carregarTurmas();
        } else {
            alert(dados.mensagem);
        }
    } catch (erro) {
        console.error("Erro ao excluir turma:", erro);
        alert("Não foi possível conectar ao servidor. Tente novamente.");
    }
}

function montarPainelAlunos(turma) {
    const painel = document.createElement("section");
    painel.className = "cartao";
    painel.hidden = true;
    painel.innerHTML = `
        <h3 class="cartao-titulo">Alunos matriculados · ${turma.nome}</h3>
        <div class="formulario--linha">
            <div class="campo">
                <label>Matricular aluno</label>
                <select data-seletor-aluno></select>
            </div>
            <div class="campo campo--acoes">
                <button type="button" class="acao acao--primaria" data-acao-matricular>Matricular</button>
            </div>
        </div>
        <p class="formulario-mensagem" data-mensagem-matricula></p>
        <ul class="lista-entregas" data-lista-alunos style="margin-top: 12px;"></ul>
    `;
    return painel;
}

async function carregarAlunosDaTurma(turma, painel) {
    const lista = painel.querySelector("[data-lista-alunos]");
    const seletor = painel.querySelector("[data-seletor-aluno]");
    const mensagem = painel.querySelector("[data-mensagem-matricula]");

    try {
        const [respostaMatriculados, respostaTodos] = await Promise.all([
            fetch(`${API_URL}/admin/turmas/${turma.id}/alunos?admin_email=${encodeURIComponent(usuario.email)}`),
            fetch(`${API_URL}/admin/alunos?admin_email=${encodeURIComponent(usuario.email)}`),
        ]);

        const matriculados = (await respostaMatriculados.json()).alunos || [];
        const todos = (await respostaTodos.json()).alunos || [];

        lista.innerHTML = "";
        if (matriculados.length === 0) {
            const item = document.createElement("li");
            item.textContent = "Nenhum aluno matriculado ainda.";
            lista.appendChild(item);
        } else {
            matriculados.forEach((email) => {
                const item = document.createElement("li");
                item.innerHTML = `
                    <span class="entrega-info"><strong>${email}</strong></span>
                `;
                const botao = document.createElement("button");
                botao.type = "button";
                botao.className = "botao-corrigir";
                botao.textContent = "Remover";
                botao.addEventListener("click", () => desmatricular(turma, email, painel));
                item.appendChild(botao);
                lista.appendChild(item);
            });
        }

        const disponiveis = todos.filter((email) => !matriculados.includes(email));
        seletor.innerHTML = disponiveis.length
            ? disponiveis.map((email) => `<option value="${email}">${email}</option>`).join("")
            : `<option value="">Nenhum aluno disponível</option>`;
    } catch (erro) {
        console.error("Erro ao carregar alunos da turma:", erro);
        mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }

    const botaoMatricular = painel.querySelector("[data-acao-matricular]");
    botaoMatricular.onclick = async () => {
        const alunoEmail = seletor.value;
        if (!alunoEmail) return;

        try {
            const resposta = await fetch(`${API_URL}/admin/matriculas`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ admin_email: usuario.email, aluno_email: alunoEmail, turma_id: turma.id }),
            });
            const dados = await resposta.json();
            mensagem.textContent = dados.mensagem;
            mensagem.classList.toggle("formulario-mensagem--sucesso", !!dados.sucesso);

            if (dados.sucesso) {
                carregarAlunosDaTurma(turma, painel);
            }
        } catch (erro) {
            console.error("Erro ao matricular aluno:", erro);
            mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
        }
    };
}

async function desmatricular(turma, alunoEmail, painel) {
    if (!confirm(`Remover ${alunoEmail} da turma "${turma.nome}"?`)) return;

    try {
        const resposta = await fetch(`${API_URL}/admin/matriculas`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ admin_email: usuario.email, aluno_email: alunoEmail, turma_id: turma.id }),
        });
        const dados = await resposta.json();

        if (dados.sucesso) {
            carregarAlunosDaTurma(turma, painel);
        } else {
            alert(dados.mensagem);
        }
    } catch (erro) {
        console.error("Erro ao desmatricular aluno:", erro);
        alert("Não foi possível conectar ao servidor. Tente novamente.");
    }
}

function ligarPlaceholders() {
    document.querySelectorAll("[data-em-breve]").forEach((elemento) => {
        elemento.addEventListener("click", (evento) => {
            evento.preventDefault();
            alert(`${elemento.dataset.emBreve} ainda não está disponível — chega em uma próxima sprint.`);
        });
    });
}
