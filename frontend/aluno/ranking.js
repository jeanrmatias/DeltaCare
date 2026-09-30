/**
 * Ranking da turma, pelo XP do semestre.
 *
 * A tela mostra três coisas: onde o aluno está (só ele vê), o topo da turma e
 * quem mais evoluiu na semana. O fundo da lista não aparece para ninguém — é
 * a decisão central do módulo, e ela é do servidor (regras/ranking.py): esta
 * tela só desenha o que chega, e o que não chega não tem como vazar.
 */

const usuario = exigirAcesso("aluno");

if (usuario) {
    montarRodapePerfil(usuario);
    ligarRodapePerfil();
    ligarNotificacoes();
    ligarVisibilidade();
    carregar();
}

function montarRodapePerfil(usuario) {
    const nome = nomeExibicao(usuario);
    document.querySelector("#avatarRodape").textContent = iniciaisDe(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

function ordinal(posicao) {
    return `${posicao}º`;
}

function seloDeFaixa(faixa) {
    const selo = document.createElement("span");
    selo.className = "ranking-faixa";
    selo.dataset.faixa = faixa.chave;
    selo.textContent = faixa.nome;
    return selo;
}

async function carregar(coorteId) {
    const vazio = document.querySelector("#vazio");
    const painel = document.querySelector("#painelRanking");

    try {
        const consulta = coorteId ? `?coorte_id=${encodeURIComponent(coorteId)}` : "";
        const resposta = await api(`/aluno/ranking${consulta}`);
        const dados = await resposta.json();

        if (!dados.sucesso || !dados.coorte) {
            painel.hidden = true;
            vazio.hidden = false;
            vazio.textContent = dados.mensagem || "Não foi possível carregar o ranking.";
            return;
        }

        vazio.hidden = true;
        painel.hidden = false;

        document.querySelector("#rankingTurma").textContent =
            `${dados.coorte.nome} · semestre ${dados.semestre}`;

        montarSeletorDeTurma(dados);
        montarMinhaPosicao(dados);
        montarTopo(dados.topo);
        montarEvolucao(dados.evoluiu, dados.dias_da_evolucao);
    } catch (erro) {
        console.error("Erro ao carregar o ranking:", erro);
        painel.hidden = true;
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

/** Só aparece para quem está em mais de uma turma no semestre. */
function montarSeletorDeTurma(dados) {
    const campo = document.querySelector("#campoTurmaRanking");
    const seletor = document.querySelector("#seletorTurmaRanking");

    campo.hidden = dados.coortes.length < 2;
    if (campo.hidden) return;

    seletor.textContent = "";
    dados.coortes.forEach((coorte) => {
        const opcao = document.createElement("option");
        opcao.value = coorte.id;
        opcao.textContent = coorte.nome;
        opcao.selected = coorte.id === dados.coorte.id;
        seletor.appendChild(opcao);
    });
    seletor.onchange = () => carregar(seletor.value);
}

function montarMinhaPosicao(dados) {
    const eu = dados.eu;

    // Com zero XP, "58º de 58" não diz nada útil e soa como castigo. A frase
    // muda para o que de fato importa: ainda não começou.
    document.querySelector("#minhaPosicao").textContent = eu.xp > 0
        ? `${ordinal(eu.posicao)} de ${dados.total}`
        : "Ainda sem pontos";

    document.querySelector("#meuXp").textContent = eu.xp > 0
        ? `${eu.xp} XP neste semestre · ${eu.xp_semana} nos últimos ${dados.dias_da_evolucao} dias`
        : "Abra um material, pergunte ao assistente ou entregue uma atividade para entrar no ranking.";

    const faixa = document.querySelector("#minhaFaixa");
    faixa.textContent = "";
    faixa.appendChild(seloDeFaixa(eu.faixa));

    document.querySelector("#campoAparecer").checked = eu.aparece;
    document.querySelector("#dicaAparecer").textContent = eu.aparece
        ? "Os colegas veem seu nome se você estiver no topo."
        : "Os colegas veem \"colega que preferiu não aparecer\" no seu lugar. Sua posição continua visível só para você.";
}

function montarTopo(topo) {
    const lista = document.querySelector("#listaTopo");
    lista.textContent = "";

    if (!topo.length) {
        const item = document.createElement("li");
        item.className = "estado-vazio";
        item.textContent = "Ninguém pontuou neste semestre ainda.";
        lista.appendChild(item);
        return;
    }

    topo.forEach((linha) => {
        const item = document.createElement("li");
        item.className = "ranking-linha" + (linha.eu ? " ranking-linha--eu" : "");

        const posicao = document.createElement("span");
        posicao.className = "ranking-posicao";
        posicao.textContent = ordinal(linha.posicao);

        const nome = document.createElement("span");
        nome.className = "ranking-nome" + (linha.nome ? "" : " ranking-nome--oculto");
        nome.textContent = linha.nome
            ? (linha.eu ? `${linha.nome} (você)` : linha.nome)
            : "Colega que preferiu não aparecer";

        const xp = document.createElement("span");
        xp.className = "ranking-xp";
        xp.textContent = `${linha.xp} XP`;

        item.appendChild(posicao);
        item.appendChild(nome);
        item.appendChild(seloDeFaixa(linha.faixa));
        item.appendChild(xp);
        lista.appendChild(item);
    });
}

function montarEvolucao(evoluiu, dias) {
    const lista = document.querySelector("#listaEvolucao");
    document.querySelector("#tituloEvolucao").textContent =
        `Quem mais evoluiu nos últimos ${dias} dias`;
    lista.textContent = "";

    if (!evoluiu.length) {
        const item = document.createElement("li");
        item.className = "estado-vazio";
        item.textContent = "Ninguém estudou nesta semana ainda. Pode ser você.";
        lista.appendChild(item);
        return;
    }

    evoluiu.forEach((linha) => {
        const item = document.createElement("li");
        item.className = "ranking-linha" + (linha.eu ? " ranking-linha--eu" : "");

        const nome = document.createElement("span");
        nome.className = "ranking-nome";
        nome.textContent = linha.eu ? `${linha.nome} (você)` : linha.nome;

        const xp = document.createElement("span");
        xp.className = "ranking-xp";
        xp.textContent = `+${linha.xp_semana} XP`;

        item.appendChild(nome);
        item.appendChild(xp);
        lista.appendChild(item);
    });
}

function ligarVisibilidade() {
    const campo = document.querySelector("#campoAparecer");

    campo.addEventListener("change", async () => {
        const aparecer = campo.checked;
        campo.disabled = true;

        try {
            const resposta = await api("/aluno/ranking/visibilidade", {
                method: "PUT",
                body: JSON.stringify({ aparecer }),
            });
            const dados = await resposta.json();

            if (!dados.sucesso) {
                campo.checked = !aparecer;
                await avisarErro(dados.mensagem || "Não foi possível mudar a visibilidade.");
                return;
            }

            // Recarrega em vez de só trocar o texto: o próprio topo muda
            // (o nome some ou volta), e mostrar o estado antigo seria mentir.
            const seletor = document.querySelector("#seletorTurmaRanking");
            carregar(document.querySelector("#campoTurmaRanking").hidden ? undefined : seletor.value);
        } catch (erro) {
            campo.checked = !aparecer;
            console.error("Erro ao mudar a visibilidade:", erro);
            await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
        } finally {
            campo.disabled = false;
        }
    });
}
