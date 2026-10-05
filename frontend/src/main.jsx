import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router"

import { App } from "./App"
import { DialogosProvider } from "./dialogos/DialogosProvider"
import "./index.css"
import { SessaoProvider } from "./sessao/SessaoProvider"

// A ordem importa: o BrowserRouter por fora (as rotas leem o endereço), a
// sessão por dentro dele (o login navega depois de entrar), e o App por último.
createRoot(document.getElementById("root")).render(
  <StrictMode>
    {/* basename "/app": as rotas do React (/aluno, /admin...) ficam embaixo
        dele, e a raiz do endereço continua sendo da API. */}
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "")}>
      <SessaoProvider>
        <DialogosProvider>
          <App />
        </DialogosProvider>
      </SessaoProvider>
    </BrowserRouter>
  </StrictMode>,
)
