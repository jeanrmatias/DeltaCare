"""Anonimiza as contas cuja exclusão passou do prazo (regras/privacidade.py).

O servidor já faz isso ao subir e quando a administração abre a fila de
pedidos. Este script cobre o servidor que fica meses no ar sem ninguém abrir a
fila: agende uma vez por dia, junto do backup (ver README, Implantação).
"""

from infra.database import configurar_banco
from regras.privacidade import anonimizar_vencidas

if __name__ == "__main__":
    configurar_banco(silencioso=True)
    quantas = anonimizar_vencidas()
    print(f"[Delta Care] {quantas} conta(s) anonimizada(s).")
