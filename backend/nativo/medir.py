"""Mede a similaridade do chat em Python e em C++, na máquina onde roda.

    python nativo/medir.py      (de dentro de backend/, com a biblioteca compilada)

Vetores sorteados de 768 dimensões, o tamanho do modelo de embedding do
projeto (nomic-embed-text). Só a etapa da similaridade: a consulta ao banco,
o corte e o bônus literal são os mesmos nos dois caminhos.

Os tamanhos:
    41      trechos do banco de demonstração (10 PDFs)
    3.000   uma disciplina com uns 30 PDFs de aula
    18.000  modo automático do chat: seis disciplinas do aluno de uma vez

Cada medida é a melhor de 5 repetições: o que se quer é o custo da conta, não
o de outro programa disputando o processador naquele instante.
"""

import os
import platform
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from infra import nativo  # noqa: E402
from infra.vetores import empacotar, normalizar, similaridade_em_python  # noqa: E402

DIMENSAO = 768
TAMANHOS = (41, 3_000, 18_000)
REPETICOES = 5


def melhor_tempo(funcao) -> float:
    melhor = float("inf")
    for _ in range(REPETICOES):
        inicio = time.perf_counter()
        funcao()
        melhor = min(melhor, time.perf_counter() - inicio)
    return melhor


def main() -> None:
    if not nativo.disponivel():
        sys.exit(f"Biblioteca em C++: {nativo.situacao()}")

    sorteio = random.Random(2026)
    pergunta = normalizar([sorteio.gauss(0, 1) for _ in range(DIMENSAO)])
    todos = [empacotar([sorteio.gauss(0, 1) for _ in range(DIMENSAO)]) for _ in range(max(TAMANHOS))]

    print(f"Processador: {platform.processor() or platform.machine()} · Python {platform.python_version()}")
    print(f"Vetores de {DIMENSAO} dimensões, melhor de {REPETICOES}\n")
    print("| Trechos | Python | C++ | Vezes mais rápido |")
    print("|---:|---:|---:|---:|")
    for quantidade in TAMANHOS:
        blobs = todos[:quantidade]
        em_python = melhor_tempo(lambda: [similaridade_em_python(pergunta, b) for b in blobs])
        em_cpp = melhor_tempo(lambda: nativo.similaridades(pergunta, blobs))
        # Conferência: a medida só vale se as duas contas derem o mesmo.
        if nativo.similaridades(pergunta, blobs) != [similaridade_em_python(pergunta, b) for b in blobs]:
            sys.exit("C++ e Python deram resultados diferentes: a medida não vale.")
        print(f"| {quantidade:,} | {em_python * 1000:,.2f} ms | {em_cpp * 1000:,.2f} ms | {em_python / em_cpp:,.0f}× |"
              .replace(",", "."))


if __name__ == "__main__":
    main()
