/**
 * Arquivos de material e de entrega: o que abre na plataforma e como baixar.
 */
import { api } from "./api.js"

const VISUALIZAVEIS = {
  pdf: "application/pdf",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  webp: "image/webp",
  mp4: "video/mp4",
  webm: "video/webm",
  mp3: "audio/mpeg",
  txt: "text/plain",
}

export function extensaoDe(nomeArquivo) {
  const partes = String(nomeArquivo || "").split(".")
  return partes.length > 1 ? partes.pop().toLowerCase() : ""
}

/** O tipo MIME para mostrar o arquivo na plataforma, ou "" se não abre aqui. */
export function mimeVisualizavel(nomeArquivo) {
  return VISUALIZAVEIS[extensaoDe(nomeArquivo)] || ""
}

export function podeVisualizar(material) {
  return material.tipo !== "link" && Boolean(mimeVisualizavel(material.arquivo_nome))
}

/**
 * Baixa pela rota autenticada. Não dá para ser um link direto: a navegação do
 * navegador não envia o header Authorization, e o token na URL ficaria no
 * histórico e nos logs do servidor.
 */
export async function baixarArquivo(caminho, nomeArquivo) {
  const resposta = await api(caminho)
  if (!resposta.ok) throw new Error(`Falha ao baixar (${resposta.status})`)

  const url = URL.createObjectURL(await resposta.blob())
  const ancora = document.createElement("a")
  ancora.href = url
  ancora.download = nomeArquivo || "arquivo"
  document.body.appendChild(ancora)
  ancora.click()
  ancora.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}
