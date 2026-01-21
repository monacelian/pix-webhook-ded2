console.log("📘 Extensão DedMais Pix ativa");

function criarPixContainer() {
  if (document.getElementById("pix-container")) return;

  const container = document.createElement("div");
  container.id = "pix-container";
  container.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    background: #f5f5f5;
    padding: 10px 14px;
    border: 1px solid #ccc;
    border-radius: 6px;
    z-index: 9999;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    font-family: sans-serif;
  `;

  const input = document.createElement("input");
  input.id = "input-email-pix";
  input.placeholder = "Digite seu email";
  input.style.cssText = `
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid #ccc;
    width: 180px;
  `;

  const btn = document.createElement("button");
  btn.id = "btn-validar-pix";
  btn.textContent = "Gerar Pix 1 real";
  btn.style.cssText = `
    margin-left: 6px;
    padding: 4px 10px;
    border-radius: 4px;
    background: #1976d2;
    color: white;
    font-weight: bold;
    cursor: pointer;
    border: none;
  `;

  container.appendChild(input);
  container.appendChild(btn);
  document.body.appendChild(container);

  btn.onclick = async () => {
    const email = input.value.trim();
    if (!email) {
      alert("Digite um email!");
      return;
    }

    btn.disabled = true;
    btn.textContent = "Gerando...";

    try {
      const resp = await fetch(`https://web-production-dc4e3.up.railway.app/gerar_pix?email=${encodeURIComponent(email)}`);
      const json = await resp.json();

      if (json.qr_base64) {
        // Remove QR antigo se existir
        const oldQr = document.getElementById("qr-pix");
        if (oldQr) oldQr.remove();

        // Cria QR Code usando Base64
        const qrImg = document.createElement("img");
        qrImg.src = `data:image/png;base64,${json.qr_base64}`;
        qrImg.style.marginTop = "8px";
        qrImg.id = "qr-pix";
        container.appendChild(qrImg);

        btn.textContent = "Pago? ⏳"; // opcional, muda após o pagamento
        alert(`✅ Pix gerado: R$${json.valor}`);
      } else {
        alert("❌ Não foi possível gerar Pix");
      }
    } catch (e) {
      console.error(e);
      alert("Erro na comunicação com o servidor");
    } finally {
      btn.disabled = false;
      btn.textContent = "Gerar Pix 1 real";
    }
  };
}

window.addEventListener("load", criarPixContainer);
