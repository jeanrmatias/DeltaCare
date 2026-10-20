import { useState } from "react"

import { Icone } from "../componentes/Icone"

/**
 * O olho dentro do campo de senha, que mostra o que foi digitado.
 *
 * Devolve o `type` que o input deve usar e o botão, para o campo pôr dentro
 * de um wrapper `relative` (o botão fica no canto direito do input). Campo que
 * não é de senha recebe o próprio tipo e nenhum botão.
 *
 * Um botão de alternância (aria-pressed) com nome fixo: o leitor de tela diz
 * "Mostrar senha, pressionado" — mais claro que um nome que troca a cada toque.
 */
export function useVerSenha(tipo, idDoCampo) {
  const [visivel, setVisivel] = useState(false)
  if (tipo !== "password") return { tipo, botao: null }

  const botao = (
    <button
      type="button"
      onClick={() => setVisivel((atual) => !atual)}
      aria-label="Mostrar senha"
      aria-pressed={visivel}
      aria-controls={idDoCampo}
      className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-campo text-texto-secundario outline-none hover:text-primaria focus-visible:ring-3 focus-visible:ring-primaria/30"
    >
      <Icone nome={visivel ? "olho-fechado" : "olho"} />
    </button>
  )
  return { tipo: visivel ? "text" : "password", botao }
}
