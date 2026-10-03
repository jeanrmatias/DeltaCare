import { useState } from "react"

import { Botao } from "../../componentes/Botao"
import { Carregando, EstadoVazio } from "../../componentes/Cartao"
import { Visualizador } from "../../componentes/Visualizador"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { useSessao } from "../../hooks/useSessao"
import { Cabecalho } from "../../layout/Painel"
import { baixarArquivo, podeVisualizar } from "../../lib/arquivos"
import { ROTULOS_TIPO_MATERIAL } from "../../lib/formatos"

/**
 * Semestres anteriores: o material das disciplinas que já terminaram. Um
 * componente para aluno e professor; o servidor devolve só o que cada um pode
 * ver, e a diferença aqui é só a rota.
 *
 * A busca vai até dentro dos PDFs. Para quem vai prestar residência, o que se
 * procura raramente está no título ("Aula 7"): está no texto ("forame
 * magno"). O trecho que o servidor devolve diz por que aquele material veio.
 */
export function Historico() {
  const { usuario } = useSessao()
  const aluno = usuario.tipo === "aluno"
  const [digitado, setDigitado] = useState("")
  const [busca, setBusca] = useState("")
  const { dados, carregando, erro } = useApi(`${aluno ? "/aluno/historico" : "/historico"}${busca ? `?busca=${encodeURIComponent(busca)}` : ""}`)
  const [vendo, setVendo] = useState(null)

  const arquivoDe = (material) => (aluno ? `/aluno/materiais/${material.id}/arquivo` : `/materiais/${material.id}/arquivo`)
  const semestres = dados?.semestres || []
  const total = semestres.reduce((soma, s) => soma + s.disciplinas.reduce((p, d) => p + d.materiais.length, 0), 0)

  let resumo = ""
  if (busca && dados && !dados.busca) resumo = "Digite pelo menos 3 letras para buscar. Mostrando tudo."
  else if (dados?.busca) resumo = total === 1 ? `1 material com "${dados.busca}".` : `${total} materiais com "${dados.busca}".`

  return (
    <>
      <Cabecalho titulo="Semestres anteriores"
        descricao={`O material das disciplinas que já terminaram.${dados?.semestre_vigente ? ` Semestre atual: ${dados.semestre_vigente}.` : ""}`} />

      <form role="search" onSubmit={(evento) => { evento.preventDefault(); setBusca(digitado.trim()) }}
        className="mb-5 rounded-cartao bg-superficie p-5 shadow-cartao">
        <label htmlFor="busca-historico" className="mb-2 block text-[13px] font-medium text-texto">Buscar no material, inclusive dentro dos PDFs</label>
        <div className="flex flex-col gap-2.5 sm:flex-row">
          <input id="busca-historico" type="search" value={digitado} autoComplete="off" placeholder="ex.: forame magno"
            onChange={(evento) => { setDigitado(evento.target.value); if (!evento.target.value.trim()) setBusca("") }}
            className="min-w-0 flex-1 rounded-campo border border-borda-campo px-3 py-2.5 text-sm outline-none focus:border-primaria" />
          <Botao tipo="submit">Buscar</Botao>
        </div>
        {resumo && <p className="mt-2 text-[13px] text-texto-secundario">{resumo}</p>}
      </form>

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados?.sucesso && semestres.length === 0 && (
        <EstadoVazio>
          {dados.busca ? `Nada com "${dados.busca}" nos semestres anteriores.`
            : aluno ? "Você ainda não tem semestres anteriores. As disciplinas aparecem aqui quando o semestre virar."
              : "Você ainda não tem disciplinas de semestres anteriores."}
        </EstadoVazio>
      )}

      {semestres.map((semestre) => (
        <section key={semestre.semestre} className="mb-7">
          <h2 className="mb-3 text-[13px] font-bold tracking-widest text-texto-secundario uppercase">{semestre.semestre}</h2>
          <div className="flex flex-col gap-3">
            {semestre.disciplinas.map((disciplina) => (
              // Com busca, as disciplinas já abrem: o resultado está lá dentro.
              <details key={disciplina.id} open={Boolean(dados.busca)} className="group rounded-cartao bg-superficie shadow-cartao">
                <summary className="flex cursor-pointer list-none flex-wrap items-baseline gap-x-3 gap-y-1 p-5">
                  <span className="text-texto-secundario transition group-open:rotate-90" aria-hidden="true">›</span>
                  <strong className="text-navy-900">{disciplina.nome}</strong>
                  <span className="text-[13px] text-texto-secundario">
                    Prof. {disciplina.professor_nome} · {disciplina.materiais.length === 1 ? "1 material" : `${disciplina.materiais.length} materiais`}
                  </span>
                </summary>
                <div className="flex flex-col gap-3 px-5 pb-5">
                  {disciplina.materiais.length === 0 && <p className="text-sm text-texto-secundario">Nenhum material publicado nesta disciplina.</p>}
                  {disciplina.materiais.map((material) => (
                    <MaterialAntigo key={material.id} material={material} caminho={arquivoDe(material)} aoVer={() => setVendo(material)} />
                  ))}
                </div>
              </details>
            ))}
          </div>
        </section>
      ))}

      {vendo && <Visualizador material={vendo} caminho={arquivoDe(vendo)} aoFechar={() => setVendo(null)} />}
    </>
  )
}

const classeAcao = "rounded-campo border px-3.5 py-2 text-[13px] font-semibold transition"

function MaterialAntigo({ material, caminho, aoVer }) {
  const [baixando, setBaixando] = useState(false)
  const { avisar } = useDialogo()
  const visualizavel = podeVisualizar(material)

  async function baixar() {
    setBaixando(true)
    try {
      await baixarArquivo(caminho, material.arquivo_nome)
    } catch (erro) {
      console.error("Erro ao baixar material:", erro)
      await avisar("Não foi possível baixar este material.", "Algo deu errado")
    } finally {
      setBaixando(false)
    }
  }

  return (
    <article className="flex flex-col gap-3 rounded-bloco border border-borda p-4 md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <span className="rounded-campo bg-fundo px-2 py-0.5 text-[11px] font-bold tracking-wide text-texto-secundario uppercase">
          {ROTULOS_TIPO_MATERIAL[material.tipo] || material.tipo}
        </span>
        <h3 className="mt-1.5 font-bold text-navy-900">{material.titulo}</h3>
        {material.classificacao && <p className="mt-1 text-xs font-medium text-primaria">{material.classificacao}</p>}
        {material.trecho ? (
          <blockquote className="mt-2 border-l-3 border-alerta bg-alerta-fundo px-3 py-1.5 text-[13px] text-texto">{material.trecho}</blockquote>
        ) : material.descricao && <p className="mt-1.5 text-[13px] text-texto-secundario">{material.descricao}</p>}
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        {material.tipo === "link" && material.link_url && (
          <a href={material.link_url} target="_blank" rel="noopener noreferrer" className={`${classeAcao} border-primaria bg-primaria text-white`}>Abrir link</a>
        )}
        {material.tipo !== "link" && visualizavel && (
          <button type="button" onClick={aoVer} className={`${classeAcao} border-primaria bg-primaria text-white`}>Visualizar</button>
        )}
        {material.tipo !== "link" && material.arquivo_nome && (
          <button type="button" onClick={baixar} disabled={baixando}
            className={`${classeAcao} ${visualizavel ? "border-borda bg-superficie text-texto" : "border-primaria bg-primaria text-white"}`}>
            {baixando ? "Baixando..." : "Baixar"}
          </button>
        )}
      </div>
    </article>
  )
}
