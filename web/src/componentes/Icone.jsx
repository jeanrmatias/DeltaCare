/**
 * Os ícones do Delta Care, um por conceito.
 *
 * No front antigo cada página trazia o SVG colado no próprio HTML, e o mesmo
 * conceito tinha desenhos diferentes conforme a tela (o "Início" do professor
 * era outra casa; "Avisos" tinha dois megafones). Aqui é um lugar só.
 */
const DESENHOS = {
  inicio: <><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /></>,
  chat: <path d="M21 12a8.5 8.5 0 0 1-8.9 8.5c-1.4 0-2.7-.3-3.9-.9L3 21l1.5-4.7A8.5 8.5 0 1 1 21 12Z" />,
  mensagens: <path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 9 9 0 0 1-3.5-.8L3 21l1.6-4.7A8.4 8.4 0 0 1 12 3a8.4 8.4 0 0 1 9 8.5Z" />,
  materiais: <><path d="M12 6.5C10.5 5 8 4.5 4 4.5v13c4 0 6.5.5 8 2 1.5-1.5 4-2 8-2v-13c-4 0-6.5.5-8 2Z" /><path d="M12 6.5v13" /></>,
  atividades: <><rect x="3" y="3" width="18" height="18" rx="3" /><path d="M8 12l3 3 5-6" /></>,
  desempenho: <path d="M6 20V10M12 20V4M18 20v-7" />,
  denuncias: <><path d="M12 9v4M12 16.5h.01" /><path d="M10.3 4.3 2.8 17a1.7 1.7 0 0 0 1.5 2.5h15.4a1.7 1.7 0 0 0 1.5-2.5L13.7 4.3a1.7 1.7 0 0 0-3 0Z" /></>,
  favoritos: <path d="m12 4 2.4 4.9 5.4.8-3.9 3.8.9 5.4-4.8-2.5-4.8 2.5.9-5.4L4.2 9.7l5.4-.8Z" />,
  anotacoes: <path d="M16 3H8a2 2 0 0 0-2 2v14l6-3 6 3V5a2 2 0 0 0-2-2Z" />,
  ranking: <><path d="M8 21h8M12 17v4" /><path d="M7 4h10v5a5 5 0 0 1-10 0Z" /><path d="M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3" /></>,
  historico: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 4v4h4" /><path d="M12 8v4l3 2" /></>,
  calendario: <><rect x="3" y="4.5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 9.5h18" /></>,
  turmas: <><circle cx="9" cy="8" r="3.2" /><path d="M2.5 20c0-3.3 2.9-6 6.5-6s6.5 2.7 6.5 6" /><circle cx="17" cy="9" r="2.6" /><path d="M15.5 14c2.7.3 4.5 2.6 4.5 6" /></>,
  avisos: <><path d="M3 11v2a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1Z" /><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" /></>,
  usuarios: <><circle cx="12" cy="8" r="3.5" /><path d="M4.5 20c0-4.1 3.4-7.5 7.5-7.5s7.5 3.4 7.5 7.5" /></>,
  lacunas: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14" /><path d="M12 17h.01" /></>,
  privacidade: <><path d="M12 3 5 6v5c0 4.5 3 8.3 7 10 4-1.7 7-5.5 7-10V6Z" /><path d="m9 12 2 2 4-4" /></>,
  marca: <><path d="M12 3 3 8l9 5 9-5-9-5Z" /><path d="M3 8v8l9 5 9-5V8" /></>,
  sino: <><path d="M18 8.5a6 6 0 1 0-12 0c0 6-2.5 7.5-2.5 7.5h17S18 14.5 18 8.5Z" /><path d="M10.5 19a1.7 1.7 0 0 0 3 0" /></>,
}

/**
 * `nome` escolhe o desenho; `tamanho` em pixels. Decorativo por padrão
 * (aria-hidden): o texto ao lado é que diz o que o botão faz.
 */
export function Icone({ nome, tamanho = 18, className = "" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={tamanho}
      height={tamanho}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {DESENHOS[nome]}
    </svg>
  )
}
