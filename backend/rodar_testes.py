"""Roda a suíte do backend em paralelo.

    python rodar_testes.py          # um processo por núcleo
    python rodar_testes.py 4        # quatro processos

Divide as classes de teste entre vários processos `python -m unittest`. Cada
processo tem o seu banco e a sua pasta de arquivos (o pid entra no nome, ver o
topo de testes.py), então eles não se enxergam.

Existe porque a suíte em série passou de dois minutos e meio, e é rodada a cada
mudança. Só biblioteca padrão, de propósito: pytest-xdist faria o mesmo, mas
traria uma dependência a mais para um projeto que tem quatro.

`python testes.py` continua funcionando igual, em série. Este arquivo é só
um atalho, e o resultado tem que ser o mesmo.
"""

import os
import re
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))


def classes_de_teste() -> list:
    """(nome da classe, quantidade de testes), das maiores para as menores."""
    sys.path.insert(0, AQUI)
    import testes  # noqa: E402

    carregador = unittest.TestLoader()
    encontradas = []
    for nome in dir(testes):
        objeto = getattr(testes, nome)
        if isinstance(objeto, type) and issubclass(objeto, unittest.TestCase):
            quantidade = carregador.loadTestsFromTestCase(objeto).countTestCases()
            if quantidade:
                encontradas.append((nome, quantidade))

    return sorted(encontradas, key=lambda par: par[1], reverse=True)


def repartir(classes: list, processos: int) -> list:
    """Distribui as classes pelo processo mais leve até o momento.

    Não é por número de classes porque elas têm tamanhos muito diferentes: uma
    divisão ingênua deixaria um processo com as quatro maiores enquanto os
    outros terminam cedo e ficam parados.
    """
    grupos = [[] for _ in range(processos)]
    cargas = [0] * processos

    for nome, quantidade in classes:
        mais_leve = cargas.index(min(cargas))
        grupos[mais_leve].append(nome)
        cargas[mais_leve] += quantidade

    return [grupo for grupo in grupos if grupo]


def rodar_grupo(grupo: list) -> dict:
    alvos = [f"testes.{nome}" for nome in grupo]
    processo = subprocess.run(
        [sys.executable, "-m", "unittest", *alvos],
        cwd=AQUI,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    saida = processo.stderr + processo.stdout

    rodados = re.search(r"^Ran (\d+) tests?", saida, re.M)
    return {
        "rodados": int(rodados.group(1)) if rodados else 0,
        "ok": processo.returncode == 0,
        "saida": saida,
    }


def main() -> int:
    # O console do Windows usa cp1252 e quebra com caractere fora dele — e foi
    # justamente ao imprimir uma falha que o runner morria, escondendo a falha.
    # Troca o caractere por "?" em vez de derrubar o relatório.
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(errors="replace")

    processos = int(sys.argv[1]) if len(sys.argv) > 1 else (os.cpu_count() or 4)

    classes = classes_de_teste()
    total_esperado = sum(quantidade for _, quantidade in classes)
    grupos = repartir(classes, processos)

    print(f"{total_esperado} testes em {len(classes)} classes, {len(grupos)} processos")

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(grupos)) as executor:
        resultados = list(executor.map(rodar_grupo, grupos))
    duracao = time.perf_counter() - inicio

    rodados = sum(r["rodados"] for r in resultados)
    falhos = [r for r in resultados if not r["ok"]]

    for resultado in falhos:
        print("\n" + "=" * 70)
        print(resultado["saida"])

    # Conferir o total não é enfeite: se um processo morrer antes de rodar, ou
    # uma classe cair fora da divisão, a suíte "passaria" com menos testes.
    if rodados != total_esperado:
        print(f"\nATENÇÃO: rodaram {rodados} de {total_esperado} testes.")
        return 1

    situacao = "FALHOU" if falhos else "OK"
    print(f"\nRan {rodados} tests in {duracao:.1f}s -- {situacao}")
    return 1 if falhos else 0


if __name__ == "__main__":
    sys.exit(main())
