import { Link } from "react-router"

import { Botao } from "../componentes/Botao"
import { Modal } from "../componentes/Modal"
import { useApi } from "../hooks/useApi"
import { iniciaisDe, nomeExibicao } from "../lib/usuario"

const PERFIS = { adm: "Administração", professor: "Professor", aluno: "Aluno" }

/**
 * Os dados da própria conta, de `/eu`. Só leitura: o aluno corrige um dado
 * pedindo à administração, pela tela Meus dados (LGPD).
 */
export function Perfil({ aoFechar }) {
  const { dados, erro } = useApi("/eu")
  const nome = nomeExibicao(dados)
  const turmas = dados?.turmas || []

  const linhas = dados
    ? [
        ["E-mail", dados.email],
        ["Matrícula", dados.matricula],
        ["Disciplinas", dados.disciplinas],
        [dados.tipo === "professor" ? "Disciplinas que leciona" : "Disciplinas que cursa", turmas.map((t) => `${t.nome} · ${t.semestre}`).join("\n")],
      ].filter(([, valor]) => valor) // campo vazio não vira linha: "Matrícula: —" só diz que falta algo
    : []

  return (
    <Modal aberto aoFechar={aoFechar}>
      {erro && <p className="text-sm text-texto-secundario">{erro}</p>}
      {dados?.sucesso && (
        <>
          <div className="mb-4 flex items-center gap-3">
            <span className="flex size-12 items-center justify-center rounded-full bg-primaria text-base font-bold text-white">{iniciaisDe(nome)}</span>
            <div>
              <strong className="block text-base text-navy-900">{nome}</strong>
              <span className="text-[13px] text-texto-secundario">{PERFIS[dados.tipo] || dados.tipo}</span>
            </div>
          </div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            {linhas.map(([rotulo, valor]) => (
              <div key={rotulo} className="contents">
                <dt className="text-texto-secundario">{rotulo}</dt>
                <dd className="whitespace-pre-line text-texto">{valor}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-[13px] text-texto-secundario">
            {dados.tipo === "aluno" ? (
              <>Algum dado errado? Peça a correção, baixe uma cópia ou peça a exclusão em{" "}
                <Link to="/aluno/meus-dados" onClick={aoFechar} className="font-semibold text-primaria hover:underline">Meus dados</Link>.</>
            ) : "Para alterar estes dados, fale com a administração."}
          </p>
        </>
      )}
      <div className="mt-5 flex justify-end"><Botao onClick={aoFechar}>Fechar</Botao></div>
    </Modal>
  )
}
