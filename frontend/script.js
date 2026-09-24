const formulario = document.querySelector("form");
const botao = formulario.querySelector("button[type='submit']");
const mensagem = document.querySelector("#mensagem");

function mostrarMensagem(texto) {
    mensagem.textContent = texto;
}

formulario.addEventListener("submit", async function (event) {
    event.preventDefault();

    const email = document.querySelector("#email").value.trim();
    const senha = document.querySelector("#senha").value;

    mostrarMensagem("");
    botao.disabled = true;
    botao.textContent = "Entrando...";

    try {
        const resposta = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email: email, senha: senha })
        });

        const dados = await resposta.json();

        if (dados.mensagem) {
            mostrarMensagem(dados.mensagem);
        }

        if (dados.pagina && dados.token) {
            // O token é o que autentica as próximas requisições; sem ele, as
            // páginas de perfil mandam de volta para cá.
            salvarUsuarioLogado({ email: dados.email, tipo: dados.tipo, nome: dados.nome || "" }, dados.token);
            window.location.href = dados.pagina;
            return;
        }

        if (!resposta.ok && !dados.mensagem) {
            mostrarMensagem("E-mail ou senha incorretos.");
        }
    } catch (erro) {
        console.error("Erro no login:", erro);
        mostrarMensagem("Não foi possível conectar ao servidor. Tente novamente.");
    }

    botao.disabled = false;
    botao.textContent = "Entrar";
});

const esqueciSenha = document.querySelector("#esqueciSenha");

esqueciSenha.addEventListener("click", async function (event) {
    event.preventDefault();

    const email = await perguntar(
        { nome: "email", rotulo: "E-mail da conta", tipo: "email", placeholder: "nome@instituicao.edu.br" },
        { titulo: "Recuperar senha", mensagem: "Enviaremos um código de recuperação para este e-mail.", rotulo: "Enviar código" }
    );

    if (!email) return;

    try {
        const resposta = await fetch(`${API_URL}/recuperar-senha`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email: email })
        });

        const dados = await resposta.json();

        if (!resposta.ok || !dados.mensagem || !dados.mensagem.startsWith("Enviamos")) {
            await avisarErro(dados.mensagem || "Não foi possível iniciar a recuperação.");
            return;
        }

        // Código e nova senha no mesmo diálogo: são dois campos do mesmo passo,
        // e pedir um de cada vez fazia o usuário perder o código ao voltar.
        const redefinicao = await perguntar(
            [
                { nome: "token", rotulo: "Código de recuperação" },
                { nome: "senha", rotulo: "Nova senha", tipo: "password", minimo: 6, placeholder: "mínimo 6 caracteres" },
            ],
            { titulo: "Definir nova senha", mensagem: dados.mensagem, rotulo: "Redefinir" }
        );

        if (!redefinicao) return;

        const respostaReset = await fetch(`${API_URL}/redefinir-senha`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ token: redefinicao.token, nova_senha: redefinicao.senha })
        });

        const dadosReset = await respostaReset.json();

        if (dadosReset.sucesso) {
            await avisar(dadosReset.mensagem, "Senha redefinida");
        } else {
            await avisarErro(dadosReset.mensagem || "Não foi possível redefinir a senha.");
        }
    } catch (erro) {
        console.error("Erro na recuperação de senha:", erro);
        await avisarErro("Não foi possível conectar ao servidor. Tente novamente.");
    }
});
