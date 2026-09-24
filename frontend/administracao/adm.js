const usuario = exigirAcesso("adm");

if (usuario) {
    montarSaudacao(usuario);
    carregarResumo();
    ligarPlaceholders();
    ligarNotificacoes();
    document.querySelector("#botaoSair").addEventListener("click", sair);
}

function montarSaudacao(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#saudacao").textContent = `Olá, ${nome}`;
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

async function carregarResumo() {
    try {
        const [respostaProfessores, respostaTurmas] = await Promise.all([
            api("/admin/professores"),
            api("/admin/turmas"),
        ]);

        const dadosProfessores = await respostaProfessores.json();
        const dadosTurmas = await respostaTurmas.json();

        document.querySelector("#statProfessores").textContent = (dadosProfessores.professores || []).length;
        document.querySelector("#statTurmas").textContent = (dadosTurmas.turmas || []).length;

        const totalMateriais = (dadosTurmas.turmas || []).reduce((soma, turma) => soma + turma.total_materiais, 0);
        document.querySelector("#statMateriais").textContent = totalMateriais;
    } catch (erro) {
        console.error("Erro ao carregar resumo:", erro);
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
