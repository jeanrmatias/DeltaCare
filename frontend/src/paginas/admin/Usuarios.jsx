import { useState } from "react"

import { Botao } from "../../componentes/Botao"
import { Carregando, Cartao, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { AreaDeTexto, Escolha, MensagemDeFormulario, Texto } from "../../componentes/Campos"
import { AcoesDoModal, Modal } from "../../componentes/Modal"
import { Selo } from "../../componentes/Selo"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { useSessao } from "../../hooks/useSessao"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { dataComAno } from "../../lib/formatos"
import { normalizar } from "../../lib/texto"
import { useEnvio } from "../../hooks/useEnvio"

/**
 * Contas da plataforma. É o único caminho de entrada: não existe cadastro
 * público — quem é aluno da faculdade é decidido pela secretaria, não por
 * quem preenche um formulário.
 */
const PERFIS = { adm: "Administrador", professor: "Professor", aluno: "Aluno" }

export function Usuarios() {
  const { usuario } = useSessao()
  const { dados, carregando, erro, recarregar } = useApi("/admin/usuarios")
  const turmas = useApi("/admin/turmas")
  const [aberto, setAberto] = useState(null) // "conta" | "planilha" | null
  const [busca, setBusca] = useState("")
  const [excluindo, setExcluindo] = useState(null)
  const [aviso, setAviso] = useState("")
  const { confirmar } = useDialogo()
  // Conta anonimizada não é mais de ninguém: só segura notas e entregas do
  // registro acadêmico. Não aparece na lista nem nos números.
  const todos = (dados?.usuarios || []).filter((u) => !u.anonimizado)
  const professoresAtivos = todos.filter((u) => u.tipo === "professor" && !u.desativado)
  const termo = normalizar(busca.trim())
  const filtrados = todos.filter((u) => !termo || normalizar(`${u.email} ${u.nome || ""}`).includes(termo))
  const contar = (tipo) => todos.filter((u) => u.tipo === tipo).length
  const opcoesTurma = (turmas.dados?.turmas || []).map((t) => ({ valor: String(t.id), rotulo: `${t.nome} · ${t.semestre}` }))

  return (
    <>
      <Cabecalho titulo="Usuários" descricao="Contas com acesso à plataforma. Toda conta nasce aqui ou pela planilha.">
        <input type="search" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome ou e-mail" aria-label="Buscar usuários"
          className="w-56 max-w-full rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria" />
        <Botao variante="neutra" onClick={() => setAberto(aberto === "planilha" ? null : "planilha")}>Importar planilha</Botao>
        <Botao onClick={() => setAberto(aberto === "conta" ? null : "conta")}>Nova conta</Botao>
      </Cabecalho>

      {dados?.sucesso && (
        <Numeros>
          <Numero rotulo="Administradores" valor={contar("adm")} />
          <Numero rotulo="Professores" valor={contar("professor")} />
          <Numero rotulo="Alunos" valor={contar("aluno")} />
        </Numeros>
      )}

      {aberto === "conta" && <NovaConta turmas={opcoesTurma} aoFechar={() => setAberto(null)} aoCriar={recarregar} />}
      {aberto === "planilha" && <Importacao turmas={opcoesTurma} aoFechar={() => setAberto(null)} aoImportar={recarregar} />}

      {aviso && <p role="status" className="mb-4 text-sm font-medium text-sucesso">{aviso}</p>}
      {excluindo && (
        <ExcluirConta conta={excluindo} professores={professoresAtivos.filter((p) => p.email !== excluindo.email)}
          aoFechar={() => setExcluindo(null)}
          aoExcluir={(mensagem) => { setExcluindo(null); setAviso(mensagem); recarregar() }} />
      )}

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados?.sucesso && !filtrados.length && <EstadoVazio>{todos.length ? "Nenhuma conta corresponde à sua busca." : "Nenhuma conta cadastrada."}</EstadoVazio>}

      <section className="flex flex-col gap-2.5">
        {filtrados.map((conta) => (
          <article key={conta.email} className="rounded-cartao bg-superficie px-5 py-4 shadow-cartao">
            {/* Sem flex-wrap: com wrap, um e-mail comprido empurrava o botão
                para baixo em uns cartões e não em outros. O texto encolhe e
                quebra; o botão fica sempre no mesmo canto. */}
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <Selo tom={conta.tipo === "adm" ? "perigo" : conta.tipo === "professor" ? "alerta" : "neutro"}>{PERFIS[conta.tipo] || conta.tipo}</Selo>
                  {conta.desativado && <Selo tom="perigo">Desativada · anonimiza em {dataComAno(conta.anonimizar_em)}</Selo>}
                  {conta.email === usuario.email && <span className="text-xs font-semibold text-texto-secundario">você</span>}
                </div>
                <h2 className="text-[17px] font-semibold text-navy-900">{conta.nome || conta.email}</h2>
                <p className="text-[14px] [overflow-wrap:anywhere] text-texto-secundario">{conta.email}</p>
                <p className="mt-0.5 text-xs font-medium text-primaria">{vinculo(conta)}</p>
              </div>
              {conta.tipo !== "adm" && !conta.desativado && (
                <Botao variante="neutra" pequeno className="shrink-0" onClick={() => { setAviso(""); setExcluindo(conta) }}>Excluir</Botao>
              )}
              {conta.desativado && conta.exclusao_id && (
                <Botao variante="neutra" pequeno className="shrink-0" onClick={() => desfazer(conta)}>Desfazer exclusão</Botao>
              )}
            </div>
          </article>
        ))}
      </section>
    </>
  )

  async function desfazer(conta) {
    const sim = await confirmar(`Desfazer a exclusão de ${conta.nome || conta.email}?\n\nA conta volta a entrar com a senha de antes. ` +
      (conta.tipo === "professor" ? "As disciplinas que passaram para outro professor continuam com ele: atribua de volta em Disciplinas, se for o caso." : ""),
    { titulo: "Desfazer exclusão", rotulo: "Desfazer" })
    if (!sim) return
    try {
      const resultado = await (await api(`/admin/privacidade/solicitacoes/${conta.exclusao_id}/reverter`, { method: "POST" })).json()
      setAviso(resultado.mensagem || "")
      recarregar()
    } catch (erro) {
      console.error("Erro ao desfazer exclusão:", erro)
      setAviso(ERRO_DE_CONEXAO)
    }
  }
}

