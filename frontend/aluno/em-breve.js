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

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    const avatar = document.querySelector("#avatarRodape");
    const rodape = document.querySelector("#nomeRodape");
    if (avatar) avatar.textContent = iniciaisDe(nome);
    if (rodape) rodape.textContent = nome;
}
