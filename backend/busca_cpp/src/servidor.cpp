// Serviço de busca do Delta Care, em C++.
//
// Uma API HTTP pequena (cpp-httplib) que o backend em Python chama a cada
// pergunta do chat: recebe o vetor da pergunta e os materiais que o aluno pode
// ver, e devolve os trechos mais parecidos. Guarda os vetores na memória
// (indice.cpp) e faz a conta com SSE2 (similaridade.cpp).
//
//     busca_cpp [caminho do banco]
//
//     DELTACARE_DB           o banco, se não vier na linha de comando (padrão: deltacare.db)
//     DELTACARE_BUSCA_PORTA  a porta (padrão: 8090)
//
// Escuta só em 127.0.0.1: quem chama é o backend, na mesma máquina. Não há
// login porque a rota não sai da máquina; o aluno nunca fala com este
// serviço, só com o backend, que é quem confere a sessão e a permissão.
//
// Rotas: GET /saude, GET /indice, POST /busca. Exemplos em docs/SPRINT_4_ECCS.md.

// A cpp-httplib pede Windows 10 ou mais novo. Alguns compiladores já definem
// isto; os que não definem, ou definem mais antigo, recebem aqui.
#if defined(_WIN32) && (!defined(_WIN32_WINNT) || _WIN32_WINNT < 0x0A00)
#undef _WIN32_WINNT
#define _WIN32_WINNT 0x0A00
#endif

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <memory>
#include <string>

#include <httplib.h>
#include <nlohmann/json.hpp>

#include "indice.hpp"

using json = nlohmann::json;

namespace {

// Limites da entrada: o serviço é interno, mas um pedido malformado não pode
// derrubá-lo nem fazê-lo alocar memória sem fim.
constexpr std::size_t MAX_DIMENSAO = 4096;
constexpr std::size_t MAX_MATERIAIS = 100000;
constexpr std::size_t MAX_TOP_K = 100;
constexpr std::size_t MAX_CORPO = 4 * 1024 * 1024;

// Pedido inválido: vira 400 com a mensagem, para quem chamou saber o que corrigir.
struct PedidoInvalido : std::runtime_error {
    using std::runtime_error::runtime_error;
};

void responder(httplib::Response& resposta, int status, const json& corpo) {
    resposta.status = status;
    resposta.set_content(corpo.dump(), "application/json; charset=utf-8");
}

const char* variavel(const char* nome, const char* padrao) {
    const char* valor = std::getenv(nome);
    return valor && *valor ? valor : padrao;
}

Indice::Pedido ler_pedido(const std::string& corpo) {
    const json entrada = json::parse(corpo, nullptr, false);
    if (entrada.is_discarded() || !entrada.is_object()) {
        throw PedidoInvalido("o corpo precisa ser um objeto JSON");
    }

    Indice::Pedido pedido;

    const auto pergunta = entrada.find("pergunta");
    if (pergunta == entrada.end() || !pergunta->is_array() || pergunta->empty() || pergunta->size() > MAX_DIMENSAO) {
        throw PedidoInvalido("\"pergunta\" precisa ser uma lista de 1 a 4096 números");
    }
    pedido.pergunta.reserve(pergunta->size());
    for (const json& valor : *pergunta) {
        if (!valor.is_number() || !std::isfinite(valor.get<double>())) {
            throw PedidoInvalido("\"pergunta\" só aceita números finitos");
        }
        pedido.pergunta.push_back(valor.get<double>());
    }

    const auto materiais = entrada.find("materiais");
    if (materiais == entrada.end() || !materiais->is_array() || materiais->size() > MAX_MATERIAIS) {
        throw PedidoInvalido("\"materiais\" precisa ser uma lista de ids");
    }
    for (const json& valor : *materiais) {
        if (!valor.is_number_integer()) {
            throw PedidoInvalido("\"materiais\" só aceita ids inteiros");
        }
        pedido.materiais.insert(valor.get<std::int64_t>());
    }

    const json top_k = entrada.value("top_k", json(10));
    if (!top_k.is_number_integer() || top_k.get<std::int64_t>() < 1 ||
        top_k.get<std::int64_t>() > static_cast<std::int64_t>(MAX_TOP_K)) {
        throw PedidoInvalido("\"top_k\" precisa ser um inteiro de 1 a 100");
    }
    pedido.top_k = top_k.get<std::size_t>();

    const json folga = entrada.value("folga", json(0.0));
    if (!folga.is_number() || !std::isfinite(folga.get<double>()) || folga.get<double>() < 0) {
        throw PedidoInvalido("\"folga\" precisa ser um número maior ou igual a zero");
    }
    pedido.folga = folga.get<double>();
    return pedido;
}

}  // namespace

