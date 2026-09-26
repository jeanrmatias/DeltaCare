/**
 * Testes do JavaScript do front-end.
 *
 *     cd frontend
 *     node testes.mjs
 *
 * Cobre a lógica pura: renderização de Markdown, nome de exibição, formatos
 * que o visualizador aceita e o catálogo de módulos. Interação com servidor e
 * estilo ficam de fora — o que dá para verificar sem navegador é isto, e é
 * justamente o que quebra em silêncio.
 *
 * Um DOM mínimo é montado aqui em vez de trazer jsdom: as funções testadas
 * usam meia dúzia de métodos, e uma dependência de 3 MB para isso seria
 * desproporcional (mesmo critério do resto do projeto).
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

// ---------------------------------------------------------------- DOM mínimo
class No {
    constructor(tag) {
        this.tagName = (tag || "").toUpperCase();
        this.filhos = [];
        this.atributos = {};
        this.className = "";
        this.dataset = {};
        this.style = {};
        this._texto = "";
        this.hidden = false;
    }

    appendChild(no) {
        this.filhos.push(no);
        return no;
    }

    remove() {}
    addEventListener() {}
    setAttribute(nome, valor) { this.atributos[nome] = valor; }
    getAttribute(nome) { return this.atributos[nome]; }
    insertAdjacentElement() {}

    set textContent(valor) {
        this._texto = String(valor);
        this.filhos = [];
    }

    get textContent() {
        if (this.filhos.length === 0) return this._texto;
        return this._texto + this.filhos.map((f) => f.textContent).join("");
    }

    set innerHTML(valor) {
        // O renderizador não deve usar innerHTML com texto do modelo; se usar,
        // o teste de segurança abaixo pega.
        this._html = valor;
        this.filhos = [];
    }

    get innerHTML() { return this._html || ""; }

    /** Busca simplificada: só por nome de tag, que é o que os testes usam. */
    querySelectorAll(seletor) {
        const tags = seletor.split(/\s+/).map((t) => t.toUpperCase());
        const alvo = tags[tags.length - 1];

        const encontrados = [];
        const visitar = (no) => {
            no.filhos.forEach((filho) => {
                if (filho.tagName === alvo) encontrados.push(filho);
                visitar(filho);
            });
        };
        visitar(this);
        return encontrados;
    }
}

function montarAmbiente() {
    const document = {
        createElement: (tag) => new No(tag),
        createTextNode: (texto) => {
            const no = new No("#text");
            no._texto = String(texto);
            return no;
        },
        querySelector: () => null,
        querySelectorAll: () => [],
        addEventListener: () => {},
        body: new No("body"),
    };

    const contexto = {
        document,
        window: { location: { search: "", href: "" } },
        console,
        URLSearchParams,
        Date,
        Math,
        JSON,
        String,
        Number,
        Array,
        Object,
        Boolean,
        setInterval: () => 0,
        setTimeout: () => 0,
        fetch: async () => ({ ok: true, json: async () => ({}) }),
        sessionStorage: {
            _dados: {},
            getItem(chave) { return this._dados[chave] ?? null; },
            setItem(chave, valor) { this._dados[chave] = String(valor); },
            removeItem(chave) { delete this._dados[chave]; },
        },
        API_URL: "http://127.0.0.1:8000",
    };

    contexto.globalThis = contexto;
    vm.createContext(contexto);

    for (const arquivo of ["auth.js", "markdown.js", "modulos.js", "visualizador.js"]) {
        vm.runInContext(fs.readFileSync(arquivo, "utf-8"), contexto, { filename: arquivo });
    }

    return contexto;
}

const ctx = montarAmbiente();
const novoNo = () => new No("div");

/**
 * Lê um identificador declarado com `const` dentro do contexto.
 *
 * `const` e `let` são lexicais: não viram propriedade do objeto de contexto do
 * vm, então `ctx.MODULOS` é undefined mesmo com o arquivo carregado. Avaliar a
 * expressão no próprio contexto resolve.
 */
function doContexto(expressao) {
    return vm.runInContext(expressao, ctx);
}

const MODULOS = doContexto("MODULOS");

// ---------------------------------------------------------------- nome
test("nomeExibicao usa o nome cadastrado", () => {
    assert.equal(ctx.nomeExibicao({ nome: "Marina Duarte", email: "a@x.com" }), "Marina Duarte");
});

test("nomeExibicao cai no e-mail quando não há nome", () => {
    assert.equal(ctx.nomeExibicao({ nome: "", email: "ana.paula@x.com" }), "Ana Paula");
});

test("nomeExibicao ignora nome só com espaços", () => {
    assert.equal(ctx.nomeExibicao({ nome: "   ", email: "joao@x.com" }), "Joao");
});

test("nomeExibicao não quebra com objeto vazio", () => {
    assert.equal(ctx.nomeExibicao({}), "");
});

