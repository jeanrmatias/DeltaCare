/**
 * Favoritar e anotar, onde quer que o material apareça.
 *
 * Três telas usam isto — Materiais, Favoritos e Anotações —, e o mesmo gesto
 * tem que se comportar igual nas três. Uma cópia por tela seria três lugares
 * para a estrela divergir.
 *
 * Anotação é privada: a tela diz isso ao lado do campo, porque o aluno só
 * escreve com franqueza ("não entendi nada desta aula") se souber que ninguém
 * mais lê. E é verdade no servidor — não existe rota de professor ou de
 * administração para anotações (regras/anotacoes.py).
 */

// =========================================================================
// Favorito
// =========================================================================

/** Botão de estrela. `aoMudar(material)` é chamado depois que o servidor confirma. */
function botaoFavorito(material, aoMudar) {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "botao-favorito";

    const pintar = () => {
        botao.textContent = material.favorito ? "★" : "☆";
        botao.classList.toggle("botao-favorito--ativo", !!material.favorito);
        botao.setAttribute("aria-pressed", String(!!material.favorito));
        botao.title = material.favorito ? "Tirar dos favoritos" : "Guardar nos favoritos";
        botao.setAttribute("aria-label", botao.title);
    };
    pintar();

    botao.addEventListener("click", async () => {
        botao.disabled = true;
        try {
            // A estrela só muda depois da resposta: acender antes e apagar se
            // falhar faria o aluno achar que guardou o que não guardou.
            const resposta = material.favorito
                ? await api(`/aluno/favoritos/${material.id}`, { method: "DELETE" })
                : await api(`/aluno/favoritos/${material.id}`, { method: "PUT" });
            const dados = await resposta.json();

            if (!dados.sucesso) {
                await avisarErro(dados.mensagem || "Não foi possível mudar o favorito.");
                return;
            }
            material.favorito = dados.favorito;
            pintar();
            if (aoMudar) aoMudar(material);
        } catch (erro) {
            console.error("Erro no favorito:", erro);
            await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
        } finally {
            botao.disabled = false;
        }
    });

    return botao;
}

// =========================================================================
// Anotações
// =========================================================================

function formatarDataCurta(iso) {
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
}

/** Uma anotação, com as ações de editar e apagar. */
function montarAnotacao(anotacao, { aoEditar, aoApagar, mostrarMaterial = false }) {
    const item = document.createElement("article");
    item.className = "anotacao";

    if (mostrarMaterial) {
        const origem = document.createElement("p");
        origem.className = "anotacao-origem";
        origem.textContent = anotacao.material_disponivel
            ? anotacao.material_titulo
            // Material apagado pelo professor: a anotação fica, e diz de onde era.
            : `${anotacao.material_titulo} (material removido)`;
        item.appendChild(origem);
    }

    if (anotacao.trecho) {
        const trecho = document.createElement("blockquote");
        trecho.className = "anotacao-trecho";
        trecho.textContent = anotacao.trecho;
        item.appendChild(trecho);
    }

    const texto = document.createElement("p");
    texto.className = "anotacao-texto";
    texto.textContent = anotacao.texto;
    item.appendChild(texto);

    const rodape = document.createElement("div");
    rodape.className = "anotacao-rodape";

    const data = document.createElement("span");
    data.textContent = formatarDataCurta(anotacao.atualizado_em);
    rodape.appendChild(data);

    const editar = document.createElement("button");
    editar.type = "button";
    editar.className = "acao acao--discreta";
    editar.textContent = "Editar";
    editar.addEventListener("click", () => aoEditar(anotacao));
    rodape.appendChild(editar);

    const apagar = document.createElement("button");
    apagar.type = "button";
    apagar.className = "acao acao--discreta";
    apagar.textContent = "Apagar";
    apagar.addEventListener("click", () => aoApagar(anotacao));
    rodape.appendChild(apagar);

    item.appendChild(rodape);
    return item;
}

/**
 * Formulário de anotação num <dialog>. Serve para criar (sem `anotacao`) e
 * para editar. Resolve com a anotação salva, ou null se o aluno fechou.
 */
