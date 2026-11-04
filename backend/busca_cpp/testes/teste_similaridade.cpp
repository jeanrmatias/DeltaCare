// Testes da conta da busca, em C++, sem Python nem HTTP no meio.
//
// O que a suíte do backend (backend/testes/testes.py) não pega: a conta
// isolada, com valores que dá para conferir à mão. A comparação bit a bit
// com o Python fica na suíte do backend, que sobe o serviço e compara.
//
// Compilado pelo CMake; rodado por `ctest --test-dir build`.

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

#include "similaridade.hpp"

namespace {

int falhas = 0;

void conferir(bool condicao, const char* descricao) {
    std::printf("  %s  %s\n", condicao ? "ok   " : "FALHA", descricao);
    if (!condicao) {
        ++falhas;
    }
}

// Os trechos como o banco guarda: cada um, um bloco de bytes em float32.
struct Trechos {
    std::vector<std::vector<unsigned char>> blocos;

    void adicionar(const std::vector<float>& vetor) {
        const auto* bytes = reinterpret_cast<const unsigned char*>(vetor.data());
        blocos.emplace_back(bytes, bytes + vetor.size() * 4);
    }
};

// Chama a conta como o serviço chama: endereços e tamanhos em bytes.
// A saída começa em -5, que nenhum cosseno dá, para ver o que não foi escrito.
std::vector<double> calcular(const std::vector<double>& pergunta, const Trechos& trechos,
                             std::int64_t* devolvido = nullptr) {
    std::vector<const unsigned char*> enderecos;
    std::vector<std::int64_t> tamanhos;
    for (const auto& bloco : trechos.blocos) {
        enderecos.push_back(bloco.data());
        tamanhos.push_back(static_cast<std::int64_t>(bloco.size()));
    }
    std::vector<double> saida(trechos.blocos.size(), -5.0);
    const std::int64_t r = similaridade::calcular(pergunta.data(), static_cast<std::int64_t>(pergunta.size()),
                                                  enderecos.data(), tamanhos.data(),
                                                  static_cast<std::int64_t>(saida.size()), saida.data());
    if (devolvido) {
        *devolvido = r;
    }
    return saida;
}

}  // namespace