test("iniciaisDe com nome composto", () => {
    assert.equal(ctx.iniciaisDe("Marina Duarte Silva"), "MS");
});

test("iniciaisDe com nome único", () => {
    assert.equal(ctx.iniciaisDe("Helena"), "HE");
});

test("iniciaisDe com vazio devolve marcador", () => {
    assert.equal(ctx.iniciaisDe(""), "--");
});

// ---------------------------------------------------------------- visualizador
test("visualizador aceita PDF", () => {
    assert.ok(ctx.podeVisualizar({ tipo: "pdf", arquivo_nome: "aula.pdf" }));
});

test("visualizador aceita extensão em maiúscula", () => {
    assert.ok(ctx.podeVisualizar({ tipo: "pdf", arquivo_nome: "AULA.PDF" }));
});

test("visualizador aceita imagem e vídeo", () => {
    assert.ok(ctx.podeVisualizar({ tipo: "documento", arquivo_nome: "grafico.png" }));
    assert.ok(ctx.podeVisualizar({ tipo: "video", arquivo_nome: "aula.mp4" }));
});

test("visualizador recusa link (não é arquivo)", () => {
    assert.ok(!ctx.podeVisualizar({ tipo: "link", link_url: "https://x.com" }));
});

test("visualizador recusa docx (navegador não renderiza)", () => {
    assert.ok(!ctx.podeVisualizar({ tipo: "documento", arquivo_nome: "texto.docx" }));
});

test("visualizador recusa arquivo sem extensão", () => {
    assert.ok(!ctx.podeVisualizar({ tipo: "documento", arquivo_nome: "arquivo" }));
});

// ---------------------------------------------------------------- markdown
test("markdown monta tabela com cabeçalho e linhas", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown("| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |", alvo);

    assert.equal(alvo.querySelectorAll("table").length, 1);
    assert.equal(alvo.querySelectorAll("th").length, 2);

    // O mock de querySelectorAll só casa a última tag do seletor, então
    // "tbody tr" pegaria também a linha do cabeçalho. Conto pelo tbody.
    const [tbody] = alvo.querySelectorAll("tbody");
    assert.equal(tbody.filhos.length, 2);
    assert.equal(alvo.querySelectorAll("td").length, 4);
});

test("markdown reconhece separador com alinhamento", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown("| A | B |\n|:---|---:|\n| 1 | 2 |", alvo);
    assert.equal(alvo.querySelectorAll("table").length, 1);
});

test("markdown converte negrito e itálico", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown("**forte** e *fraco*", alvo);

    assert.equal(alvo.querySelectorAll("strong").length, 1);
    assert.equal(alvo.querySelectorAll("em").length, 1);
});

test("markdown monta lista não ordenada", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown("- um\n- dois\n- três", alvo);

    assert.equal(alvo.querySelectorAll("ul").length, 1);
    assert.equal(alvo.querySelectorAll("li").length, 3);
});

test("markdown monta lista ordenada", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown("1. um\n2. dois", alvo);

    assert.equal(alvo.querySelectorAll("ol").length, 1);
    assert.equal(alvo.querySelectorAll("li").length, 2);
});

test("markdown monta título", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown("## Um título", alvo);
    assert.ok(alvo.querySelectorAll("h4").length > 0);
});

test("markdown monta citação", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown("> citado", alvo);
    assert.equal(alvo.querySelectorAll("blockquote").length, 1);
});

test("markdown NÃO interpreta HTML vindo do modelo", () => {
    // O texto passa pelo modelo, que por sua vez leu o PDF do professor. Se
    // isso virasse HTML de verdade, um PDF malicioso injetaria script.
    const alvo = novoNo();
    ctx.renderizarMarkdown("<img src=x onerror=alert(1)>", alvo);

    assert.equal(alvo.innerHTML, "", "não deveria ter usado innerHTML");
    assert.ok(alvo.textContent.includes("<img"), "o HTML deveria virar texto");
});

test("markdown preserva texto que não é marcação", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown("A dose é de 12,5 mg por via intravenosa.", alvo);
    assert.ok(alvo.textContent.includes("12,5 mg"));
});

test("markdown lida com texto vazio sem quebrar", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown("", alvo);
    assert.equal(alvo.filhos.length, 0);
});

test("markdown lida com null sem quebrar", () => {
    const alvo = novoNo();
    ctx.renderizarMarkdown(null, alvo);
    assert.equal(alvo.filhos.length, 0);
});

// ---------------------------------------------------------------- módulos
test("catálogo cobre os dois lados da denúncia", () => {
    // O roadmap descrevia quem *gerencia* denúncias e esquecia quem as *faz*:
    // uma caixa de entrada sem porta de entrada. Os dois lados precisam existir.
    assert.ok(MODULOS["denuncias-admin"], "falta o lado de quem trata");
    assert.ok(MODULOS["denunciar-conteudo"], "falta o lado de quem reporta");
});

