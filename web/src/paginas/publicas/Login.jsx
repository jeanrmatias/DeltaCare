import { useState } from "react"
import { Link, useLocation, useNavigate } from "react-router"

import { Botao } from "../../componentes/Botao"
import { CampoTexto } from "../../componentes/CampoTexto"
import { Icone } from "../../componentes/Icone"
import { useSessao } from "../../hooks/useSessao"
import { useTituloDaPagina } from "../../hooks/useTituloDaPagina"
import { apiPublica, ERRO_DE_CONEXAO } from "../../lib/api"
import { INICIO_DO_PERFIL } from "../../lib/usuario"

/**
 * Login e recuperação de senha, na mesma tela.
 *
 * A recuperação era uma sequência de caixas de diálogo; aqui é a mesma tela
 * mudando de etapa (`etapa`), e o e-mail digitado no login já vem preenchido.
 *
 * Professor e administração têm uma etapa a mais: a senha certa leva ao
 * código que chega por e-mail (o segundo fator), e só ele abre a sessão.
 */
export function Login() {
  const [etapa, setEtapa] = useState("entrar")
  const [email, setEmail] = useState("")
  const [desafio, setDesafio] = useState(null)
  useTituloDaPagina("Entrar")

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-4">
      <div className="w-full max-w-[420px] rounded-cartao bg-superficie px-6 py-7 shadow-cartao">
        <div className="mb-2 flex items-center justify-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-campo bg-primaria text-white">
            <Icone nome="marca" />
          </span>
          <h1 className="text-[26px] font-bold text-navy-900">Delta Care</h1>
        </div>

        {etapa === "entrar" && (
          <FormularioEntrar email={email} setEmail={setEmail} aoEsquecer={() => setEtapa("pedir")}
            aoPedirCodigo={(dados) => { setDesafio(dados); setEtapa("codigo") }} />
        )}
        {etapa === "codigo" && desafio && (
          <FormularioCodigo desafio={desafio} aoVoltar={() => { setDesafio(null); setEtapa("entrar") }} />
        )}
        {etapa === "pedir" && (
          <FormularioPedirCodigo
            email={email}
            setEmail={setEmail}
            aoEnviar={() => setEtapa("redefinir")}
            aoVoltar={() => setEtapa("entrar")}
          />
        )}
        {etapa === "redefinir" && (
          <FormularioRedefinir email={email} aoTerminar={() => setEtapa("entrar")} aoVoltar={() => setEtapa("pedir")} />
        )}
      </div>

      <nav aria-label="Documentos" className="flex gap-4 text-[13px] font-medium text-texto-secundario">
        <Link to="/privacidade" className="hover:text-primaria">Privacidade e uso de dados</Link>
        <Link to="/termos" className="hover:text-primaria">Termos de uso</Link>
      </nav>
    </main>
  )
}

function Subtitulo({ children }) {
  return <p className="mb-3 text-center text-sm text-texto-secundario">{children}</p>
}

function Mensagem({ texto, sucesso = false }) {
  return (
    <p role="alert" className={`mt-4 min-h-5 text-center text-[13px] font-medium ${sucesso ? "text-sucesso" : "text-perigo"}`}>
      {texto}
    </p>
  )
}

function LinkDeTexto({ children, onClick }) {
  return (
    <button type="button" onClick={onClick} className="mt-4 block w-full text-center text-[13px] font-medium text-primaria hover:underline">
      {children}
    </button>
  )
}

/** Guarda a sessão e leva para onde a pessoa tentava ir — ou para o início do perfil. */
function useConcluirLogin() {
  const { entrar } = useSessao()
  const navegar = useNavigate()
  const local = useLocation()

  return (dados) => {
    entrar(dados)
    if (dados.trocar_senha) return navegar("/trocar-senha", { replace: true })
    // Volta para onde a pessoa tentava ir antes do login, se for do perfil
    // dela; senão, para o início do perfil.
    const inicio = INICIO_DO_PERFIL[dados.tipo] ?? "/"
    const destino = local.state?.de
    navegar(destino && destino.startsWith(inicio) ? destino : inicio, { replace: true })
  }
}