/**
 * Excluir é desativar agora e anonimizar em 45 dias (regras/privacidade.py):
 * até lá, "Desfazer exclusão" devolve a conta. Professor com disciplina só
 * sai com alguém para assumi-las — o material e as notas são do curso.
 */
function ExcluirConta({ conta, professores, aoFechar, aoExcluir }) {
  const [motivo, setMotivo] = useState("")
  const [novo, setNovo] = useState("")
  const [mensagem, setMensagem] = useState("")
  const [enviando, setEnviando] = useState(false)
  const temDisciplinas = conta.tipo === "professor" && conta.total_turmas > 0

  async function excluir(evento) {
    evento.preventDefault()
    setEnviando(true)
    try {
      const corpo = { email: conta.email, motivo: motivo.trim(), novo_professor_email: novo }
      const resultado = await (await api("/admin/usuarios/exclusao", { method: "POST", body: JSON.stringify(corpo) })).json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem)
      aoExcluir(resultado.mensagem)
    } catch (erro) {
      console.error("Erro ao excluir conta:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal aberto aoFechar={aoFechar} titulo={`Excluir ${conta.nome || conta.email}`}>
      <p className="mb-4 text-sm leading-relaxed text-texto-secundario">
        A conta para de entrar agora. Em 45 dias, nome, e-mail e o que é pessoal são anonimizados;
        {conta.tipo === "aluno" ? " notas e entregas ficam no registro acadêmico, sem identificação." : " o material e as atividades continuam nas disciplinas."}
        {" "}Até lá dá para desfazer.
      </p>
      <form onSubmit={excluir} className="flex flex-col gap-4">
        {temDisciplinas && (
          <Escolha rotulo={conta.total_turmas === 1 ? "Quem assume a disciplina dele" : `Quem assume as ${conta.total_turmas} disciplinas dele`} valor={novo} aoMudar={setNovo}
            opcoes={[{ valor: "", rotulo: professores.length ? "Escolha um professor" : "Nenhum outro professor ativo" },
              ...professores.map((p) => ({ valor: p.email, rotulo: p.nome ? `${p.nome} · ${p.email}` : p.email }))]} />
        )}
        <AreaDeTexto rotulo="Motivo (fica registrado)" valor={motivo} aoMudar={setMotivo} linhas={3} maximo={500}
          placeholder="Ex.: transferido para outra instituição" obrigatorio />
        <MensagemDeFormulario texto={mensagem} />
        <AcoesDoModal>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
          <Botao variante="perigo" tipo="submit" desativado={enviando || (temDisciplinas && !novo)}>{enviando ? "Excluindo..." : "Excluir conta"}</Botao>
        </AcoesDoModal>
      </form>
    </Modal>
  )
}

function vinculo(conta) {
  if (conta.tipo === "professor") {
    const n = conta.total_turmas || 0
    const disciplinas = n === 0 ? "Nenhuma disciplina atribuída" : `${n} disciplina${n > 1 ? "s" : ""} atribuída${n > 1 ? "s" : ""}`
    return conta.disciplinas ? `${disciplinas} · ${conta.disciplinas}` : disciplinas
  }
  if (conta.tipo === "aluno") {
    const n = conta.total_matriculas || 0
    return [conta.matricula && `Matrícula ${conta.matricula}`, n === 0 ? "Sem disciplina" : `Em ${n} disciplina${n > 1 ? "s" : ""}`].filter(Boolean).join(" · ")
  }
  return "Acesso completo à administração"
}

const CONTA_VAZIA = { nome: "", email: "", senha: "", tipo: "aluno", matricula: "", disciplinas: "", turma_id: "" }

function NovaConta({ turmas, aoFechar, aoCriar }) {
  const [campos, setCampos] = useState(CONTA_VAZIA)
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })
  const mudar = (nome) => (valor) => setCampos((atual) => ({ ...atual, [nome]: valor }))

  const [enviando, executar] = useEnvio()

  async function criar(evento) {
    evento.preventDefault()
    const corpo = { ...campos, nome: campos.nome.trim(), email: campos.email.trim(), matricula: campos.matricula.trim(), disciplinas: campos.disciplinas.trim() }
    delete corpo.turma_id
    if (campos.tipo === "aluno" && campos.turma_id) corpo.turma_id = Number(campos.turma_id)
    try {
      const resultado = await (await api("/admin/usuarios", { method: "POST", body: JSON.stringify(corpo) })).json()
      setMensagem({ texto: resultado.mensagem || "", sucesso: resultado.sucesso })
      if (resultado.sucesso) { setCampos(CONTA_VAZIA); aoCriar() }
    } catch (erro) {
      console.error("Erro ao criar conta:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO })
    }
  }

  return (
    <Cartao titulo="Nova conta" className="mb-5">
      <p className="mb-4 text-[14px] text-texto-secundario">Toda conta nasce aqui ou pela importação da planilha, inclusive a de aluno: não existe cadastro pela tela de login.</p>
      <form onSubmit={executar(criar)} className="grid gap-4 sm:grid-cols-2">
        <Texto rotulo="Nome completo" valor={campos.nome} aoMudar={mudar("nome")} placeholder="Ex.: Ana Paula Ribeiro" obrigatorio />
        <Escolha rotulo="Perfil" valor={campos.tipo} aoMudar={mudar("tipo")} opcoes={[{ valor: "aluno", rotulo: "Aluno" }, { valor: "professor", rotulo: "Professor" }, { valor: "adm", rotulo: "Administrador" }]} />
        <Texto rotulo="E-mail institucional" tipo="email" valor={campos.email} aoMudar={mudar("email")} placeholder="nome@instituicao.edu.br" obrigatorio />
        <Texto rotulo="Senha provisória" valor={campos.senha} aoMudar={mudar("senha")} placeholder="mínimo 8 caracteres" obrigatorio />
        {/* Só os campos do perfil escolhido: matrícula de administrador seria um
            campo vazio dando a entender que faltou um dado. */}
        {campos.tipo === "aluno" && (
          <>
            <Texto rotulo="Matrícula" valor={campos.matricula} aoMudar={mudar("matricula")} placeholder="Ex.: 2026001234" />
            <Escolha rotulo="Matricular já em uma disciplina" valor={campos.turma_id} aoMudar={mudar("turma_id")} opcoes={[{ valor: "", rotulo: "Não matricular agora" }, ...turmas]} />
          </>
        )}
        {campos.tipo === "professor" && (
          <Texto rotulo="Disciplinas que leciona" valor={campos.disciplinas} aoMudar={mudar("disciplinas")} placeholder="Separe por ponto e vírgula: Cardiologia; Clínica Médica" className="sm:col-span-2" />
        )}
        <div className="flex gap-2.5 sm:col-span-2">
          <Botao tipo="submit" desativado={enviando}>Criar conta</Botao>
          <Botao variante="neutra" onClick={aoFechar}>Fechar</Botao>
        </div>
      </form>
      <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />
    </Cartao>
  )
}

