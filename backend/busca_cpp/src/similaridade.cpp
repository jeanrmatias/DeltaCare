// Similaridade entre a pergunta do aluno e os trechos de material, em C++.
//
// É o laço mais pesado do chat: a cada pergunta, a busca compara o vetor da
// pergunta (768 números) com o vetor de cada trecho publicado nas disciplinas
// do aluno. Em Python, cada multiplicação passa pelo interpretador; aqui o
// laço vira instruções de máquina, duas contas por instrução (SSE2).
//
// O resultado é o mesmo da busca em Python — bit a bit, não "parecido". Duas
// coisas garantem isso:
//
//   1. A soma segue o algoritmo do sum() do Python (desde a 3.12): soma
//      compensada de Neumaier, que guarda à parte o que se perde no
//      arredondamento de cada adição e devolve no fim.
//   2. O compilador não pode fundir "a * b + c" numa instrução FMA, que
//      arredonda uma vez só em vez de duas e muda a última casa. Por isso o
//      CMakeLists.txt compila com -ffp-contract=off.

#include "similaridade.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>

// SSE2 faz parte de todo processador x86-64 (é o mínimo da arquitetura), então
// usar estas instruções não exclui nenhuma máquina desse tipo.
#if defined(__SSE2__) || defined(_M_X64)
#include <emmintrin.h>
#define DC_SSE2 1
#else
#define DC_SSE2 0
#endif