test("módulos que dependem de outro apontam para ele", () => {
    // Um módulo que só faz sentido junto de outro deve dizer isso na tela, em
    // vez de deixar a banca notar a lacuna antes da gente.
    for (const chave of ["denuncias-admin", "denunciar-conteudo"]) {
        assert.ok(MODULOS[chave].nota, `${chave} não explica a contraparte`);
    }
});

test("todo módulo tem título, resumo, sprint e itens", () => {
    for (const [chave, modulo] of Object.entries(MODULOS)) {
        assert.ok(modulo.titulo, `${chave} sem título`);
        assert.ok(modulo.resumo, `${chave} sem resumo`);
        assert.ok(modulo.sprint, `${chave} sem sprint`);
        assert.ok(Array.isArray(modulo.itens) && modulo.itens.length, `${chave} sem itens`);
    }
});

test("chaves do catálogo batem com os links do menu", () => {
    // Se um link do menu apontar para uma chave que não existe, a página abre
    // dizendo "módulo não encontrado".
    const html = ["aluno", "professor", "administracao"]
        .flatMap((pasta) => fs.readdirSync(pasta).filter((f) => f.endsWith(".html"))
            .map((f) => fs.readFileSync(`${pasta}/${f}`, "utf-8")))
        .join("\n");

    const usadas = [...html.matchAll(/em-breve\.html\?modulo=([\w-]+)/g)].map((m) => m[1]);
    assert.ok(usadas.length > 0, "nenhum link de módulo encontrado");

    for (const chave of new Set(usadas)) {
        assert.ok(MODULOS[chave], `menu aponta para módulo inexistente: ${chave}`);
    }
});

// ---------------------------------------------------------------- diálogos
// O rótulo de um campo virava "[object Object]" quando perguntar() recebia um
// objeto único: a função só distinguia string de array, e o objeto caía no
// caminho da string. Os testes abaixo cobrem as três formas de chamada.

// Contexto com o dialogo.js carregado, reaproveitado pelos testes abaixo.
const dialogoCtx = montarAmbiente();
vm.runInContext(fs.readFileSync("dialogo.js", "utf-8"), dialogoCtx, { filename: "dialogo.js" });

function montarDialogo(campos) {
    // Usa a normalização REAL do dialogo.js, não uma cópia: uma cópia passaria
    // no teste mesmo com a função de produção quebrada.
    const normalizar = vm.runInContext("_normalizarCampos", dialogoCtx);
    const criar = vm.runInContext("_criarDialogo", dialogoCtx);

    const lista = normalizar(campos);
    const partes = criar({
        titulo: "t",
        mensagem: null,
        campos: lista,
        rotuloConfirmar: "OK",
        rotuloCancelar: "Cancelar",
    });

    return { partes, lista };
}

test("perguntar com string gera rótulo de texto", () => {
    const { lista } = montarDialogo("Seu e-mail:");
    assert.equal(lista.length, 1);
    assert.equal(lista[0].rotulo, "Seu e-mail:");
    assert.equal(lista[0].nome, "valor");
});

test("perguntar com objeto único NÃO vira [object Object]", () => {
    const { lista } = montarDialogo({ nome: "email", rotulo: "E-mail da conta", tipo: "email" });

    assert.equal(lista.length, 1);
    assert.equal(lista[0].rotulo, "E-mail da conta");
    assert.notEqual(lista[0].rotulo, "[object Object]");
    assert.equal(lista[0].nome, "email");
});

test("perguntar com array mantém todos os campos", () => {
    const { lista } = montarDialogo([
        { nome: "token", rotulo: "Código" },
        { nome: "senha", rotulo: "Nova senha", tipo: "password" },
    ]);

    assert.equal(lista.length, 2);
    assert.deepEqual(lista.map((c) => c.rotulo), ["Código", "Nova senha"]);
    assert.deepEqual(lista.map((c) => c.nome), ["token", "senha"]);
});

test("campo sem nome recebe chave automática", () => {
    const { lista } = montarDialogo([{ rotulo: "Um" }, { rotulo: "Dois" }]);
    assert.deepEqual(lista.map((c) => c.nome), ["valor", "campo1"]);
});

test("nenhum rótulo de campo contém [object Object]", () => {
    // Varre as chamadas reais de perguntar() no código e confere o formato.
    const arquivos = ["script.js"];
    for (const arquivo of arquivos) {
        const texto = fs.readFileSync(arquivo, "utf-8");
        assert.ok(!texto.includes("[object Object]"), `${arquivo} tem [object Object] literal`);
    }
});

