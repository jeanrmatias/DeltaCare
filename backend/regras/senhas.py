"""O que uma senha nova precisa ter. Uma régua só, para todo lugar que define
senha: conta nova, troca no perfil, recuperação por e-mail, planilha.

Seguimos a recomendação atual do NIST (SP 800-63B), e não a de dez anos atrás:

- **Comprimento mínimo de 8.** É o que mais pesa contra adivinhação.
- **Recusar senha conhecida**: as mais usadas no Brasil e as óbvias para
  quem conhece o lugar ("medicina123", "deltacare"). São as primeiras que um
  atacante tenta, e 8 caracteres não salvam "12345678".
- **Nada de "maiúscula, número e símbolo obrigatórios"** nem de troca
  periódica forçada. As duas regras produzem "Senha@2026" virando
  "Senha@2027": previsível, e anotada num papel. A senha só muda quando há
  motivo (vazou, é provisória).
"""

import unicodedata

TAMANHO_MINIMO = 8
TAMANHO_MAXIMO = 128  # PBKDF2 aguenta mais; o limite é contra abuso, não contra a pessoa

# As mais vazadas em listas públicas (com as variações brasileiras) e as do
# contexto: curso, instituição, plataforma. Comparadas em minúsculas e sem
# acento. A lista é curta de propósito: as longas pegam o que o comprimento
# mínimo já barra.
COMUNS = {
    "12345678", "123456789", "1234567890", "87654321", "11111111", "00000000",
    "12341234", "11223344", "123123123", "1q2w3e4r", "1q2w3e4r5t", "q1w2e3r4",
    "qwertyui", "qwerty123", "asdfghjk", "zxcvbnm1", "abcd1234", "abc12345",
    "a1b2c3d4", "password", "password1", "passw0rd", "iloveyou", "princesa",
    "senha123", "senha1234", "senha12345", "minhasenha", "mudar123", "mudar1234",
    "trocar123", "acesso123", "admin123", "admin1234", "administrador",
    "brasil123", "flamengo", "corinthians", "palmeiras", "gremio123", "internacional",
    "amor1234", "teamo123", "jesus123", "deus1234", "familia123",
    "medicina", "medicina1", "medicina123", "medicina2026", "medico123", "doutor123",
    "enfermagem", "faculdade", "faculdade123", "universidade", "estudante", "aluno123",
    "professor", "professor1", "professor123", "deltacare", "deltacare1", "deltacare123",
    "moinhos123", "hospital123", "fiap1234", "fiap2026",
}


def _simples(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower().strip()


def problema_da_senha(senha: str, email: str = "", nome: str = "") -> str | None:
    """O que impede essa senha, numa frase para a pessoa ler. None: serve."""
    senha = senha or ""
    if len(senha) < TAMANHO_MINIMO:
        return f"A senha precisa ter pelo menos {TAMANHO_MINIMO} caracteres."
    if len(senha) > TAMANHO_MAXIMO:
        return f"A senha pode ter no máximo {TAMANHO_MAXIMO} caracteres."
    simples = _simples(senha)
    if simples in COMUNS or len(set(simples)) <= 2:
        return "Essa senha é muito usada e fácil de adivinhar. Escolha outra — uma frase curta funciona bem."
    usuario = _simples((email or "").split("@")[0])
    partes_do_nome = [p for p in _simples(nome).split() if len(p) >= 4]
    if (usuario and len(usuario) >= 4 and usuario in simples) or any(simples.startswith(p) and len(simples) - len(p) <= 4 for p in partes_do_nome):
        return "A senha não pode ser o seu e-mail ou o seu nome. Escolha outra."
    return None
