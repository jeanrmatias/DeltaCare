// A conta da busca: a similaridade da pergunta com cada trecho de material.
//
// Os vetores têm norma 1 (o backend em Python normaliza ao gravar), então o
// cosseno é o produto escalar. A soma é a compensada de Neumaier, a mesma do
// sum() do Python 3.12+: o resultado é idêntico ao da busca em Python até o
// último bit. Detalhes em similaridade.cpp.

#pragma once

#include <cstdint>

namespace similaridade {

// Calcula a similaridade da pergunta com `quantidade` trechos de uma vez.
//
//   pergunta    vetor da pergunta, já normalizado (`dimensao` números)
//   trechos[i]  endereço dos bytes do trecho i, em float32
//   bytes[i]    quantos bytes o trecho i tem
//   saida[i]    recebe a similaridade do trecho i
//
// Devolve -1 se deu tudo certo, ou a posição do primeiro trecho cujo tamanho
// não é múltiplo de 4 (não é uma sequência de float32 inteiros); nesse caso
// nada é calculado.
//
// Trecho com outro tamanho (vetor de outro modelo de embedding) é comparado
// até o menor dos dois, como o map() do Python, que para no mais curto.
std::int64_t calcular(const double* pergunta, std::int64_t dimensao, const unsigned char* const* trechos,
                      const std::int64_t* bytes, std::int64_t quantidade, double* saida);

}  // namespace similaridade
