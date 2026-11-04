"""Compila a parte em C++ do backend.

    python nativo/compilar.py              compila a biblioteca
    python nativo/compilar.py --testar     compila e roda os testes em C++
    python nativo/compilar.py --situacao   só diz se o backend está usando a biblioteca

Rodar de dentro de backend/. Só biblioteca padrão.

**Compilador:** o da variável CXX, se houver; senão g++ ou clang++; senão o
zig do pip (`pip install ziglang`), que traz um clang completo e serve em
qualquer sistema sem instalar nada fora do Python. No Linux do servidor:
`apt install g++`. MSVC (cl.exe) não é aceito: as opções de ponto flutuante
abaixo são as do GCC/Clang.

**Sem compilador o backend continua funcionando**, com a busca em Python
(ver app/infra/nativo.py). Este script falha, o servidor não.
"""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "app"))

from infra.nativo import CAMINHO_DA_BIBLIOTECA  # noqa: E402

FONTE = os.path.join(AQUI, "similaridade.cpp")
TESTE = os.path.join(AQUI, "teste_similaridade.cpp")

# -O2: otimiza sem trocar o resultado das contas.
# -ffp-contract=off: proíbe fundir "a * b + c" numa instrução FMA. A FMA
#   arredonda uma vez em vez de duas, e a similaridade deixaria de ser
#   idêntica à do Python na última casa. Em x86 sem -march o GCC já não usa
#   FMA, mas em ARM (outro servidor, um Mac M1) usaria.
# -fno-fast-math: idem, contra quem passar -ffast-math pela CXXFLAGS.
# -fvisibility=hidden: só as funções marcadas com DC_API saem da biblioteca.
OPCOES = ["-std=c++17", "-O2", "-ffp-contract=off", "-fno-fast-math", "-Wall", "-Wextra"]


def achar_compilador() -> list:
    if os.environ.get("CXX"):
        return shlex.split(os.environ["CXX"], posix=os.name != "nt")
    for nome in ("g++", "clang++"):
        caminho = shutil.which(nome)
        if caminho:
            return [caminho]
    try:
        import ziglang  # noqa: F401

        return [sys.executable, "-m", "ziglang", "c++"]
    except ImportError:
        pass
    sys.exit(
        "Nenhum compilador C++ encontrado.\n"
        "  Linux:   sudo apt install g++\n"
        "  Windows: pip install ziglang  (ou instale o MinGW-w64 e ponha o g++ no PATH)\n"
        "O backend continua funcionando sem a biblioteca, com a busca em Python."
    )


def rodar(comando: list) -> None:
    print("  $", " ".join(comando))
    resultado = subprocess.run(comando)
    if resultado.returncode != 0:
        sys.exit(f"Falhou (código {resultado.returncode}).")


def compilar_biblioteca(compilador: list) -> None:
    opcoes = OPCOES + ["-shared", "-fvisibility=hidden"]
    if sys.platform != "win32":
        opcoes.append("-fPIC")
    elif os.path.basename(compilador[0]).startswith("g++"):
        # MinGW: sem isto a DLL depende de libgcc/libstdc++ em DLLs à parte,
        # que o Python não acha.
        opcoes += ["-static-libgcc", "-static-libstdc++"]

    # Compila numa pasta temporária e troca o arquivo de uma vez (os.replace).
    # Sobrescrever a biblioteca no lugar, com o servidor no ar, corrompe a
    # cópia que o processo já tem carregada na memória (o arquivo é mapeado).
    # Trocando o arquivo, o processo antigo segue com a versão dele até o
    # reinício. O zig ainda deixa .lib e .pdb ao lado: ficam na temporária.
    with tempfile.TemporaryDirectory() as pasta:
        saida = os.path.join(pasta, os.path.basename(CAMINHO_DA_BIBLIOTECA))
        rodar(compilador + opcoes + [FONTE, "-o", saida])
        provisorio = CAMINHO_DA_BIBLIOTECA + ".novo"
        shutil.copyfile(saida, provisorio)
    try:
        os.replace(provisorio, CAMINHO_DA_BIBLIOTECA)
    except PermissionError:
        os.remove(provisorio)
        sys.exit("A biblioteca está em uso (no Windows, uma DLL carregada não pode ser trocada). "
                 "Pare o backend e rode de novo.")
    print(f"Biblioteca: {CAMINHO_DA_BIBLIOTECA}")


def testar(compilador: list) -> None:
    with tempfile.TemporaryDirectory() as pasta:
        programa = os.path.join(pasta, "teste_similaridade" + (".exe" if sys.platform == "win32" else ""))
        rodar(compilador + OPCOES + [TESTE, FONTE, "-o", programa])
        rodar([programa])


def situacao() -> str:
    """Pergunta a um processo novo, como o servidor faria ao subir: este aqui
    não pode carregar a biblioteca (travaria a DLL no Windows)."""
    codigo = "import sys; sys.path.insert(0, 'app'); from infra import nativo; print(nativo.situacao())"
    pasta = os.path.dirname(AQUI)
    return subprocess.run([sys.executable, "-c", codigo], cwd=pasta, capture_output=True, text=True).stdout.strip()


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)  # as mensagens na ordem, entre as do compilador
    argumentos = sys.argv[1:]
    if argumentos == ["--situacao"]:
        print("Biblioteca em C++:", situacao())
        return
    if argumentos not in ([], ["--testar"]):
        sys.exit(__doc__)

    compilador = achar_compilador()
    print("Compilando a biblioteca")
    compilar_biblioteca(compilador)
    if argumentos == ["--testar"]:
        print("Testes em C++")
        testar(compilador)
    print("Biblioteca em C++:", situacao())


if __name__ == "__main__":
    main()
