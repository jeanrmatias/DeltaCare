document.getElementById('loginForm').addEventListener('submit', function(e) {
  e.preventDefault();
  const lgpd = document.getElementById('lgpd');
  if (!lgpd.checked) {
    alert('Você deve aceitar a política de privacidade e LGPD para continuar.');
    return;
  }
  alert('Login realizado com sucesso!');
});