import { useState } from "react"
import { Link } from "react-router"

import { Botao } from "../../componentes/Botao"
import { Carregando, Cartao } from "../../componentes/Cartao"
import { AreaDeTexto, Escolha, MensagemDeFormulario, Texto } from "../../componentes/Campos"
import { AcoesDoModal, Modal } from "../../componentes/Modal"
import { Selo } from "../../componentes/Selo"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { dataComAno } from "../../lib/formatos"
import { nomeArquivoDaCopia, statusPrivacidade } from "../../lib/privacidade"

/**
 * Os direitos do titular (LGPD), na tela do próprio aluno. A cópia sai na
 * hora; correção e exclusão viram pedido para a administração.
 */
export function MeusDados() {
  const pedidos = useApi("/aluno/privacidade/solicitacoes")
  const prazo = pedidos.dados?.prazo_anonimizacao_dias ?? 45

  return (
    <>
      <Cabecalho titulo="Meus dados" descricao="Uma cópia de tudo, correção do que estiver errado e exclusão da conta." />
      <div className="flex max-w-3xl flex-col gap-5">
        <Copia aoBaixar={pedidos.recarregar} />
        <Correcao aoPedir={pedidos.recarregar} />
        <Exclusao prazo={prazo} aoPedir={pedidos.recarregar} />
        <Cartao titulo="Seus pedidos">
          {pedidos.carregando && <Carregando />}
          {pedidos.erro && <p className="text-sm text-texto-secundario">{pedidos.erro}</p>}
          {pedidos.dados && !pedidos.dados.solicitacoes.length && <p className="text-sm text-texto-secundario">Nenhum pedido ainda.</p>}
          <div className="flex flex-col gap-2.5">
            {(pedidos.dados?.solicitacoes || []).map((pedido) => (
              <Pedido key={pedido.id} pedido={pedido} aoCancelar={pedidos.recarregar} />
            ))}
          </div>
        </Cartao>
        <p className="text-[13px] text-texto-secundario">
          Como a plataforma trata seus dados: <Link to="/privacidade" className="font-semibold text-primaria hover:underline">política de privacidade</Link>.
        </p>
      </div>
    </>
  )
}

function Copia({ aoBaixar }) {
  const [estado, setEstado] = useState({ enviando: false, texto: "", sucesso: false })

  async function baixar() {
    setEstado({ enviando: true, texto: "Preparando a cópia...", sucesso: false })
    try {
      const resultado = await (await api("/aluno/privacidade/exportar")).json()
      if (!resultado.sucesso) return setEstado({ enviando: false, texto: resultado.mensagem || "Não foi possível gerar a cópia.", sucesso: false })

      // O arquivo nasce no próprio navegador: os dados já vieram na resposta,
      // e uma segunda rota só para o download seria outra porta a proteger.
      const url = URL.createObjectURL(new Blob([JSON.stringify(resultado.dados, null, 2)], { type: "application/json" }))
      const ancora = document.createElement("a")
      ancora.href = url
      ancora.download = nomeArquivoDaCopia(resultado.dados.gerado_em)
      ancora.click()
      URL.revokeObjectURL(url)

      setEstado({ enviando: false, texto: "Cópia baixada.", sucesso: true })
      aoBaixar()
    } catch (erro) {
      console.error("Erro ao exportar:", erro)
      setEstado({ enviando: false, texto: ERRO_DE_CONEXAO, sucesso: false })
    }
  }

  return (
    <Cartao titulo="Baixar uma cópia">
      <p className="mb-4 text-sm leading-relaxed text-texto-secundario">
        Tudo o que a plataforma guarda sobre você: cadastro, disciplinas, entregas e notas, material que abriu,
        favoritos, anotações, conversas com o assistente e com os professores. Sai na hora, num arquivo que qualquer
        programa abre.
      </p>
      <Botao onClick={baixar} desativado={estado.enviando}>Baixar meus dados</Botao>
      <MensagemDeFormulario texto={estado.texto} sucesso={estado.sucesso} />
    </Cartao>
  )
}

const CAMPOS = [
  { valor: "nome", rotulo: "Nome" },
  { valor: "email", rotulo: "E-mail" },
  { valor: "matricula", rotulo: "Matrícula" },
]

