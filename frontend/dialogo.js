/**
 * Diálogos da plataforma: substituem alert(), confirm() e prompt().
 *
 * Os diálogos nativos do navegador travam a página inteira, não seguem a
 * identidade visual e, em alguns navegadores, podem ser silenciados pelo
 * usuário — o que faria uma confirmação de exclusão sumir sem aviso.
 *
 * Todos retornam Promise, então o código chamador fica igual ao que já era:
 *
 *     await avisar("Material salvo.");
 *     if (await confirmar("Excluir?")) { ... }
 *     const valor = await perguntar("Seu e-mail:");
 *
 * Acessibilidade: usa <dialog> nativo, que já entrega foco preso dentro do
 * diálogo, fechamento por Esc e semântica de modal para leitores de tela.
 */

function _criarDialogo({ titulo, mensagem, tipo = "aviso", campos = null, rotuloConfirmar, rotuloCancelar }) {
    const dialogo = document.createElement("dialog");
    dialogo.className = `dialogo dialogo--${tipo}`;

    const caixa = document.createElement("div");
    caixa.className = "dialogo-caixa";

    if (titulo) {
        const h2 = document.createElement("h2");
        h2.className = "dialogo-titulo";
        h2.textContent = titulo;
        caixa.appendChild(h2);
    }

    if (mensagem) {
        // Cada linha vira um parágrafo: mensagens de erro do servidor às vezes
        // vêm com quebras, e um bloco só ficaria ilegível.
        String(mensagem).split("\n").filter((linha) => linha.trim()).forEach((linha) => {
            const p = document.createElement("p");
            p.className = "dialogo-texto";
            p.textContent = linha;
            caixa.appendChild(p);
        });
    }

    const formulario = document.createElement("form");
    formulario.method = "dialog";
    formulario.className = "dialogo-formulario";

    const entradas = [];

    (campos || []).forEach((campo, indice) => {
        const rotulo = document.createElement("label");
        rotulo.className = "campo campo--larga";

        const texto = document.createElement("span");
        texto.textContent = campo.rotulo;

        const entrada = document.createElement("input");
        entrada.type = campo.tipo || "text";
        entrada.value = campo.valor || "";
        if (campo.placeholder) entrada.placeholder = campo.placeholder;
        if (campo.obrigatorio !== false) entrada.required = true;
        if (campo.minimo) entrada.minLength = campo.minimo;
        if (indice === 0) entrada.autofocus = true;

        rotulo.appendChild(texto);
        rotulo.appendChild(entrada);
        formulario.appendChild(rotulo);
        entradas.push({ nome: campo.nome, entrada });
    });

    const acoes = document.createElement("div");
    acoes.className = "dialogo-acoes";

    if (rotuloCancelar) {
        const cancelar = document.createElement("button");
        cancelar.type = "button";
        cancelar.className = "acao";
        cancelar.textContent = rotuloCancelar;
        cancelar.addEventListener("click", () => {
            dialogo.returnValue = "cancelar";
            dialogo.close();
        });
        acoes.appendChild(cancelar);
    }

    const confirmar = document.createElement("button");
    confirmar.type = "submit";
    confirmar.className = tipo === "perigo" ? "acao acao--perigo" : "acao acao--primaria";
    confirmar.textContent = rotuloConfirmar || "OK";
    confirmar.value = "confirmar";
    acoes.appendChild(confirmar);

    formulario.appendChild(acoes);
    caixa.appendChild(formulario);
    dialogo.appendChild(caixa);
    document.body.appendChild(dialogo);

    return { dialogo, formulario, entradas, confirmar };
}

function _abrir({ dialogo, formulario, entradas, confirmar }) {
    return new Promise((resolver) => {
        let valorConfirmado = null;

        formulario.addEventListener("submit", () => {
            // method="dialog" já fecha; aqui só capturamos o que foi digitado
            // antes de o formulário ser limpo.
            valorConfirmado = entradas.length
                ? Object.fromEntries(entradas.map(({ nome, entrada }) => [nome, entrada.value]))
                : true;
        });

        dialogo.addEventListener("close", () => {
            dialogo.remove();
            resolver(dialogo.returnValue === "cancelar" ? null : valorConfirmado);
        });

        // Clique fora da caixa fecha, como o usuário espera de um modal.
        dialogo.addEventListener("click", (evento) => {
            if (evento.target === dialogo) {
                dialogo.returnValue = "cancelar";
                dialogo.close();
            }
        });

        dialogo.showModal();

        if (entradas.length) entradas[0].entrada.focus();
        else confirmar.focus();
    });
}

/** Mensagem simples. Resolve quando o usuário fecha. */
async function avisar(mensagem, titulo = null, tipo = "aviso") {
    const partes = _criarDialogo({ titulo, mensagem, tipo, rotuloConfirmar: "Entendi" });
    await _abrir(partes);
}

/** Mensagem de erro — mesma coisa, com destaque visual diferente. */
async function avisarErro(mensagem, titulo = "Algo deu errado") {
    await avisar(mensagem, titulo, "erro");
}

/** Confirmação. Resolve true se o usuário confirmou. */
async function confirmar(mensagem, { titulo = "Confirmar", rotulo = "Confirmar", perigo = false } = {}) {
    const partes = _criarDialogo({
        titulo,
        mensagem,
        tipo: perigo ? "perigo" : "aviso",
        rotuloConfirmar: rotulo,
        rotuloCancelar: "Cancelar",
    });
    return (await _abrir(partes)) !== null;
}

/**
 * Transforma as três formas aceitas de descrever campos numa lista única.
 *
 * Extraída de `perguntar()` para poder ser testada direto: o bug que fazia o
 * rótulo virar "[object Object]" morava exatamente aqui, e um teste que
 * duplicasse essa lógica passaria mesmo com a função quebrada.
 */
function _normalizarCampos(campos) {
    let lista;

    if (Array.isArray(campos)) {
        lista = campos;
    } else if (campos && typeof campos === "object") {
        lista = [campos];
    } else {
        lista = [{ nome: "valor", rotulo: String(campos) }];
    }

    // Um campo sem `nome` ainda precisa de uma chave para o valor voltar.
    return lista.map((campo, indice) => ({
        ...campo,
        nome: campo.nome || (indice === 0 ? "valor" : `campo${indice}`),
    }));
}

/**
 * Pede um ou mais valores. Resolve null se o usuário cancelar.
 *
 * Aceita três formas de descrever os campos, porque as três são naturais de
 * escrever e passar a errada resultava num rótulo "[object Object]":
 *
 *   perguntar("Seu e-mail:")                          -> resolve a string
 *   perguntar({ nome: "email", rotulo: "E-mail" })    -> resolve a string
 *   perguntar([{...}, {...}])                         -> resolve um objeto
 */
async function perguntar(campos, { titulo = null, mensagem = null, rotulo = "Continuar" } = {}) {
    const varios = Array.isArray(campos);
    const lista = _normalizarCampos(campos);

    const partes = _criarDialogo({
        titulo,
        mensagem,
        campos: lista,
        rotuloConfirmar: rotulo,
        rotuloCancelar: "Cancelar",
    });

    const resposta = await _abrir(partes);

    if (resposta === null) return null;

    // Com vários campos devolve o objeto inteiro; com um só, devolve direto o
    // que foi digitado — o chamador não deveria ter que saber a chave interna.
    return varios ? resposta : resposta[lista[0].nome];
}
