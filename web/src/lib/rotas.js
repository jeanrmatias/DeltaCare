/**
 * As notificações guardadas no banco apontam para páginas do front antigo
 * ("materiais.html"). Aqui cada uma vira a rota do React, conforme o perfil
 * de quem recebeu — "avisos.html" é a tela de avisos para o professor, e o
 * início para o aluno, que não tem tela de avisos.
 *
 * O banco não muda: o front antigo continua lendo os mesmos links enquanto
 * os dois convivem.
 */
const ROTAS_ANTIGAS = {
  aluno: {
    "inicio.html": "/aluno",
    "aluno.html": "/aluno/chat",
    "materiais.html": "/aluno/materiais",
    "atividades.html": "/aluno/atividades",
    "mensagens.html": "/aluno/mensagens",
    "denuncias.html": "/aluno/denuncias",
    "meus-dados.html": "/aluno/meus-dados",
    "avisos.html": "/aluno",
    "turmas.html": "/aluno",
  },
  professor: {
    "prof.html": "/professor",
    "inicio.html": "/professor",
    "materiais.html": "/professor/materiais",
    "atividades.html": "/professor/atividades",
    "mensagens.html": "/professor/mensagens",
    "denuncias.html": "/professor/denuncias",
    "avisos.html": "/professor/avisos",
    "turmas.html": "/professor/disciplinas",
  },
  adm: {
    "adm.html": "/admin",
    "inicio.html": "/admin",
    "denuncias.html": "/admin/denuncias",
    "solicitacoes.html": "/admin/privacidade",
    "avisos.html": "/admin/avisos",
    "turmas.html": "/admin/disciplinas",
  },
}

/** Link guardado na notificação → rota do React, ou null se não houver para onde ir. */
export function rotaDoLink(link, perfil) {
  if (!link) return null
  const [pagina, consulta] = link.split("?")
  const rota = ROTAS_ANTIGAS[perfil]?.[pagina.split("/").pop()]
  if (!rota) return null
  return consulta ? `${rota}?${consulta}` : rota
}
