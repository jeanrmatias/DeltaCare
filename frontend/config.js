/**
 * Onde está a API.
 *
 * - **Produção:** o próprio servidor da API entrega as telas (em /app/), então
 *   a API está na mesma origem da página. Nada a configurar.
 * - **Desenvolvimento:** frontend/servir.py serve as telas na porta 5500 e a
 *   API roda na 8000, no mesmo computador.
 * - `window.DELTACARE_API_URL`, se alguém definir antes deste arquivo, vence
 *   os dois — para o caso raro de a API ficar em outro domínio.
 *
 * Antes era "http://127.0.0.1:8000" fixo: no servidor da instituição, o
 * navegador de cada aluno procuraria a API no computador do próprio aluno.
 */
function enderecoDaApi(local) {
    if (typeof window !== "undefined" && window.DELTACARE_API_URL) {
        return window.DELTACARE_API_URL;
    }
    if (local.port === "5500") {
        return `${local.protocol}//${local.hostname}:8000`;
    }
    return local.origin;
}

const API_URL = enderecoDaApi(window.location);
