import { Link } from "react-router"

/**
 * Lista curta de "o que espera você": um número em vermelho, um título e uma
 * linha de detalhe; o item inteiro leva à tela onde se resolve.
 *
 * `itens`: [{ chave, numero, titulo, detalhe, para }]. `vazio` é o texto
 * quando não há nada — e `erro`, quando não deu para buscar.
 */
export function ListaComContador({ itens, vazio, erro }) {
  if (erro) return <p className="py-3.5 text-[14px] text-texto-secundario">{erro}</p>
  if (!itens.length) return <p className="py-3.5 text-[14px] text-texto-secundario">{vazio}</p>

  return (
    <ul>
      {itens.map((item) => (
        <li key={item.chave} className="border-b border-borda last:border-b-0">
          <Link to={item.para} className="flex items-start gap-2.5 rounded-campo px-1 py-2.5 hover:bg-fundo">
            <span className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-perigo px-[5px] text-[12px] font-bold text-white">
              {item.numero}
            </span>
            <span className="flex min-w-0 flex-col gap-0.5">
              <strong className="text-[14.5px] leading-snug font-semibold text-texto">{item.titulo}</strong>
              {item.detalhe && <span className="truncate text-xs text-texto-secundario">{item.detalhe}</span>}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