namespace {

// Lê o float32 na posição `indice` de um bloco de bytes.
//
// Os vetores chegam do banco como bytes (o BLOB do SQLite). Ler com memcpy em
// vez de converter o ponteiro para float* evita depender do alinhamento do
// bloco e da regra de "aliasing" do C++; o compilador transforma este memcpy
// de 4 bytes numa leitura simples de memória.
inline float ler_float(const unsigned char* bytes, std::int64_t indice) {
    float valor;
    std::memcpy(&valor, bytes + indice * 4, sizeof valor);
    return valor;
}

// Um passo da soma compensada de Neumaier: o que o sum() do Python faz com
// cada parcela. `compensacao` acumula o que o arredondamento de `soma + parcela`
// jogou fora; volta para a soma no fim (ver terminar).
//
// As duas expressões são calculadas e uma é escolhida, em vez de um if com
// desvio: o resultado é o mesmo, e é assim que a versão SIMD (somar_dois)
// precisa fazer — lá não há como desviar só uma das pistas.
inline void somar(double& soma, double& compensacao, double parcela) {
    const double nova = soma + parcela;
    const double se_soma_maior = (soma - nova) + parcela;
    const double se_parcela_maior = (parcela - nova) + soma;
    compensacao += std::fabs(soma) >= std::fabs(parcela) ? se_soma_maior : se_parcela_maior;
    soma = nova;
}

// Igual ao CPython: a compensação só entra se for finita, para um estouro
// (infinito) não virar NaN no fim.
inline double terminar(double soma, double compensacao) {
    if (compensacao != 0.0 && std::isfinite(compensacao)) {
        soma += compensacao;
    }
    return soma;
}

// O float32 do trecho vira double antes de multiplicar, como o Python faz ao
// ler um array("f"). Essa conversão é exata: todo float32 cabe num double.
inline double parcela(const double* pergunta, const unsigned char* trecho, std::int64_t i) {
    return pergunta[i] * static_cast<double>(ler_float(trecho, i));
}

// Produto escalar de um trecho, na mesma ordem e com as mesmas operações que
// sum(map(operator.mul, pergunta, trecho)) no Python.
double soma_de_um(const double* pergunta, const unsigned char* trecho, std::int64_t dimensao) {
    double soma = 0.0, compensacao = 0.0;
    for (std::int64_t i = 0; i < dimensao; ++i) {
        somar(soma, compensacao, parcela(pergunta, trecho, i));
    }
    return terminar(soma, compensacao);
}

#if DC_SSE2
// O mesmo passo de `somar`, para dois trechos numa instrução só (SIMD: uma
// instrução, vários dados). Um registrador SSE2 tem 128 bits = dois double;
// a "pista" de baixo é um trecho, a de cima é outro. Cada pista faz
// exatamente as operações de `somar`, com o mesmo arredondamento IEEE 754:
// o resultado de cada trecho é o mesmo, bit a bit.
//
// O valor absoluto é o número sem o bit de sinal (andnot com -0.0, que só tem
// esse bit ligado). A escolha entre as duas expressões é feita com uma
// máscara: a comparação deixa a pista com todos os bits em 1 onde é verdade.
inline void somar_dois(__m128d& soma, __m128d& compensacao, __m128d parcela) {
    const __m128d bit_de_sinal = _mm_set1_pd(-0.0);
    const __m128d nova = _mm_add_pd(soma, parcela);
    const __m128d se_soma_maior = _mm_add_pd(_mm_sub_pd(soma, nova), parcela);
    const __m128d se_parcela_maior = _mm_add_pd(_mm_sub_pd(parcela, nova), soma);
    const __m128d soma_maior = _mm_cmpge_pd(_mm_andnot_pd(bit_de_sinal, soma), _mm_andnot_pd(bit_de_sinal, parcela));
    const __m128d escolhida = _mm_or_pd(_mm_and_pd(soma_maior, se_soma_maior), _mm_andnot_pd(soma_maior, se_parcela_maior));
    compensacao = _mm_add_pd(compensacao, escolhida);
    soma = nova;
}
#endif

// Quatro trechos ao mesmo tempo, cada um com a própria soma.
//
// Com SSE2 (todo processador x86-64 tem), são dois registradores de dois
// trechos cada: cada instrução trabalha em dois trechos, e os dois
// registradores são independentes, então o processador executa os dois
// juntos. Sem SSE2 (ARM, por exemplo), o mesmo laço em C++ comum.
//
// Cada trecho continua somado na mesma ordem e com as mesmas operações, então
// o resultado de cada um é o mesmo de soma_de_um, bit a bit (há teste).
void soma_de_quatro(const double* pergunta, const unsigned char* const* trechos, std::int64_t dimensao,
                    double* saida) {
    double soma[4] = {0.0, 0.0, 0.0, 0.0};
    double compensacao[4] = {0.0, 0.0, 0.0, 0.0};
#if DC_SSE2
    __m128d soma_01 = _mm_setzero_pd(), compensacao_01 = _mm_setzero_pd();
    __m128d soma_23 = _mm_setzero_pd(), compensacao_23 = _mm_setzero_pd();
    for (std::int64_t i = 0; i < dimensao; ++i) {
        const __m128d p = _mm_set1_pd(pergunta[i]);
        // _mm_set_pd(alto, baixo): o trecho 0 na pista de baixo.
        const __m128d t01 = _mm_set_pd(ler_float(trechos[1], i), ler_float(trechos[0], i));
        const __m128d t23 = _mm_set_pd(ler_float(trechos[3], i), ler_float(trechos[2], i));
        somar_dois(soma_01, compensacao_01, _mm_mul_pd(p, t01));
        somar_dois(soma_23, compensacao_23, _mm_mul_pd(p, t23));
    }
    _mm_storeu_pd(soma, soma_01);
    _mm_storeu_pd(soma + 2, soma_23);
    _mm_storeu_pd(compensacao, compensacao_01);
    _mm_storeu_pd(compensacao + 2, compensacao_23);
#else
    for (std::int64_t i = 0; i < dimensao; ++i) {
        for (int k = 0; k < 4; ++k) {
            somar(soma[k], compensacao[k], parcela(pergunta, trechos[k], i));
        }
    }
#endif
    for (int k = 0; k < 4; ++k) {
        saida[k] = terminar(soma[k], compensacao[k]);
    }
}

}  // namespace

namespace similaridade {

std::int64_t calcular(const double* pergunta, std::int64_t dimensao, const unsigned char* const* trechos,
                      const std::int64_t* bytes, std::int64_t quantidade, double* saida) {
    for (std::int64_t i = 0; i < quantidade; ++i) {
        if (bytes[i] % 4 != 0) {
            return i;
        }
    }
    auto usar = [&](std::int64_t i) { return bytes[i] / 4 < dimensao ? bytes[i] / 4 : dimensao; };

    std::int64_t i = 0;
    // De quatro em quatro, quando os quatro têm o mesmo tamanho (o normal:
    // todos os trechos vêm do mesmo modelo). O que sobra vai um a um.
    for (; i + 4 <= quantidade; i += 4) {
        const std::int64_t n = usar(i);
        if (usar(i + 1) == n && usar(i + 2) == n && usar(i + 3) == n) {
            soma_de_quatro(pergunta, trechos + i, n, saida + i);
        } else {
            for (std::int64_t k = i; k < i + 4; ++k) {
                saida[k] = soma_de_um(pergunta, trechos[k], usar(k));
            }
        }
    }
    for (; i < quantidade; ++i) {
        saida[i] = soma_de_um(pergunta, trechos[i], usar(i));
    }
    return -1;
}

}  // namespace similaridade
