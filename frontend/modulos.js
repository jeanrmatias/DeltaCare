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
