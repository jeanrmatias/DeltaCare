import { useEffect, useRef, useState } from "react"
import { Link, NavLink, Outlet, useLocation } from "react-router"

import { Icone } from "../componentes/Icone"
import { useSessao } from "../hooks/useSessao"
import { useTituloDaPagina } from "../hooks/useTituloDaPagina"
import { INICIO_DO_PERFIL, iniciaisDe, nomeExibicao } from "../lib/usuario"
import { MENUS } from "./menus"
import { Perfil } from "./Perfil"
import { Sino } from "./Sino"

// Quanto arrastar (px) para a gaveta abrir pela borda ou fechar puxando.
const ARRASTO_PARA_FECHAR = 80
const ARRASTO_PARA_ABRIR = 50
const BORDA_DA_TELA = 24

/**
 * A moldura de toda tela logada: menu, a pessoa e, no meio, a página da vez
 * (`<Outlet />` é onde o React Router encaixa a rota filha).
 *
 * No computador e no tablet, o menu é a coluna da esquerda. No celular, uma
 * barra fina no topo e o menu numa gaveta que desliza da direita: aberto o
 * tempo todo, ocupava quase metade da tela antes do conteúdo (349 px de 844).
 * A gaveta abre pelo botão ou puxando da borda direita, e fecha tocando fora,
 * com Esc, escolhendo um item ou empurrando-a de volta.
 */
export function Painel() {
  const { usuario } = useSessao()
  const local = useLocation()
  const [vendoPerfil, setVendoPerfil] = useState(false)
  const [gavetaAberta, setGavetaAberta] = useState(false)
  const botaoMenu = useRef(null)
  const inicio = INICIO_DO_PERFIL[usuario.tipo] ?? "/"

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Para quem navega pelo teclado: sem isto, são onze itens de menu a
          atravessar com Tab em toda página antes de chegar ao conteúdo.
          Invisível até receber o foco. */}
      <a href="#conteudo"
        className="sr-only z-50 rounded-campo bg-superficie px-4 py-2 text-sm font-semibold text-primaria shadow-cartao focus:not-sr-only focus:fixed focus:top-3 focus:left-3">
        Pular para o conteúdo
      </a>

      {/* Computador e tablet: a coluna de sempre. */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col bg-navy-900 px-4 py-5 text-texto-inverso md:flex">
        <Marca para={inicio} className="mb-6" />
        <ItensDoMenu tipo={usuario.tipo} />
        <Rodape aoVerPerfil={() => setVendoPerfil(true)} />
      </aside>

      {/* Celular: a barra do topo. */}
      <header className="sticky top-0 z-30 flex items-center justify-between bg-navy-900 px-4 py-3 md:hidden">
        <Marca para={inicio} />
        <button ref={botaoMenu} type="button" onClick={() => setGavetaAberta(true)} aria-expanded={gavetaAberta} aria-controls="gaveta-menu"
          className="flex items-center gap-2 rounded-campo px-3 py-2 text-sm font-semibold text-white transition hover:bg-navy-700">
          <Icone nome="menu" />
          Menu
        </button>
      </header>
      <Gaveta aberta={gavetaAberta} aoFechar={() => setGavetaAberta(false)} aoAbrir={() => setGavetaAberta(true)} botaoMenu={botaoMenu}
        tipo={usuario.tipo} aoVerPerfil={() => { setGavetaAberta(false); setVendoPerfil(true) }} />

      <main id="conteudo" tabIndex={-1} className="relative min-w-0 flex-1 p-5">
        {/* O sino fica no canto de toda tela logada, por cima do cabeçalho
            da página — que reserva o espaço dele (ver Cabecalho). */}
        <div className="absolute top-5 right-5 z-10">
          <Sino />
        </div>
        {/* A tela nova entra com um esmaecer curto (index.css: animate-entrar).
            A chave é o endereço: trocar de tela remonta e anima; trocar só o
            filtro da mesma tela (?turma=), não. */}
        <div key={local.pathname} className="animate-entrar motion-reduce:animate-none">
          <Outlet />
        </div>
      </main>

      {vendoPerfil && <Perfil aoFechar={() => setVendoPerfil(false)} />}
    </div>
  )
}

