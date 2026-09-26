/**
 * Seletor de data e hora do Delta Care.
 *
 * Substitui o `<input type="datetime-local">`, que tinha dois problemas para
 * quem agenda aula: o calendário é o do navegador — muda de aparência em cada
 * um e não segue a identidade do sistema — e, na prática, o professor acabava
 * dependendo dele, porque digitar naquele campo é desconfortável.
 *
 * Aqui são duas portas para a mesma coisa:
 *
 * 1. **Digitar.** O campo aceita `dd/mm/aaaa` e `dd/mm/aaaa hh:mm`, e também
 *    o que as pessoas escrevem de verdade: `5/3`, `05/03/26`, `5 3 2026`.
 * 2. **Escolher.** O botão abre um calendário desenhado com os componentes do
 *    próprio sistema, com atalhos para hoje, amanhã e a próxima semana.
 *
 * O valor sai sempre como ISO com fuso, que é o que o backend guarda.
 */

const MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

const DIAS_CURTOS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

/** Interpreta o que a pessoa digitou. Devolve Date ou null. */
function interpretarDataDigitada(texto) {
    const limpo = String(texto || "").trim();
    if (!limpo) return null;

    // Separadores variados: 05/03/2026, 05-03-2026, 5 3 26.
    const partes = limpo.split(/[\s/.-]+/).filter(Boolean);
    if (partes.length < 2) return null;

    const dia = Number(partes[0]);
    const mes = Number(partes[1]);
    if (!Number.isInteger(dia) || !Number.isInteger(mes)) return null;
    if (dia < 1 || dia > 31 || mes < 1 || mes > 12) return null;

    const agora = new Date();
    let ano = agora.getFullYear();

    if (partes.length >= 3 && /^\d+$/.test(partes[2])) {
        ano = Number(partes[2]);
        if (ano < 100) ano += 2000;
    }

    // A hora pode vir como 4º pedaço (14:30 vira "14" e "30" pelo split) ou
    // colada num "14:30" que o split já separou.
    let hora = 0;
    let minuto = 0;
    const horaCrua = limpo.match(/(\d{1,2}):(\d{2})/);
    if (horaCrua) {
        hora = Number(horaCrua[1]);
        minuto = Number(horaCrua[2]);
        if (hora > 23 || minuto > 59) return null;
    }

    const data = new Date(ano, mes - 1, dia, hora, minuto, 0, 0);

    // Rejeita data que "virou" — 31/02 viraria 2 ou 3 de março.
    if (data.getDate() !== dia || data.getMonth() !== mes - 1) return null;

    return data;
}

function formatarParaCampo(data) {
    if (!data) return "";
    const dois = (n) => String(n).padStart(2, "0");
    return `${dois(data.getDate())}/${dois(data.getMonth() + 1)}/${data.getFullYear()} ` +
           `${dois(data.getHours())}:${dois(data.getMinutes())}`;
}

function mesmoDia(a, b) {
    return Boolean(a) && Boolean(b) &&
        a.getFullYear() === b.getFullYear() &&
        a.getMonth() === b.getMonth() &&
        a.getDate() === b.getDate();
}

/**
 * Monta o seletor dentro de `container`.
 *
 * Devolve `{ valor, definir, limpar }` — `valor()` dá ISO ou null.
 */
