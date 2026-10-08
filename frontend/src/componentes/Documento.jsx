import { Link } from "react-router"

import { useSessao } from "../hooks/useSessao"
import { useTituloDaPagina } from "../hooks/useTituloDaPagina"
import { INICIO_DO_PERFIL } from "../lib/usuario"

/**
 * A moldura dos documentos públicos (Privacidade, Termos de uso): legíveis
 * antes de entrar, e por quem já entrou, que volta para o próprio início.
 */
export function Documento({ titulo, subtitulo, children }) {
  const { usuario } = useSessao()
  const voltar = usuario ? INICIO_DO_PERFIL[usuario.tipo] : "/"
  useTituloDaPagina(titulo)

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <main className="rounded-cartao bg-superficie px-6 py-8 shadow-cartao sm:px-10">
        <h1 className="text-[32px] leading-tight font-semibold tracking-tight text-navy-900">{titulo}</h1>
        <p className="mt-1 text-sm text-texto-secundario">{subtitulo}</p>
        {children}
      </main>
      {/* Dentro de um <footer>: conteúdo fora de toda região (main, nav,
          footer) fica de fora da navegação por regiões do leitor de tela. */}
      <footer>
        <Link to={voltar} className="mt-6 block text-center text-sm font-medium text-primaria hover:underline">
          ← {usuario ? "Voltar para o início" : "Voltar para o login"}
        </Link>
      </footer>
    </div>
  )
}

export function Titulo({ children }) {
  return <h2 className="mt-9 mb-2 text-[20px] font-semibold text-navy-900">{children}</h2>
}

export function Paragrafo({ children }) {
  return <p className="mt-3 text-sm leading-relaxed text-texto">{children}</p>
}

export function Lista({ children }) {
  return <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-texto">{children}</ul>
}

export function AvisoDeAprovacao({ children }) {
  return <div className="mt-6 rounded-bloco bg-alerta-fundo px-4 py-3 text-sm text-texto">{children}</div>
}
