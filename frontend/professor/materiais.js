const usuario = exigirAcesso("professor");

let turmas = [];
let turmaSelecionadaId = null;
// Guardadas ao carregar o seletor do topo; o formulário de publicação reusa a
// mesma lista para montar os checkboxes, sem buscar de novo.
let turmasDoProfessor = [];
let editandoId = null;

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();

    ligarPlaceholders();
    ligarNotificacoes();
    ligarFormulario();
    carregarTurmas();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = `Prof. ${nome}`;
}

function ligarPlaceholders() {
    document.querySelectorAll("[data-em-breve]").forEach((elemento) => {
        elemento.addEventListener("click", async (evento) => {
            evento.preventDefault();
            avisar(
                `${elemento.dataset.emBreve} ainda não faz parte desta versão.`,
                "Módulo em construção"
            );
        });
    });
}

async function carregarTurmas() {
    try {
        const resposta = await api("/turmas");
        const dados = await resposta.json();
        turmas = dados.turmas || [];
        turmasDoProfessor = turmas;

        const seletor = document.querySelector("#seletorTurma");
        const semTurmas = document.querySelector("#semTurmas");

        if (turmas.length === 0) {
            semTurmas.hidden = false;
            document.querySelector("#seletorTurmaCampo").hidden = true;
            document.querySelector("#botaoNovoMaterial").disabled = true;
            document.querySelector("#listaMateriais").innerHTML = "";
            document.querySelector("#materiaisVazio").hidden = true;
            return;
        }

        semTurmas.hidden = true;
        document.querySelector("#seletorTurmaCampo").hidden = false;
        document.querySelector("#botaoNovoMaterial").disabled = false;

        seletor.innerHTML = turmas
            .map((turma) => `<option value="${turma.id}">${turma.nome} · ${turma.semestre}</option>`)
            .join("");

        const parametroUrl = new URLSearchParams(window.location.search).get("turma");
        const turmaValida = turmas.some((turma) => String(turma.id) === parametroUrl);
        turmaSelecionadaId = turmaValida ? parametroUrl : String(turmas[0].id);
        seletor.value = turmaSelecionadaId;

        seletor.addEventListener("change", () => {
            turmaSelecionadaId = seletor.value;
            carregarMateriais();
        });

        carregarMateriais();
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
        document.querySelector("#semTurmas").hidden = false;
        document.querySelector("#semTurmas").textContent =
            "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

const RUTULOS_STATUS = { rascunho: "Rascunho", agendado: "Agendado", publicado: "Publicado" };
const RUTULOS_TIPO = { pdf: "PDF", documento: "Documento", video: "Vídeo", link: "Link" };

/** Ids das turmas marcadas no formulário de publicação. */
function turmasMarcadas() {
    return Array.from(document.querySelectorAll("#listaTurmasCheck input[data-turma]:checked"))
        .map((entrada) => Number(entrada.dataset.turma));
}

/**
 * Monta a lista de turmas com checkbox.
 *
 * `turmaPadrao` já vem marcada: quem abriu o formulário estando numa turma
 * espera publicar nela, e ter que marcar de novo seria um passo a mais para o
 * caso mais comum.
 */
function montarChecklistTurmas(turmas, turmaPadrao) {
    const lista = document.querySelector("#listaTurmasCheck");
    const dica = document.querySelector("#dicaTurmas");
    if (!lista) return;

    lista.innerHTML = "";

    if (turmas.length === 0) {
        dica.textContent = "Você ainda não tem turmas atribuídas.";
        return;
    }

    // "Selecionar todas" só faz sentido com mais de uma turma.
    if (turmas.length > 1) {
        const rotuloTodas = document.createElement("label");
        rotuloTodas.className = "turma-check turma-check--todas";

        const todas = document.createElement("input");
        todas.type = "checkbox";
        todas.id = "turmasTodas";
        todas.addEventListener("change", () => {
            lista.querySelectorAll("input[data-turma]").forEach((entrada) => {
                entrada.checked = todas.checked;
            });
            atualizarDicaTurmas();
        });

        const texto = document.createElement("span");
        texto.textContent = "Selecionar todas";

        rotuloTodas.appendChild(todas);
        rotuloTodas.appendChild(texto);
        lista.appendChild(rotuloTodas);
    }

    turmas.forEach((turma) => {
        const rotulo = document.createElement("label");
        rotulo.className = "turma-check";

        const entrada = document.createElement("input");
        entrada.type = "checkbox";
        entrada.dataset.turma = turma.id;
        entrada.checked = String(turma.id) === String(turmaPadrao);
        entrada.addEventListener("change", atualizarDicaTurmas);

        const texto = document.createElement("span");
        texto.textContent = `${turma.nome} · ${turma.semestre}`;

        rotulo.appendChild(entrada);
        rotulo.appendChild(texto);
        lista.appendChild(rotulo);
    });

    atualizarDicaTurmas();
}

function atualizarDicaTurmas() {
    const dica = document.querySelector("#dicaTurmas");
    const total = turmasMarcadas().length;

    if (!dica) return;

    if (total === 0) {
        dica.textContent = "Nenhuma turma marcada.";
    } else if (total === 1) {
        dica.textContent = "O material vai para 1 turma.";
    } else {
        dica.textContent = `O material será publicado em ${total} turmas.`;
    }

    // Mantém o "selecionar todas" coerente com o que está marcado.
    const todas = document.querySelector("#turmasTodas");
    if (todas) {
        const caixas = document.querySelectorAll("#listaTurmasCheck input[data-turma]");
        todas.checked = total === caixas.length && total > 0;
        todas.indeterminate = total > 0 && total < caixas.length;
    }
}

async function carregarMateriais() {
    const lista = document.querySelector("#listaMateriais");
    const vazio = document.querySelector("#materiaisVazio");

    try {
        const resposta = await api(`/materiais?turma_id=${turmaSelecionadaId}`);
        const dados = await resposta.json();
        const materiais = dados.materiais || [];

        lista.innerHTML = "";

        if (materiais.length === 0) {
            vazio.hidden = false;
            return;
        }
        vazio.hidden = true;

        materiais.forEach((material) => {
            lista.appendChild(criarLinhaMaterial(material));
        });
    } catch (erro) {
        console.error("Erro ao carregar materiais:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function criarLinhaMaterial(material) {
    const linha = document.createElement("article");
    linha.className = "cartao material-linha";

    const classificacao = [material.assunto, material.topico, material.aula, material.semestre]
        .filter(Boolean)
        .join(" · ");

    let referencia = "";
    if (material.tipo === "link" && material.link_url) {
        referencia = `<a href="${material.link_url}" target="_blank" rel="noopener">Abrir link</a>`;
    } else if (material.arquivo_nome) {
        // Não dá para usar <a href> aqui: navegação do navegador não envia o
        // header Authorization, e colocar o token na URL o deixaria gravado no
        // histórico e nos logs do servidor. O clique busca o arquivo
        // autenticado e abre a partir de um blob local.
        referencia = `<a href="#" data-arquivo-id="${material.id}">${material.arquivo_nome}</a>` +
            (podeVisualizar(material) ? ` · <a href="#" data-visualizar-id="${material.id}">visualizar</a>` : "");
    }

    linha.innerHTML = `
        <div class="material-linha-info">
            <div class="material-linha-topo">
                <span class="badge-tipo">${RUTULOS_TIPO[material.tipo] ?? material.tipo}</span>
                <span class="badge-status badge-status--${material.status}">${RUTULOS_STATUS[material.status]}</span>
            </div>
            <h3>${material.titulo}</h3>
            ${classificacao ? `<p class="material-classificacao">${classificacao}</p>` : ""}
            ${material.descricao ? `<p class="material-descricao">${material.descricao}</p>` : ""}
            ${referencia ? `<p class="material-referencia">${referencia}</p>` : ""}
        </div>
        <div class="material-linha-acoes">
            <button type="button" class="acao" data-acao-editar>Editar</button>
            <button type="button" class="acao acao--perigo" data-acao-excluir>Excluir</button>
        </div>
    `;

    linha.querySelector("[data-acao-editar]").addEventListener("click", () => abrirFormulario(material));
    linha.querySelector("[data-acao-excluir]").addEventListener("click", () => excluirMaterial(material));

    const linkVisualizar = linha.querySelector("[data-visualizar-id]");
    if (linkVisualizar) {
        linkVisualizar.addEventListener("click", (evento) => {
            evento.preventDefault();
            abrirVisualizador(material, `/materiais/${material.id}/arquivo`);
        });
    }

    const linkArquivo = linha.querySelector("[data-arquivo-id]");
    if (linkArquivo) {
        linkArquivo.addEventListener("click", (evento) => {
            evento.preventDefault();
            baixarArquivo(linkArquivo.dataset.arquivoId, material.arquivo_nome);
        });
    }

    return linha;
}

/**
 * Baixa o arquivo do material passando pelo helper autenticado.
 *
 * O download não pode ser um link direto: o navegador não manda o header
 * Authorization numa navegação, e o token não deve viajar na URL. Então o
 * arquivo vem por fetch e é aberto a partir de um blob local.
 */
async function baixarArquivo(materialId, nomeArquivo) {
    try {
        const resposta = await api(`/materiais/${materialId}/arquivo`);

        if (!resposta.ok) {
            await avisarErro("Não foi possível baixar o arquivo.");
            return;
        }

        const blob = await resposta.blob();
        const url = URL.createObjectURL(blob);

        const ancora = document.createElement("a");
        ancora.href = url;
        ancora.download = nomeArquivo || "material";
        document.body.appendChild(ancora);
        ancora.click();
        ancora.remove();

        // Libera a memória do blob depois que o navegador iniciou o download.
        setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (erro) {
        console.error("Erro ao baixar arquivo:", erro);
    }
}

function ligarFormulario() {
    const tipoSelect = document.querySelector("#materialTipo");
    const campoArquivo = document.querySelector("#campoArquivo");
    const campoLink = document.querySelector("#campoLink");

    tipoSelect.addEventListener("change", () => {
        const ehLink = tipoSelect.value === "link";
        campoArquivo.hidden = ehLink;
        campoLink.hidden = !ehLink;
    });

    document.querySelector("#botaoNovoMaterial").addEventListener("click", () => abrirFormulario(null));
    document.querySelector("#botaoCancelarMaterial").addEventListener("click", fecharFormulario);

    document.querySelector("#formularioMaterial").addEventListener("submit", async (evento) => {
        evento.preventDefault();
        const publicar = evento.submitter?.dataset.acao === "publicar";
        await salvarMaterial(publicar);
    });
}

function abrirFormulario(material) {
    const cartao = document.querySelector("#formularioMaterialCartao");
    const titulo = document.querySelector("#formularioMaterialTitulo");
    const tipoSelect = document.querySelector("#materialTipo");
    const arquivoInput = document.querySelector("#materialArquivo");
    const mensagem = document.querySelector("#materialMensagem");

    mensagem.textContent = "";
    document.querySelector("#formularioMaterial").reset();

    editandoId = material ? material.id : null;
    titulo.textContent = material ? "Editar material" : "Novo material";

    tipoSelect.disabled = Boolean(material);
    arquivoInput.disabled = Boolean(material);

    // A escolha de turmas só existe ao criar: editar altera o registro daquela
    // turma, e mover um material entre turmas seria outra operação.
    const campoTurmas = document.querySelector("#campoTurmasPublicacao");
    if (campoTurmas) {
        campoTurmas.hidden = Boolean(material);
        if (!material) montarChecklistTurmas(turmasDoProfessor, turmaSelecionadaId);
    }

    if (material) {
        document.querySelector("#materialTitulo").value = material.titulo;
        document.querySelector("#materialDescricao").value = material.descricao || "";
        tipoSelect.value = material.tipo;
        document.querySelector("#materialLink").value = material.link_url || "";
        document.querySelector("#materialAssunto").value = material.assunto || "";
        document.querySelector("#materialTopico").value = material.topico || "";
        document.querySelector("#materialAula").value = material.aula || "";
        document.querySelector("#materialSemestre").value = material.semestre || "";
        document.querySelector("#materialDataLiberacao").value = paraDatetimeLocal(material.data_liberacao);

        document.querySelector("#campoArquivo").hidden = material.tipo === "link";
        document.querySelector("#campoLink").hidden = material.tipo !== "link";
    } else {
        document.querySelector("#campoArquivo").hidden = false;
        document.querySelector("#campoLink").hidden = true;
    }

    cartao.hidden = false;
    cartao.scrollIntoView({ behavior: "smooth", block: "start" });
}

function fecharFormulario() {
    document.querySelector("#formularioMaterialCartao").hidden = true;
    document.querySelector("#formularioMaterial").reset();
    editandoId = null;
}

function paraDatetimeLocal(isoString) {
    if (!isoString) return "";
    const data = new Date(isoString);
    if (Number.isNaN(data.getTime())) return "";
    const deslocamento = data.getTimezoneOffset();
    const local = new Date(data.getTime() - deslocamento * 60000);
    return local.toISOString().slice(0, 16);
}

function lerArquivoComoBase64(arquivo) {
    return new Promise((resolve, reject) => {
        const leitor = new FileReader();
        leitor.onload = () => resolve(leitor.result);
        leitor.onerror = () => reject(leitor.error);
        leitor.readAsDataURL(arquivo);
    });
}

async function salvarMaterial(publicar) {
    const mensagem = document.querySelector("#materialMensagem");
    mensagem.className = "formulario-mensagem";
    mensagem.textContent = "Salvando...";

    const titulo = document.querySelector("#materialTitulo").value.trim();
    const descricao = document.querySelector("#materialDescricao").value.trim();
    const tipo = document.querySelector("#materialTipo").value;
    const link = document.querySelector("#materialLink").value.trim();
    const assunto = document.querySelector("#materialAssunto").value.trim();
    const topico = document.querySelector("#materialTopico").value.trim();
    const aula = document.querySelector("#materialAula").value.trim();
    const semestre = document.querySelector("#materialSemestre").value.trim();
    const dataLiberacaoCampo = document.querySelector("#materialDataLiberacao").value;
    const dataLiberacao = dataLiberacaoCampo ? new Date(dataLiberacaoCampo).toISOString() : null;
    const arquivoInput = document.querySelector("#materialArquivo");

    try {
        if (editandoId) {
            const corpo = {
                titulo, descricao, assunto, topico, aula, semestre,
                rascunho: !publicar,
                data_liberacao: dataLiberacao,
            };
            if (tipo === "link") corpo.link_url = link;

            const resposta = await api(`/materiais/${editandoId}`, {
                method: "PUT",
                body: JSON.stringify(corpo),
            });
            const dados = await resposta.json();
            mensagem.textContent = dados.mensagem;

            if (dados.sucesso) {
                mensagem.classList.add("formulario-mensagem--sucesso");
                fecharFormulario();
                carregarMateriais();
                carregarTurmas();
            }
            return;
        }

        let arquivoBase64 = null;
        let arquivoNome = null;

        if (tipo !== "link") {
            const arquivo = arquivoInput.files[0];
            if (!arquivo) {
                mensagem.textContent = "Selecione um arquivo.";
                return;
            }
            if (arquivo.size > 15 * 1024 * 1024) {
                mensagem.textContent = "O arquivo passa do limite de 15MB.";
                return;
            }
            arquivoBase64 = await lerArquivoComoBase64(arquivo);
            arquivoNome = arquivo.name;
        }

        const turmasEscolhidas = turmasMarcadas();

        if (turmasEscolhidas.length === 0) {
            mensagem.textContent = "Escolha pelo menos uma turma.";
            return;
        }

        const resposta = await api("/materiais", {
            method: "POST",
            body: JSON.stringify({
                turma_ids: turmasEscolhidas,
                titulo, descricao, tipo, assunto, topico, aula, semestre,
                rascunho: !publicar,
                data_liberacao: dataLiberacao,
                link_url: tipo === "link" ? link : null,
                arquivo_base64: arquivoBase64,
                arquivo_nome: arquivoNome,
            }),
        });

        const dados = await resposta.json();
        mensagem.textContent = dados.mensagem;

        if (dados.sucesso) {
            mensagem.classList.add("formulario-mensagem--sucesso");
            fecharFormulario();
            carregarMateriais();
            carregarTurmas();
        }
    } catch (erro) {
        console.error("Erro ao salvar material:", erro);
        mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

async function excluirMaterial(material) {
    const confirmou = await confirmar(
        `Excluir "${material.titulo}"?
O arquivo e os trechos indexados para o assistente saem junto. Não há como desfazer.`,
        { titulo: "Excluir material", rotulo: "Excluir", perigo: true }
    );
    if (!confirmou) return;

    try {
        const resposta = await api(`/materiais/${material.id}`, { method: "DELETE" });
        const dados = await resposta.json();

        if (dados.sucesso) {
            carregarMateriais();
            carregarTurmas();
        } else {
            await avisarErro(dados.mensagem);
        }
    } catch (erro) {
        console.error("Erro ao excluir material:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
