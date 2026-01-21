# server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import os

app = Flask(__name__)
CORS(app)

# -----------------------------
# Configurações do Mercado Pago
# -----------------------------
MP_ACCESS_TOKEN = "APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780"
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# -----------------------------
# Rota para gerar PIX
# -----------------------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,
        "description": "Pagamento Pix DedMais",
        "payment_method_id": "pix",
        "payer": {"email": email},
    }

    try:
        payment = mp.payment().create(payment_data)
    except Exception as e:
        return jsonify({"error": f"Erro ao criar pagamento: {str(e)}"}), 500

    result = payment.get("response", {})
    pi = result.get("point_of_interaction", {}).get("transaction_data", {})

    pix_payload = pi.get("qr_code")
    qr_base64 = pi.get("qr_code_base64")

    if not pix_payload or not qr_base64:
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

    return jsonify({
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": result.get("transaction_amount", 0)
    })

# -----------------------------
# Healthcheck
# -----------------------------
@app.route("/")
def home():
    return "Servidor PIX DedMais ONLINE 🚀"

# -----------------------------
# Rodar servidor
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
