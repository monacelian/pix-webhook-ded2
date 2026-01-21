# server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import os

app = Flask(__name__)

# Permitir apenas nosso site
CORS(app, origins=["https://dedmais.educacao.mg.gov.br"])

# Mercado Pago
mp = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # Cria pagamento Pix
    payment_data = {
        "transaction_amount": 1.0,
        "description": "Pagamento Pix DedMais",
        "payment_method_id": "pix",
        "payer": {"email": email},
    }

    payment = mp.payment().create(payment_data)

    if payment["status"] != 201:
        return jsonify({"error": "Erro ao criar pagamento"}), 500

    result = payment["response"]

    pix_payload = result.get("point_of_interaction", {}) \
                        .get("transaction_data", {}) \
                        .get("qr_code")

    qr_base64 = result.get("point_of_interaction", {}) \
                      .get("transaction_data", {}) \
                      .get("qr_code_base64")

    if not pix_payload or not qr_base64:
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

    return jsonify({
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": result["transaction_amount"]
    })

@app.route("/")
def home():
    return "Servidor PIX ONLINE 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
