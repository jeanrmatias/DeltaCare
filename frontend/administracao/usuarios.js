/**
 * Gestão de usuários (admin).
 *
 * Fecha o caminho pelo qual professores e administradores entram no sistema.
 * A rota `POST /admin/usuarios` já existia no backend, mas nenhuma tela a
 * chamava — na prática, criar uma conta de professor exigia rodar um script.
 *
 * Conta de aluno não se cria aqui de propósito: o aluno se cadastra sozinho
 * pela tela de login (`/cadastro`, que só aceita o tipo "aluno"), e a
 * administração apenas o matricula numa turma. Isso mantém o cadastro público
 * sem nenhum caminho para virar conta de confiança.
 */

const usuario = exigirAcesso("adm");

let usuariosCarregados = [];

if (usuario) {
    montarRodapePerfil(usuario);
    carregarUsuarios();
    ligarFormulario();
    ligarPlaceholders();
    document.querySelector("#botaoSair").addEventListener("click", sair);
    document.querySelector("#campoBusca").addEventListener("input", desenharLista);
}

function nomeAPartirDoEmail(email) {
    const apelido = (email || "").split("@")[0].replace(/[._-]+/g, " ");
    return apelido
        .split(" ")
        .filter(Boolean)
        .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
        .join(" ");
}

function iniciais(nome) {
    const partes = (nome || "").trim().split(/\s+/).filter(Boolean);
    if (partes.length === 0) return "--";
    if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
    return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function montarRodapePerfil(usuario) {
    const nome = nomeAPartirDoEmail(usuario.email);
    document.querySelector("#avatarRodape").textContent = iniciais(nome);
    document.querySelector("#nomeRodape").textContent = nome;
}

const ROTULOS_PERFIL = {
    adm: "Administrador",
    professor: "Professor",
    aluno: "Aluno",
};

async function carregarUsuarios() {
    const vazio = document.querySelector("#estadoVazio");

    try {
        const resposta = await api("/admin/usuarios");
        const dados = await resposta.json();

        if (!dados.sucesso) {
            vazio.hidden = false;
            vazio.textContent = dados.mensagem || "Não foi possível carregar os usuários.";
            return;
        }

        usuariosCarregados = dados.usuarios || [];
        preencherEstatisticas();
        desenharLista();
    } catch (erro) {
        console.error("Erro ao carregar usuários:", erro);
        vazio.hidden = false;
        vazio.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
    }
}

function preencherEstatisticas() {
    const contar = (tipo) => usuariosCarregados.filter((u) => u.tipo === tipo).length;

    document.querySelector("#statAdmins").textContent = contar("adm");
    document.querySelector("#statProfessores").textContent = contar("professor");
    document.querySelector("#statAlunos").textContent = contar("aluno");
}

function desenharLista() {
    const lista = document.querySelector("#listaUsuarios");
    const cartao = document.querySelector("#cartaoLista");
    const vazio = document.querySelector("#estadoVazio");

    const termo = document.querySelector("#campoBusca").value.trim().toLowerCase();
    const filtrados = usuariosCarregados.filter((u) => !termo || u.email.toLowerCase().includes(termo));

    if (filtrados.length === 0) {
        cartao.hidden = true;
        vazio.hidden = false;
        vazio.textContent = usuariosCarregados.length === 0
            ? "Nenhuma conta cadastrada."
            : "Nenhuma conta corresponde à sua busca.";
        return;
    }

    vazio.hidden = true;
    cartao.hidden = false;
    lista.innerHTML = "";

    filtrados.forEach((u) => lista.appendChild(montarLinha(u)));
}

function montarLinha(dados) {
    const linha = document.createElement("article");
    linha.className = "material-linha";

    const info = document.createElement("div");
    info.className = "material-linha-info";

    const topo = document.createElement("div");
    topo.className = "material-linha-topo";

    const badge = document.createElement("span");
    badge.className = `badge-tipo badge-perfil badge-perfil--${dados.tipo}`;
    badge.textContent = ROTULOS_PERFIL[dados.tipo] || dados.tipo;
    topo.appendChild(badge);

    // A conta em uso fica marcada: ajuda a não confundir na demonstração e,
    // no futuro, a impedir que o admin remova o próprio acesso.
    if (dados.email === usuario.email) {
        const marca = document.createElement("span");
        marca.className = "material-turma";
        marca.textContent = "você";
        topo.appendChild(marca);
    }

    const titulo = document.createElement("h3");
    titulo.textContent = dados.email;

    info.appendChild(topo);
    info.appendChild(titulo);

    const vinculo = descreverVinculo(dados);
    if (vinculo) {
        const p = document.createElement("p");
        p.className = "material-classificacao";
        p.textContent = vinculo;
        info.appendChild(p);
    }

    linha.appendChild(info);
    return linha;
}

function descreverVinculo(dados) {
    if (dados.tipo === "professor") {
        const n = dados.total_turmas || 0;
        return n === 0 ? "Nenhuma turma atribuída" : `${n} turma${n > 1 ? "s" : ""} atribuída${n > 1 ? "s" : ""}`;
    }

    if (dados.tipo === "aluno") {
        const n = dados.total_matriculas || 0;
        return n === 0 ? "Sem matrícula" : `Matriculado em ${n} turma${n > 1 ? "s" : ""}`;
    }

    return "Acesso completo à administração";
}

function ligarFormulario() {
    const cartao = document.querySelector("#cartaoFormulario");
    const formulario = document.querySelector("#formularioUsuario");
    const mensagem = document.querySelector("#mensagemFormulario");

    document.querySelector("#botaoNovoUsuario").addEventListener("click", () => {
        cartao.hidden = !cartao.hidden;
        mensagem.textContent = "";
        mensagem.classList.remove("formulario-mensagem--sucesso");
        if (!cartao.hidden) document.querySelector("#usuarioEmail").focus();
    });

    document.querySelector("#botaoCancelar").addEventListener("click", () => {
        cartao.hidden = true;
        formulario.reset();
        mensagem.textContent = "";
    });

    formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const email = document.querySelector("#usuarioEmail").value.trim();
        const senha = document.querySelector("#usuarioSenha").value;
        const tipo = document.querySelector("#usuarioTipo").value;

        mensagem.textContent = "";
        mensagem.classList.remove("formulario-mensagem--sucesso");

        try {
            const resposta = await api("/admin/usuarios", {
                method: "POST",
                body: JSON.stringify({ email, senha, tipo }),
            });
            const dados = await resposta.json();

            mensagem.textContent = dados.mensagem || "";

            if (dados.sucesso) {
                mensagem.classList.add("formulario-mensagem--sucesso");
                formulario.reset();
                await carregarUsuarios();
            }
        } catch (erro) {
            console.error("Erro ao criar conta:", erro);
            mensagem.textContent = "Não foi possível conectar ao servidor. Tente novamente.";
        }
    });
}

function ligarPlaceholders() {
    document.querySelectorAll("[data-em-breve]").forEach((elemento) => {
        elemento.addEventListener("click", (evento) => {
            evento.preventDefault();
            alert(`${elemento.dataset.emBreve} ainda não está disponível nesta versão.`);
        });
    });
}
