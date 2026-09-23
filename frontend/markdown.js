/**
 * Renderizador de Markdown para as respostas da IA.
 *
 * Por que não usar innerHTML: o texto vem do modelo de linguagem, que por sua
 * vez recebeu o conteúdo dos PDFs enviados pelos professores. Jogar isso em
 * innerHTML deixaria qualquer HTML embutido nesse caminho virar elemento de
 * verdade na página. Aqui todo texto entra por textContent e só os elementos
 * que este arquivo cria (negrito, lista, tabela...) existem no resultado.
 *
 * Cobre o que os modelos de chat costumam devolver: títulos, negrito, itálico,
 * código, listas, tabelas, citações e separadores. O que não for reconhecido
 * vira parágrafo de texto simples — nunca some da tela.
 */

/**
 * Converte a marcação inline (negrito, itálico, código) de uma linha em nós de
 * texto e elementos, anexados a `destino`.
 */
function aplicarMarcacaoInline(texto, destino) {
    // `código` | **negrito** | *itálico* | _itálico_
    const padrao = /`([^`]+)`|\*\*([^*]+)\*\*|\*([^*\n]+)\*|_([^_\n]+)_/g;
    let ultimoIndice = 0;
    let achado;

    while ((achado = padrao.exec(texto)) !== null) {
        if (achado.index > ultimoIndice) {
            destino.appendChild(
                document.createTextNode(texto.slice(ultimoIndice, achado.index))
            );
        }

        const [, codigo, negrito, italico, italicoUnderline] = achado;
        let elemento;

        if (codigo !== undefined) {
            elemento = document.createElement("code");
            elemento.textContent = codigo;
        } else if (negrito !== undefined) {
            elemento = document.createElement("strong");
            elemento.textContent = negrito;
        } else {
            elemento = document.createElement("em");
            elemento.textContent = italico !== undefined ? italico : italicoUnderline;
        }

        destino.appendChild(elemento);
        ultimoIndice = padrao.lastIndex;
    }

    if (ultimoIndice < texto.length) {
        destino.appendChild(document.createTextNode(texto.slice(ultimoIndice)));
    }
}

/** Quebra uma linha de tabela ("| a | b |") nas células, sem os pipes das pontas. */
function celulasDaLinha(linha) {
    return linha
        .trim()
        .replace(/^\||\|$/g, "")
        .split("|")
        .map((celula) => celula.trim());
}

/** Reconhece a linha separadora do cabeçalho de tabela: |---|:---:|---| */
function ehSeparadorDeTabela(linha) {
    return /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(linha) && linha.includes("-");
}

function montarTabela(linhas, indiceInicial) {
    const tabela = document.createElement("table");
    tabela.className = "md-tabela";

    const cabecalho = document.createElement("thead");
    const linhaCabecalho = document.createElement("tr");

    celulasDaLinha(linhas[indiceInicial]).forEach((celula) => {
        const th = document.createElement("th");
        aplicarMarcacaoInline(celula, th);
        linhaCabecalho.appendChild(th);
    });

    cabecalho.appendChild(linhaCabecalho);
    tabela.appendChild(cabecalho);

    const corpo = document.createElement("tbody");
    let indice = indiceInicial + 2; // pula cabeçalho e separador

    while (indice < linhas.length && linhas[indice].trim().startsWith("|")) {
        const tr = document.createElement("tr");
        celulasDaLinha(linhas[indice]).forEach((celula) => {
            const td = document.createElement("td");
            aplicarMarcacaoInline(celula, td);
            tr.appendChild(td);
        });
        corpo.appendChild(tr);
        indice += 1;
    }

    tabela.appendChild(corpo);

    // A tabela vai dentro de um contêiner que rola na horizontal, para não
    // estourar a largura da bolha do chat em tela estreita.
    const moldura = document.createElement("div");
    moldura.className = "md-tabela-moldura";
    moldura.appendChild(tabela);

    return { elemento: moldura, proximoIndice: indice };
}

function montarLista(linhas, indiceInicial, ordenada) {
    const lista = document.createElement(ordenada ? "ol" : "ul");
    lista.className = "md-lista";

    const padraoItem = ordenada ? /^\s*\d+[.)]\s+(.*)$/ : /^\s*[-*+]\s+(.*)$/;
    let indice = indiceInicial;

    while (indice < linhas.length) {
        const achado = linhas[indice].match(padraoItem);
        if (!achado) break;

        const item = document.createElement("li");
        aplicarMarcacaoInline(achado[1], item);
        lista.appendChild(item);
        indice += 1;
    }

    return { elemento: lista, proximoIndice: indice };
}

/**
 * Renderiza `texto` (Markdown) dentro de `destino`, criando os elementos um a
 * um. Não devolve HTML como string de propósito: assim não há caminho possível
 * entre o texto do modelo e a interpretação de HTML pelo navegador.
 */
function renderizarMarkdown(texto, destino) {
    const linhas = String(texto || "").split("\n");
    let indice = 0;

    while (indice < linhas.length) {
        const linha = linhas[indice];

        if (!linha.trim()) {
            indice += 1;
            continue;
        }

        // Tabela: linha com pipes seguida da linha separadora
        if (
            linha.trim().startsWith("|") &&
            indice + 1 < linhas.length &&
            ehSeparadorDeTabela(linhas[indice + 1])
        ) {
            const { elemento, proximoIndice } = montarTabela(linhas, indice);
            destino.appendChild(elemento);
            indice = proximoIndice;
            continue;
        }

        // Título: # até ######
        const tituloAchado = linha.match(/^\s*(#{1,6})\s+(.*)$/);
        if (tituloAchado) {
            const nivel = Math.min(tituloAchado[1].length + 2, 6); // h1 vira h3
            const titulo = document.createElement(`h${nivel}`);
            titulo.className = "md-titulo";
            aplicarMarcacaoInline(tituloAchado[2], titulo);
            destino.appendChild(titulo);
            indice += 1;
            continue;
        }

        // Separador: --- ou ***
        if (/^\s*([-*_])\1{2,}\s*$/.test(linha)) {
            destino.appendChild(document.createElement("hr"));
            indice += 1;
            continue;
        }

        // Lista não ordenada
        if (/^\s*[-*+]\s+/.test(linha)) {
            const { elemento, proximoIndice } = montarLista(linhas, indice, false);
            destino.appendChild(elemento);
            indice = proximoIndice;
            continue;
        }

        // Lista ordenada
        if (/^\s*\d+[.)]\s+/.test(linha)) {
            const { elemento, proximoIndice } = montarLista(linhas, indice, true);
            destino.appendChild(elemento);
            indice = proximoIndice;
            continue;
        }

        // Citação: > texto (agrupa linhas seguidas)
        if (/^\s*>\s?/.test(linha)) {
            const citacao = document.createElement("blockquote");
            citacao.className = "md-citacao";
            const conteudo = [];

            while (indice < linhas.length && /^\s*>\s?/.test(linhas[indice])) {
                conteudo.push(linhas[indice].replace(/^\s*>\s?/, ""));
                indice += 1;
            }

            renderizarMarkdown(conteudo.join("\n"), citacao);
            destino.appendChild(citacao);
            continue;
        }

        // Parágrafo: junta as linhas seguintes até uma linha em branco ou o
        // início de outro bloco.
        const paragrafo = document.createElement("p");
        paragrafo.className = "md-paragrafo";
        const pedacos = [];

        while (indice < linhas.length) {
            const atual = linhas[indice];
            const comecaOutroBloco =
                !atual.trim() ||
                /^\s*[-*+]\s+/.test(atual) ||
                /^\s*\d+[.)]\s+/.test(atual) ||
                /^\s*#{1,6}\s+/.test(atual) ||
                /^\s*>\s?/.test(atual) ||
                atual.trim().startsWith("|");

            if (comecaOutroBloco) break;

            pedacos.push(atual.trim());
            indice += 1;
        }

        aplicarMarcacaoInline(pedacos.join(" "), paragrafo);
        destino.appendChild(paragrafo);
    }
}
