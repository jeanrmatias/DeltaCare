/**
 * Página de módulo planejado. O conteúdo vem de modulos.js, escolhido pelo
 * parâmetro ?modulo= da URL.
 */

const usuario = exigirAcesso("aluno");

if (usuario) {
    montarRodapePerfil(usuario);
    montarPaginaDeModulo();
    document.querySelector("#botaoSair").addEventListener("click", sair);
}

function nomeAPartirDoEmail(email) {
    const apelido = (email || "").split("@")[0].replace(/[._-]+/g, " ");
    return apelido
        .split(" ")
        .filter(Boolean)
        .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
        .join(" ");
}

function iniciais(nome) {
    const partes = (nome || "").trim().split(/\s+/).filter(Boolean);
    if (partes.length === 0) return "--";
    if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
    return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function montarRodapePerfil(usuario) {
    const nome = nomeAPartirDoEmail(usuario.email);
    const avatar = document.querySelector("#avatarRodape");
    const rodape = document.querySelector("#nomeRodape");
    if (avatar) avatar.textContent = iniciais(nome);
    if (rodape) rodape.textContent = nome;
}
