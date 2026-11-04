"""A ponte para a parte em C++ do backend (backend/nativo/).

A biblioteca compilada calcula a similaridade da pergunta com os trechos de
material — o laço mais pesado do chat. Ela é **opcional**: sem ela (ninguém
compilou, a máquina não tem compilador, ou DELTACARE_NATIVO=0), a busca roda
em Python e devolve o mesmo resultado. O servidor nunca deixa de subir por
causa dela.

Carregada pelo ctypes, da biblioteca padrão: nenhuma dependência nova.

    python nativo/compilar.py            compila (de dentro de backend/)
    python nativo/compilar.py --testar   compila e roda os testes em C++
"""

import ctypes
import os
import sys
import threading
from array import array

VERSAO_ESPERADA = 1  # dc_versao() em nativo/similaridade.cpp

_PASTA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "nativo")
_NOMES = {"win32": "similaridade.dll", "darwin": "libsimilaridade.dylib"}
CAMINHO_DA_BIBLIOTECA = os.path.join(_PASTA, _NOMES.get(sys.platform, "libsimilaridade.so"))

_carregada = None  # a biblioteca, False se não deu, None se ainda não tentou
_motivo = ""
_trava = threading.Lock()


def _carregar():
    """Carrega na primeira busca, não no import: o compilar.py importa este
    módulo para saber o caminho, e no Windows uma DLL carregada não pode ser
    substituída."""
    global _carregada, _motivo
    with _trava:
        if _carregada is not None:
            return _carregada
        if os.environ.get("DELTACARE_NATIVO", "1") == "0":
            _carregada, _motivo = False, "desligada por DELTACARE_NATIVO=0"
        elif not os.path.exists(CAMINHO_DA_BIBLIOTECA):
            _carregada, _motivo = False, "não compilada (python nativo/compilar.py)"
        else:
            try:
                biblioteca = ctypes.CDLL(CAMINHO_DA_BIBLIOTECA)
                versao = biblioteca.dc_versao()
                if versao != VERSAO_ESPERADA:
                    raise OSError(f"versão {versao}, esperada {VERSAO_ESPERADA}: recompile")
                funcao = biblioteca.dc_similaridades
                funcao.restype = ctypes.c_int64
                funcao.argtypes = [
                    ctypes.c_void_p, ctypes.c_int64,   # pergunta, dimensão
                    ctypes.c_void_p, ctypes.c_void_p,  # endereço e tamanho em bytes de cada trecho
                    ctypes.c_int64,                    # quantidade
                    ctypes.c_void_p,                   # saída
                ]
                _carregada, _motivo = funcao, "carregada"
            except (OSError, AttributeError) as erro:
                # Biblioteca de outra arquitetura, corrompida ou antiga: segue
                # em Python. O motivo sai em `python nativo/compilar.py --situacao`.
                _carregada, _motivo = False, f"não carregou: {erro}"
        return _carregada


def disponivel() -> bool:
    return bool(_carregar())


def situacao() -> str:
    """Uma linha para o diagnóstico: carregada, ou por que não."""
    _carregar()
    return _motivo


def _endereco(buffer: array) -> int:
    return buffer.buffer_info()[0]


def similaridades(pergunta, vetores: list) -> list | None:
    """Produto escalar de `pergunta` com cada vetor (bytes em float32, como
    infra/vetores.empacotar grava). None se a biblioteca não estiver
    disponível — quem chama faz a conta em Python.

    `pergunta` é a lista de floats (double) já normalizada.
    """
    funcao = _carregar()
    if not funcao:
        return None
    quantidade = len(vetores)
    if quantidade == 0:
        return []

    # Os endereços dos próprios bytes que vieram do banco: o C++ lê de onde
    # eles já estão, sem cópia. Colar tudo num bloco só (b"".join) custava
    # mais que a própria conta: 11 ms para copiar 55 MB, com 18 mil trechos.
    enderecos = (ctypes.c_char_p * quantidade)(*vetores)
    tamanhos = array("q", map(len, vetores))
    consulta = array("d", pergunta)
    saida = array("d", bytes(8 * quantidade))
    quebrado = funcao(_endereco(consulta), len(consulta), ctypes.addressof(enderecos), _endereco(tamanhos),
                      quantidade, _endereco(saida))
    if quebrado >= 0:
        # O mesmo erro de array.frombytes, que é o caminho em Python.
        raise ValueError("bytes length not a multiple of item size")
    return saida.tolist()
