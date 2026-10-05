/**
 * Como mostrar uma pessoa na tela: nome e iniciais do avatar.
 */

/**
 * Prefere o nome cadastrado. Conta sem nome vira um apelido a partir do
 * e-mail ("ana.paula@x" -> "Ana Paula"), melhor do que o endereço cru.
 */
export function nomeExibicao(usuario) {
  const nome = usuario?.nome?.trim()
  if (nome) return nome

  const email = usuario?.email || ""
  const apelido = email
    .split("@")[0]
    .replace(/[._-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
    .join(" ")
  return apelido || email
}

/** Iniciais para o avatar: primeira e última palavra do nome. */
export function iniciaisDe(nome) {
  const partes = (nome || "").trim().split(/\s+/).filter(Boolean)
  if (partes.length === 0) return "--"
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase()
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase()
}

/** Página inicial de cada perfil. O valor `adm` vem do banco. */
export const INICIO_DO_PERFIL = {
  aluno: "/aluno",
  professor: "/professor",
  adm: "/admin",
}
