/**
 * Catálogo dos módulos ainda não construídos.
 *
 * Em vez de um alert("em breve"), cada item do menu leva a uma página que diz
 * o que aquele módulo vai fazer. A decisão é a mesma tomada no dashboard do
 * professor: declarar o que não existe é melhor do que simular com dados de
 * exemplo — e melhor do que um beco sem saída no menu.
 *
 * O conteúdo veio do backlog do projeto, então esta tela é o roadmap visível
 * dentro do próprio produto.
 */

const MODULOS = {
    "calendario-professor": {
        titulo: "Calendário",
        resumo: "Visão do semestre com material e atividades por data.",
        sprint: "Sprint 4",
        itens: [
            "Lançar material ou atividade direto por uma data",
            "Ver num mês o que já está agendado",
            "Indicadores de entrega próxima e prazo vencido",
        ],
    },
    "chat-professor": {
        titulo: "Mensagens",
        resumo: "Conversa direta entre professor e aluno, por turma.",
        sprint: "Sprint 4",
        itens: [
            "Receber dúvidas dos alunos da turma",
            "Histórico de conversa por aluno",
            "Aviso de mensagem nova",
        ],
        nota: "Hoje o aluno tira dúvidas com o assistente de IA, que responde apenas com base no material liberado. Este módulo é para o que a IA não resolve.",
    },
    "conteudo-admin": {
        titulo: "Supervisão de conteúdo",
        resumo: "Acesso da administração ao material de qualquer turma.",
        sprint: "Sprint 8",
        itens: [
            "Consultar materiais e atividades de qualquer turma",
            "Verificar conformidade com as políticas da instituição",
        ],
        nota: "Hoje a administração cria turmas e matricula alunos, mas não abre o material das turmas — o acesso é do professor responsável.",
    },
    // ---------------------------------------------------------------------
    // Os cinco abaixo saíram de uma conferência do backlog contra este
    // catálogo: existiam como card e não apareciam em lugar nenhum do produto.
    // É a mesma lacuna das denúncias, repetida cinco vezes — sinal de que a
    // conferência precisa virar hábito, e não acontecer só quando alguém
    // pergunta "cadê tal coisa?".
    //
    // Levam "Backlog" no lugar de "Sprint N" porque ainda não foram
    // sequenciados. Inventar um número aqui seria fingir um planejamento que
    // não existe.
    // ---------------------------------------------------------------------

    "favoritos-aluno": {
        titulo: "Favoritos",
        resumo: "Marcar o que você quer reencontrar rápido.",
        sprint: "Backlog",
        itens: [
            "Marcar e desmarcar material como favorito",
            "Aba dedicada, separada da lista geral",
            "Favoritos que continuam válidos entre semestres",
        ],
    },
    "anotacoes-aluno": {
        titulo: "Anotações",
        resumo: "Suas notas e destaques dentro do material de aula.",
        sprint: "Backlog",
        itens: [
            "Escrever, editar e apagar anotações num material",
            "Destacar trechos do conteúdo",
            "Anotação é privada: ninguém além de você enxerga",
        ],
        nota: "A privacidade aqui não é detalhe de interface. Anotação de estudo é do aluno, e nem professor nem administração devem conseguir ler.",
    },
    "ranking-aluno": {
        titulo: "Ranking",
        resumo: "Como você está em relação à turma, se quiser aparecer.",
        sprint: "Backlog",
        itens: [
            "Posição na turma calculada a partir do XP",
            "Escolher não aparecer no ranking público",
            "Destaque de quem mais evoluiu no período",
        ],
        nota: "Depende do XP, que já existe e já conta atividade entregue e nota. A opção de não aparecer é parte do módulo, não um extra: ranking obrigatório expõe quem está indo mal.",
    },
    "avisos-professor": {
        titulo: "Avisos",
        resumo: "Recado do professor ou da administração para a turma.",
        sprint: "Backlog",
        itens: [
            "Escrever aviso para uma turma ou para todas",
            "Marcar como urgente",
            "Histórico do que já foi enviado",
            "Aviso geral da administração para a instituição inteira",
        ],
        nota: "Diferente das notificações, que nascem de eventos do sistema. Aqui é uma pessoa escrevendo para outras.",
    },
    "historico-semestres": {
        titulo: "Semestres anteriores",
        resumo: "O material das turmas que já terminaram.",
        sprint: "Backlog",
        itens: [
            "Consultar material de semestres passados",
            "Buscar por palavra dentro do arquivo histórico",
            "Vale para aluno e para professor",
        ],
        nota: "Hoje o material some da vista quando o semestre vira. Para quem vai prestar prova de residência, é justamente o conteúdo antigo que importa.",
    },

    "relatorios-admin": {
        titulo: "Relatórios",
        resumo: "Indicadores da instituição para coordenação.",
        sprint: "Sprint 7",
        itens: [
            "Desempenho por turma e por período",
            "Uso da plataforma por perfil",
            "Exportação dos indicadores",
        ],
    },
};

/**
 * Renderiza na página o módulo indicado em `?modulo=` na URL.
 */
function montarPaginaDeModulo() {
    const parametros = new URLSearchParams(window.location.search);
    const chave = parametros.get("modulo");
    const modulo = MODULOS[chave];

    const titulo = document.querySelector("#moduloTitulo");
    const resumo = document.querySelector("#moduloResumo");
    const lista = document.querySelector("#moduloItens");
    const etiqueta = document.querySelector("#moduloSprint");
    const nota = document.querySelector("#moduloNota");

    if (!modulo) {
        titulo.textContent = "Módulo não encontrado";
        resumo.textContent = "Volte pelo menu ao lado.";
        etiqueta.hidden = true;
        return;
    }

    document.title = `Delta Care | ${modulo.titulo}`;
    titulo.textContent = modulo.titulo;
    resumo.textContent = modulo.resumo;
    etiqueta.textContent = modulo.sprint;

    lista.innerHTML = "";
    modulo.itens.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        lista.appendChild(li);
    });

    if (modulo.nota) {
        nota.textContent = modulo.nota;
        nota.hidden = false;
    }
}
