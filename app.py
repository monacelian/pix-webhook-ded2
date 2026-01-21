btn.onclick = async () => {
  const email = input.value.trim();
  if (!email) {
    status.textContent = "❌ Digite um email!";
    return;
  }

  btn.disabled = true;
  btn.textContent = "Gerando...";
  status.textContent = "";

  try {
    const resp = await fetch(`https://web-production-dc4e3.up.railway.app/gerar_pix?email=${encodeURIComponent(email)}`);
    const json = await resp.json();

    if (json.qr_base64) {
      // Remove QR antigo
      const oldQr = document.getElementById("qr-pix");
      if (oldQr) oldQr.remove();

      const qrImg = document.createElement("img");
      qrImg.id = "qr-pix";
      qrImg.src = `data:image/png;base64,${json.qr_base64}`;
      qrImg.style.marginTop = "8px";
      qrImg.style.display = "block";

      container.appendChild(qrImg);
      status.textContent = `✅ Pix gerado: R$${json.valor}`;
      btn.textContent = "Pago? ⏳";
    } else {
      status.textContent = "❌ Não foi possível gerar Pix";
    }
  } catch (e) {
    console.error(e);
    status.textContent = "⚠️ Erro na comunicação com o servidor";
  } finally {
    btn.disabled = false;
    btn.textContent = "Gerar Pix 1 real";
  }
};
