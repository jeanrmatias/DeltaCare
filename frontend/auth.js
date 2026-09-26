/**
 * Sessão do usuário no navegador.
 *
 * O login devolve um token (ver backend/sessoes.py) que é guardado aqui e
 * enviado em toda requisição no header `Authorization: Bearer <token>`. É esse
 * token — e não o e-mail informado pelo cliente — que o backend usa para saber
 * quem está fazendo a requisição.
 *
 * O que fica no sessionStorage (e-mail, tipo) serve só para a interface decidir
 * o que desenhar. Adulterar isso não dá acesso a nada: o backend nunca confia
 * no que vem do cliente, só no token, que ele valida no banco a cada chamada.
 */

const USUARIO_KEY = "deltacare_usuario";
const TOKEN_KEY = "deltacare_token";

function salvarUsuarioLogado(usuario, token) {
    try {
        sessionStorage.setItem(USUARIO_KEY, JSON.stringify(usuario));
        if (token) {
            sessionStorage.setItem(TOKEN_KEY, token);
        }
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

function obterToken() {
    try {
        return sessionStorage.getItem(TOKEN_KEY) || "";
    } catch (erro) {
        return "";
    }
}

function limparSessaoLocal() {
    try {
        sessionStorage.removeItem(USUARIO_KEY);
        sessionStorage.removeItem(TOKEN_KEY);
    } catch (erro) {
        /* sessionStorage indisponível: nada a limpar */
    }
}

// As páginas de perfil ficam em subpastas (professor/, aluno/, administracao/)
// e o login está na raiz; as páginas da raiz sobrescrevem isto para "index.html".
const CAMINHO_LOGIN = "../index.html";

/**
 * Chama a API sem token: login, cadastro e recuperação de senha.
 *
 * Existe para as três telas públicas passarem pelo mesmo ponto que o resto do
 * sistema, em vez de montarem a URL cada uma do seu jeito.
 *
 * **Não há modo de contingência.** Se o backend não responder, a chamada falha
 * e a tela diz isso. O Delta Care é um sistema de instituição: exibir dado
 * fictício quando o servidor cai seria pior do que não exibir nada — o usuário
 * não teria como saber que está olhando para algo que não é real.
 */
async function apiPublica(caminho, opcoes = {}) {
    return fetch(`${API_URL}${caminho}`, opcoes);
}

/**
 * Chama a API já autenticada.
 *
 * Centraliza três coisas que antes estavam espalhadas por 23 chamadas soltas:
 * o header do token, o Content-Type do JSON e o que fazer quando a sessão
 * expira (401) — nesse caso manda de volta para o login em vez de deixar a
 * tela quebrada com erro no console.
 */
async function api(caminho, opcoes = {}) {
    const cabecalhos = Object.assign({}, opcoes.headers || {});
    const token = obterToken();

    if (token) {
        cabecalhos["Authorization"] = `Bearer ${token}`;
    }

    if (opcoes.body && !cabecalhos["Content-Type"]) {
        cabecalhos["Content-Type"] = "application/json";
    }

    const resposta = await fetch(`${API_URL}${caminho}`, Object.assign({}, opcoes, { headers: cabecalhos }));

    if (resposta.status === 401) {
        limparSessaoLocal();
        window.location.href = CAMINHO_LOGIN;
        throw new Error("Sessão expirada");
    }

    return resposta;
}

/**
 * Nome a exibir para um usuário.
 *
 * Prefere o nome cadastrado. Contas criadas antes de o campo existir não têm
 * esse dado, e aí o e-mail vira um nome aproximado ("ana.paula@x" -> "Ana
 * Paula") — melhor do que mostrar o endereço cru no rodapé.
 */
function nomeExibicao(usuario) {
    if (usuario && usuario.nome && usuario.nome.trim()) {
        return usuario.nome.trim();
    }

    const email = (usuario && usuario.email) || "";
    const apelido = email.split("@")[0].replace(/[._-]+/g, " ");

    return apelido
        .split(" ")
        .filter(Boolean)
        .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
        .join(" ") || email;
}

/** Iniciais para o avatar, a partir do nome de exibição. */
function iniciaisDe(nome) {
    const partes = (nome || "").trim().split(/\s+/).filter(Boolean);
    if (partes.length === 0) return "--";
    if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
    return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

/**
 * Garante que a página só é usada por quem logou com `tipoEsperado`.
 *
 * Isto é só navegação: impede a tela errada de aparecer, não protege dado
 * nenhum. Quem protege é o backend, que confere o token e o perfil em cada
 * rota (backend/main.py, exigir_perfil).
 */
function exigirAcesso(tipoEsperado) {
    const usuario = obterUsuarioLogado();

    if (!usuario || usuario.tipo !== tipoEsperado || !obterToken()) {
        window.location.href = CAMINHO_LOGIN;
        return null;
    }

    return usuario;
}

async function sair() {
    // Avisa o backend para invalidar o token; se a chamada falhar, a sessão
    // local é limpa do mesmo jeito — o usuário não pode ficar preso na conta.
    try {
        await api("/logout", { method: "POST" });
    } catch (erro) {
        /* segue para a limpeza local */
    }

    limparSessaoLocal();
    window.location.href = CAMINHO_LOGIN;
}
