// O índice da busca: os vetores dos trechos de material, na memória.
//
// Sem ele, cada pergunta lia do banco o vetor de todos os trechos das
// disciplinas do aluno — com 18 mil trechos, 55 MB lidos por pergunta. Aqui
// eles são lidos uma vez e ficam na memória; o índice só volta ao banco
// quando algum trecho entra ou sai (um professor publicou ou apagou material).
//
// O índice não decide o que o aluno pode ver: quem chama passa a lista de
// materiais visíveis, e a regra (rascunho, material agendado) continua no
// backend em Python, num lugar só.

#pragma once

#include <cstdint>
#include <mutex>
#include <shared_mutex>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

struct sqlite3;

class Indice {
public:
    // Abre o banco só para leitura: o serviço nunca escreve nele.
    explicit Indice(std::string caminho_do_banco);
    ~Indice();
    Indice(const Indice&) = delete;
    Indice& operator=(const Indice&) = delete;

    struct Pedido {
        std::vector<double> pergunta;           // já normalizada
        std::unordered_set<std::int64_t> materiais;  // os que o aluno pode ver
        std::size_t top_k = 10;
        double folga = 0.0;                     // o bônus literal máximo do Python
    };

    struct Achado {
        std::int64_t id;          // material_chunks.id
        double similaridade;
    };

    struct Resposta {
        std::vector<Achado> trechos;      // em ordem de id
        std::int64_t considerados = 0;    // trechos dos materiais pedidos
        std::int64_t fora_do_indice = 0;  // trechos que o C++ não sabe calcular
        double milissegundos = 0.0;
    };

    // A busca. Devolve os candidatos que ainda podem entrar no top-k depois
    // do bônus literal: similaridade >= (k-ésima melhor) - folga. É o mesmo
    // corte que o Python faz, com a mesma conta, então o Python recebe
    // exatamente os trechos que teria escolhido sozinho.
    Resposta buscar(const Pedido& pedido);

    struct Situacao {
        std::int64_t trechos = 0;
        std::int64_t fora_do_indice = 0;
        std::int64_t dimensao = 0;
        std::int64_t bytes_na_memoria = 0;
        std::int64_t recargas = 0;
        std::string carregado_em;
        std::string banco;
    };
    Situacao situacao();

private:
    struct Trecho {
        std::int64_t id;
        std::int64_t material_id;
        std::size_t inicio;    // onde o vetor começa em `vetores`, em bytes
        std::int64_t bytes;    // -1: sem vetor binário (linha antiga, em JSON)
    };

    struct Dados {
        std::vector<Trecho> trechos;          // em ordem de id
        std::vector<unsigned char> vetores;   // todos os float32, um atrás do outro
        std::int64_t fora_do_indice = 0;
        std::string carregado_em;
    };

    void atualizar_se_mudou();
    Dados carregar();

    std::string caminho_;
    sqlite3* conexao_ = nullptr;

    // Uma trava para a conexão (só uma thread fala com o SQLite por vez) e
    // outra para os dados: várias buscas leem juntas; a troca depois de uma
    // recarga espera todas terminarem.
    std::mutex trava_do_banco_;
    std::shared_mutex trava_dos_dados_;

    Dados dados_;
    std::int64_t versao_do_banco_ = -1;
    std::pair<std::int64_t, std::int64_t> assinatura_{-1, -1};  // (quantidade, maior id)
    std::int64_t recargas_ = 0;
};
