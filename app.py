from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import qrcode
from io import BytesIO
import base64
import threading
import time

# ---------------- CONFIGURAÇÃO ----------------
ACCESS_TOKEN = "APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780"
sdk = mercadopago.SDK(ACCESS_TOKEN)

app = Flask(__name__)
CORS(app)  # permite comunicação com a extensão

# ---------------- PAGAMENTOS PENDENTES ----------------
pagamentos_pendentes = {}

# ---------------- FUNÇÃO PARA GERAR QR CODE BASE64 ----------------
def gerar_qr_base64(payload):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    qr_b64 = base64.b64encode(buf.read()).decode("utf-8")
    return qr_b64

# ---------------- ENDPOINT PARA GERAR PIX ----------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,  # valor fixo 1 real
        "description": "Pagamento via DedMais Pix",
        "payment_method_id": "pix",
        "payer": {"email": email},
    }

    try:
        payment_response = sdk.payment().create(payment_data)
        payment = payment_response["response"]

        pix_payload = payment.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")
        if not pix_payload:
            return jsonify({"error": "Não foi possível gerar Pix"}), 500

        qr_base64 = gerar_qr_base64(pix_payload)

        # Salvar pagamento pendente
        pagamentos_pendentes[payment["id"]] = {
            "status": "pending",
            "pix_payload": pix_payload,
            "valor": payment.get("transaction_amount", 1.0),
            "email": email
        }

        return jsonify({
            "pix_payload": pix_payload,
            "qr_base64": qr_base64,
            "valor": payment.get("transaction_amount", 1.0),
            "pix_id": payment["id"]
        })

    except Exception as e:
        print("Erro ao gerar Pix:", e)
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

# ---------------- WEBHOOK PARA RECEBER NOTIFICAÇÕES ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("=== Notificação recebida do Mercado Pago ===")
    print(data)

    payment_id = None
    if "data" in data and "id" in data["data"]:
        payment_id = data["data"]["id"]
    elif "resource" in data:
        payment_id = data["resource"].split("/")[-1]

    if payment_id and payment_id in pagamentos_pendentes:
        resp = sdk.payment().get(payment_id)
        payment = resp["response"]
        status = payment.get("status")
        pagamentos_pendentes[payment_id]["status"] = status
        print(f"Pagamento {payment_id} atualizado para {status}")

    return "OK", 200

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