function lerBase64(arquivo) {
  return new Promise((resolver, rejeitar) => {
    const leitor = new FileReader()
    leitor.onload = () => resolver(String(leitor.result).split(",")[1])
    leitor.onerror = rejeitar
    leitor.readAsDataURL(arquivo)
  })
}

/**
 * Importação em duas etapas, de propósito: "Conferir" lê e valida sem gravar
 * nada, e só então "Importar". Uma planilha com metade das linhas erradas não
 * deve criar metade das contas para a secretaria descobrir depois.
 */
function Importacao({ turmas, aoFechar, aoImportar }) {
  const [arquivo, setArquivo] = useState(null)
  const [senha, setSenha] = useState("")
  const [turma, setTurma] = useState("")
  const [relatorio, setRelatorio] = useState(null)
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })
  const [ocupado, setOcupado] = useState(false)
  const { avisar } = useDialogo()

  async function corpoDaPlanilha() {
    if (!arquivo) {
      await avisar("Escolha uma planilha primeiro.", "Nenhum arquivo")
      return null
    }
    return { arquivo_base64: await lerBase64(arquivo), arquivo_nome: arquivo.name }
  }

  async function conferir() {
    const corpo = await corpoDaPlanilha()
    if (!corpo) return
    setOcupado(true)
    setMensagem({ texto: "Conferindo..." })
    try {
      const resultado = await (await api("/admin/importar/analisar", { method: "POST", body: JSON.stringify(corpo) })).json()
      if (!resultado.sucesso) { setRelatorio(null); return setMensagem({ texto: resultado.mensagem }) }
      setMensagem({ texto: "" })
      setRelatorio({ ...resultado, importado: false })
    } catch (erro) {
      console.error("Erro ao conferir planilha:", erro)
      setMensagem({ texto: "Não foi possível conferir a planilha." })
    } finally {
      setOcupado(false)
    }
  }

  async function importar(evento) {
    evento.preventDefault()
    const corpo = await corpoDaPlanilha()
    if (!corpo) return
    if (senha.length < 8) return setMensagem({ texto: "A senha provisória precisa ter pelo menos 8 caracteres." })
    setOcupado(true)
    setMensagem({ texto: "Importando..." })
    try {
      const resultado = await (await api("/admin/importar", {
        method: "POST", body: JSON.stringify({ ...corpo, senha_padrao: senha, ...(turma && { turma_id: Number(turma) }) }),
      })).json()
      setMensagem({ texto: resultado.mensagem || "", sucesso: resultado.sucesso })
      if (resultado.sucesso) { setRelatorio({ ...resultado, importado: true }); aoImportar() }
    } catch (erro) {
      console.error("Erro ao importar:", erro)
      setMensagem({ texto: "Não foi possível importar a planilha." })
    } finally {
      setOcupado(false)
    }
  }

  const prontos = relatorio ? (relatorio.importado ? relatorio.criados : relatorio.validos)?.length || 0 : 0
  const rejeitados = relatorio?.rejeitados || []

  return (
    <Cartao titulo="Importar alunos de uma planilha" className="mb-5">
      <p className="mb-4 text-[14px] text-texto-secundario">
        Aceita <strong>.csv</strong> e <strong>.xlsx</strong>. A planilha precisa ter uma coluna de nome e uma de e-mail; matrícula é opcional.
        O cabeçalho pode estar escrito de várias formas ("Nome Completo", "Aluno", "E-mail", "RA").
      </p>
      <form onSubmit={importar} className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-[14px] font-medium text-texto">
          Planilha
          <input type="file" accept=".csv,.xlsx,.xlsm" required onChange={(e) => { setArquivo(e.target.files?.[0] || null); setRelatorio(null); setMensagem({ texto: "" }) }}
            className="text-sm font-normal" />
        </label>
        <Texto rotulo="Senha provisória" valor={senha} aoMudar={setSenha} placeholder="mínimo 8 caracteres" obrigatorio />
        <Escolha rotulo="Matricular todos na disciplina" valor={turma} aoMudar={setTurma} opcoes={[{ valor: "", rotulo: "Não matricular agora" }, ...turmas]} />
        <div className="flex flex-wrap items-end gap-2.5">
          <Botao variante="neutra" onClick={conferir} desativado={ocupado}>Conferir planilha</Botao>
          {/* Importar só depois de conferir, e só se houver linha válida. */}
          <Botao tipo="submit" desativado={ocupado || !relatorio || relatorio.importado || !prontos}>Importar</Botao>
          <Botao variante="neutra" onClick={aoFechar}>Fechar</Botao>
        </div>
      </form>
      <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />

      {/* O relatório linha a linha é o ponto do recurso: sem ele, a secretaria
          sabe que "faltaram 3", mas não quais nem por quê. */}
      {relatorio && (
        <div className="mt-4">
          <div className="flex flex-wrap gap-2">
            <Selo tom="sucesso">{relatorio.importado ? `${prontos} conta(s) criada(s)` : `${prontos} linha(s) pronta(s) para importar`}</Selo>
            {rejeitados.length > 0 && <Selo tom="perigo">{rejeitados.length} rejeitada(s)</Selo>}
          </div>
          {rejeitados.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1.5">
              {rejeitados.map((item) => (
                <li key={item.linha} className="rounded-campo bg-perigo-fundo px-3 py-1.5 text-[14px]">
                  <strong>Linha {item.linha}</strong> — {[item.email || item.nome, item.motivo].filter(Boolean).join(" — ")}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Cartao>
  )
}