/** A logo, que leva ao início do perfil — de qualquer tela. */
function Marca({ para, className = "" }) {
  return (
    <Link to={para} aria-label="Delta Care — ir para o início"
      className={`flex items-center gap-2.5 rounded-campo px-2 font-titulo text-[19px] font-semibold tracking-tight text-white transition hover:opacity-90 ${className}`}>
      <span className="flex size-[30px] items-center justify-center rounded-campo bg-marca">
        <Icone nome="marca" />
      </span>
      Delta Care
    </Link>
  )
}

function ItensDoMenu({ tipo, aoEscolher }) {
  return (
    <nav aria-label="Menu principal" className="flex flex-1 flex-col gap-0.5 overflow-y-auto">
      {MENUS[tipo].map((item) => (
        <NavLink
          key={item.caminho}
          to={item.caminho}
          end={item.exato}
          onClick={aoEscolher}
          className={({ isActive }) =>
            [
              "flex items-center gap-2.5 rounded-campo border-l-[3px] px-2.5 py-2 text-sm font-medium transition-colors duration-150",
              // Ativo: a barra na cor exata da marca e o texto branco sobre o
              // azul-marinho — branco direto no azul da marca não passaria
              // no contraste de texto (4,45:1).
              isActive ? "border-marca bg-navy-700 font-semibold text-white" : "border-transparent text-texto-inverso/75 hover:bg-navy-800 hover:text-white",
            ].join(" ")
          }
        >
          <Icone nome={item.icone} />
          {item.rotulo}
        </NavLink>
      ))}
    </nav>
  )
}

function Rodape({ aoVerPerfil }) {
  const { usuario, sair } = useSessao()
  const nome = nomeExibicao(usuario)
  return (
    <footer className="mt-4 flex items-center gap-2.5 border-t border-navy-700 px-2 pt-2.5 pb-1">
      <span className="flex size-[34px] shrink-0 items-center justify-center rounded-full bg-navy-700 text-[14px] font-semibold text-white ring-1 ring-marca">
        {iniciaisDe(nome)}
      </span>
      <div className="min-w-0">
        <strong className="block truncate text-sm text-white">{usuario.tipo === "professor" ? `Prof. ${nome}` : nome}</strong>
        <div className="flex gap-3">
          <button type="button" onClick={aoVerPerfil} className="text-xs font-medium text-texto-inverso/70 hover:text-texto-inverso">
            Ver perfil
          </button>
          <button type="button" onClick={sair} className="text-xs font-medium text-texto-inverso/70 hover:text-texto-inverso">
            Sair
          </button>
        </div>
      </div>
    </footer>
  )
}

/**
 * O menu do celular, numa gaveta que vem da direita.
 *
 * Fechada, ela continua na página (para poder deslizar), mas `inert`: nem o
 * Tab nem o leitor de tela chegam nela. Aberta, o fundo escurecido cobre o
 * resto, o foco vai para o botão Fechar e volta para o Menu ao fechar.
 */
