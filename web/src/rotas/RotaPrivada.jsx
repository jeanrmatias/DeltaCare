import { Navigate, Outlet, useLocation } from "react-router"

import { useSessao } from "../hooks/useSessao"
import { INICIO_DO_PERFIL } from "../lib/usuario"

/**
 * Rota privada: só deixa passar quem está logado **com o perfil certo**.
 *
 * - Sem sessão: vai para o login, levando o endereço que tentou abrir, para
 *   voltar a ele depois de entrar.
 * - Perfil errado (aluno abrindo /professor): vai para o início do próprio
 *   perfil, e não para uma tela de erro.
 *
 * Isto é navegação, não segurança. Quem protege os dados é o backend, que
 * confere o token e o perfil em cada rota. Esta checagem só evita mostrar uma
 * tela que, de qualquer forma, não receberia dado nenhum.
 */
export function RotaPrivada({ perfil }) {
  const { usuario } = useSessao()
  const local = useLocation()

  if (!usuario) {
    return <Navigate to="/" replace state={{ de: local.pathname + local.search }} />
  }
  if (usuario.tipo !== perfil) {
    return <Navigate to={INICIO_DO_PERFIL[usuario.tipo] ?? "/"} replace />
  }
  return <Outlet />
}

/**
 * Rota pública que não faz sentido para quem já entrou (o login): manda para
 * o início do perfil. A política de privacidade, pública para todos, não usa.
 */
export function SoVisitante() {
  const { usuario } = useSessao()

  if (usuario) return <Navigate to={INICIO_DO_PERFIL[usuario.tipo] ?? "/"} replace />
  return <Outlet />
}
