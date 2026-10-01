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
        this.eventos = {};
    }

    appendChild(no) {
        this.filhos.push(no);
        return no;
    }

    remove() {}

    // Guarda os ouvintes para os testes poderem disparar o clique. Sem isso
    // dá para verificar que o botão existe, mas não o que ele faz — e o que
    // ele faz é o comportamento que importa.
    addEventListener(tipo, funcao) {
        (this.eventos[tipo] = this.eventos[tipo] || []).push(funcao);
    }

    disparar(tipo) {
        (this.eventos[tipo] || []).forEach((funcao) => funcao({ preventDefault() {} }));
    }
    focus() {}

    // classList mínimo, lendo e escrevendo o próprio className — assim quem
    // testa por className e quem testa por classList enxergam a mesma coisa.
    get classList() {
        const no = this;
        const lista = () => no.className.split(/\s+/).filter(Boolean);
        return {
            contains: (c) => lista().includes(c),
            add: (...cs) => { no.className = [...new Set([...lista(), ...cs])].join(" "); },
            remove: (...cs) => { no.className = lista().filter((x) => !cs.includes(x)).join(" "); },
            toggle: (c, forcar) => {
                const ligar = forcar === undefined ? !lista().includes(c) : Boolean(forcar);
                if (ligar) no.classList.add(c); else no.classList.remove(c);
                return ligar;
            },
        };
    }
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

    for (const arquivo of ["auth.js", "markdown.js", "modulos.js", "visualizador.js", "privacidade.js"]) {
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
test("denúncia tem os dois lados construídos", () => {
    // O backlog descrevia quem *gerencia* denúncias e esquecia quem as *faz*:
    // uma caixa de entrada sem porta de entrada. Enquanto era roadmap, o teste
    // olhava o catálogo; agora que é tela, olha as telas. A garantia é a mesma:
    // ninguém entrega metade deste módulo.
    for (const pagina of ["aluno/denuncias.html", "professor/denuncias.html",
                          "administracao/denuncias.html"]) {
        assert.ok(fs.existsSync(pagina), `falta a tela ${pagina}`);
    }
});

test("dá para reportar de dentro do material", () => {
    // Reportar só pela tela de Denúncias exigiria lembrar o nome do arquivo e
    // navegar até lá. Sem o atalho no item, a porta de entrada existe no papel
    // e não na prática.
    assert.ok(fs.existsSync("reportar.js"), "falta o módulo de reportar");

    for (const pagina of ["aluno/materiais.html", "professor/materiais.html"]) {
        const html = fs.readFileSync(pagina, "utf-8");
        assert.ok(html.includes("reportar.js"), `${pagina} não carrega reportar.js`);
    }

    for (const script of ["aluno/materiais.js", "professor/materiais.js"]) {
        const codigo = fs.readFileSync(script, "utf-8");
        assert.ok(codigo.includes("reportarMaterial"), `${script} não oferece o atalho`);
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


// ---------------------------------------------- oferta de falar com o professor
/**
 * Quando o assistente recusa uma pergunta (volta sem fonte citada), o chat
 * oferece levar a dúvida ao professor da turma e leva o texto junto.
 *
 * Duas telas, um caminho: `aluno.js` monta a oferta e guarda o rascunho,
 * `mensagens.js` consome. Testados juntos porque o contrato entre eles é uma
 * chave de sessionStorage — o tipo de acordo que quebra em silêncio quando um
 * dos lados muda o nome ou o formato.
 *
 * Os dois arquivos rodam código no topo, mas só dentro de `if (usuario)`. Com
 * `exigirAcesso` devolvendo null nada dispara, e as funções ficam disponíveis
 * para o teste chamar uma a uma.
 */
function montarContextoPagina(arquivo, { pathname, nos }) {
    const contexto = {
        console, JSON, Date, Math, String, Number, Array, Object, Boolean, Promise,
        setInterval: () => 0,
        setTimeout: () => 0,
        exigirAcesso: () => null,
        document: {
            createElement: (tag) => new No(tag),
            querySelector: (seletor) => nos[seletor] || null,
            querySelectorAll: () => [],
            addEventListener: () => {},
        },
        window: { location: { pathname, href: "" } },
        sessionStorage: {
            _dados: {},
            getItem(chave) { return this._dados[chave] ?? null; },
            setItem(chave, valor) { this._dados[chave] = String(valor); },
            removeItem(chave) { delete this._dados[chave]; },
        },
    };

    contexto.globalThis = contexto;
    vm.createContext(contexto);
    vm.runInContext(fs.readFileSync(arquivo, "utf-8"), contexto, { filename: arquivo });

    return contexto;
}

/** Contexto novo por teste: sessionStorage e DOM sujos contaminariam o seguinte. */
function contextoChat() {
    const chatMensagens = new No("div");
    const ctxAluno = montarContextoPagina("aluno/aluno.js", {
        pathname: "/aluno/aluno.html",
        nos: { "#chatMensagens": chatMensagens },
    });

    vm.runInContext(
        `turmasDoAluno = [{ id: 7, nome: "Cardiologia", semestre: "2026.2", professor_nome: "Marina Duarte" }];
         turmaAtual = 7;`,
        ctxAluno
    );

    return { ctxAluno, chatMensagens, oferecer: vm.runInContext("oferecerProfessor", ctxAluno) };
}

test("a oferta nomeia a turma e o professor, e fala no condicional", () => {
    const { chatMensagens, oferecer } = contextoChat();
    oferecer("O que é tetralogia de Fallot?");

    const texto = chatMensagens.textContent;
    // O "se" é a razão de a oferta existir nesta forma: a plataforma não sabe
    // se a pergunta tem a ver com a matéria. Afirmar seria dar conselho errado
    // para quem perguntou qualquer coisa.
    assert.match(texto, /^Se isso for matéria de Cardiologia/);
    assert.match(texto, /Prof\. Marina Duarte/);
});

test("a oferta não aparece sem professor conhecido", () => {
    // Turma sem professor_nome: a oferta sairia "leve ao Prof. undefined".
    const { ctxAluno, chatMensagens, oferecer } = contextoChat();
    vm.runInContext("turmasDoAluno = [{ id: 7, nome: \"Cardiologia\" }];", ctxAluno);

    oferecer("Qualquer pergunta.");

    assert.equal(chatMensagens.filhos.length, 0);
});

test("clicar na oferta guarda a pergunta e a turma para a tela de mensagens", () => {
    const { ctxAluno, chatMensagens, oferecer } = contextoChat();
    const pergunta = "O que é tetralogia de Fallot?";
    oferecer(pergunta);

    chatMensagens.querySelectorAll("button")[0].disparar("click");

    const guardado = JSON.parse(ctxAluno.sessionStorage.getItem("deltacare_rascunho_mensagem"));
    assert.equal(guardado.turma_id, 7);
    assert.equal(guardado.texto, pergunta);
    assert.match(ctxAluno.window.location.href, /mensagens\.html$/);
});

/** Lado de mensagens.js: recebe o rascunho e abre a conversa certa. */
function contextoMensagens(rascunho, conversas) {
    const campo = new No("textarea");
    const ctx = montarContextoPagina("mensagens.js", {
        pathname: "/aluno/mensagens.html",
        nos: { "#campoMensagem": campo },
    });

    if (rascunho !== null) {
        ctx.sessionStorage.setItem("deltacare_rascunho_mensagem", JSON.stringify(rascunho));
    }

    const abertas = [];
    ctx.abertas = abertas;
    // Substitui abrirConversa: a de verdade fala com o servidor. O que este
    // teste verifica é *qual* conversa foi escolhida.
    vm.runInContext(
        `conversas = ${JSON.stringify(conversas)};
         abrirConversa = (c) => { abertas.push(c); return Promise.resolve(); };`,
        ctx
    );

    return { ctx, campo, aplicar: vm.runInContext("aplicarRascunho", ctx) };
}

const CONVERSAS = [
    { turma_id: 3, titulo: "Prof. Outro" },
    { turma_id: 7, titulo: "Prof. Marina Duarte" },
];

test("o rascunho abre a conversa da turma certa, não a primeira da lista", async () => {
    const { campo, aplicar, ctx } = contextoMensagens({ turma_id: 7, texto: "O que é tetralogia de Fallot?" }, CONVERSAS);

    assert.equal(aplicar(), true);
    await Promise.resolve();

    assert.equal(ctx.abertas.length, 1);
    assert.equal(ctx.abertas[0].turma_id, 7);
    assert.equal(campo.value, "O que é tetralogia de Fallot?");
});

test("o rascunho é consumido de uma vez", async () => {
    // Voltar para esta tela depois é para ver a resposta, não para reabrir a
    // mesma pergunta por cima do que a pessoa tiver escrito.
    const { aplicar, ctx } = contextoMensagens({ turma_id: 7, texto: "Pergunta." }, CONVERSAS);

    assert.equal(aplicar(), true);
    assert.equal(ctx.sessionStorage.getItem("deltacare_rascunho_mensagem"), null);
    assert.equal(aplicar(), false);
});

test("sem rascunho a tela segue o caminho normal", () => {
    const { aplicar, ctx } = contextoMensagens(null, CONVERSAS);

    assert.equal(aplicar(), false);
    assert.equal(ctx.abertas.length, 0);
});

test("rascunho de turma sem conversa não abre nada", () => {
    // Aluno desmatriculado entre o chat e o clique: quem manda é a lista do
    // servidor, não o que ficou guardado no navegador.
    const { aplicar, ctx } = contextoMensagens({ turma_id: 99, texto: "Pergunta." }, CONVERSAS);

    assert.equal(aplicar(), false);
    assert.equal(ctx.abertas.length, 0);
});

test("rascunho corrompido não derruba a tela", () => {
    const { ctx, aplicar } = contextoMensagens(null, CONVERSAS);
    ctx.sessionStorage.setItem("deltacare_rascunho_mensagem", "{isso não é json");

    assert.equal(aplicar(), false);
});


// ---------------------------------------------- seletor de turma do chat
/**
 * Uma `turma` no banco é na prática **uma disciplina**: tem um professor e um
 * corpo de material só dela. Uma mesma turma de alunos cursando cinco matérias
 * são cinco entradas, e o aluno é matriculado nas cinco.
 *
 * Por isso o seletor precisa distinguir as opções: cada uma escolhe em qual
 * material o assistente vai buscar. Duas opções com o mesmo rótulo fazem o
 * aluno perguntar de Anatomia na entrada de Fisiologia e ouvir que o material
 * não cobre — sem entender por quê.
 */
test("o seletor distingue disciplinas que o admin batizou com o mesmo nome", () => {
    const seletor = new No("select");
    const ctxAluno = montarContextoPagina("aluno/aluno.js", {
        pathname: "/aluno/aluno.html",
        nos: { "#seletorTurma": seletor },
    });

    // O caso real: admin seguiu o rótulo antigo e batizou as duas pela turma.
    vm.runInContext("preencherSeletor", ctxAluno)(seletor, [
        { id: 1, nome: "MED 3A", semestre: "2026/2", professor_nome: "Marina Duarte" },
        { id: 2, nome: "MED 3A", semestre: "2026/2", professor_nome: "Renato Alves" },
    ]);

    const rotulos = seletor.filhos.map((o) => o.textContent);
    assert.equal(new Set(rotulos).size, 2, `opções indistinguíveis: ${JSON.stringify(rotulos)}`);
    assert.match(rotulos[0], /Marina Duarte/);
    assert.match(rotulos[1], /Renato Alves/);
});

test("o seletor não escreve HTML vindo do banco", () => {
    // Nome de turma e de professor são digitados por um admin. Esta tela não
    // tem o `esc` das outras, então as opções são montadas com textContent.
    const seletor = new No("select");
    const ctxAluno = montarContextoPagina("aluno/aluno.js", {
        pathname: "/aluno/aluno.html",
        nos: { "#seletorTurma": seletor },
    });

    vm.runInContext("preencherSeletor", ctxAluno)(seletor, [
        { id: 1, nome: "<img src=x onerror=alert(1)>", semestre: "2026/2", professor_nome: "Ana" },
    ]);

    assert.equal(seletor.innerHTML, "");
    assert.match(seletor.filhos[0].textContent, /<img src=x onerror=alert\(1\)>/);
});

test("o seletor sobrevive a turma sem professor conhecido", () => {
    const seletor = new No("select");
    const ctxAluno = montarContextoPagina("aluno/aluno.js", {
        pathname: "/aluno/aluno.html",
        nos: { "#seletorTurma": seletor },
    });

    vm.runInContext("preencherSeletor", ctxAluno)(seletor, [
        { id: 1, nome: "Cardiologia I", semestre: "2026/2" },
    ]);

    assert.equal(seletor.filhos[0].textContent, "Cardiologia I · 2026/2");
});


// ---------------------------------------------------------------- escape de HTML
/**
 * `esc` é a única defesa contra XSS nas telas que montam HTML por template.
 *
 * Estava copiado idêntico em três arquivos, enquanto outros três precisavam
 * dele e não tinham — e foi assim que nome de disciplina digitado pelo admin
 * chegava cru ao navegador do professor. Agora mora em auth.js, carregado em
 * toda página, e é testado num lugar só.
 */
test("esc neutraliza os cinco caracteres que abrem tag e atributo", () => {
    assert.equal(ctx.esc("<script>"), "&lt;script&gt;");
    assert.equal(ctx.esc('"'), "&quot;");
    assert.equal(ctx.esc("'"), "&#39;");
    assert.equal(ctx.esc("&"), "&amp;");
});

test("esc escapa o & primeiro, senão desfaz o próprio escape", () => {
    // Trocando `<` antes de `&`, o "&lt;" produzido viraria "&amp;lt;" e o
    // texto apareceria literalmente errado na tela.
    assert.equal(ctx.esc("&lt;"), "&amp;lt;");
});

test("esc barra o payload clássico de injeção por atributo", () => {
    const escapado = ctx.esc('" onerror="alert(1)');

    assert.ok(!escapado.includes('"'), `sobrou aspa: ${escapado}`);
});

test("esc trata null e undefined como texto vazio", () => {
    // Campo opcional do banco chega como null. Sem isto a tela mostraria a
    // palavra "null" onde deveria estar vazio.
    assert.equal(ctx.esc(null), "");
    assert.equal(ctx.esc(undefined), "");
});

test("esc não estraga texto comum", () => {
    assert.equal(ctx.esc("Cardiologia I · 2026/2"), "Cardiologia I · 2026/2");
    assert.equal(ctx.esc("Anatomia — Prof. Marina Duarte"), "Anatomia — Prof. Marina Duarte");
});

test("esc converte número sem reclamar", () => {
    assert.equal(ctx.esc(42), "42");
});


test("o seletor do chat separa as disciplinas antigas num grupo à parte", () => {
    // As antigas continuam no seletor — perguntar sobre material de semestre
    // passado é como se revisa para a residência —, mas misturadas com as de
    // agora o aluno abriria o chat na disciplina errada.
    const seletor = new No("select");
    const ctxAluno = montarContextoPagina("aluno/aluno.js", {
        pathname: "/aluno/aluno.html",
        nos: { "#seletorTurma": seletor },
    });

    vm.runInContext("preencherSeletor", ctxAluno)(seletor, [
        { id: 1, nome: "Cardiologia I", semestre: "2026/2", vigente: true },
        { id: 2, nome: "Anatomia", semestre: "2026/1", vigente: false },
        { id: 3, nome: "Fisiologia", semestre: "2026/1", vigente: false },
    ]);

    assert.equal(seletor.filhos.length, 2, "uma opção solta e um grupo");
    assert.equal(seletor.filhos[0].tagName, "OPTION");
    assert.match(seletor.filhos[0].textContent, /Cardiologia/);

    const grupo = seletor.filhos[1];
    assert.equal(grupo.tagName, "OPTGROUP");
    assert.equal(grupo.label, "Semestres anteriores");
    assert.deepEqual(grupo.filhos.map((o) => o.value), [2, 3]);
});

test("sem a marca de vigente, o seletor fica como era", () => {
    // Servidor antigo, ou resposta sem o campo: nada vai para o grupo.
    const seletor = new No("select");
    const ctxAluno = montarContextoPagina("aluno/aluno.js", {
        pathname: "/aluno/aluno.html",
        nos: { "#seletorTurma": seletor },
    });

    vm.runInContext("preencherSeletor", ctxAluno)(seletor, [
        { id: 1, nome: "Cardiologia I", semestre: "2026/2" },
        { id: 2, nome: "Anatomia", semestre: "2026/1" },
    ]);

    assert.ok(seletor.filhos.every((f) => f.tagName === "OPTION"));
});


// ---------------------------------------------------------------- estrela de favorito
/**
 * A estrela só muda depois que o servidor confirma. Acender antes e apagar se
 * falhar faria o aluno achar, por um instante ou para sempre (se a resposta
 * nunca chegar), que guardou o que não guardou.
 */
function contextoEstrela(respostaDoServidor) {
    const ctx = montarContextoPagina("aluno/estudo.js", { pathname: "/aluno/materiais.html", nos: {} });
    ctx.erros = [];
    ctx.api = async () => ({ json: async () => respostaDoServidor });
    ctx.avisarErro = async (mensagem) => { ctx.erros.push(mensagem); };
    return ctx;
}

const esperarRespostas = () => new Promise((resolver) => setImmediate(resolver));

test("a estrela acende quando o servidor confirma", async () => {
    const ctx = contextoEstrela({ sucesso: true, favorito: true });
    const material = { id: 1, favorito: false };
    const botao = vm.runInContext("botaoFavorito", ctx)(material);

    assert.equal(botao.textContent, "☆");
    botao.disparar("click");
    await esperarRespostas();

    assert.equal(botao.textContent, "★");
    assert.equal(material.favorito, true);
});

test("a estrela não acende quando o servidor recusa", async () => {
    const ctx = contextoEstrela({ sucesso: false, mensagem: "Material não encontrado." });
    const material = { id: 1, favorito: false };
    const botao = vm.runInContext("botaoFavorito", ctx)(material);

    botao.disparar("click");
    await esperarRespostas();

    assert.equal(botao.textContent, "☆");
    assert.equal(material.favorito, false);
    assert.deepEqual(ctx.erros, ["Material não encontrado."]);
});


// ---------------------------------------------------------------- endereço da API
/**
 * Era "http://127.0.0.1:8000" fixo: no servidor da instituição, o navegador de
 * cada aluno procuraria a API no próprio computador do aluno.
 */
function enderecoPara(local, sobrescrito) {
    const ctx = {
        console,
        window: { location: local, ...(sobrescrito ? { DELTACARE_API_URL: sobrescrito } : {}) },
    };
    vm.createContext(ctx);
    vm.runInContext(fs.readFileSync("config.js", "utf-8"), ctx, { filename: "config.js" });
    return vm.runInContext("API_URL", ctx);
}

test("em produção a API é a mesma origem da página", () => {
    const local = { port: "", protocol: "https:", hostname: "deltacare.moinhos.org.br",
                    origin: "https://deltacare.moinhos.org.br" };
    assert.equal(enderecoPara(local), "https://deltacare.moinhos.org.br");
});

test("no servidor de desenvolvimento a API fica na porta 8000 do mesmo computador", () => {
    const local = { port: "5500", protocol: "http:", hostname: "localhost", origin: "http://localhost:5500" };
    assert.equal(enderecoPara(local), "http://localhost:8000");
});

test("um endereço definido explicitamente vence a dedução", () => {
    const local = { port: "", protocol: "https:", hostname: "a.com", origin: "https://a.com" };
    assert.equal(enderecoPara(local, "https://api.b.com"), "https://api.b.com");
});

// ---------------------------------------------------------------- privacidade
test("a cópia dos dados leva a data no nome, para duas cópias não se sobrescreverem", () => {
    const nome = doContexto("nomeArquivoDaCopia")("2026-10-01T14:03:00+00:00");
    assert.equal(nome, "delta-care-meus-dados-2026-10-01.json");
});

test("todo status que o servidor grava tem nome na tela", () => {
    // Lido do próprio backend: um status novo lá sem rótulo aqui apareceria
    // para o aluno como "agendada" cru, ou como nada.
    const regras = fs.readFileSync("../backend/regras/privacidade.py", "utf-8");
    const gravados = new Set([
        ...[...regras.matchAll(/status = '(\w+)'/g)].map((m) => m[1]),
        ...[...regras.matchAll(/VALUES \(\?, \?, '(\w+)'/g)].map((m) => m[1]),
        ...[...regras.matchAll(/'exportacao', '(\w+)'/g)].map((m) => m[1]),
    ]);
    const rotulos = doContexto("STATUS_PRIVACIDADE");

    assert.ok(gravados.size >= 6, `poucos status encontrados: ${[...gravados]}`);
    for (const status of gravados) {
        assert.ok(rotulos[status], `status sem rótulo: ${status}`);
    }
});

test("conta desativada aparece em destaque, e status desconhecido não quebra a tela", () => {
    const selo = doContexto("seloDeStatus");

    assert.match(selo("agendada").className, /badge-status--perigo/);
    assert.equal(selo("agendada").textContent, "Conta desativada");
    assert.equal(selo("inventado").textContent, "inventado");
});