function FormularioEntrar({ email, setEmail, aoEsquecer, aoPedirCodigo }) {
  const [senha, setSenha] = useState("")
  const [mensagem, setMensagem] = useState("")
  const [enviando, setEnviando] = useState(false)
  const concluir = useConcluirLogin()

  async function enviar(evento) {
    evento.preventDefault()
    setMensagem("")
    setEnviando(true)

    try {
      const resposta = await apiPublica("/login", { email: email.trim(), senha })
      const dados = await resposta.json()

      if (dados.sucesso && dados.segundo_fator) return aoPedirCodigo(dados)
      if (!dados.sucesso || !dados.token) {
        setMensagem(dados.mensagem || "E-mail ou senha incorretos.")
        return
      }
      concluir(dados)
    } catch (erro) {
      console.error("Erro no login:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={enviar}>
      <Subtitulo>Entre com sua conta para continuar</Subtitulo>
      <CampoTexto rotulo="E-mail" tipo="email" valor={email} aoMudar={setEmail} placeholder="seu@email.com" autoComplete="email" obrigatorio />
      <CampoTexto rotulo="Senha" tipo="password" valor={senha} aoMudar={setSenha} placeholder="Digite sua senha" autoComplete="current-password" obrigatorio />
      <Botao tipo="submit" largo desativado={enviando} className="mt-6">
        {enviando ? "Entrando..." : "Entrar"}
      </Botao>
      <LinkDeTexto onClick={aoEsquecer}>Esqueci minha senha</LinkDeTexto>
      <Mensagem texto={mensagem} />
    </form>
  )
}

/** O código de 6 dígitos que chegou no e-mail (professor e administração). */
function FormularioCodigo({ desafio, aoVoltar }) {
  const [codigo, setCodigo] = useState("")
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })
  const [enviando, setEnviando] = useState(false)
  const [expirado, setExpirado] = useState(false)
  const concluir = useConcluirLogin()

  async function confirmar(evento) {
    evento.preventDefault()
    setEnviando(true)
    try {
      const dados = await (await apiPublica("/login/codigo", { desafio: desafio.desafio, codigo: codigo.trim() })).json()
      if (dados.sucesso && dados.token) return concluir(dados)
      setMensagem({ texto: dados.mensagem || "Código incorreto.", sucesso: false })
      setExpirado(Boolean(dados.expirado))
      setCodigo("")
    } catch (erro) {
      console.error("Erro ao conferir o código:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO, sucesso: false })
    } finally {
      setEnviando(false)
    }
  }

  async function reenviar() {
    try {
      const dados = await (await apiPublica("/login/codigo/reenviar", { desafio: desafio.desafio })).json()
      setMensagem({ texto: dados.mensagem, sucesso: Boolean(dados.sucesso) })
      setExpirado(Boolean(dados.expirado))
    } catch (erro) {
      console.error("Erro ao reenviar o código:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO, sucesso: false })
    }
  }

  return (
    <form onSubmit={confirmar}>
      <Subtitulo>
        Enviamos um código de 6 dígitos para <strong>{desafio.email_mascarado}</strong>. Ele vale por 10 minutos.
      </Subtitulo>
      {!expirado && (
        <>
          <CampoTexto rotulo="Código" valor={codigo} aoMudar={(valor) => setCodigo(valor.replace(/\D/g, "").slice(0, 6))}
            autoComplete="one-time-code" placeholder="000000" obrigatorio minimo={6} maximo={6} modoTeclado="numeric" />
          <Botao tipo="submit" largo desativado={enviando || codigo.length !== 6} className="mt-6">
            {enviando ? "Conferindo..." : "Entrar"}
          </Botao>
          <LinkDeTexto onClick={reenviar}>Não chegou? Enviar outro código</LinkDeTexto>
        </>
      )}
      {expirado && <Botao largo onClick={aoVoltar} className="mt-4">Entrar de novo</Botao>}
      {!expirado && <LinkDeTexto onClick={aoVoltar}>Voltar</LinkDeTexto>}
      <Mensagem texto={mensagem.texto} sucesso={mensagem.sucesso} />
    </form>
  )
}

function FormularioPedirCodigo({ email, setEmail, aoEnviar, aoVoltar }) {
  const [mensagem, setMensagem] = useState("")
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setEnviando(true)
    setMensagem("")

    try {
      // A resposta é a mesma exista a conta ou não: a tela segue adiante nos
      // dois casos, para não virar verificador de quem é aluno daqui.
      const resposta = await apiPublica("/recuperar-senha", { email: email.trim() })
      const dados = await resposta.json()
      if (!resposta.ok) {
        setMensagem(dados.mensagem || "Não foi possível iniciar a recuperação.")
        return
      }
      aoEnviar()
    } catch (erro) {
      console.error("Erro na recuperação de senha:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={enviar}>
      <Subtitulo>Enviaremos um código de recuperação para o e-mail da conta.</Subtitulo>
      <CampoTexto rotulo="E-mail da conta" tipo="email" valor={email} aoMudar={setEmail} placeholder="nome@instituicao.edu.br" autoComplete="email" obrigatorio />
      <Botao tipo="submit" largo desativado={enviando} className="mt-6">
        {enviando ? "Enviando..." : "Enviar código"}
      </Botao>
      <LinkDeTexto onClick={aoVoltar}>Voltar para o login</LinkDeTexto>
      <Mensagem texto={mensagem} />
    </form>
  )
}

function FormularioRedefinir({ email, aoTerminar, aoVoltar }) {
  const [codigo, setCodigo] = useState("")
  const [senha, setSenha] = useState("")
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })
  const [enviando, setEnviando] = useState(false)
  const [concluido, setConcluido] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setEnviando(true)

    try {
      const resposta = await apiPublica("/redefinir-senha", { email: email.trim(), token: codigo.trim(), nova_senha: senha })
      const dados = await resposta.json()
      setMensagem({ texto: dados.mensagem || "Não foi possível redefinir a senha.", sucesso: Boolean(dados.sucesso) })
      setConcluido(Boolean(dados.sucesso))
    } catch (erro) {
      console.error("Erro ao redefinir a senha:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO, sucesso: false })
    } finally {
      setEnviando(false)
    }
  }

  if (concluido) {
    return (
      <div>
        <Mensagem texto={mensagem.texto} sucesso />
        <Botao largo onClick={aoTerminar} className="mt-4">Entrar com a nova senha</Botao>
      </div>
    )
  }

  return (
    <form onSubmit={enviar}>
      <Subtitulo>
        Se houver uma conta com <strong>{email}</strong>, o código chegou por e-mail. Ele vale por 15 minutos.
      </Subtitulo>
      <CampoTexto rotulo="Código de recuperação" valor={codigo} aoMudar={setCodigo} autoComplete="one-time-code" obrigatorio />
      <CampoTexto rotulo="Nova senha" tipo="password" valor={senha} aoMudar={setSenha} placeholder="mínimo 8 caracteres" autoComplete="new-password" minimo={8} obrigatorio />
      <Botao tipo="submit" largo desativado={enviando} className="mt-6">
        {enviando ? "Salvando..." : "Redefinir senha"}
      </Botao>
      <LinkDeTexto onClick={aoVoltar}>Pedir outro código</LinkDeTexto>
      <Mensagem texto={mensagem.texto} sucesso={mensagem.sucesso} />
    </form>
  )
}
