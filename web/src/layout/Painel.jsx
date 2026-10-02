import { useState } from "react"
import { NavLink, Outlet } from "react-router"

import { Icone } from "../componentes/Icone"
import { useSessao } from "../hooks/useSessao"
import { iniciaisDe, nomeExibicao } from "../lib/usuario"
import { MENUS } from "./menus"
import { Perfil } from "./Perfil"
import { Sino } from "./Sino"

/**
 * A moldura de toda tela logada: menu lateral, rodapé com a pessoa e, no
 * meio, a página da vez (`<Outlet />` é onde o React Router encaixa a rota
 * filha).
 *
 * No celular o menu fica em cima, em linha; a partir do tablet vira a coluna
 * da esquerda — o mesmo comportamento do front antigo.
 */
export function Painel() {
  const { usuario, sair } = useSessao()
  const [vendoPerfil, setVendoPerfil] = useState(false)
  const nome = nomeExibicao(usuario)

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex w-full shrink-0 flex-col bg-navy-900 px-4 py-5 text-texto-inverso md:sticky md:top-0 md:h-screen md:w-60">
        <div className="mb-6 flex items-center gap-2.5 px-2 text-[17px] font-bold text-white">
          <span className="flex size-[30px] items-center justify-center rounded-campo bg-primaria">
            <Icone nome="marca" />
          </span>
          Delta Care
        </div>

        <nav aria-label="Menu principal" className="flex flex-1 flex-row flex-wrap gap-0.5 md:flex-col md:flex-nowrap md:overflow-y-auto">
          {MENUS[usuario.tipo].map((item) => (
            <NavLink
              key={item.caminho}
              to={item.caminho}
              end={item.exato}
              className={({ isActive }) =>
                [
                  "flex items-center gap-2.5 rounded-campo px-2.5 py-2 text-sm font-medium transition",
                  isActive ? "bg-primaria text-white" : "text-texto-inverso/75 hover:bg-navy-700 hover:text-white",
                ].join(" ")
              }
            >
              <Icone nome={item.icone} />
              {item.rotulo}
            </NavLink>
          ))}
        </nav>

        <footer className="mt-4 flex items-center gap-2.5 border-t border-navy-700 px-2 pt-2.5 pb-1">
          <span className="flex size-[34px] shrink-0 items-center justify-center rounded-full bg-primaria text-[13px] font-bold text-white">
            {iniciaisDe(nome)}
          </span>
          <div className="min-w-0">
            <strong className="block truncate text-sm text-white">{usuario.tipo === "professor" ? `Prof. ${nome}` : nome}</strong>
            <div className="flex gap-3">
              <button type="button" onClick={() => setVendoPerfil(true)} className="text-xs font-medium text-texto-inverso opacity-70 hover:opacity-100">
                Ver perfil
              </button>
              <button type="button" onClick={sair} className="text-xs font-medium text-texto-inverso opacity-70 hover:opacity-100">
                Sair
              </button>
            </div>
          </div>
        </footer>
      </aside>

      <main className="relative min-w-0 flex-1 p-5">
        {/* O sino fica no canto de toda tela logada, por cima do cabeçalho
            da página — que reserva o espaço dele (ver Cabecalho). */}
        <div className="absolute top-5 right-5 z-10">
          <Sino />
        </div>
        <Outlet />
      </main>

      {vendoPerfil && <Perfil aoFechar={() => setVendoPerfil(false)} />}
    </div>
  )
}

/** O cabeçalho de cada página: título e uma linha do que ela é. */
export function Cabecalho({ titulo, descricao, children }) {
  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-5 pr-14">
      <div>
        <h1 className="text-2xl font-bold text-navy-900">{titulo}</h1>
        {descricao && <p className="mt-1 text-[13px] text-texto-secundario">{descricao}</p>}
      </div>
      {children && <div className="flex items-center gap-3">{children}</div>}
    </header>
  )
}
