"""Mede a busca do chat com e sem o serviço em C++, na máquina onde roda.

    python busca_cpp/medir.py      (de dentro de backend/, com o serviço compilado)

Cria um banco temporário com trechos sorteados de 768 dimensões (o tamanho
do modelo de embedding do projeto, nomic-embed-text) — 1% parecidos com a
pergunta, o resto não, como numa disciplina de verdade —, sobe o serviço em C++
apontando para ele e mede `buscar_trechos_relevantes` inteira — a mesma
função que o chat chama —, pelos dois caminhos:

    Python   lê o vetor de todos os trechos do banco e faz a conta em Python
    C++      o serviço já tem os vetores na memória e faz a conta com SSE2;
             o Python só lê o texto dos poucos trechos escolhidos

Os tamanhos:
    41      trechos do banco de demonstração (10 PDFs)
    3.000   uma disciplina com uns 30 PDFs de aula
    18.000  modo automático do chat: seis disciplinas do aluno de uma vez

Cada medida é a melhor de 5 repetições. Usa um núcleo e leva cerca de um
minuto, quase todo gasto sorteando os vetores.
"""

import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from unittest import mock

PASTA = tempfile.mkdtemp(prefix="deltacare_medir_")
BANCO = os.path.join(PASTA, "medir.db")
# Antes de importar o projeto: o caminho do banco é lido no import.
os.environ["DELTACARE_DB"] = BANCO
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from infra import busca_cpp  # noqa: E402
from infra.database import configurar_banco  # noqa: E402
from infra.vetores import empacotar  # noqa: E402
from regras import chat_ia  # noqa: E402

DIMENSAO = 768
TAMANHOS = (41, 3_000, 18_000)
REPETICOES = 5
AQUI = os.path.dirname(os.path.abspath(__file__))


def binario() -> str:
    nome = "busca_cpp.exe" if sys.platform == "win32" else "busca_cpp"
    for caminho in (os.path.join(AQUI, "build", nome), os.path.join(AQUI, "build", "Release", nome)):
        if os.path.exists(caminho):
            return caminho
    sys.exit("Serviço não compilado. Ver docs/SPRINT_4_ECCS.md, seção \"Como compilar\".")


def povoar(sorteio, quantidade) -> list:
    """Uma disciplina com `quantidade` trechos. Devolve a pergunta."""
    import sqlite3

    agora = "2026-01-01T00:00:00+00:00"
    pergunta = [sorteio.gauss(0, 1) for _ in range(DIMENSAO)]
    conexao = sqlite3.connect(BANCO)
    conexao.execute("DELETE FROM material_chunks")
    conexao.execute("DELETE FROM materiais")
    conexao.execute("DELETE FROM turmas")
    turma = conexao.execute("INSERT INTO turmas (nome, semestre, professor_id, criado_em) VALUES ('Medida', '2026/2', 1, ?)",
                            (agora,)).lastrowid
    material = conexao.execute(
        "INSERT INTO materiais (professor_id, turma_id, titulo, tipo, criado_em, atualizado_em, rascunho)"
        " VALUES (1, ?, 'Aula', 'link', ?, ?, 0)", (turma, agora, agora)).lastrowid
    for indice in range(quantidade):
        # Como numa disciplina de verdade: 1% dos trechos fala do assunto da
        # pergunta (similaridade perto de 0,9); o resto fala de outra coisa
        # (até uns 0,45). Com vetores todos ao acaso, as similaridades ficam
        # coladas, quase todo trecho passa no corte, e a medida passaria a ser
        # a do bônus literal — que é Python nos dois caminhos.
        peso = sorteio.uniform(2.0, 3.0) if sorteio.random() < 0.01 else sorteio.uniform(0.0, 0.5)
        vetor = [peso * x + sorteio.gauss(0, 1) for x in pergunta]
        conexao.execute("INSERT INTO material_chunks (material_id, indice, texto, embedding, vetor) VALUES (?, ?, ?, '', ?)",
                        (material, indice, f"Trecho {indice} sobre dobutamina.", empacotar(vetor)))
    conexao.commit()
    conexao.close()
    return turma, pergunta


def numero(valor, casas=1) -> str:
    """No jeito brasileiro: 18.000 e 352,2."""
    return f"{valor:_.{casas}f}".replace(".", ",").replace("_", ".")


def melhor_tempo(funcao) -> float:
    melhor = float("inf")
    for _ in range(REPETICOES):
        inicio = time.perf_counter()
        funcao()
        melhor = min(melhor, time.perf_counter() - inicio)
    return melhor


def main() -> None:
    configurar_banco(silencioso=True)
    with socket.socket() as livre:
        livre.bind(("127.0.0.1", 0))
        porta = livre.getsockname()[1]
    servico = subprocess.Popen([binario(), BANCO], env=dict(os.environ, DELTACARE_BUSCA_PORTA=str(porta)),
                               stdout=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{porta}"
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"{url}/saude", timeout=1).close()
                break
            except OSError:
                time.sleep(0.05)

        sorteio = random.Random(2026)
        print(f"Vetores de {DIMENSAO} dimensões, busca inteira (banco + conta), melhor de {REPETICOES}\n")
        print("| Trechos | Python | C++ | Vezes mais rápido |")
        print("|---:|---:|---:|---:|")
        for quantidade in TAMANHOS:
            turma, pergunta = povoar(sorteio, quantidade)

            def buscar():
                return chat_ia.buscar_trechos_relevantes(turma, "dose de dobutamina", gerar_embedding_fn=lambda _: pergunta)

            with mock.patch.object(busca_cpp, "URL", ""):
                em_python = melhor_tempo(buscar)
                esperado = buscar()
            with mock.patch.multiple(busca_cpp, URL=url, _falhou_em=None):
                buscar()   # a primeira busca depois de povoar recarrega o índice; não entra na conta
                em_cpp = melhor_tempo(buscar)
                obtido = buscar()
                usou = busca_cpp.buscar([1.0], [], 1, 0.0) is not None
            # A medida só vale se os dois caminhos derem o mesmo e o C++ tiver sido usado.
            if obtido != esperado or not usou:
                sys.exit("Os dois caminhos deram resultados diferentes (ou o C++ não respondeu): a medida não vale.")
            print(f"| {numero(quantidade, 0)} | {numero(em_python * 1000)} ms | {numero(em_cpp * 1000)} ms "
                  f"| {numero(em_python / em_cpp, 1 if em_python < 10 * em_cpp else 0)}× |")
    finally:
        servico.terminate()
        servico.wait(timeout=10)


if __name__ == "__main__":
    main()
