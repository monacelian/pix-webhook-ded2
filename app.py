# servidor_pix.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import qrcode
import io
import base64

# ----------------- CONFIGURAÇÃO -----------------
# Substitua pelo seu Access Token de PRODUÇÃO
ACCESS_TOKEN = "APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780"

sdk = mercadopago.SDK(ACCESS_TOKEN)
app = Flask(__name__)
CORS(app)  # permite comunicação com a extensão

# ----------------- GERAR PIX -----------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,  # valor em reais
        "description": "Pagamento via DedMais Pix",
        "payment_method_id": "pix",
        "payer": {"email": email},
    }

    try:
        # Criar pagamento Pix
        payment_response = sdk.payment().create(payment_data)
        payment = payment_response["response"]

        # Pega o payload Pix oficial
        pix_payload = payment.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")

        if not pix_payload:
            return jsonify({"error": "Não foi possível gerar Pix"}), 500

        # Gerar QR Code em base64 (pode usar na extensão)
        qr = qrcode.QRCode()
        qr.add_data(pix_payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        qr_base64 = base64.b64encode(buf.read()).decode("utf-8")

        return jsonify({
            "pix_payload": pix_payload,     # Payload oficial do Pix
            "qr_base64": qr_base64,         # QR Code em base64 para mostrar direto
            "valor": payment.get("transaction_amount", 1.0)
        })

    except Exception as e:
        print("Erro ao gerar Pix:", e)
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

# ----------------- WEBHOOK -----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Recebi webhook:", data)

    # Aqui você pode adicionar lógica para marcar pagamento como concluído
    # ou enviar mensagem para extensão via websocket / polling

    return "OK", 200

# ----------------- RUN -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
