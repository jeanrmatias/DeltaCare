import { Navigate, useNavigate } from "react-router"

import { FormularioSenha } from "../../componentes/FormularioSenha"
import { useSessao } from "../../hooks/useSessao"
import { useTituloDaPagina } from "../../hooks/useTituloDaPagina"
import { INICIO_DO_PERFIL } from "../../lib/usuario"

/**
 * Troca obrigatória no primeiro acesso. A senha atual é a provisória que a
 * secretaria passou — às vezes a mesma para a turma inteira, e por isso não
 * pode continuar valendo.
 *
 * Fica fora do Painel de propósito: sem menu, não há para onde ir antes de
 * trocar (e o servidor recusaria de qualquer jeito).
 */
export function TrocarSenha() {
  const { usuario, senhaTrocada, sair } = useSessao()
  const navegar = useNavigate()
  useTituloDaPagina("Defina a sua senha")

  if (!usuario) return <Navigate to="/" replace />
  if (!usuario.trocar_senha) return <Navigate to={INICIO_DO_PERFIL[usuario.tipo] ?? "/"} replace />

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-[420px] rounded-cartao bg-superficie px-6 py-7 shadow-cartao">
        <h1 className="text-xl font-bold text-navy-900">Defina a sua senha</h1>
        <p className="mt-2 mb-5 text-sm leading-relaxed text-texto-secundario">
          Você entrou com a senha provisória que recebeu da secretaria. Antes de continuar, escolha uma senha só sua.
        </p>
        <FormularioSenha
          rotuloAtual="Senha provisória"
          aoTrocar={() => {
            senhaTrocada()
            navegar(INICIO_DO_PERFIL[usuario.tipo] ?? "/", { replace: true })
          }}
          acoesExtras={
            <button type="button" onClick={sair} className="px-3 text-sm font-semibold text-texto-secundario hover:text-texto">Sair</button>
          }
        />
      </div>
    </main>
  )
}
