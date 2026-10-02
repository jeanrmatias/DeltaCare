import { Cartao, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { ListaComContador } from "../../componentes/ListaComContador"
import { useApi } from "../../hooks/useApi"
import { useSessao } from "../../hooks/useSessao"
import { Cabecalho } from "../../layout/Painel"
import { nomeExibicao } from "../../lib/usuario"

/**
 * Tela inicial da administração: o tamanho da instituição e o que está
 * esperando uma decisão.
 *
 * No front antigo havia um "Próximo passo" fixo, que mandava criar turmas e
 * apontava para a tela que hoje se chama Disciplinas. Texto fixo envelhece
 * sem ninguém ver; uma lista do que está pendente, vinda do servidor, não.
 */
export function InicioAdmin() {
  const { usuario } = useSessao()
  const professores = useApi("/admin/professores")
  const turmas = useApi("/admin/turmas")
  const denuncias = useApi("/admin/denuncias?status=aberta")
  const privacidade = useApi("/admin/privacidade/solicitacoes?status=pendente")

  const disciplinas = turmas.dados?.turmas || []
  const abertas = denuncias.dados?.resumo?.abertas || 0
  const pedidos = privacidade.dados?.contagem?.pendente || 0

  const pendencias = [
    abertas > 0 && {
      chave: "denuncias",
      numero: abertas,
      titulo: abertas === 1 ? "Denúncia de conteúdo aberta" : "Denúncias de conteúdo abertas",
      detalhe: "Reportadas por alunos e professores",
      para: "/admin/denuncias",
    },
    pedidos > 0 && {
      chave: "privacidade",
      numero: pedidos,
      titulo: pedidos === 1 ? "Pedido sobre dados pessoais" : "Pedidos sobre dados pessoais",
      detalhe: "Correção ou exclusão de conta (LGPD)",
      para: "/admin/privacidade",
    },
  ].filter(Boolean)

  return (
    <>
      <Cabecalho titulo={`Olá, ${nomeExibicao(usuario)}`} descricao="Painel de administração do Delta Care." />

      {turmas.erro && <EstadoVazio>{turmas.erro}</EstadoVazio>}

      <Numeros>
        <Numero rotulo="Professores cadastrados" valor={(professores.dados?.professores || []).length} />
        <Numero rotulo="Disciplinas" valor={disciplinas.length} />
        <Numero rotulo="Materiais cadastrados" valor={disciplinas.reduce((soma, t) => soma + (t.total_materiais || 0), 0)} />
      </Numeros>

      <Cartao titulo="Esperando a administração" className="max-w-2xl">
        <ListaComContador
          erro={(denuncias.erro || privacidade.erro) && "Não foi possível carregar as pendências."}
          vazio="Nada pendente. Denúncias e pedidos sobre dados pessoais aparecem aqui."
          itens={pendencias}
        />
      </Cartao>
    </>
  )
}
