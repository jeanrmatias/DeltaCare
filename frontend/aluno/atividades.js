/**
 * Atividades na visão do aluno: resolver, entregar e ver a nota.
 *
 * Duas coisas moldaram esta tela:
 *
 * **O progresso é salvo, não perdido.** O aluno pode fechar a aba no meio de
 * um quiz e voltar depois. O que ele marcou fica guardado no servidor como
 * entrega ainda não enviada.
 *
 * **O prazo avisa, não impede.** Passado o prazo, o botão continua lá e a tela
 * diz que a entrega vai constar como atrasada. Quem decide o que fazer com o
 * atraso é o professor — a plataforma só informa.
 */

const usuario = exigirAcesso("aluno");

let turmas = [];
let turmaSelecionadaId = null;
let atividades = [];
// Atividade aberta no painel, com as questões e o que o aluno já respondeu.
let aberta = null;
let respostas = null;
// O arquivo escolhido nesta sessão, ainda não enviado. Fora de `respostas`
// porque `respostas` é salvo como progresso a cada rascunho, e mandar um PDF
// de 15MB a cada tecla digitada não é opção.
let arquivoEscolhido = null;

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    ligarPainel();
    carregarTurmas();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function formatarData(iso) {
    if (!iso) return "";
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleString("pt-BR", {
        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
}

function prazoVencido(iso) {
    if (!iso) return false;
    const prazo = new Date(iso);
    return !Number.isNaN(prazo.getTime()) && prazo < new Date();
}

// =========================================================================
// Turmas e listagem
// =========================================================================

async function carregarTurmas() {
    try {
        const resposta = await api("/aluno/turmas");
        const dados = await resposta.json();
        turmas = dados.turmas || [];

        const seletor = document.querySelector("#seletorTurma");

        if (turmas.length === 0) {
            document.querySelector("#seletorTurmaCampo").hidden = true;
            document.querySelector("#vazio").hidden = false;
            document.querySelector("#vazio").textContent =
                "Você ainda não está matriculado em nenhuma turma.";
            return;
        }

        seletor.innerHTML = "";

        const todas = document.createElement("option");
        todas.value = "";
        todas.textContent = "Todas as turmas";
        seletor.appendChild(todas);

        turmas.forEach((turma) => {
            const opcao = document.createElement("option");
            opcao.value = turma.id;
            opcao.textContent = `${turma.nome} · ${turma.semestre}`;
            seletor.appendChild(opcao);
        });

        seletor.onchange = () => {
            turmaSelecionadaId = seletor.value ? Number(seletor.value) : null;
            carregarAtividades();
        };

        carregarAtividades();
    } catch (erro) {
        console.error("Erro ao carregar turmas:", erro);
        document.querySelector("#vazio").hidden = false;
        document.querySelector("#vazio").textContent =
            "Não foi possível conectar ao servidor. Verifique se o backend está no ar.";
    }
}

async function carregarAtividades() {
    const lista = document.querySelector("#lista");
    const vazio = document.querySelector("#vazio");
    const resumo = document.querySelector("#resumoAtividades");

    try {
        const caminho = turmaSelecionadaId
            ? `/aluno/atividades?turma_id=${turmaSelecionadaId}`
            : "/aluno/atividades";
        const resposta = await api(caminho);
        const dados = await resposta.json();
        atividades = dados.atividades || [];

        lista.innerHTML = "";
        vazio.hidden = atividades.length > 0;
        resumo.hidden = atividades.length === 0;

        document.querySelector("#statPendentes").textContent =
            atividades.filter((a) => a.situacao === "pendente" || a.situacao === "em andamento").length;
        document.querySelector("#statEntregues").textContent =
            atividades.filter((a) => a.situacao === "entregue").length;
        document.querySelector("#statCorrigidas").textContent =
            atividades.filter((a) => a.situacao === "corrigida").length;

        atividades.forEach((atividade) => lista.appendChild(criarLinha(atividade)));
    } catch (erro) {
        console.error("Erro ao carregar atividades:", erro);
        lista.innerHTML = "";
        resumo.hidden = true;
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

const SELO_SITUACAO = {
    pendente: { classe: "rascunho", texto: "A fazer" },
    "em andamento": { classe: "agendado", texto: "Em andamento" },
    entregue: { classe: "agendado", texto: "Entregue" },
    corrigida: { classe: "publicado", texto: "Corrigida" },
};

function criarLinha(atividade) {
    const linha = document.createElement("article");
    linha.className = "cartao material-linha";

    const selo = SELO_SITUACAO[atividade.situacao] || SELO_SITUACAO.pendente;
    const classificacao = [atividade.turma_nome, atividade.assunto, atividade.topico]
        .filter(Boolean).join(" · ");

    const detalhes = [];
    if (atividade.tipo === "objetiva") detalhes.push(`${atividade.total_questoes} questão(ões)`);
    detalhes.push(`vale ${atividade.pontos}`);

    let aviso = "";
    if (atividade.prazo) {
        const vencido = prazoVencido(atividade.prazo);
        const entregue = atividade.situacao === "entregue" || atividade.situacao === "corrigida";

        if (atividade.atrasada) {
            aviso = `<p class="atividade-pendencia">Entregue com atraso</p>`;
        } else if (vencido && !entregue) {
            aviso = `<p class="atividade-pendencia">Prazo venceu em ${formatarData(atividade.prazo)} — ainda dá para entregar, constará como atrasada</p>`;
        } else {
            aviso = `<p class="atividade-acompanhamento">Prazo: ${formatarData(atividade.prazo)}</p>`;
        }
    }

    const nota = atividade.nota !== null && atividade.nota !== undefined
        ? `<p class="atividade-nota"><strong>Nota ${atividade.nota}</strong> de ${atividade.pontos}</p>`
        : "";

    const devolutiva = atividade.devolutiva
        ? `<p class="entrega-devolutiva">${esc(atividade.devolutiva)}</p>`
        : "";

    linha.innerHTML = `
        <div class="material-linha-info">
            <div class="material-linha-topo">
                <span class="badge-tipo">${atividade.tipo === "objetiva" ? "Objetiva" : "Dissertativa"}</span>
                <span class="badge-status badge-status--${selo.classe}">${selo.texto}</span>
            </div>
            <h3>${esc(atividade.titulo)}</h3>
            ${classificacao ? `<p class="material-classificacao">${esc(classificacao)}</p>` : ""}
            <p class="material-descricao">${esc(detalhes.join(" · "))}</p>
            ${aviso}
            ${nota}
            ${devolutiva}
        </div>
        <div class="material-linha-acoes">
            <button type="button" class="acao acao--primaria" data-abrir>
                ${atividade.situacao === "pendente" ? "Começar"
                  : atividade.situacao === "em andamento" ? "Continuar"
                  : "Ver"}
            </button>
        </div>
    `;

    linha.querySelector("[data-abrir]").addEventListener("click", () => abrirAtividade(atividade));
    return linha;
}

// =========================================================================
// Painel de resolução
// =========================================================================

function ligarPainel() {
    document.querySelector("#fecharAtividade").addEventListener("click", () => {
        document.querySelector("#painelAtividade").close();
    });
    document.querySelector("#botaoSalvarProgresso").addEventListener("click", () => enviar(false));
    document.querySelector("#botaoEntregar").addEventListener("click", () => enviar(true));
}

async function abrirAtividade(atividade) {
    const painel = document.querySelector("#painelAtividade");
    const corpo = document.querySelector("#atividadeCorpo");

    document.querySelector("#atividadeTitulo").textContent = atividade.titulo;
    document.querySelector("#atividadeDetalhe").textContent =
        [atividade.turma_nome, `vale ${atividade.pontos}`,
         atividade.prazo ? `prazo ${formatarData(atividade.prazo)}` : ""]
            .filter(Boolean).join(" · ");

    corpo.innerHTML = "<p class='visualizador-carregando'>Carregando...</p>";
    limparMensagem();
    painel.showModal();

    try {
        const resposta = await api(`/aluno/atividades/${atividade.id}`);
        const dados = await resposta.json();

        if (!dados.sucesso) {
            corpo.innerHTML = `<p class="estado-vazio">${esc(dados.mensagem)}</p>`;
            return;
        }

        aberta = dados;
        desenharAtividade(dados);
    } catch (erro) {
        console.error("Erro ao abrir atividade:", erro);
        corpo.innerHTML = "<p class='estado-vazio'>Não foi possível carregar a atividade.</p>";
    }
}

function desenharAtividade(dados) {
    const corpo = document.querySelector("#atividadeCorpo");
    const rodape = document.querySelector("#atividadeRodape");
    const entregue = Boolean(dados.entrega.enviado_em);

    corpo.innerHTML = "";

    if (dados.atividade.enunciado) {
        const enunciado = document.createElement("p");
        enunciado.className = "atividade-enunciado";
        enunciado.textContent = dados.atividade.enunciado;
        corpo.appendChild(enunciado);
    }

    if (dados.atividade.tipo === "objetiva") {
        respostas = Array.isArray(dados.entrega.respostas)
            ? [...dados.entrega.respostas]
            : new Array(dados.questoes.length).fill(null);

        dados.questoes.forEach((questao, indice) => {
            corpo.appendChild(criarQuestao(questao, indice, entregue));
        });
    } else {
        respostas = typeof dados.entrega.respostas === "string" ? dados.entrega.respostas : "";

        const campo = document.createElement("textarea");
        campo.className = "atividade-resposta";
        campo.placeholder = "Escreva sua resposta";
        campo.value = respostas;
        campo.disabled = entregue;
        campo.addEventListener("input", () => {
            respostas = campo.value;
        });
        corpo.appendChild(campo);
    }

    if (dados.atividade.anexo && dados.atividade.anexo !== "nenhum" && !entregue) {
        corpo.appendChild(criarSeletorDeArquivo(dados.atividade.anexo));
    }

    // Entregue não volta atrás: o aluno vê o que mandou e a devolutiva.
    rodape.hidden = entregue;

    if (entregue) {
        const resultado = document.createElement("div");
        resultado.className = "atividade-resultado";

        const temNota = dados.entrega.nota !== null && dados.entrega.nota !== undefined;
        resultado.innerHTML = `
            <p><strong>Entregue</strong> em ${formatarData(dados.entrega.enviado_em)}
               ${dados.entrega.atrasada ? `<span class="atividade-pendencia">· com atraso</span>` : ""}</p>
            ${temNota
                ? `<p class="atividade-nota"><strong>Nota ${dados.entrega.nota}</strong> de ${dados.atividade.pontos}</p>`
                : `<p>Aguardando correção do professor.</p>`}
            ${dados.entrega.devolutiva
                ? `<p class="entrega-devolutiva">${esc(dados.entrega.devolutiva)}</p>`
                : ""}
        `;

        // O aluno consegue rever o que entregou. Sem isto ele mandaria o
        // arquivo e nunca teria como confirmar que foi o certo.
        //
        // Botão com download autenticado, e não um link: a navegação do
        // navegador não envia o token, e o link direto respondia 401.
        if (dados.entrega.arquivo_nome && dados.entrega.entrega_id) {
            const link = document.createElement("button");
            link.type = "button";
            link.className = "entrega-anexo";
            link.textContent = `Anexo enviado: ${dados.entrega.arquivo_nome}`;
            link.addEventListener("click", () => baixarAnexoDaEntrega(dados.entrega));
            resultado.appendChild(link);
        }

        corpo.appendChild(resultado);
    } else if (prazoVencido(dados.atividade.prazo)) {
        mostrarMensagem("O prazo já venceu. A entrega será registrada como atrasada.");
    }
}

function criarQuestao(questao, indice, bloqueada) {
    const bloco = document.createElement("div");
    bloco.className = "questao-aluno";

    const alternativas = questao.alternativas.map((texto, posicao) => `
        <label class="questao-opcao">
            <input type="radio" name="q${indice}" value="${posicao}"
                   ${respostas[indice] === posicao ? "checked" : ""}
                   ${bloqueada ? "disabled" : ""}>
            <span>${esc(texto)}</span>
        </label>
    `).join("");

    bloco.innerHTML = `
        <p class="questao-pergunta"><strong>${indice + 1}.</strong> ${esc(questao.enunciado)}</p>
        <div class="questao-opcoes">${alternativas}</div>
    `;

    bloco.querySelectorAll("input[type=radio]").forEach((radio) => {
        radio.addEventListener("change", () => {
            respostas[indice] = Number(radio.value);
        });
    });

    return bloco;
}

function limparMensagem() {
    const mensagem = document.querySelector("#atividadeMensagem");
    mensagem.textContent = "";
    mensagem.className = "formulario-mensagem";
}

function mostrarMensagem(texto, sucesso = false) {
    const mensagem = document.querySelector("#atividadeMensagem");
    mensagem.textContent = texto;
    mensagem.className = "formulario-mensagem" + (sucesso ? " formulario-mensagem--sucesso" : "");
}

/**
 * Campo de arquivo da entrega.
 *
 * O aviso de limite fica escrito na tela, e não só na recusa do servidor: o
 * aluno descobrir os 15MB depois de esperar o upload de um vídeo é o tipo de
 * frustração que dá para evitar com uma linha de texto.
 */
function criarSeletorDeArquivo(anexo) {
    arquivoEscolhido = null;

    const bloco = document.createElement("div");
    bloco.className = "campo entrega-anexo-campo";

    const rotulo = document.createElement("label");
    rotulo.textContent = anexo === "obrigatorio"
        ? "Arquivo da entrega (obrigatório)"
        : "Arquivo da entrega (opcional)";
    bloco.appendChild(rotulo);

    const campo = document.createElement("input");
    campo.type = "file";
    campo.accept = ".pdf,.doc,.docx,.odt,.txt,.rtf,.png,.jpg,.jpeg,.webp,.xlsx,.csv,.ppt,.pptx,.odp";
    bloco.appendChild(campo);

    const dica = document.createElement("span");
    dica.className = "campo-dica";
    dica.textContent = "Até 15MB. PDF, documento, imagem, planilha ou apresentação.";
    bloco.appendChild(dica);

    campo.addEventListener("change", () => {
        const arquivo = campo.files && campo.files[0];
        if (!arquivo) {
            arquivoEscolhido = null;
            return;
        }

        // Barrado aqui **e** no servidor. Aqui é cortesia; a regra é lá, porque
        // o cliente é do aluno e o servidor não pode confiar nele.
        if (arquivo.size > 15 * 1024 * 1024) {
            arquivoEscolhido = null;
            campo.value = "";
            mostrarMensagem(`"${arquivo.name}" passa de 15MB. Escolha um arquivo menor.`);
            return;
        }

        const leitor = new FileReader();
        leitor.onload = () => {
            arquivoEscolhido = { nome: arquivo.name, base64: leitor.result };
            mostrarMensagem(`Anexo pronto: ${arquivo.name}`, true);
        };
        leitor.onerror = () => {
            arquivoEscolhido = null;
            mostrarMensagem("Não foi possível ler o arquivo. Tente escolher de novo.");
        };
        leitor.readAsDataURL(arquivo);
    });

    return bloco;
}

async function enviar(definitivo) {
    if (!aberta) return;

    const anexo = aberta.atividade.anexo || "nenhum";

    if (definitivo) {
        // Recusa antes de confirmar: o servidor também recusa, mas descobrir
        // isso depois de dizer "Entregar" é um passo a mais para nada.
        if (anexo === "obrigatorio" && !arquivoEscolhido) {
            mostrarMensagem("Esta atividade exige um arquivo. Escolha o arquivo antes de entregar.");
            return;
        }

        const objetiva = aberta.atividade.tipo === "objetiva";
        // Com anexo obrigatório o documento é a entrega, e o texto é comentário
        // — cobrar "resposta em branco" ali seria falso alarme.
        const faltando = objetiva
            ? respostas.filter((r) => r === null || r === undefined).length
            : (String(respostas).trim() || anexo === "obrigatorio" ? 0 : 1);

        const texto = faltando > 0
            ? `Você deixou ${faltando} ${objetiva ? "questão(ões) sem responder" : "a resposta em branco"}. Entregar assim mesmo?`
            : "Depois de entregar não dá para alterar. Confirmar?";

        const confirmou = await confirmar(texto, {
            titulo: "Entregar atividade",
            rotulo: "Entregar",
        });
        if (!confirmou) return;
    }

    const caminho = definitivo
        ? `/aluno/atividades/${aberta.atividade.id}/entrega`
        : `/aluno/atividades/${aberta.atividade.id}/progresso`;

    const corpo = { respostas };

    // Só vai junto na entrega definitiva. No progresso salvo seria reenviar o
    // arquivo inteiro a cada clique em "Salvar".
    if (definitivo && arquivoEscolhido) {
        corpo.arquivo_base64 = arquivoEscolhido.base64;
        corpo.arquivo_nome = arquivoEscolhido.nome;
    }

    try {
        const resposta = await api(caminho, {
            method: "POST",
            body: JSON.stringify(corpo),
        });
        const dados = await resposta.json();

        if (!dados.sucesso) {
            mostrarMensagem(dados.mensagem || "Não foi possível enviar.");
            return;
        }

        if (definitivo) {
            document.querySelector("#painelAtividade").close();
            await avisar(dados.mensagem, "Atividade entregue");
            carregarAtividades();
        } else {
            mostrarMensagem(dados.mensagem, true);
        }
    } catch (erro) {
        console.error("Erro ao enviar:", erro);
        mostrarMensagem("Não foi possível conectar ao servidor. Tente novamente.");
    }
}

/** Baixa o anexo da própria entrega pela rota autenticada (o token vai no header). */
async function baixarAnexoDaEntrega(entrega) {
    try {
        const resposta = await api(`/entregas/${entrega.entrega_id}/arquivo`);
        if (!resposta.ok) {
            await avisarErro("Não foi possível baixar o anexo.");
            return;
        }
        const url = URL.createObjectURL(await resposta.blob());
        const ancora = document.createElement("a");
        ancora.href = url;
        ancora.download = entrega.arquivo_nome || "anexo";
        document.body.appendChild(ancora);
        ancora.click();
        ancora.remove();
        setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (erro) {
        console.error("Erro ao baixar anexo:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
