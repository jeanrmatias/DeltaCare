import { useDialogo } from "../hooks/useDialogo"
import { baixarArquivo } from "../lib/arquivos"
import { Icone } from "./Icone"

/**
 * Um arquivo como botão de baixar, com o clipe na frente. É como o arquivo
 * que o professor anexou à atividade aparece nas três visões (aluno,
 * professor e coordenação), cada uma pela sua rota: quem pode baixar é o
 * servidor que decide, não esta tela.
 */
export function ArquivoParaBaixar({ caminho, nome }) {
  const { avisar } = useDialogo()

  async function baixar() {
    try {
      await baixarArquivo(caminho, nome)
    } catch (erro) {
      console.error("Erro ao baixar arquivo:", erro)
      await avisar("Não foi possível baixar o arquivo.", "Algo deu errado")
    }
  }

  return (
    <button type="button" onClick={baixar}
      className="inline-flex items-center gap-2 self-start rounded-campo border border-borda bg-superficie px-3 py-2 text-left text-[14px] font-semibold text-primaria hover:bg-fundo">
      <Icone nome="clipe" tamanho={16} className="shrink-0" />
      <span className="[overflow-wrap:anywhere]"><span className="sr-only">Baixar </span>{nome}</span>
    </button>
  )
}
