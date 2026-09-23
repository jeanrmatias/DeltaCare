"""Utilitários de hash de senha, sem dependências externas (só hashlib/os/hmac)."""

import hashlib
import hmac
import os

ITERACOES = 260_000


def hash_senha(senha: str) -> str:
    """Gera um hash seguro da senha no formato 'salt_hex$hash_hex'."""
    salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, ITERACOES)
    return f"{salt.hex()}${hash_bytes.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere se `senha` corresponde ao hash gerado por hash_senha()."""
    try:
        salt_hex, hash_hex = senha_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        hash_esperado = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False

    hash_calculado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, ITERACOES)
    return hmac.compare_digest(hash_calculado, hash_esperado)
