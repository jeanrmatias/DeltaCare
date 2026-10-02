/** Minúsculas e sem acento: "forame" acha "Forâme" e "FORAME". */
export function normalizar(texto) {
  return String(texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
}
