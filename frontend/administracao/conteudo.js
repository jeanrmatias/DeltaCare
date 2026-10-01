/**
 * Supervisão de conteúdo: o que as turmas recebem.
 *
 * Material e atividades publicados ou agendados, de qualquer disciplina.
 * Rascunho, entrega, anotação, conversa e mensagem não aparecem — não por
 * filtro desta tela, mas porque o servidor não tem rota que os entregue à
 * administração (regras/conteudo.py).
 *
 * Só leitura. Tirar material do ar é decisão de política ainda não tomada; o
 * que a tela mostra é quantas denúncias abertas cada material tem, e o caminho
 * para tratá-las é a tela de Denúncias.
 */

const usuario = exigirAcesso("adm");

const ROTULOS_TIPO = { pdf: "PDF", video: "Vídeo", documento: "Documento", link: "Link" };
const ROTULOS_STATUS = { publicado: "Publicado", agendado: "Agendado" };

let dados = null;

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    document.querySelector("#seletorSemestre").addEventListener("change", (evento) => carregar(evento.target.value));
    document.querySelector("#campoBuscaConteudo").addEventListener("input", desenhar);
    carregar();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

function dataCurta(iso) {
    const data = new Date(iso);
    return Number.isNaN(data.getTime())
        ? ""
        : data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

async function carregar(semestre) {
    const vazio = document.querySelector("#vazio");
    try {
        const consulta = semestre ? `?semestre=${encodeURIComponent(semestre)}` : "";
        const resposta = await api(`/admin/conteudo${consulta}`);
        dados = await resposta.json();

        if (!dados.sucesso) {
            vazio.hidden = false;
            vazio.textContent = dados.mensagem;
            return;
        }

        const seletor = document.querySelector("#seletorSemestre");
        seletor.textContent = "";
        dados.semestres.forEach((s) => {
            const opcao = document.createElement("option");
            opcao.value = s;
            opcao.textContent = s;
            opcao.selected = s === dados.semestre;
            seletor.appendChild(opcao);
        });

        desenhar();
    } catch (erro) {
        console.error("Erro ao carregar conteúdo:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function normalizar(texto) {
    return String(texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/**
 * A busca filtra na própria tela: por disciplina, professor ou título. Uma
 * disciplina aparece se ela casar, ou se algum material ou atividade dela
 * casar — e aí só com o que casou.
 */
function desenhar() {
    const lista = document.querySelector("#listaConteudo");
    const vazio = document.querySelector("#vazio");
    const busca = normalizar(document.querySelector("#campoBuscaConteudo").value.trim());
    lista.textContent = "";

    const disciplinas = (dados?.disciplinas || []).map((d) => {
        if (!busca || normalizar(`${d.nome} ${d.professor_nome} ${d.professor_email}`).includes(busca)) return d;
        return {
            ...d,
            materiais: d.materiais.filter((m) => normalizar(m.titulo).includes(busca)),
            atividades: d.atividades.filter((a) => normalizar(a.titulo).includes(busca)),
        };
    }).filter((d) => !busca || d.materiais.length || d.atividades.length
        || normalizar(`${d.nome} ${d.professor_nome}`).includes(busca));

    vazio.hidden = disciplinas.length > 0;
    vazio.textContent = busca
        ? "Nada com esse termo neste semestre."
        : `Nenhuma disciplina em ${dados?.semestre || "este semestre"}.`;

    disciplinas.forEach((disciplina) => lista.appendChild(montarDisciplina(disciplina, Boolean(busca))));
}

function montarDisciplina(disciplina, aberta) {
    const cartao = document.createElement("details");
    cartao.className = "cartao historico-disciplina";
    cartao.open = aberta;

    const cabecalho = document.createElement("summary");
    const nome = document.createElement("strong");
    nome.textContent = disciplina.nome;
    const detalhe = document.createElement("span");
    detalhe.className = "historico-disciplina-detalhe";
    const denuncias = disciplina.materiais.reduce((soma, m) => soma + m.denuncias_abertas, 0);
    detalhe.textContent = `Prof. ${disciplina.professor_nome} · ${disciplina.total_alunos} aluno(s) · `
        + `${disciplina.materiais.length} material(is) · ${disciplina.atividades.length} atividade(s)`
        + (denuncias ? ` · ${denuncias} denúncia(s) aberta(s)` : "");
    cabecalho.appendChild(nome);
    cabecalho.appendChild(detalhe);
    cartao.appendChild(cabecalho);

    if (!disciplina.materiais.length && !disciplina.atividades.length) {
        const p = document.createElement("p");
        p.className = "estado-vazio";
        p.textContent = "Nada publicado ou agendado nesta disciplina.";
        cartao.appendChild(p);
        return cartao;
    }

    disciplina.materiais.forEach((material) => cartao.appendChild(montarMaterial(material)));
    disciplina.atividades.forEach((atividade) => cartao.appendChild(montarAtividade(atividade, disciplina)));
    return cartao;
}

function selo(texto, classe) {
    const span = document.createElement("span");
    span.className = classe;
    span.textContent = texto;
    return span;
}

function montarMaterial(material) {
    const linha = document.createElement("article");
    linha.className = "material-linha";

    const info = document.createElement("div");
    info.className = "material-linha-info";

    const topo = document.createElement("div");
    topo.className = "material-linha-topo";
    topo.appendChild(selo(ROTULOS_TIPO[material.tipo] || material.tipo, "badge-tipo"));
    topo.appendChild(selo(
        material.status === "agendado" ? `Agendado · ${dataCurta(material.data_liberacao)}` : "Publicado",
        `badge-status badge-status--${material.status}`
    ));
    if (material.denuncias_abertas) {
        topo.appendChild(selo(`${material.denuncias_abertas} denúncia(s) aberta(s)`, "badge-status badge-status--rascunho"));
    }
    info.appendChild(topo);

    const titulo = document.createElement("h3");
    titulo.textContent = material.titulo;
    info.appendChild(titulo);

    if (material.classificacao) {
        const p = document.createElement("p");
        p.className = "material-classificacao";
        p.textContent = material.classificacao;
        info.appendChild(p);
    }

    const acoes = document.createElement("div");
    acoes.className = "material-linha-acoes";

    if (material.tipo === "link" && material.link_url) {
        const link = document.createElement("a");
        link.className = "acao";
        link.href = material.link_url;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = "Abrir link";
        acoes.appendChild(link);
    } else if (material.arquivo_nome) {
        const baixar = document.createElement("button");
        baixar.type = "button";
        baixar.className = "acao";
        baixar.textContent = "Baixar";
        baixar.addEventListener("click", () => baixarMaterial(baixar, material));
        acoes.appendChild(baixar);
    }

    linha.appendChild(info);
    linha.appendChild(acoes);
    return linha;
}

/**
 * Pela rota autenticada, como em todo o sistema: link direto não levaria o
 * token, e token na URL fica em histórico e log.
 */
async function baixarMaterial(botao, material) {
    const texto = botao.textContent;
    botao.disabled = true;
    botao.textContent = "Baixando...";
    try {
        const resposta = await api(`/admin/conteudo/materiais/${material.id}/arquivo`);
        if (!resposta.ok) {
            await avisarErro("Não foi possível baixar este material.");
            return;
        }
        const url = URL.createObjectURL(await resposta.blob());
        const ancora = document.createElement("a");
        ancora.href = url;
        ancora.download = material.arquivo_nome || "material";
        document.body.appendChild(ancora);
        ancora.click();
        ancora.remove();
        setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (erro) {
        console.error("Erro ao baixar material:", erro);
    } finally {
        botao.disabled = false;
        botao.textContent = texto;
    }
}

function montarAtividade(atividade, disciplina) {
    const linha = document.createElement("article");
    linha.className = "material-linha";

    const info = document.createElement("div");
    info.className = "material-linha-info";

    const topo = document.createElement("div");
    topo.className = "material-linha-topo";
    topo.appendChild(selo(atividade.tipo === "objetiva" ? "Objetiva" : "Dissertativa", "badge-tipo"));
    topo.appendChild(selo(ROTULOS_STATUS[atividade.status] || atividade.status, `badge-status badge-status--${atividade.status}`));
    info.appendChild(topo);

    const titulo = document.createElement("h3");
    titulo.textContent = atividade.titulo;
    info.appendChild(titulo);

    const resumo = document.createElement("p");
    resumo.className = "material-classificacao";
    // Contagem, e não conteúdo: quantos entregaram é acompanhamento; o que
    // entregaram é trabalho do aluno e não passa por aqui.
    resumo.textContent = `${atividade.pontos} pontos`
        + (atividade.prazo ? ` · prazo ${dataCurta(atividade.prazo)}` : "")
        + ` · ${atividade.entregues} de ${disciplina.total_alunos} entregaram`;
    info.appendChild(resumo);

    const acoes = document.createElement("div");
    acoes.className = "material-linha-acoes";
    const ver = document.createElement("button");
    ver.type = "button";
    ver.className = "acao";
    ver.textContent = atividade.tipo === "objetiva" ? "Ver questões" : "Ver enunciado";
    ver.addEventListener("click", () => abrirAtividade(atividade.id));
    acoes.appendChild(ver);

    linha.appendChild(info);
    linha.appendChild(acoes);
    return linha;
}

async function abrirAtividade(atividadeId) {
    try {
        const resposta = await api(`/admin/conteudo/atividades/${atividadeId}`);
        const dadosAtividade = await resposta.json();
        if (!dadosAtividade.sucesso) {
            await avisarErro(dadosAtividade.mensagem);
            return;
        }

        const { atividade, questoes } = dadosAtividade;
        const dialogo = document.createElement("dialog");
        dialogo.className = "painel-supervisao";

        const titulo = document.createElement("h2");
        titulo.textContent = `${atividade.titulo} · ${atividade.turma_nome}`;
        dialogo.appendChild(titulo);

        if (atividade.enunciado) {
            const enunciado = document.createElement("p");
            enunciado.className = "painel-supervisao-enunciado";
            enunciado.textContent = atividade.enunciado;
            dialogo.appendChild(enunciado);
        }

        const lista = document.createElement("ol");
        lista.className = "painel-supervisao-questoes";
        questoes.forEach((questao) => {
            const item = document.createElement("li");
            const pergunta = document.createElement("p");
            pergunta.textContent = questao.enunciado;
            item.appendChild(pergunta);

            const alternativas = document.createElement("ul");
            questao.alternativas.forEach((alternativa, indice) => {
                const opcao = document.createElement("li");
                opcao.textContent = alternativa;
                // O gabarito marcado: é para isto que a coordenação abre a
                // questão, quando chega um "a resposta certa está errada".
                if (indice === questao.correta) {
                    opcao.className = "alternativa-correta";
                    opcao.textContent += "  ✓ gabarito";
                }
                alternativas.appendChild(opcao);
            });
            item.appendChild(alternativas);
            lista.appendChild(item);
        });
        if (questoes.length) dialogo.appendChild(lista);

        const fechar = document.createElement("button");
        fechar.type = "button";
        fechar.className = "acao";
        fechar.textContent = "Fechar";
        const fecharDialogo = () => { dialogo.close(); dialogo.remove(); };
        fechar.addEventListener("click", fecharDialogo);
        dialogo.addEventListener("cancel", fecharDialogo);
        dialogo.appendChild(fechar);

        document.body.appendChild(dialogo);
        dialogo.showModal();
    } catch (erro) {
        console.error("Erro ao abrir atividade:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
