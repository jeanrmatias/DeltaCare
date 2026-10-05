import { useEffect, useState } from "react"

import { api } from "../lib/api"
import { mimeVisualizavel } from "../lib/arquivos"
import { Botao } from "./Botao"
import { Modal } from "./Modal"

/**
 * Abre o material dentro da plataforma, sem baixar.
 *
 * O arquivo é buscado autenticado e vira um endereço local (blob). Um
 * <iframe src="/aluno/materiais/1/arquivo"> não serviria: a navegação do
 * iframe não envia o token, e passá-lo na URL o deixaria nos logs.
 */
export function Visualizador({ material, caminho, aoFechar }) {
  const mime = mimeVisualizavel(material.arquivo_nome)
  const [estado, setEstado] = useState({ url: null, erro: false })

  useEffect(() => {
    let url = null
    let vigente = true

    api(caminho)
      .then((resposta) => (resposta.ok ? resposta.blob() : Promise.reject(new Error(String(resposta.status)))))
      .then((blob) => {
        if (!vigente) return
        url = URL.createObjectURL(new Blob([blob], { type: mime }))
        setEstado({ url, erro: false })
      })
      .catch((erro) => {
        console.error("Erro ao abrir material:", erro)
        if (vigente) setEstado({ url: null, erro: true })
      })

    // Ao fechar, o endereço local é liberado: senão o arquivo fica na memória.
    return () => {
      vigente = false
      if (url) URL.revokeObjectURL(url)
    }
  }, [caminho, mime])

  return (
    <Modal aberto aoFechar={aoFechar} largura="max-w-[1040px]" rotulo={material.titulo}>
      <div className="mb-3 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <strong className="block truncate text-navy-900">{material.titulo}</strong>
          <span className="text-xs text-texto-secundario">{[material.turma_nome, material.arquivo_nome].filter(Boolean).join(" · ")}</span>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {/* O Chrome do Android não mostra PDF dentro da página (e o iPhone,
              só a primeira folha): em outra aba, abre o leitor do aparelho. */}
          {estado.url && mime === "application/pdf" && (
            <a href={estado.url} target="_blank" rel="noopener" className="text-[14px] font-semibold text-primaria hover:underline">
              Abrir em outra aba
            </a>
          )}
          <Botao variante="neutra" onClick={aoFechar} className="py-2">Fechar</Botao>
        </div>
      </div>

      <div className="flex h-[min(78vh,820px)] items-center justify-center overflow-hidden rounded-bloco bg-fundo">
        {estado.erro && <p className="text-sm text-texto-secundario">Não foi possível carregar este material.</p>}
        {!estado.erro && !estado.url && <p className="text-sm text-texto-secundario">Carregando material...</p>}
        {estado.url && <Conteudo mime={mime} url={estado.url} titulo={material.titulo} />}
      </div>
    </Modal>
  )
}

function Conteudo({ mime, url, titulo }) {
  if (mime.startsWith("image/")) return <img src={url} alt={titulo} className="max-h-full max-w-full object-contain" />
  if (mime.startsWith("video/")) return <video src={url} controls className="max-h-full max-w-full" />
  if (mime.startsWith("audio/")) return <audio src={url} controls />
  return <iframe src={url} title={titulo} className="size-full border-0 bg-white" />
}
