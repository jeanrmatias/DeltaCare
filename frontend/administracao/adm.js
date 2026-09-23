const usuario = exigirAcesso("adm");

if (usuario) {
    montarSaudacao(usuario);
    carregarResumo();
    ligarPlaceholders();
    document.querySelector("#botaoSair").addEventListener("click", sair);
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

function montarSaudacao(usuario) {
    const nome = nomeAPartirDoEmail(usuario.email);
    document.querySelector("#saudacao").textContent = `Olá, ${nome}`;
    document.querySelector("#avatarRodape").textContent = iniciais(nome);
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
        elemento.addEventListener("click", (evento) => {
            evento.preventDefault();
            alert(`${elemento.dataset.emBreve} ainda não está disponível — chega em uma próxima sprint.`);
        });
    });
}
