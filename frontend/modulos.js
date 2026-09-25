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
    "atividades-aluno": {
        titulo: "Atividades",
        resumo: "Exercícios, trabalhos e desafios propostos pelo professor.",
        sprint: "Sprint 3",
        itens: [
            "Resolver exercícios separados por tema",
            "Salvar o progresso e retomar de onde parou",
            "Enviar resumo ou trabalho dentro do prazo",
            "Ver a nota e a devolutiva do professor",
        ],
    },
    "desempenho-aluno": {
        titulo: "Desempenho",
        resumo: "Seu progresso na disciplina, com pontos e histórico de acertos.",
        sprint: "Sprint 5",
        itens: [
            "Pontuação acumulada pelas atividades entregues",
            "Ofensiva diária de estudo",
            "Tópicos em que você mais erra, para orientar a revisão",
            "Posição no ranking da turma, se você optar por aparecer",
        ],
    },
    "atividades-professor": {
        titulo: "Atividades",
        resumo: "Criação e correção das atividades da turma.",
        sprint: "Sprint 3",
        itens: [
            "Criar exercícios, trabalhos e desafios",
            "Definir data de liberação e prazo de entrega",
            "Acompanhar quem entregou e quem está pendente",
            "Corrigir e escrever devolutiva para o aluno",
        ],
    },
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
    "desempenho-professor": {
        titulo: "Desempenho",
        resumo: "Como a turma está indo, em números.",
        sprint: "Sprint 7",
        itens: [
            "Tópicos com maior índice de erro na turma",
            "Média e totalização por atividade",
            "Filtros por turma e período",
            "Visão agregada e por aluno",
        ],
    },
    "denunciar-conteudo": {
        titulo: "Denúncias",
        resumo: "Reportar conteúdo inadequado e acompanhar o que você reportou.",
        sprint: "Sprint 8",
        itens: [
            "Reportar um material direto da tela em que ele aparece",
            "Escolher o motivo e descrever o problema",
            "Acompanhar o andamento do que você reportou",
            "Ser avisado quando a administração concluir a análise",
        ],
        nota: "Este é o lado de quem reporta. Quem recebe e trata as denúncias é a administração, no módulo de mesmo nome — os dois fazem parte da mesma entrega.",
    },
    "denuncias-admin": {
        titulo: "Denúncias",
        resumo: "Registro e tratamento do conteúdo reportado por alunos e professores.",
        sprint: "Sprint 8",
        itens: [
            "Receber e listar denúncias abertas",
            "Acompanhar o status de cada uma",
            "Registrar a ação tomada",
            "Devolver o resultado a quem reportou",
        ],
        nota: "As denúncias chegam do módulo de mesmo nome nas áreas do aluno e do professor, onde o conteúdo é reportado. Sem aquele lado, esta tela não teria o que listar.",
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
