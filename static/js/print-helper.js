(function () {
  function criarBarra() {
    if (document.getElementById("print-toolbar")) return;
    const barra = document.createElement("div");
    barra.id = "print-toolbar";
    barra.className = "print-toolbar no-print";
    barra.innerHTML = [
      '<button type="button" id="print-action">Imprimir novamente</button>',
      '<span id="print-status" role="status">Comprovante pronto para impressão.</span>'
    ].join("");
    document.body.prepend(barra);
    document.getElementById("print-action").addEventListener("click", solicitarImpressao);
  }

  function definirStatus(texto) {
    const status = document.getElementById("print-status");
    if (status) status.textContent = texto;
  }

  function solicitarImpressao() {
    definirStatus("Enviando para a janela de impressão...");
    window.print();
  }

  window.solicitarImpressao = solicitarImpressao;
  window.addEventListener("beforeprint", function () {
    definirStatus("Janela de impressão aberta.");
  });
  window.addEventListener("afterprint", function () {
    definirStatus("Janela de impressão concluída ou cancelada. Confirme a saída na impressora.");
  });
  window.addEventListener("load", function () {
    criarBarra();
    const auto = new URLSearchParams(window.location.search).get("autoprint") !== "0";
    if (auto) window.setTimeout(solicitarImpressao, 120);
  });
})();
