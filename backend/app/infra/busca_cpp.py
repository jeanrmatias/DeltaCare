"""O cliente do serviço de busca em C++ (backend/busca_cpp/).

O serviço guarda na memória os vetores dos trechos de material e devolve, a
cada pergunta, os trechos mais parecidos. Ele é **opcional**: desligado,
fora do ar, lento ou com resposta estranha, a busca do chat roda em Python
(regras/chat_ia.buscar_trechos_relevantes) e devolve o mesmo resultado. O
chat nunca para por causa dele.

    DELTACARE_BUSCA_URL   onde o serviço escuta, ex.: http://127.0.0.1:8090
                          (vazio, o padrão: não usa o serviço)

Desligado por padrão de propósito: no Windows, conectar numa porta local
fechada leva uns 2 s até desistir, e quem não subiu o serviço pagaria isso a
cada pergunta.

Só biblioteca padrão (urllib), como as chamadas ao Ollama.
"""

import json
import os
import time
import urllib.request

URL = os.environ.get("DELTACARE_BUSCA_URL", "").strip().rstrip("/")

# Quanto esperar a resposta. A busca em C++ leva milissegundos; passou disso,
# algo está errado e a busca em Python resolve.
TEMPO_LIMITE = 2.0

# Depois de uma falha, quanto tempo sem tentar de novo. Sem isto, com o
# serviço fora do ar, toda pergunta pagaria a tentativa antes de cair no
# Python.
PAUSA_DEPOIS_DE_FALHA = 30.0

_falhou_em = None

# Sem proxy: o serviço está na mesma máquina, e um HTTP_PROXY configurado no
# sistema mandaria a pergunta para fora.
_abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def ligado() -> bool:
    return bool(URL)


def buscar(pergunta: list, materiais: list, top_k: int, folga: float) -> list | None:
    """Os candidatos da busca, como [(id do trecho, similaridade)], em ordem de
    id; ou None, e quem chama faz a busca em Python.

    `materiais` são os que o aluno pode ver: a regra de visibilidade fica no
    Python, e o serviço só calcula. `folga` é o bônus literal máximo: o
    serviço devolve todo trecho que ainda pode chegar ao top-k com ele.
    """
    global _falhou_em
    if not URL:
        return None
    if _falhou_em is not None and time.monotonic() - _falhou_em < PAUSA_DEPOIS_DE_FALHA:
        return None

    corpo = json.dumps({"pergunta": pergunta, "materiais": materiais, "top_k": top_k, "folga": folga})
    requisicao = urllib.request.Request(f"{URL}/busca", data=corpo.encode("utf-8"),
                                        headers={"Content-Type": "application/json"})
    try:
        with _abridor.open(requisicao, timeout=TEMPO_LIMITE) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        achados = [(int(t["id"]), float(t["similaridade"])) for t in dados["trechos"]]
        fora = int(dados["fora_do_indice"])
    except (OSError, ValueError, KeyError, TypeError) as erro:
        if _falhou_em is None:
            print(f"[Delta Care] Busca em C++ indisponível ({erro}); usando a busca em Python.")
        _falhou_em = time.monotonic()
        return None

    if _falhou_em is not None:
        print("[Delta Care] Busca em C++ de volta.")
        _falhou_em = None
    # Trecho que o serviço não sabe calcular (linha antiga, ainda em JSON):
    # o Python faz a busca inteira, para o resultado não depender de quem fez.
    if fora:
        return None
    return achados