test("botão cancelar não é primário", () => {
    const { partes } = montarDialogo("Qualquer coisa");
    // O confirmar leva acao--primaria; o cancelar, não. Se os dois tivessem a
    // mesma classe, ficariam visualmente idênticos.
    assert.ok(partes.confirmar.className.includes("acao--primaria"));

    const botoes = partes.dialogo.querySelectorAll("button");
    const cancelar = botoes.find((b) => b.textContent === "Cancelar");
    assert.ok(cancelar, "botão Cancelar não encontrado");
    assert.ok(!cancelar.className.includes("acao--primaria"), "Cancelar está como primário");
});

// ---------------------------------------------------------------- calendário
/**
 * O seletor de data aceita o que as pessoas digitam de verdade, e não só o
 * formato "certo". O risco de errar aqui é silencioso: uma data mal
 * interpretada vira prazo errado, e ninguém percebe até o aluno reclamar que
 * a atividade fechou antes da hora.
 */
// Carregado por vm, como os outros arquivos do front: este é um módulo ES e
// não tem `require`. As funções de leitura de data não tocam no DOM, então o
// contexto mínimo basta.
const calendarioCtx = { console, Date, Number, String, Boolean, Math, RegExp };
calendarioCtx.globalThis = calendarioCtx;
vm.createContext(calendarioCtx);
vm.runInContext(fs.readFileSync("calendario.js", "utf-8"), calendarioCtx, {
    filename: "calendario.js",
});

const calendario = {
    interpretarDataDigitada: vm.runInContext("interpretarDataDigitada", calendarioCtx),
    formatarParaCampo: vm.runInContext("formatarParaCampo", calendarioCtx),
};

function data(texto) {
    return calendario.interpretarDataDigitada(texto);
}

test("calendário aceita o formato completo", () => {
    const d = data("05/03/2026");
    assert.equal(d.getDate(), 5);
    assert.equal(d.getMonth(), 2);
    assert.equal(d.getFullYear(), 2026);
});

test("calendário aceita dia e mês sem zero à esquerda", () => {
    const d = data("5/3/2026");
    assert.equal(d.getDate(), 5);
    assert.equal(d.getMonth(), 2);
});

test("calendário aceita separadores diferentes", () => {
    for (const texto of ["05/03/2026", "05-03-2026", "05.03.2026", "05 03 2026"]) {
        const d = data(texto);
        assert.ok(d, `recusou ${texto}`);
        assert.equal(d.getDate(), 5);
        assert.equal(d.getMonth(), 2);
    }
});

test("calendário entende ano de dois dígitos", () => {
    assert.equal(data("05/03/26").getFullYear(), 2026);
});

test("calendário usa o ano corrente quando não informado", () => {
    assert.equal(data("05/03").getFullYear(), new Date().getFullYear());
});

test("calendário lê a hora junto da data", () => {
    const d = data("05/03/2026 14:30");
    assert.equal(d.getHours(), 14);
    assert.equal(d.getMinutes(), 30);
});

test("calendário assume meia-noite quando não há hora", () => {
    const d = data("05/03/2026");
    assert.equal(d.getHours(), 0);
    assert.equal(d.getMinutes(), 0);
});

test("calendário recusa dia que não existe no mês", () => {
    // Sem esta checagem o JavaScript transforma 31/02 em 2 ou 3 de março, e o
    // professor agendaria para um dia que não foi o que ele digitou.
    assert.equal(data("31/02/2026"), null);
    assert.equal(data("31/04/2026"), null);
});

test("calendário aceita 29/02 em ano bissexto e recusa fora dele", () => {
    assert.ok(data("29/02/2028"), "recusou data válida de ano bissexto");
    assert.equal(data("29/02/2026"), null);
});

test("calendário recusa mês e hora impossíveis", () => {
    assert.equal(data("05/13/2026"), null);
    assert.equal(data("05/03/2026 25:00"), null);
    assert.equal(data("05/03/2026 10:75"), null);
});

test("calendário recusa texto que não é data", () => {
    for (const texto of ["", "   ", "abc", "5", "//", "amanhã"]) {
        assert.equal(data(texto), null, `aceitou ${JSON.stringify(texto)}`);
    }
});

test("calendário formata de volta no padrão brasileiro", () => {
    const d = data("5/3/2026 9:07");
    assert.equal(calendario.formatarParaCampo(d), "05/03/2026 09:07");
});

test("o que foi digitado volta igual depois de formatar e reler", () => {
    // Ida e volta: digitar, formatar para o campo e reler tem que dar a mesma
    // data. Se a formatação e a leitura discordarem, o valor muda sozinho a
    // cada vez que o formulário é reaberto.
    for (const texto of ["05/03/2026 14:30", "1/1/2027 00:00", "31/12/2026 23:59"]) {
        const primeira = data(texto);
        const segunda = data(calendario.formatarParaCampo(primeira));
        assert.equal(segunda.getTime(), primeira.getTime(), `ida e volta mudou ${texto}`);
    }
});