int main(int argc, char** argv) {
    const std::string banco = argc > 1 ? argv[1] : variavel("DELTACARE_DB", "deltacare.db");
    const int porta = std::atoi(variavel("DELTACARE_BUSCA_PORTA", "8090"));

    std::unique_ptr<Indice> indice;
    try {
        indice = std::make_unique<Indice>(banco);
    } catch (const std::exception& erro) {
        std::fprintf(stderr, "Erro ao carregar o índice: %s\n", erro.what());
        return 1;
    }

    httplib::Server servidor;
    servidor.set_payload_max_length(MAX_CORPO);

    // Qualquer exceção numa rota vira 500 em JSON, em vez de derrubar o processo.
    servidor.set_exception_handler([](const httplib::Request&, httplib::Response& resposta, std::exception_ptr ep) {
        std::string mensagem = "erro interno";
        try {
            std::rethrow_exception(ep);
        } catch (const std::exception& erro) {
            mensagem = erro.what();
        } catch (...) {
        }
        std::fprintf(stderr, "Erro: %s\n", mensagem.c_str());
        responder(resposta, 500, {{"erro", mensagem}});
    });

    servidor.Get("/saude", [](const httplib::Request&, httplib::Response& resposta) {
        responder(resposta, 200, {{"status", "ok"}});
    });

    servidor.Get("/indice", [&indice](const httplib::Request&, httplib::Response& resposta) {
        const Indice::Situacao s = indice->situacao();
        responder(resposta, 200,
                  {{"trechos", s.trechos},
                   {"fora_do_indice", s.fora_do_indice},
                   {"dimensao", s.dimensao},
                   {"bytes_na_memoria", s.bytes_na_memoria},
                   {"recargas", s.recargas},
                   {"carregado_em", s.carregado_em},
                   {"banco", s.banco}});
    });

    servidor.Post("/busca", [&indice](const httplib::Request& requisicao, httplib::Response& resposta) {
        Indice::Pedido pedido;
        try {
            pedido = ler_pedido(requisicao.body);
        } catch (const PedidoInvalido& erro) {
            responder(resposta, 400, {{"erro", erro.what()}});
            return;
        }
        const Indice::Resposta achados = indice->buscar(pedido);
        json trechos = json::array();
        for (const Indice::Achado& achado : achados.trechos) {
            // O double sai com dígitos suficientes para voltar idêntico no
            // Python (nlohmann usa a representação mais curta que faz o
            // caminho de volta exato).
            trechos.push_back({{"id", achado.id}, {"similaridade", achado.similaridade}});
        }
        responder(resposta, 200,
                  {{"trechos", trechos},
                   {"considerados", achados.considerados},
                   {"fora_do_indice", achados.fora_do_indice},
                   {"milissegundos", achados.milissegundos}});
    });

    const Indice::Situacao inicial = indice->situacao();
    std::printf("Busca em C++ no ar: http://127.0.0.1:%d  (%lld trechos de %s)\n", porta,
                static_cast<long long>(inicial.trechos), banco.c_str());
    std::fflush(stdout);
    if (!servidor.listen("127.0.0.1", porta)) {
        std::fprintf(stderr, "Não consegui escutar na porta %d (já está em uso?)\n", porta);
        return 1;
    }
    return 0;
}
