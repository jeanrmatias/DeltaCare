import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// O Vite é a ferramenta de build: em desenvolvimento serve as telas com
// recarga instantânea (npm run dev, porta 5173); no build gera a pasta dist/,
// com nomes de arquivo novos a cada versão — é isso que aposenta o `?v=N` que
// o front antigo pedia trocar à mão em cada página.
//
// `base`: as telas moram em /app/ — no servidor de verdade, a raiz é da API
// (/aluno/materiais é rota da API; a tela é /app/aluno/materiais).
export default defineConfig({
  base: "/app/",
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true },
})
