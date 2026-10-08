import { useState } from "react"

import { Carregando, EstadoVazio } from "../../componentes/Cartao"
import { Selo } from "../../componentes/Selo"
import { Celula, Tabela } from "../../componentes/Tabela"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"
import { dataEHora } from "../../lib/formatos"

const PERIODOS = [["1", "Últimas 24 horas"], ["7", "Últimos 7 dias"], ["30", "Últimos 30 dias"], ["90", "Últimos 90 dias"], ["", "Tudo o que está guardado"]]

/**
 * A trilha de auditoria: quem fez o quê, quando, de onde, e se deu certo.
 *
 * Só leitura — não há como apagar ou editar um registro pela plataforma.
 * Senha, código de verificação e arquivo nunca aparecem: o servidor os tira
 * antes de gravar (backend/app/regras/auditoria.py).
 */
export function Auditoria() {
  const [filtros, setFiltros] = useState({ acao: "", busca: "", dias: "30", so_falhas: false })
  const consulta = new URLSearchParams({ acao: filtros.acao, busca: filtros.busca.trim(), so_falhas: filtros.so_falhas })
  if (filtros.dias) consulta.set("dias", filtros.dias)
  else consulta.set("dias", "0")
  const { dados, carregando, erro } = useApi(`/admin/auditoria?${consulta}`)
  const mudar = (campo) => (evento) =>
    setFiltros((atual) => ({ ...atual, [campo]: evento.target.type === "checkbox" ? evento.target.checked : evento.target.value }))
  const registros = dados?.registros || []

  return (
    <>
      <Cabecalho titulo="Auditoria" descricao="Quem fez o quê, quando e de onde: ações da administração, exclusões de conteúdo e acessos." />

      <section className="mb-5 flex flex-wrap items-end gap-3">
        <Filtro rotulo="Ação">
          <select value={filtros.acao} onChange={mudar("acao")} className={CAMPO}>
            <option value="">Todas</option>
            {(dados?.acoes || []).map((a) => <option key={a.valor} value={a.valor}>{a.rotulo}</option>)}
          </select>
        </Filtro>
        <Filtro rotulo="Período">
          <select value={filtros.dias} onChange={mudar("dias")} className={CAMPO}>
            {PERIODOS.map(([valor, rotulo]) => <option key={valor} value={valor}>{rotulo}</option>)}
          </select>
        </Filtro>
        <Filtro rotulo="Buscar e-mail, IP ou texto" largo>
          <input type="search" value={filtros.busca} onChange={mudar("busca")} autoComplete="off" placeholder="ex.: lucas.martins@" className={CAMPO} />
        </Filtro>
        <label className="flex items-center gap-2 pb-2.5 text-sm text-texto">
          <input type="checkbox" checked={filtros.so_falhas} onChange={mudar("so_falhas")} className="size-4 accent-primaria" />
          Só o que deu errado ou foi recusado
        </label>
      </section>

      {carregando && !dados && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados?.sucesso && !registros.length && <EstadoVazio>Nenhum registro com esses filtros.</EstadoVazio>}

      {registros.length > 0 && (
        <section className="rounded-cartao bg-superficie p-5 shadow-cartao">
          <Tabela rotulo="Trilha de auditoria" colunas={["Quando", "Quem", "Ação", "Detalhe", "Resultado", "IP"]}>
            {registros.map((r) => (
              <tr key={r.id}>
                <Celula>{dataEHora(r.quando)}</Celula>
                <Celula>{r.quem || "—"}</Celula>
                <Celula>{r.acao}</Celula>
                <Celula detalhe={r.mensagem || null}>{resumo(r.detalhe)}</Celula>
                <Celula>{r.sucesso ? <Selo tom="sucesso">Feito</Selo> : <Selo tom="perigo">{r.status >= 400 ? `Recusado (${r.status})` : "Não feito"}</Selo>}</Celula>
                <Celula>{r.ip || "—"}</Celula>
              </tr>
            ))}
          </Tabela>
          <p className="mt-4 text-xs text-texto-secundario">
            {registros.length >= dados.limite ? `Mostrando os ${dados.limite} mais recentes; use os filtros para achar o resto. ` : ""}
            Cada registro é guardado por {dados.retencao_dias} dias e depois apagado sozinho.
          </p>
        </section>
      )}
    </>
  )
}

const CAMPO = "rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm font-normal outline-none focus:border-primaria"

function Filtro({ rotulo, largo = false, children }) {
  return (
    <label className={`flex flex-col gap-1.5 text-[14px] font-medium text-texto ${largo ? "min-w-56 flex-1" : ""}`}>
      {rotulo}
      {children}
    </label>
  )
}

/** "email: nova@teste.com · tipo: aluno" — o que foi pedido, em uma linha. */
function resumo(detalhe) {
  const partes = { ...(detalhe?.parametros || {}), ...(detalhe?.dados || {}) }
  const texto = Object.entries(partes).filter(([, valor]) => valor !== "" && valor !== null && valor !== undefined)
    .map(([chave, valor]) => `${chave}: ${valor}`).join(" · ")
  return texto || "—"
}
