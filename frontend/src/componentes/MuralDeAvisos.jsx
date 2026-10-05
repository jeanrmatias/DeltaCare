import { useApi } from "../hooks/useApi"
import { dataCurta } from "../lib/formatos"
import { Aviso } from "./Aviso"
import { Cartao } from "./Cartao"

/**
 * Os avisos recebidos, na tela inicial (aluno e professor).
 *
 * Sem aviso, sem cartão: um "Nenhum aviso" fixo ocuparia a tela inicial para
 * dizer nada. Se a busca falhar, também some — o mural é complemento, e não
 * pode derrubar o resto da tela. Urgente recente vem primeiro (o servidor
 * ordena).
 */
export function MuralDeAvisos({ limite = 5 }) {
  const { dados } = useApi("/avisos/recebidos")
  const avisos = (dados?.avisos || []).slice(0, limite)

  if (!avisos.length) return null

  return (
    <Cartao titulo="Avisos" className="mb-5">
      <div className="flex flex-col gap-2.5">
        {avisos.map((aviso) => (
          <ItemDoMural key={aviso.id} aviso={aviso} />
        ))}
      </div>
    </Cartao>
  )
}

function ItemDoMural({ aviso }) {
  const autor = aviso.autor_e_administracao ? "Coordenação" : `Prof. ${aviso.autor}`
  return <Aviso aviso={aviso} rodape={[autor, dataCurta(aviso.criado_em), aviso.disciplinas.join(", ")].filter(Boolean).join(" · ")} />
}
