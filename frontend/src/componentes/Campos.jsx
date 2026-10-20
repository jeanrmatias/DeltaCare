import { useId } from "react"

import { useVerSenha } from "../hooks/useVerSenha"

/**
 * Campos de formulário com rótulo em cima, no estilo das telas logadas
 * (o CampoTexto do login tem espaçamento próprio). Todos controlados:
 * `valor` + `aoMudar`.
 */
const classeCampo =
  "w-full rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm text-texto outline-none focus:border-primaria"

export function Rotulado({ rotulo, children, className = "", id: idDeFora }) {
  const idProprio = useId()
  const id = idDeFora ?? idProprio
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-[14px] font-medium text-texto">{rotulo}</label>
      {children(id)}
    </div>
  )
}

export function AreaDeTexto({ rotulo, valor, aoMudar, linhas = 4, maximo, placeholder, obrigatorio = false, className }) {
  return (
    <Rotulado rotulo={rotulo} className={className}>
      {(id) => (
        <textarea
          id={id}
          rows={linhas}
          value={valor}
          onChange={(evento) => aoMudar(evento.target.value)}
          maxLength={maximo}
          placeholder={placeholder}
          required={obrigatorio}
          className={`${classeCampo} resize-y`}
        />
      )}
    </Rotulado>
  )
}

export function Escolha({ rotulo, valor, aoMudar, opcoes, className }) {
  return (
    <Rotulado rotulo={rotulo} className={className}>
      {(id) => (
        <select id={id} value={valor} onChange={(evento) => aoMudar(evento.target.value)} className={classeCampo}>
          {opcoes.map((opcao) => <option key={opcao.valor} value={opcao.valor}>{opcao.rotulo}</option>)}
        </select>
      )}
    </Rotulado>
  )
}

export function Texto({ rotulo, valor, aoMudar, tipo = "text", placeholder, maximo, obrigatorio = false, className }) {
  // O id sai daqui, e não do Rotulado, porque o olho da senha precisa dele
  // antes do input existir (aria-controls).
  const id = useId()
  const senha = useVerSenha(tipo, id)
  return (
    <Rotulado rotulo={rotulo} className={className} id={id}>
      {() => (
        <div className="relative">
          <input
            id={id}
            type={senha.tipo}
            value={valor}
            onChange={(evento) => aoMudar(evento.target.value)}
            placeholder={placeholder}
            maxLength={maximo}
            required={obrigatorio}
            className={`${classeCampo} ${senha.botao ? "pr-11" : ""}`}
          />
          {senha.botao}
        </div>
      )}
    </Rotulado>
  )
}

/** Linha de mensagem de formulário: vermelha para erro, verde para sucesso. */
export function MensagemDeFormulario({ texto, sucesso = false }) {
  if (!texto) return null
  return <p role="alert" className={`mt-3 text-[14px] font-medium ${sucesso ? "text-sucesso" : "text-perigo"}`}>{texto}</p>
}