function Correcao({ aoPedir }) {
  const [campo, setCampo] = useState("nome")
  const [valor, setValor] = useState("")
  const [motivo, setMotivo] = useState("")
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })

  async function pedir(evento) {
    evento.preventDefault()
    try {
      const resultado = await (await api("/aluno/privacidade/solicitacoes", {
        method: "POST",
        body: JSON.stringify({ tipo: "correcao", campo, valor_novo: valor, motivo }),
      })).json()
      setMensagem({ texto: resultado.mensagem, sucesso: resultado.sucesso })
      if (resultado.sucesso) {
        setValor("")
        setMotivo("")
        aoPedir()
      }
    } catch (erro) {
      console.error("Erro ao pedir correção:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO, sucesso: false })
    }
  }

  return (
    <Cartao titulo="Corrigir um dado">
      <p className="mb-4 text-sm text-texto-secundario">A administração confere com o registro acadêmico antes de trocar. Você recebe uma notificação com a resposta.</p>
      <form onSubmit={pedir} className="flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row">
          <Escolha rotulo="O que está errado" valor={campo} aoMudar={setCampo} opcoes={CAMPOS} className="sm:w-48" />
          <Texto rotulo="Como deveria ser" valor={valor} aoMudar={setValor} maximo={500} obrigatorio className="flex-1" />
        </div>
        <Texto rotulo="Observação (opcional)" valor={motivo} aoMudar={setMotivo} maximo={500} placeholder="Ex.: meu nome saiu sem o segundo sobrenome" />
        <div><Botao tipo="submit">Enviar pedido</Botao></div>
        <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />
      </form>
    </Cartao>
  )
}

function Exclusao({ prazo, aoPedir }) {
  const [aberto, setAberto] = useState(false)
  const [motivo, setMotivo] = useState("")
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })

  async function pedir(evento) {
    evento.preventDefault()
    try {
      const resultado = await (await api("/aluno/privacidade/solicitacoes", {
        method: "POST",
        body: JSON.stringify({ tipo: "exclusao", motivo }),
      })).json()
      setMensagem({ texto: resultado.mensagem, sucesso: resultado.sucesso })
      setAberto(false)
      if (resultado.sucesso) aoPedir()
    } catch (erro) {
      console.error("Erro ao pedir exclusão:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO, sucesso: false })
    }
  }

  return (
    <Cartao titulo="Excluir minha conta">
      <p className="mb-4 text-sm leading-relaxed text-texto-secundario">
        O pedido vai para a administração. Aprovado, a conta é desativada na hora e, <strong>{prazo}</strong> dias depois,
        seus dados pessoais são anonimizados: nome, e-mail, matrícula, anotações, favoritos e conversas deixam de existir.
        Notas e entregas continuam no registro acadêmico da faculdade, que é obrigada a guardá-lo, mas sem nada que
        identifique você. Até o fim do prazo, a secretaria pode reativar a conta.
      </p>
      <Botao variante="perigo" onClick={() => setAberto(true)}>Pedir a exclusão da conta</Botao>
      <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />

      <Modal aberto={aberto} aoFechar={() => setAberto(false)} titulo="Excluir minha conta">
        <p className="mb-4 text-sm text-texto-secundario">Aprovado o pedido, você não entra mais na plataforma. Antes, vale baixar a cópia dos seus dados.</p>
        <form onSubmit={pedir}>
          <AreaDeTexto rotulo="Motivo (opcional)" valor={motivo} aoMudar={setMotivo} linhas={3} maximo={500} />
          <AcoesDoModal>
            <Botao variante="neutra" onClick={() => setAberto(false)}>Cancelar</Botao>
            <Botao tipo="submit" variante="perigo">Enviar pedido</Botao>
          </AcoesDoModal>
        </form>
      </Modal>
    </Cartao>
  )
}

function Pedido({ pedido, aoCancelar }) {
  const { confirmar, avisar } = useDialogo()
  const status = statusPrivacidade(pedido.status)
  const detalhes = [
    pedido.valor_novo && `Pedido: ${pedido.valor_novo}`,
    pedido.resposta && `Resposta da administração: ${pedido.resposta}`,
    pedido.status === "agendada" && pedido.anonimizar_em && `Os dados pessoais serão anonimizados em ${dataComAno(pedido.anonimizar_em)}.`,
  ].filter(Boolean)

  async function cancelar() {
    if (!(await confirmar("Cancelar este pedido?", { titulo: pedido.tipo_rotulo, rotulo: "Cancelar pedido" }))) return
    try {
      const resultado = await (await api(`/aluno/privacidade/solicitacoes/${pedido.id}`, { method: "DELETE" })).json()
      if (!resultado.sucesso) await avisar(resultado.mensagem, "Algo deu errado")
      aoCancelar()
    } catch (erro) {
      console.error("Erro ao cancelar pedido:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <article className="flex flex-col gap-3 rounded-bloco bg-fundo px-4 py-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <span className="text-xs text-texto-secundario">{dataComAno(pedido.criado_em)}</span>
          <Selo tom={status.tom}>{status.rotulo}</Selo>
        </div>
        <h3 className="text-sm font-bold text-navy-900">{pedido.campo_rotulo ? `${pedido.tipo_rotulo}: ${pedido.campo_rotulo}` : pedido.tipo_rotulo}</h3>
        {detalhes.map((texto) => <p key={texto} className="mt-1 text-[13px] text-texto-secundario">{texto}</p>)}
      </div>
      {pedido.status === "pendente" && <Botao variante="neutra" onClick={cancelar} className="shrink-0 py-2 text-[13px]">Cancelar pedido</Botao>}
    </article>
  )
}

