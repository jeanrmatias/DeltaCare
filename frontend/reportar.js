/**
 * Reportar um material direto da tela em que ele aparece.
 *
 * Carregado pelas listas de material do aluno e do professor. A tela de
 * Denúncias serve para **acompanhar** o que foi reportado; reportar acontece
 * aqui, no item, que é onde a pessoa está quando percebe o problema.
 *
 * Os motivos vêm do servidor (`GET /denuncias`), e não de uma cópia local:
 * duas listas iguais em lugares diferentes viram duas listas diferentes no dia
 * em que alguém acrescenta um motivo.
 */

let _motivosDenuncia = null;

async function carregarMotivosDenuncia() {
    if (_motivosDenuncia) return _motivosDenuncia;

    try {
        const resposta = await api("/denuncias");
        const dados = await resposta.json();
        _motivosDenuncia = dados.motivos || [];
    } catch (erro) {
        console.error("Erro ao carregar motivos:", erro);
        _motivosDenuncia = [];
    }

    return _motivosDenuncia;
}

/** Abre o diálogo de denúncia para um material e envia o que for preenchido. */
async function reportarMaterial(material) {
    const motivos = await carregarMotivosDenuncia();

    if (!motivos.length) {
        await avisarErro("Não foi possível carregar os motivos agora. Tente de novo em instantes.");
        return;
    }

    const resultado = await perguntar(
        [
            {
                nome: "motivo",
                rotulo: "Motivo",
                tipo: "select",
                opcoes: motivos.map((m) => ({ valor: m.valor, rotulo: m.rotulo })),
            },
            {
                nome: "descricao",
                rotulo: "O que está errado",
                placeholder: "Quanto mais específico, mais rápido resolve",
                // Opcional aqui; o servidor exige quando o motivo é "outro",
                // que é o único caso em que o motivo sozinho não diz nada.
                obrigatorio: false,
            },
        ],
        {
            titulo: "Reportar conteúdo",
            mensagem: `"${material.titulo}" será enviado para a administração analisar.`,
            rotulo: "Enviar denúncia",
        }
    );

    if (!resultado) return;

    try {
        const resposta = await api("/denuncias", {
            method: "POST",
            body: JSON.stringify({
                material_id: material.id,
                motivo: resultado.motivo,
                descricao: (resultado.descricao || "").trim(),
            }),
        });
        const dados = await resposta.json();

        if (dados.sucesso) {
            await avisar(dados.mensagem, "Denúncia registrada");
        } else {
            await avisarErro(dados.mensagem || "Não foi possível registrar a denúncia.");
        }
    } catch (erro) {
        console.error("Erro ao reportar material:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
}
