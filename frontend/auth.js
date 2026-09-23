/**
 * Controle de sessão no navegador (client-side apenas).
 *
 * Importante: isso guarda quem "parece" estar logado para decidir o que
 * mostrar na tela, mas não é segurança de verdade — qualquer pessoa pode
 * abrir o console do navegador e escrever o que quiser aqui. A proteção
 * real (impedir que alguém sem permissão LEIA os dados) tem que acontecer
 * no backend, validando em cada rota quem está fazendo a requisição. Hoje
 * o backend ainda não tem sessão/token, então esse arquivo serve só para
 * a navegação da interface — quando o backend ganhar autenticação por
 * token (JWT, por exemplo), este arquivo passa a guardar esse token e
 * cada chamada à API deve enviá-lo.
 */

const USUARIO_KEY = "deltacare_usuario";

function salvarUsuarioLogado(usuario) {
    try {
        sessionStorage.setItem(USUARIO_KEY, JSON.stringify(usuario));
    } catch (erro) {
        console.error("Não foi possível salvar a sessão:", erro);
    }
}

function obterUsuarioLogado() {
    try {
        const dados = sessionStorage.getItem(USUARIO_KEY);
        return dados ? JSON.parse(dados) : null;
    } catch (erro) {
        return null;
    }
}

// auth.js fica na raiz do front (arquivo global), mas exigirAcesso() e
// sair() só são chamadas de dentro de professor/, aluno/ ou adm/ — por
// isso o caminho de volta para o login é "../index.html" (um nível acima).
const CAMINHO_LOGIN = "../index.html";

/**
 * Garante que a página só é usada por quem "logou" como `tipoEsperado`
 * (ex.: "professor"). Se não houver usuário salvo ou o tipo não bater,
 * manda de volta para o login. Retorna os dados do usuário quando tudo ok.
 */
function exigirAcesso(tipoEsperado) {
    const usuario = obterUsuarioLogado();

    if (!usuario || usuario.tipo !== tipoEsperado) {
        window.location.href = CAMINHO_LOGIN;
        return null;
    }

    return usuario;
}

function sair() {
    sessionStorage.removeItem(USUARIO_KEY);
    window.location.href = CAMINHO_LOGIN;
}