function Gaveta({ aberta, aoFechar, aoAbrir, botaoMenu, tipo, aoVerPerfil }) {
  const [arrasto, setArrasto] = useState(0)
  const inicioDoToque = useRef(null)
  const botaoFechar = useRef(null)
  const jaAbriu = useRef(false)

  // Esc fecha; a página de trás não rola enquanto a gaveta está aberta.
  useEffect(() => {
    if (!aberta) return undefined
    const tecla = (evento) => evento.key === "Escape" && aoFechar()
    document.addEventListener("keydown", tecla)
    const rolagem = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", tecla)
      document.body.style.overflow = rolagem
    }
  }, [aberta, aoFechar])

  // O foco acompanha: abre no Fechar, volta ao Menu.
  useEffect(() => {
    if (aberta) {
      jaAbriu.current = true
      botaoFechar.current?.focus()
    } else if (jaAbriu.current) {
      botaoMenu.current?.focus()
    }
  }, [aberta, botaoMenu])

  // Puxar da borda direita da tela abre a gaveta, como nos apps do celular.
  useEffect(() => {
    if (aberta) return undefined
    let inicio = null
    const comecar = (evento) => {
      const dedo = evento.touches[0]
      inicio = window.innerWidth < 768 && dedo.clientX > window.innerWidth - BORDA_DA_TELA ? dedo.clientX : null
    }
    const mover = (evento) => {
      if (inicio !== null && inicio - evento.touches[0].clientX > ARRASTO_PARA_ABRIR) {
        inicio = null
        aoAbrir()
      }
    }
    document.addEventListener("touchstart", comecar, { passive: true })
    document.addEventListener("touchmove", mover, { passive: true })
    return () => {
      document.removeEventListener("touchstart", comecar)
      document.removeEventListener("touchmove", mover)
    }
  }, [aberta, aoAbrir])

  // Empurrar a gaveta aberta para a direita: ela acompanha o dedo e, passado
  // ARRASTO_PARA_FECHAR, fecha; antes disso, volta para o lugar.
  const toque = {
    onTouchStart: (evento) => { inicioDoToque.current = evento.touches[0].clientX },
    onTouchMove: (evento) => {
      if (inicioDoToque.current === null) return
      setArrasto(Math.max(0, evento.touches[0].clientX - inicioDoToque.current))
    },
    onTouchEnd: () => {
      if (arrasto > ARRASTO_PARA_FECHAR) aoFechar()
      inicioDoToque.current = null
      setArrasto(0)
    },
  }

  return (
    <div className="md:hidden">
      <div aria-hidden="true" onClick={aoFechar}
        className={`fixed inset-0 z-40 bg-navy-900/50 transition-opacity duration-300 motion-reduce:transition-none ${aberta ? "opacity-100" : "pointer-events-none opacity-0"}`} />
      <aside id="gaveta-menu" role="dialog" aria-modal="true" aria-label="Menu" inert={!aberta} {...toque}
        style={aberta && arrasto ? { transform: `translateX(${arrasto}px)` } : undefined}
        className={[
          "fixed top-0 right-0 z-50 flex h-dvh w-[min(84vw,320px)] flex-col bg-navy-900 px-4 py-4 text-texto-inverso shadow-2xl",
          arrasto ? "" : "transition-transform duration-300 ease-out motion-reduce:transition-none",
          aberta ? "translate-x-0" : "translate-x-full",
        ].join(" ")}>
        <div className="mb-4 flex items-center justify-between">
          <span className="px-2 text-sm font-semibold text-texto-inverso/75">Menu</span>
          <button ref={botaoFechar} type="button" onClick={aoFechar}
            className="flex items-center gap-2 rounded-campo px-3 py-2 text-sm font-semibold text-white transition hover:bg-navy-700">
            <Icone nome="fechar" />
            Fechar
          </button>
        </div>
        <ItensDoMenu tipo={tipo} aoEscolher={aoFechar} />
        <Rodape aoVerPerfil={aoVerPerfil} />
      </aside>
    </div>
  )
}

/** O cabeçalho de cada página: título e uma linha do que ela é. */
export function Cabecalho({ titulo, descricao, children }) {
  useTituloDaPagina(titulo)
  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-5 pr-14">
      <div>
        <h1 className="text-[28px] leading-tight font-semibold text-navy-900 sm:text-[32px]">{titulo}</h1>
        {descricao && <p className="mt-1.5 max-w-2xl text-[15px] text-texto-secundario">{descricao}</p>}
      </div>
      {/* Quebra linha no celular: busca, seletor e botões lado a lado não cabem em 390 px. */}
      {children && <div className="flex w-full flex-wrap items-center gap-3 sm:w-auto">{children}</div>}
    </header>
  )
}
