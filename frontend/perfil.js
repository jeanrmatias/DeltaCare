/**
 * Tela de perfil do usuário.
 *
 * O rodapé da barra lateral do professor trazia um "Ver perfil" que era texto
 * solto, sem botão nem tratador — clicar não fazia nada. Agora abre um diálogo
 * com os dados reais da conta.
 *
 * **Só leitura.** Editar o próprio cadastro (autosserviço) é item de escopo
 * futuro, registrado no backlog. Mostrar o que já existe é outra coisa, e
 * é o que faz o menu deixar de ser um beco sem saída.
 */

const ROTULOS_PERFIL_CONTA = {
    adm: "Administração",
    professor: "Professor",
    aluno: "Aluno",
};

/** Liga o "Ver perfil" e o "Sair" do rodapé da barra lateral. */
function ligarRodapePerfil() {
    const botaoPerfil = document.querySelector("#botaoPerfil");
    if (botaoPerfil) {
        botaoPerfil.addEventListener("click", abrirPerfil);
    }

    const botaoSair = document.querySelector("#botaoSair");
    if (botaoSair) {
        botaoSair.addEventListener("click", sair);
    }
}

async function abrirPerfil() {
    let dados;

    try {
        const resposta = await api("/eu");
        dados = await resposta.json();
    } catch (erro) {
        console.error("Erro ao carregar o perfil:", erro);
        await avisarErro("Não foi possível carregar seus dados agora.");
        return;
    }

    if (!dados || !dados.sucesso) {
        await avisarErro("Não foi possível carregar seus dados agora.");
        return;
    }

    const dialogo = document.createElement("dialog");
    dialogo.className = "dialogo perfil-dialogo";

    const caixa = document.createElement("div");
    caixa.className = "dialogo-caixa";

    // Cabeçalho com avatar e nome
    const topo = document.createElement("div");
    topo.className = "perfil-topo";

    const avatar = document.createElement("span");
    avatar.className = "avatar perfil-avatar";
    avatar.textContent = iniciaisDe(nomeExibicao(dados));

    const identificacao = document.createElement("div");

    const nome = document.createElement("strong");
    nome.className = "perfil-nome";
    nome.textContent = nomeExibicao(dados);

    const papel = document.createElement("span");
    papel.className = "perfil-papel";
    papel.textContent = ROTULOS_PERFIL_CONTA[dados.tipo] || dados.tipo;

    identificacao.appendChild(nome);
    identificacao.appendChild(papel);

    topo.appendChild(avatar);
    topo.appendChild(identificacao);
    caixa.appendChild(topo);

    // Lista de dados. Campo vazio não vira linha: "Matrícula: —" só ocupa
    // espaço dizendo que falta algo.
    const lista = document.createElement("dl");
    lista.className = "perfil-dados";

    const adicionar = (rotulo, valor) => {
        if (!valor) return;

        const dt = document.createElement("dt");
        dt.textContent = rotulo;

        const dd = document.createElement("dd");
        dd.textContent = valor;

        lista.appendChild(dt);
        lista.appendChild(dd);
    };

    adicionar("E-mail", dados.email);
    adicionar("Matrícula", dados.matricula);
    adicionar("Disciplinas", dados.disciplinas);

    const turmas = dados.turmas || [];
    if (turmas.length > 0) {
        adicionar(
            dados.tipo === "professor" ? "Turmas que leciona" : "Turmas em que está matriculado",
            turmas.map((t) => `${t.nome} · ${t.semestre}`).join("\n")
        );
    }

    caixa.appendChild(lista);

    // Aviso do que ainda não dá para fazer, em vez de um botão "Editar" que
    // abriria outro beco sem saída.
    const nota = document.createElement("p");
    nota.className = "perfil-nota";
    nota.textContent =
        "Para alterar estes dados, fale com a administração. A edição pelo próprio usuário entra numa próxima versão.";
    caixa.appendChild(nota);

    const acoes = document.createElement("div");
    acoes.className = "dialogo-acoes";

    const fechar = document.createElement("button");
    fechar.type = "button";
    fechar.className = "acao acao--primaria";
    fechar.textContent = "Fechar";
    fechar.addEventListener("click", () => dialogo.close());

    acoes.appendChild(fechar);
    caixa.appendChild(acoes);

    dialogo.appendChild(caixa);
    document.body.appendChild(dialogo);

    dialogo.addEventListener("close", () => dialogo.remove());
    dialogo.addEventListener("click", (evento) => {
        if (evento.target === dialogo) dialogo.close();
    });

    dialogo.showModal();
    fechar.focus();
}
