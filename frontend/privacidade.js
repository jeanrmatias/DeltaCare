/**
 * O que as telas de privacidade do aluno e da administração dividem: o nome
 * de cada status e o formato das datas. Num lugar só para "agendada" não
 * aparecer com um nome para o aluno e outro para a secretaria.
 *
 * As regras estão no servidor (backend/regras/privacidade.py).
 */

const STATUS_PRIVACIDADE = {
    pendente: { rotulo: "Aguardando a administração", classe: "badge-status--agendado" },
    agendada: { rotulo: "Conta desativada", classe: "badge-status--perigo" },
    concluida: { rotulo: "Concluído", classe: "badge-status--publicado" },
    recusada: { rotulo: "Recusado", classe: "badge-status--rascunho" },
    cancelada: { rotulo: "Cancelado", classe: "badge-status--rascunho" },
    revertida: { rotulo: "Exclusão revertida", classe: "badge-status--rascunho" },
};

function seloDeStatus(status) {
    const info = STATUS_PRIVACIDADE[status] || { rotulo: status, classe: "badge-status--rascunho" };
    const selo = document.createElement("span");
    selo.className = `badge-status ${info.classe}`;
    selo.textContent = info.rotulo;
    return selo;
}

function dataCurta(iso) {
    if (!iso) return "";
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** Nome do arquivo da cópia: com a data, para duas cópias não se sobrescreverem. */
function nomeArquivoDaCopia(iso) {
    const dia = String(iso || "").slice(0, 10) || "copia";
    return `delta-care-meus-dados-${dia}.json`;
}
