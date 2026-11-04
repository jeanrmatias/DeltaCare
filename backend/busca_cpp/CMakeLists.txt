# Serviço de busca do Delta Care, em C++.
#
#     cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
#     cmake --build build
#     ctest --test-dir build
#
# (de dentro de backend/busca_cpp/). As três bibliotecas de terceiros são
# baixadas na primeira configuração, com a versão presa e o SHA-256 conferido:
# se o arquivo baixado não for exatamente o esperado, a configuração para.

cmake_minimum_required(VERSION 3.16)
project(busca_cpp LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Tipo de compilação" FORCE)
endif()

# ---------------------------------------------------------------- terceiros

set(TERCEIROS ${CMAKE_BINARY_DIR}/terceiros)

function(baixar url destino sha256)
  if(NOT EXISTS ${destino})
    message(STATUS "Baixando ${url}")
    file(DOWNLOAD ${url} ${destino} EXPECTED_HASH SHA256=${sha256} TLS_VERIFY ON STATUS estado)
    list(GET estado 0 codigo)
    if(NOT codigo EQUAL 0)
      file(REMOVE ${destino})
      message(FATAL_ERROR "Falhou ao baixar ${url}: ${estado}")
    endif()
  endif()
endfunction()

# cpp-httplib: o servidor HTTP, só um cabeçalho (MIT).
baixar(https://raw.githubusercontent.com/yhirose/cpp-httplib/v0.18.1/httplib.h
       ${TERCEIROS}/httplib.h
       f870541e065de607c8a7f64fc8743b475cd1388fff5238afa8841f75dcbf2b89)

# nlohmann/json: ler e escrever JSON, só um cabeçalho (MIT).
baixar(https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp
       ${TERCEIROS}/nlohmann/json.hpp
       9bea4c8066ef4a1c206b2be5a36302f8926f7fdc6087af5d20b417d0cf103ea6)

# SQLite: o mesmo banco do backend em Python, lido direto (domínio público).
# A "amalgamation" é o SQLite inteiro num arquivo .c: compila junto, sem
# depender de o sistema ter a biblioteca instalada.
baixar(https://www.sqlite.org/2024/sqlite-amalgamation-3460100.zip
       ${TERCEIROS}/sqlite.zip
       77823cb110929c2bcb0f5d48e4833b5c59a8a6e40cdea3936b99e199dbbe5784)
if(NOT EXISTS ${TERCEIROS}/sqlite-amalgamation-3460100/sqlite3.c)
  file(ARCHIVE_EXTRACT INPUT ${TERCEIROS}/sqlite.zip DESTINATION ${TERCEIROS})
endif()

add_library(sqlite3 STATIC ${TERCEIROS}/sqlite-amalgamation-3460100/sqlite3.c)
target_include_directories(sqlite3 SYSTEM PUBLIC ${TERCEIROS}/sqlite-amalgamation-3460100)
# Sem carregar extensões (não precisa, e é uma porta a menos); com threads,
# porque o servidor atende várias requisições ao mesmo tempo.
target_compile_definitions(sqlite3 PRIVATE SQLITE_OMIT_LOAD_EXTENSION SQLITE_THREADSAFE=1 SQLITE_DEFAULT_MEMSTATUS=0)

find_package(Threads REQUIRED)

# ---------------------------------------------------------------- opções

# Opções do nosso código (não das bibliotecas de terceiros).
#
# -ffp-contract=off: proíbe fundir "a * b + c" numa instrução FMA. A FMA
#   arredonda uma vez em vez de duas, e a similaridade deixaria de ser
#   idêntica à do Python na última casa. Em x86 sem -march o compilador já não
#   usa FMA, mas em ARM (um Mac M1, um servidor ARM) usaria.
# /fp:precise: o equivalente no Visual Studio, que desde o VS 2022 não funde
#   sem /fp:contract.
# /utf-8: os comentários e as mensagens estão em português, com acento.
function(opcoes_do_projeto alvo)
  if(MSVC)
    target_compile_options(${alvo} PRIVATE /W4 /fp:precise /utf-8)
  else()
    target_compile_options(${alvo} PRIVATE -Wall -Wextra -ffp-contract=off -fno-fast-math)
  endif()
endfunction()

# ---------------------------------------------------------------- alvos

# O núcleo: a conta e o índice. Separado do servidor para o teste usar sem HTTP.
add_library(nucleo STATIC src/similaridade.cpp src/indice.cpp)
target_include_directories(nucleo PUBLIC src)
target_link_libraries(nucleo PUBLIC sqlite3 Threads::Threads)
opcoes_do_projeto(nucleo)

add_executable(busca_cpp src/servidor.cpp)
target_include_directories(busca_cpp SYSTEM PRIVATE ${TERCEIROS})
target_link_libraries(busca_cpp PRIVATE nucleo)
opcoes_do_projeto(busca_cpp)
if(WIN32)
  # A biblioteca de sockets do Windows (a versão mínima fica em servidor.cpp).
  target_link_libraries(busca_cpp PRIVATE ws2_32)
endif()
if(MINGW)
  # Sem isto o .exe depende das DLLs do MinGW, que não estão no PATH de todo mundo.
  target_link_options(busca_cpp PRIVATE -static)
endif()

enable_testing()
add_executable(teste_similaridade testes/teste_similaridade.cpp)
target_link_libraries(teste_similaridade PRIVATE nucleo)
opcoes_do_projeto(teste_similaridade)
add_test(NAME similaridade COMMAND teste_similaridade)
