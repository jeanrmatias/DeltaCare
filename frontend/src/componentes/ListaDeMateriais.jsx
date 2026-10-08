import { useState } from "react"

import { useDialogo } from "../hooks/useDialogo"
import { baixarArquivo, podeVisualizar } from "../lib/arquivos"
import { ROTULOS_TIPO_MATERIAL } from "../lib/formatos"
import { PainelAnotacoes } from "./Anotacoes"
import { BotaoFavorito } from "./BotaoFavorito"
import { ModalReportar } from "./Reportar"
import { Visualizador } from "./Visualizador"

/**
 * Materiais na visão do aluno, com tudo o que ele faz em cada um: abrir,
 * baixar, favoritar, anotar e reportar. Usada em Materiais e em Favoritos —
 * o mesmo gesto tem que se comportar igual nas duas.
 *
 * `aoDesfavoritar(material)`: a tela de Favoritos tira o item da lista.
 */
export function ListaDeMateriais({ materiais, aoDesfavoritar }) {
  // Qual janela está aberta, e para qual material. Uma de cada vez.
  const [janela, setJanela] = useState(null)
  const [totais, setTotais] = useState({})
  const fechar = () => setJanela(null)

  return (
    <section className="flex flex-col gap-3">
      {materiais.map((material) => (
        <ItemMaterial
          key={material.id}
          material={material}
          totalAnotacoes={totais[material.id] ?? material.total_anotacoes}
          abrir={(tipo) => setJanela({ tipo, material })}
          aoDesfavoritar={aoDesfavoritar}
        />
      ))}

      {janela?.tipo === "ver" && (
        <Visualizador material={janela.material} caminho={`/aluno/materiais/${janela.material.id}/arquivo`} aoFechar={fechar} />
      )}
      {janela?.tipo === "anotar" && (
        <PainelAnotacoes material={janela.material} aoFechar={fechar}
          aoMudar={(total) => setTotais((atual) => ({ ...atual, [janela.material.id]: total }))} />
      )}
      {janela?.tipo === "reportar" && <ModalReportar material={janela.material} aoFechar={fechar} />}
    </section>
  )
}

const classeAcao = "rounded-campo border px-3.5 py-2 text-[14px] font-semibold transition"
const acaoPrimaria = `${classeAcao} border-primaria bg-primaria text-white hover:bg-primaria-escura`
const acaoNeutra = `${classeAcao} border-borda bg-superficie text-texto hover:bg-fundo`

function ItemMaterial({ material, totalAnotacoes, abrir, aoDesfavoritar }) {
  const [baixando, setBaixando] = useState(false)
  const { avisar } = useDialogo()
  const visualizavel = podeVisualizar(material)
  const classificacao = [material.assunto, material.topico, material.aula].filter(Boolean).join(" · ")
  const publicado = new Date(material.criado_em)

  async function baixar() {
    setBaixando(true)
    try {
      await baixarArquivo(`/aluno/materiais/${material.id}/arquivo`, material.arquivo_nome)
    } catch (erro) {
      console.error("Erro ao baixar material:", erro)
      await avisar("Não foi possível baixar este material.", "Algo deu errado")
    } finally {
      setBaixando(false)
    }
  }

  return (
    <article className="flex flex-col gap-4 rounded-cartao bg-superficie p-5 shadow-cartao md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <div className="mb-1.5 flex flex-wrap items-center gap-2">
          <span className="rounded-campo bg-fundo px-2 py-0.5 text-[12px] font-bold tracking-wide text-texto-secundario uppercase">
            {ROTULOS_TIPO_MATERIAL[material.tipo] || material.tipo}
          </span>
          <span className="text-xs font-semibold text-texto-secundario">
            {[material.turma_nome, material.semestre].filter(Boolean).join(" · ")}
          </span>
          <BotaoFavorito material={material} aoMudar={(favorito) => !favorito && aoDesfavoritar?.(material)} />
        </div>
        <h2 className="text-base font-semibold text-navy-900">{material.titulo}</h2>
        {classificacao && <p className="mt-1 text-xs font-medium text-primaria">{classificacao}</p>}
        {material.descricao && <p className="mt-1.5 text-[14px] leading-relaxed text-texto-secundario">{material.descricao}</p>}
        {!Number.isNaN(publicado.getTime()) && (
          <p className="mt-1.5 text-xs text-texto-secundario">Publicado em {publicado.toLocaleDateString("pt-BR")}</p>
        )}
      </div>

      <div className="flex shrink-0 flex-wrap gap-2 md:justify-end">
        {material.tipo === "link" && material.link_url && (
          <a href={material.link_url} target="_blank" rel="noopener noreferrer" className={acaoPrimaria}>Abrir link</a>
        )}
        {material.tipo !== "link" && visualizavel && (
          <button type="button" onClick={() => abrir("ver")} className={acaoPrimaria}>Visualizar</button>
        )}
        {material.tipo !== "link" && material.arquivo_nome && (
          <button type="button" onClick={baixar} disabled={baixando} className={visualizavel ? acaoNeutra : acaoPrimaria}>
            {baixando ? "Baixando..." : "Baixar"}
          </button>
        )}
        <button type="button" onClick={() => abrir("anotar")} className={acaoNeutra}>
          {totalAnotacoes ? `Anotações (${totalAnotacoes})` : "Anotar"}
        </button>
        <button type="button" onClick={() => abrir("reportar")} className="px-2 py-2 text-[14px] font-semibold text-texto-secundario hover:text-perigo">
          Reportar
        </button>
      </div>
    </article>
  )
}
