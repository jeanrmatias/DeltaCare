"""Como os vetores dos trechos (embeddings) ficam guardados no banco.

Em binário — float32, 4 bytes por dimensão — e **já normalizados** (norma 1).

Antes eram JSON. Medido com 2.000 trechos de 768 dimensões: decodificar o
JSON levava 304 ms; o binário, 9 ms. E com o vetor normalizado na gravação, o
cosseno da busca vira um produto escalar — a norma de cada trecho não precisa
ser recalculada a cada pergunta. float32 basta: a diferença para o float64 do
JSON aparece na sétima casa do cosseno, longe de mudar qual trecho é o melhor.

Sem numpy de propósito: `array` é da biblioteca padrão, e o projeto tem cinco
dependências.

A busca do chat pode ser feita pelo serviço em C++ (backend/busca_cpp/, ver
infra/busca_cpp.py), que guarda os vetores na memória. Quando ele não está
no ar, a conta é a daqui, com o mesmo resultado, bit a bit.
"""

import json
import math
import operator
from array import array


def normalizar(vetor) -> list:
    """O vetor com norma 1. Vetor nulo continua nulo (cosseno 0 com tudo)."""
    norma = math.sqrt(sum(x * x for x in vetor))
    if norma == 0:
        return [0.0] * len(vetor)
    return [x / norma for x in vetor]


def empacotar(vetor) -> bytes:
    """Normaliza e grava em float32."""
    return array("f", normalizar(vetor)).tobytes()


def desempacotar(blob: bytes) -> array:
    vetor = array("f")
    vetor.frombytes(blob)
    return vetor


def similaridades(pergunta, linhas: list) -> list:
    """A similaridade de `pergunta` (já normalizada) com cada trecho.

    `linhas` são pares (vetor, embedding) como saem de material_chunks: o
    vetor em binário, ou — trecho gravado antes da coluna binária, que o banco
    converte ao subir (infra/database.py) — vazio, com o vetor em JSON.

    Os dois vetores têm norma 1: o produto escalar já é o cosseno.
    """
    return [
        sum(map(operator.mul, pergunta, desempacotar(vetor) if vetor else normalizar(json.loads(embedding))))
        for vetor, embedding in linhas
    ]
