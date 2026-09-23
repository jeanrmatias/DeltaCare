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

        if (dados.pagina) {
            salvarUsuarioLogado({ email: dados.email, tipo: dados.tipo });
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

    const email = prompt("Digite seu e-mail:");

    if (!email) {
        return;
    }

    try {
        const resposta = await fetch(`${API_URL}/recuperar-senha`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email: email })
        });

        const dados = await resposta.json();
        alert(dados.mensagem);

        if (!resposta.ok || !dados.mensagem || !dados.mensagem.startsWith("Enviamos")) {
            return;
        }

        const token = prompt("Digite o código de recuperação que você recebeu:");
        if (!token) {
            return;
        }

        const novaSenha = prompt("Digite sua nova senha (mínimo 6 caracteres):");
        if (!novaSenha) {
            return;
        }

        const respostaReset = await fetch(`${API_URL}/redefinir-senha`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ token: token, nova_senha: novaSenha })
        });

        const dadosReset = await respostaReset.json();
        alert(dadosReset.mensagem);
    } catch (erro) {
        console.error("Erro na recuperação de senha:", erro);
        alert("Não foi possível conectar ao servidor. Tente novamente.");
    }
});
