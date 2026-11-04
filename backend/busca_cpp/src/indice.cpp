#include "indice.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <ctime>
#include <functional>
#include <stdexcept>

#include <sqlite3.h>

#include "similaridade.hpp"

namespace {

// Erro do SQLite vira exceção com a mensagem dele; o servidor responde 500.
void conferir(int codigo, sqlite3* conexao, const char* fazendo) {
    if (codigo != SQLITE_OK && codigo != SQLITE_ROW && codigo != SQLITE_DONE) {
        throw std::runtime_error(std::string(fazendo) + ": " + sqlite3_errmsg(conexao));
    }
}

// Uma consulta preparada, finalizada sozinha ao sair do escopo (RAII): não
// há caminho, nem com exceção, em que ela fique aberta segurando o banco.
class Consulta {
public:
    Consulta(sqlite3* conexao, const char* sql) : conexao_(conexao) {
        conferir(sqlite3_prepare_v2(conexao, sql, -1, &stmt_, nullptr), conexao, sql);
    }
    ~Consulta() { sqlite3_finalize(stmt_); }
    Consulta(const Consulta&) = delete;
    Consulta& operator=(const Consulta&) = delete;

    bool proxima() {
        const int codigo = sqlite3_step(stmt_);
        conferir(codigo, conexao_, "lendo o banco");
        return codigo == SQLITE_ROW;
    }
    sqlite3_stmt* operator*() const { return stmt_; }

private:
    sqlite3* conexao_;
    sqlite3_stmt* stmt_ = nullptr;
};

std::int64_t um_inteiro(sqlite3* conexao, const char* sql) {
    Consulta consulta(conexao, sql);
    if (!consulta.proxima()) {
        throw std::runtime_error(std::string("sem resultado: ") + sql);
    }
    return sqlite3_column_int64(*consulta, 0);
}

void executar(sqlite3* conexao, const char* sql) {
    conferir(sqlite3_exec(conexao, sql, nullptr, nullptr, nullptr), conexao, sql);
}

std::string agora_em_utc() {
    const std::time_t agora = std::time(nullptr);
    std::tm partes{};
#if defined(_WIN32)
    gmtime_s(&partes, &agora);
#else
    gmtime_r(&agora, &partes);
#endif
    char texto[32];
    std::strftime(texto, sizeof texto, "%Y-%m-%dT%H:%M:%SZ", &partes);
    return texto;
}

}  // namespace

Indice::Indice(std::string caminho_do_banco) : caminho_(std::move(caminho_do_banco)) {
    const int codigo = sqlite3_open_v2(caminho_.c_str(), &conexao_, SQLITE_OPEN_READONLY, nullptr);
    if (codigo != SQLITE_OK) {
        const std::string mensagem = conexao_ ? sqlite3_errmsg(conexao_) : "sem memória";
        sqlite3_close(conexao_);
        throw std::runtime_error("não abriu o banco " + caminho_ + ": " + mensagem);
    }
    // O backend em Python escreve no mesmo banco. Se ele estiver no meio de
    // uma escrita, espera até 2 s em vez de falhar na hora.
    sqlite3_busy_timeout(conexao_, 2000);
    atualizar_se_mudou();
}

Indice::~Indice() {
    sqlite3_close(conexao_);
}

void Indice::atualizar_se_mudou() {
    std::lock_guard<std::mutex> trava(trava_do_banco_);

    // data_version muda quando outra conexão grava qualquer coisa no banco.
    // Custa quase nada, e na maior parte das perguntas é só isto que roda.
    const std::int64_t versao = um_inteiro(conexao_, "PRAGMA data_version");
    if (versao == versao_do_banco_) {
        return;
    }
    versao_do_banco_ = versao;

    // O banco mudou, mas quase sempre em outra tabela (uma mensagem do chat,
    // um login). Os trechos só entram e saem — nunca são editados no lugar,
    // reindexar apaga e insere com id novo —, então quantidade e maior id
    // bastam para saber se mudaram. As duas contas usam índice: não leem os
    // vetores.
    executar(conexao_, "BEGIN");
    try {
        const std::pair<std::int64_t, std::int64_t> assinatura{
            um_inteiro(conexao_, "SELECT count(*) FROM material_chunks"),
            um_inteiro(conexao_, "SELECT coalesce(max(id), 0) FROM material_chunks"),
        };
        bool tinha_fora_do_indice;
        {
            std::shared_lock<std::shared_mutex> leitura(trava_dos_dados_);
            tinha_fora_do_indice = dados_.fora_do_indice > 0;
        }
        // A exceção à regra: linha antiga, ainda em JSON, que o backend
        // converte para binário no lugar ao subir. Enquanto houver alguma,
        // qualquer mudança no banco recarrega.
        if (assinatura != assinatura_ || tinha_fora_do_indice) {
            Dados novos = carregar();
            assinatura_ = assinatura;
            std::unique_lock<std::shared_mutex> escrita(trava_dos_dados_);
            dados_ = std::move(novos);
            ++recargas_;
        }
        executar(conexao_, "COMMIT");
    } catch (...) {
        sqlite3_exec(conexao_, "ROLLBACK", nullptr, nullptr, nullptr);
        versao_do_banco_ = -1;  // tenta de novo na próxima busca
        throw;
    }
}

