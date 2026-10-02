/**
 * O menu lateral de cada perfil. Uma lista por perfil, num lugar só: no front
 * antigo o menu estava copiado dentro de cada uma das 33 páginas, e pôr um
 * item novo era editar todas.
 *
 * Item de menu nunca leva a tela vazia: o único módulo ainda não construído
 * (Relatórios) leva a uma página que diz isso e o que ele vai fazer.
 */
export const MENUS = {
  aluno: [
    { rotulo: "Início", caminho: "/aluno", icone: "inicio", exato: true },
    { rotulo: "Chat de estudos", caminho: "/aluno/chat", icone: "chat" },
    { rotulo: "Mensagens", caminho: "/aluno/mensagens", icone: "mensagens" },
    { rotulo: "Materiais", caminho: "/aluno/materiais", icone: "materiais" },
    { rotulo: "Atividades", caminho: "/aluno/atividades", icone: "atividades" },
    { rotulo: "Desempenho", caminho: "/aluno/desempenho", icone: "desempenho" },
    { rotulo: "Denúncias", caminho: "/aluno/denuncias", icone: "denuncias" },
    { rotulo: "Favoritos", caminho: "/aluno/favoritos", icone: "favoritos" },
    { rotulo: "Anotações", caminho: "/aluno/anotacoes", icone: "anotacoes" },
    { rotulo: "Ranking", caminho: "/aluno/ranking", icone: "ranking" },
    { rotulo: "Semestres anteriores", caminho: "/aluno/historico", icone: "historico" },
  ],
  professor: [
    { rotulo: "Início", caminho: "/professor", icone: "inicio", exato: true },
    { rotulo: "Materiais", caminho: "/professor/materiais", icone: "materiais" },
    { rotulo: "Atividades", caminho: "/professor/atividades", icone: "atividades" },
    { rotulo: "Calendário", caminho: "/professor/calendario", icone: "calendario" },
    { rotulo: "Disciplinas", caminho: "/professor/disciplinas", icone: "turmas" },
    { rotulo: "Chat", caminho: "/professor/mensagens", icone: "chat" },
    { rotulo: "Desempenho", caminho: "/professor/desempenho", icone: "desempenho" },
    { rotulo: "Denúncias", caminho: "/professor/denuncias", icone: "denuncias" },
    { rotulo: "Avisos", caminho: "/professor/avisos", icone: "avisos" },
    { rotulo: "Semestres anteriores", caminho: "/professor/historico", icone: "historico" },
  ],
  adm: [
    { rotulo: "Início", caminho: "/admin", icone: "inicio", exato: true },
    { rotulo: "Turmas", caminho: "/admin/turmas", icone: "turmas" },
    { rotulo: "Disciplinas", caminho: "/admin/disciplinas", icone: "materiais" },
    { rotulo: "Usuários", caminho: "/admin/usuarios", icone: "usuarios" },
    { rotulo: "Denúncias", caminho: "/admin/denuncias", icone: "denuncias" },
    { rotulo: "Avisos", caminho: "/admin/avisos", icone: "avisos" },
    { rotulo: "Conteúdo", caminho: "/admin/conteudo", icone: "materiais" },
    { rotulo: "Privacidade", caminho: "/admin/privacidade", icone: "privacidade" },
    // O módulo ainda não existe: a página diz isso e o que ele vai fazer.
    { rotulo: "Relatórios", caminho: "/admin/relatorios", icone: "desempenho" },
  ],
}