function formularioAnotacao({ material, anotacao }) {
    return new Promise((resolver) => {
        const dialogo = document.createElement("dialog");
        dialogo.className = "painel-anotacoes";

        const titulo = document.createElement("h2");
        titulo.textContent = anotacao ? "Editar anotação" : `Nova anotação · ${material.titulo}`;
        dialogo.appendChild(titulo);

        const privacidade = document.createElement("p");
        privacidade.className = "campo-dica";
        privacidade.textContent = "Só você vê suas anotações. Nem o professor, nem a coordenação.";
        dialogo.appendChild(privacidade);

        const rotuloTrecho = document.createElement("label");
        rotuloTrecho.textContent = "Trecho do material (opcional)";
        const campoTrecho = document.createElement("textarea");
        campoTrecho.rows = 2;
        campoTrecho.maxLength = 1000;
        campoTrecho.placeholder = "Cole aqui a passagem a que a anotação se refere";
        campoTrecho.value = anotacao ? anotacao.trecho : "";
        rotuloTrecho.appendChild(campoTrecho);
        dialogo.appendChild(rotuloTrecho);

        const rotuloTexto = document.createElement("label");
        rotuloTexto.textContent = "Anotação";
        const campoTexto = document.createElement("textarea");
        campoTexto.rows = 5;
        campoTexto.maxLength = 5000;
        campoTexto.value = anotacao ? anotacao.texto : "";
        rotuloTexto.appendChild(campoTexto);
        dialogo.appendChild(rotuloTexto);

        const mensagem = document.createElement("p");
        mensagem.className = "formulario-mensagem";
        dialogo.appendChild(mensagem);

        const acoes = document.createElement("div");
        acoes.className = "painel-anotacoes-acoes";
        const cancelar = document.createElement("button");
        cancelar.type = "button";
        cancelar.className = "acao";
        cancelar.textContent = "Cancelar";
        const salvar = document.createElement("button");
        salvar.type = "button";
        salvar.className = "acao acao--primaria";
        salvar.textContent = "Salvar";
        acoes.appendChild(cancelar);
        acoes.appendChild(salvar);
        dialogo.appendChild(acoes);

        const fechar = (valor) => {
            dialogo.close();
            dialogo.remove();
            resolver(valor);
        };

        cancelar.addEventListener("click", () => fechar(null));
        dialogo.addEventListener("cancel", () => fechar(null));

        salvar.addEventListener("click", async () => {
            const corpo = { texto: campoTexto.value.trim(), trecho: campoTrecho.value.trim() };
            if (!corpo.texto) {
                mensagem.textContent = "Escreva a anotação.";
                return;
            }
            salvar.disabled = true;
            try {
                const resposta = anotacao
                    ? await api(`/aluno/anotacoes/${anotacao.id}`, { method: "PUT", body: JSON.stringify(corpo) })
                    : await api("/aluno/anotacoes", {
                        method: "POST",
                        body: JSON.stringify({ ...corpo, material_id: material.id }),
                    });
                const dados = await resposta.json();
                if (!dados.sucesso) {
                    mensagem.textContent = dados.mensagem || "Não foi possível salvar.";
                    return;
                }
                fechar(dados.anotacao);
            } catch (erro) {
                console.error("Erro ao salvar anotação:", erro);
                mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
            } finally {
                salvar.disabled = false;
            }
        });

        document.body.appendChild(dialogo);
        dialogo.showModal();
        campoTexto.focus();
    });
}

/** Confirma e apaga. Resolve true se apagou. */
async function apagarAnotacao(anotacao) {
    const confirmou = await confirmar("Apagar esta anotação? Não dá para desfazer.", {
        titulo: "Apagar anotação",
        rotulo: "Apagar",
        perigo: true,
    });
    if (!confirmou) return false;

    try {
        const resposta = await api(`/aluno/anotacoes/${anotacao.id}`, { method: "DELETE" });
        const dados = await resposta.json();
        if (!dados.sucesso) {
            await avisarErro(dados.mensagem || "Não foi possível apagar.");
            return false;
        }
        return true;
    } catch (erro) {
        console.error("Erro ao apagar anotação:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
        return false;
    }
}

/**
 * As anotações de um material, num <dialog>: a lista e o botão de escrever.
 * `aoMudar(total)` recebe o novo total, para a tela atualizar o contador.
 */
async function abrirAnotacoes(material, aoMudar) {
    const dialogo = document.createElement("dialog");
    dialogo.className = "painel-anotacoes";

    const topo = document.createElement("div");
    topo.className = "painel-anotacoes-topo";
    const titulo = document.createElement("h2");
    titulo.textContent = `Anotações · ${material.titulo}`;
    const fecharBotao = document.createElement("button");
    fecharBotao.type = "button";
    fecharBotao.className = "acao";
    fecharBotao.textContent = "Fechar";
    topo.appendChild(titulo);
    topo.appendChild(fecharBotao);
    dialogo.appendChild(topo);

    const nova = document.createElement("button");
    nova.type = "button";
    nova.className = "acao acao--primaria";
    nova.textContent = "Nova anotação";
    dialogo.appendChild(nova);

    const lista = document.createElement("div");
    lista.className = "anotacoes-lista";
    dialogo.appendChild(lista);

    let total = 0;

    async function recarregar() {
        lista.textContent = "Carregando...";
        try {
            const resposta = await api(`/aluno/anotacoes?material_id=${material.id}`);
            const dados = await resposta.json();
            const anotacoes = dados.anotacoes || [];
            total = anotacoes.length;
            lista.textContent = "";

            if (!anotacoes.length) {
                const vazio = document.createElement("p");
                vazio.className = "estado-vazio";
                vazio.textContent = "Nenhuma anotação neste material ainda.";
                lista.appendChild(vazio);
            }

            anotacoes.forEach((anotacao) => lista.appendChild(montarAnotacao(anotacao, {
                aoEditar: async (alvo) => {
                    if (await formularioAnotacao({ material, anotacao: alvo })) recarregar();
                },
                aoApagar: async (alvo) => {
                    if (await apagarAnotacao(alvo)) recarregar();
                },
            })));
            if (aoMudar) aoMudar(total);
        } catch (erro) {
            console.error("Erro ao carregar anotações:", erro);
            lista.textContent = "Não foi possível carregar as anotações.";
        }
    }

    nova.addEventListener("click", async () => {
        if (await formularioAnotacao({ material })) recarregar();
    });

    const fechar = () => {
        dialogo.close();
        dialogo.remove();
    };
    fecharBotao.addEventListener("click", fechar);
    dialogo.addEventListener("cancel", fechar);

    document.body.appendChild(dialogo);
    dialogo.showModal();
    recarregar();
}