Indice::Dados Indice::carregar() {
    Dados dados;
    Consulta consulta(conexao_, "SELECT id, material_id, vetor FROM material_chunks ORDER BY id");
    while (consulta.proxima()) {
        Trecho trecho{sqlite3_column_int64(*consulta, 0), sqlite3_column_int64(*consulta, 1), 0, -1};
        if (sqlite3_column_type(*consulta, 2) == SQLITE_BLOB) {
            const auto* bytes = static_cast<const unsigned char*>(sqlite3_column_blob(*consulta, 2));
            const int tamanho = sqlite3_column_bytes(*consulta, 2);
            if (tamanho % 4 == 0) {
                trecho.inicio = dados.vetores.size();
                trecho.bytes = tamanho;
                dados.vetores.insert(dados.vetores.end(), bytes, bytes + tamanho);
            }
        }
        if (trecho.bytes < 0) {
            ++dados.fora_do_indice;
        }
        dados.trechos.push_back(trecho);
    }
    dados.carregado_em = agora_em_utc();
    return dados;
}

Indice::Resposta Indice::buscar(const Pedido& pedido) {
    const auto inicio = std::chrono::steady_clock::now();
    atualizar_se_mudou();

    Resposta resposta;
    std::shared_lock<std::shared_mutex> leitura(trava_dos_dados_);

    std::vector<const Trecho*> escolhidos;
    std::vector<const unsigned char*> enderecos;
    std::vector<std::int64_t> tamanhos;
    for (const Trecho& trecho : dados_.trechos) {
        if (pedido.materiais.count(trecho.material_id) == 0) {
            continue;
        }
        ++resposta.considerados;
        if (trecho.bytes < 0) {
            ++resposta.fora_do_indice;
            continue;
        }
        escolhidos.push_back(&trecho);
        enderecos.push_back(dados_.vetores.data() + trecho.inicio);
        tamanhos.push_back(trecho.bytes);
    }

    std::vector<double> similaridades(escolhidos.size());
    similaridade::calcular(pedido.pergunta.data(), static_cast<std::int64_t>(pedido.pergunta.size()),
                           enderecos.data(), tamanhos.data(), static_cast<std::int64_t>(escolhidos.size()),
                           similaridades.data());

    // Infinito ou NaN não cabem em JSON. Não acontece com vetor normalizado,
    // mas, se acontecer, o trecho conta como fora do índice e o Python, que
    // sabe lidar, faz a busca inteira.
    for (double valor : similaridades) {
        if (!std::isfinite(valor)) {
            ++resposta.fora_do_indice;
        }
    }

    // O corte do Python (regras/chat_ia.buscar_trechos_relevantes): quem está
    // abaixo da k-ésima melhor menos a folga não alcança o top-k nem com o
    // bônus literal inteiro.
    double corte = -INFINITY;
    if (similaridades.size() > pedido.top_k) {
        std::vector<double> copia = similaridades;
        std::nth_element(copia.begin(), copia.begin() + static_cast<std::ptrdiff_t>(pedido.top_k - 1), copia.end(),
                         std::greater<double>());
        corte = copia[pedido.top_k - 1] - pedido.folga;
    }
    for (std::size_t i = 0; i < escolhidos.size(); ++i) {
        if (similaridades[i] >= corte && std::isfinite(similaridades[i])) {
            resposta.trechos.push_back({escolhidos[i]->id, similaridades[i]});
        }
    }

    resposta.milissegundos =
        std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - inicio).count();
    return resposta;
}

Indice::Situacao Indice::situacao() {
    atualizar_se_mudou();
    std::shared_lock<std::shared_mutex> leitura(trava_dos_dados_);
    Situacao situacao;
    situacao.trechos = static_cast<std::int64_t>(dados_.trechos.size());
    situacao.fora_do_indice = dados_.fora_do_indice;
    for (const Trecho& trecho : dados_.trechos) {
        if (trecho.bytes >= 0) {
            situacao.dimensao = trecho.bytes / 4;
            break;
        }
    }
    situacao.bytes_na_memoria = static_cast<std::int64_t>(dados_.vetores.size());
    situacao.recargas = recargas_;
    situacao.carregado_em = dados_.carregado_em;
    situacao.banco = caminho_;
    return situacao;
}