int main() {
    std::printf("Conta da similaridade\n");

    const double raiz_de_meio = std::sqrt(0.5);
    const std::vector<double> pergunta = {1.0, 0.0, 0.0};

    // Os quatro primeiros têm o mesmo tamanho e passam pelo caminho de quatro
    // em quatro; os três últimos, um a um.
    Trechos trechos;
    trechos.adicionar({1.0f, 0.0f, 0.0f});                       // igual à pergunta
    trechos.adicionar({0.0f, 1.0f, 0.0f});                       // perpendicular
    trechos.adicionar({-1.0f, 0.0f, 0.0f});                      // oposto
    trechos.adicionar({static_cast<float>(raiz_de_meio), static_cast<float>(raiz_de_meio), 0.0f});  // 45 graus
    trechos.adicionar({0.0f, 0.0f, 0.0f});                       // vetor nulo
    trechos.adicionar({1.0f, 0.0f});                             // mais curto que a pergunta
    trechos.adicionar({});                                       // vazio

    std::int64_t devolvido = 0;
    const std::vector<double> s = calcular(pergunta, trechos, &devolvido);

    conferir(devolvido == -1, "tudo certo: devolve -1");
    conferir(s[0] == 1.0, "vetor igual a pergunta: cosseno 1");
    conferir(s[1] == 0.0, "vetor perpendicular: cosseno 0");
    conferir(s[2] == -1.0, "vetor oposto: cosseno -1");
    conferir(std::fabs(s[3] - raiz_de_meio) < 1e-7, "45 graus: cosseno de raiz de 1/2 (precisao do float32)");
    conferir(s[4] == 0.0, "vetor nulo: cosseno 0 com tudo");
    conferir(s[5] == 1.0, "trecho mais curto: compara ate o menor dos dois");
    conferir(s[6] == 0.0, "trecho vazio: 0, sem ler memoria fora do vetor");

    // A soma compensada: 1e16 + 1 + 1 - 1e16. Somando direto em double, cada
    // "+ 1" some no arredondamento (1e16 + 1 == 1e16) e o resultado é 0. Com a
    // compensação de Neumaier, que é a do sum() do Python, o resultado é 2.
    // (1e16 não é exato em float32, mas é o mesmo valor nas duas pontas e se
    // cancela.)
    const float grande = 1e16f;
    Trechos compensado;
    compensado.adicionar({grande, 1.0f, 1.0f, -grande});
    const std::vector<double> c = calcular({1.0, 1.0, 1.0, 1.0}, compensado);
    conferir(c[0] == 2.0, "soma compensada: 1e16 + 1 + 1 - 1e16 = 2 (a soma direta daria 0)");

    // De quatro em quatro e um a um têm de dar o mesmo, bit a bit: são as
    // mesmas operações, só intercaladas. 9 trechos = dois grupos de 4 + 1.
    std::vector<double> longa(768);
    Trechos nove;
    for (int t = 0; t < 9; ++t) {
        std::vector<float> v(768);
        for (int i = 0; i < 768; ++i) {
            v[i] = static_cast<float>(std::sin(0.37 * (i + 1) * (t + 2)));
            longa[i] = std::cos(0.11 * (i + 1));
        }
        nove.adicionar(v);
    }
    const std::vector<double> juntos = calcular(longa, nove);
    bool iguais = true;
    for (int t = 0; t < 9; ++t) {
        Trechos sozinho;
        sozinho.blocos.push_back(nove.blocos[t]);
        iguais = iguais && calcular(longa, sozinho)[0] == juntos[t];
    }
    conferir(iguais, "quatro intercalados = um de cada vez, bit a bit");

    // Grupo de quatro com tamanhos diferentes: não pode usar o tamanho do
    // primeiro para os outros (leria além do fim do mais curto).
    Trechos mistos;
    mistos.adicionar({1.0f, 0.0f, 0.0f});
    mistos.adicionar({1.0f});
    mistos.adicionar({0.0f, 1.0f, 0.0f});
    mistos.adicionar({0.5f, 0.0f});
    const std::vector<double> m = calcular(pergunta, mistos);
    conferir(m[0] == 1.0 && m[1] == 1.0 && m[2] == 0.0 && m[3] == 0.5, "grupo com tamanhos diferentes: cada um no seu");

    // Bloco de bytes desalinhado: o vetor começa no byte 1, não num múltiplo
    // de 4. A leitura por memcpy não pode depender do alinhamento.
    std::vector<unsigned char> desalinhado(1 + 3 * 4);
    const float valores[3] = {0.0f, 0.0f, 1.0f};
    std::memcpy(desalinhado.data() + 1, valores, sizeof valores);
    const unsigned char* endereco = desalinhado.data() + 1;
    const std::int64_t bytes = 12;
    const double eixo_z[3] = {0.0, 0.0, 1.0};
    double resultado = -5.0;
    similaridade::calcular(eixo_z, 3, &endereco, &bytes, 1, &resultado);
    conferir(resultado == 1.0, "bloco desalinhado na memoria: le certo");

    // 7 bytes não são float32 inteiros: devolve a posição e não calcula nada.
    Trechos quebrados;
    quebrados.adicionar({1.0f, 0.0f, 0.0f});
    quebrados.blocos.emplace_back(7, 0);
    const std::vector<double> q = calcular(pergunta, quebrados, &devolvido);
    conferir(devolvido == 1 && q[0] == -5.0, "bytes que nao sao float32 inteiros: recusa e aponta qual");

    std::printf("%s\n", falhas == 0 ? "Todos os testes passaram." : "Houve falhas.");
    return falhas == 0 ? 0 : 1;
}