function criarSeletorDataHora(container, opcoes = {}) {
    const { placeholder = "dd/mm/aaaa hh:mm" } = opcoes;

    let selecionada = null;
    let mesVisivel = new Date();

    container.classList.add("seletor-data");
    container.innerHTML = `
        <div class="seletor-data-campo">
            <input type="text" class="seletor-data-entrada" placeholder="${placeholder}"
                   autocomplete="off" inputmode="numeric">
            <button type="button" class="seletor-data-botao" aria-label="Abrir calendário" aria-expanded="false">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 11h18"/></svg>
            </button>
        </div>
        <div class="seletor-data-painel" hidden></div>
    `;

    const entrada = container.querySelector(".seletor-data-entrada");
    const botao = container.querySelector(".seletor-data-botao");
    const painel = container.querySelector(".seletor-data-painel");

    // ---------------------------------------------------------------- campo

    entrada.addEventListener("input", () => {
        const lida = interpretarDataDigitada(entrada.value);
        if (lida) {
            selecionada = lida;
            mesVisivel = new Date(lida.getFullYear(), lida.getMonth(), 1);
            entrada.classList.remove("seletor-data-entrada--invalida");
            if (!painel.hidden) desenhar();
        } else {
            selecionada = null;
            // Só marca como inválido depois que a pessoa escreveu alguma coisa
            // que parece data — avisar no primeiro dígito seria implicância.
            entrada.classList.toggle(
                "seletor-data-entrada--invalida",
                entrada.value.trim().length >= 5
            );
        }
    });

    entrada.addEventListener("blur", () => {
        // Normaliza o que ficou: "5/3" vira "05/03/2026 00:00".
        if (selecionada) entrada.value = formatarParaCampo(selecionada);
    });

    // ---------------------------------------------------------------- painel

    function abrir() {
        mesVisivel = selecionada
            ? new Date(selecionada.getFullYear(), selecionada.getMonth(), 1)
            : new Date();
        desenhar();
        painel.hidden = false;
        botao.setAttribute("aria-expanded", "true");
    }

    function fechar() {
        painel.hidden = true;
        botao.setAttribute("aria-expanded", "false");
    }

    botao.addEventListener("click", () => {
        if (painel.hidden) abrir();
        else fechar();
    });

    // Fecha ao clicar fora ou com Esc, como qualquer popover do sistema.
    document.addEventListener("click", (evento) => {
        if (!container.contains(evento.target)) fechar();
    });

    container.addEventListener("keydown", (evento) => {
        if (evento.key === "Escape" && !painel.hidden) {
            evento.stopPropagation();
            fechar();
            entrada.focus();
        }
    });

    function escolherDia(data) {
        const hora = selecionada ? selecionada.getHours() : 0;
        const minuto = selecionada ? selecionada.getMinutes() : 0;
        selecionada = new Date(data.getFullYear(), data.getMonth(), data.getDate(), hora, minuto);
        entrada.value = formatarParaCampo(selecionada);
        entrada.classList.remove("seletor-data-entrada--invalida");
        desenhar();
    }

    function desenhar() {
        const hoje = new Date();
        const primeiro = new Date(mesVisivel.getFullYear(), mesVisivel.getMonth(), 1);
        const diasNoMes = new Date(mesVisivel.getFullYear(), mesVisivel.getMonth() + 1, 0).getDate();

        const celulas = [];
        for (let vazio = 0; vazio < primeiro.getDay(); vazio += 1) {
            celulas.push('<span class="calendario-dia calendario-dia--vazio"></span>');
        }

        for (let dia = 1; dia <= diasNoMes; dia += 1) {
            const data = new Date(mesVisivel.getFullYear(), mesVisivel.getMonth(), dia);
            const classes = ["calendario-dia"];
            if (mesmoDia(data, hoje)) classes.push("calendario-dia--hoje");
            if (mesmoDia(data, selecionada)) classes.push("calendario-dia--selecionado");

            celulas.push(
                `<button type="button" class="${classes.join(" ")}" data-dia="${dia}">${dia}</button>`
            );
        }

        const horaAtual = selecionada
            ? `${String(selecionada.getHours()).padStart(2, "0")}:${String(selecionada.getMinutes()).padStart(2, "0")}`
            : "";

        painel.innerHTML = `
            <div class="calendario-topo">
                <div class="calendario-nav">
                    <button type="button" data-mes="-1" aria-label="Mês anterior">‹</button>
                </div>
                <h2>${MESES[mesVisivel.getMonth()]} de ${mesVisivel.getFullYear()}</h2>
                <div class="calendario-nav">
                    <button type="button" data-mes="1" aria-label="Próximo mês">›</button>
                </div>
            </div>
            <div class="calendario-grade">
                ${DIAS_CURTOS.map((d) => `<span class="calendario-cabecalho">${d}</span>`).join("")}
                ${celulas.join("")}
            </div>
            <div class="seletor-data-hora">
                <label>Hora
                    <input type="time" class="seletor-data-relogio" value="${horaAtual}">
                </label>
            </div>
            <div class="seletor-data-atalhos">
                <button type="button" data-atalho="hoje">Hoje</button>
                <button type="button" data-atalho="amanha">Amanhã</button>
                <button type="button" data-atalho="semana">Em 7 dias</button>
                <button type="button" data-atalho="limpar">Limpar</button>
            </div>
        `;

        painel.querySelectorAll("[data-mes]").forEach((b) => {
            b.addEventListener("click", () => {
                mesVisivel = new Date(
                    mesVisivel.getFullYear(),
                    mesVisivel.getMonth() + Number(b.dataset.mes),
                    1
                );
                desenhar();
            });
        });

        painel.querySelectorAll("[data-dia]").forEach((b) => {
            b.addEventListener("click", () => {
                escolherDia(new Date(mesVisivel.getFullYear(), mesVisivel.getMonth(), Number(b.dataset.dia)));
            });
        });

        const relogio = painel.querySelector(".seletor-data-relogio");
        relogio.addEventListener("input", () => {
            const [h, m] = relogio.value.split(":").map(Number);
            if (Number.isNaN(h)) return;
            const base = selecionada || new Date();
            selecionada = new Date(base.getFullYear(), base.getMonth(), base.getDate(), h, m || 0);
            entrada.value = formatarParaCampo(selecionada);
            desenhar();
        });

        painel.querySelectorAll("[data-atalho]").forEach((b) => {
            b.addEventListener("click", () => {
                const atalho = b.dataset.atalho;

                if (atalho === "limpar") {
                    limpar();
                    fechar();
                    return;
                }

                const alvo = new Date();
                if (atalho === "amanha") alvo.setDate(alvo.getDate() + 1);
                if (atalho === "semana") alvo.setDate(alvo.getDate() + 7);

                mesVisivel = new Date(alvo.getFullYear(), alvo.getMonth(), 1);
                escolherDia(alvo);
            });
        });
    }

    function limpar() {
        selecionada = null;
        entrada.value = "";
        entrada.classList.remove("seletor-data-entrada--invalida");
    }

    function definir(iso) {
        if (!iso) {
            limpar();
            return;
        }
        const data = new Date(iso);
        if (Number.isNaN(data.getTime())) {
            limpar();
            return;
        }
        selecionada = data;
        entrada.value = formatarParaCampo(data);
    }

    return {
        valor: () => (selecionada ? selecionada.toISOString() : null),
        definir,
        limpar,
        // exposto para os testes
        _interpretar: interpretarDataDigitada,
    };
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = { interpretarDataDigitada, formatarParaCampo, criarSeletorDataHora };
}
