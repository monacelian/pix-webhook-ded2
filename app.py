from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import os

# ------------------ APP ------------------
app = Flask(__name__)
CORS(app)

# ------------------ HOME ------------------
@app.route("/")
def home():
    return "OK"

# ------------------ MERCADO PAGO ------------------
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

if not MP_ACCESS_TOKEN:
    raise Exception("MP_ACCESS_TOKEN não definido")

mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# ------------------ GERAR PIX ------------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")

    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,
        "description": "Pagamento Pix DedMais",
        "payment_method_id": "pix",
        "payer": {
            "email": email
        }
    }

    payment = mp.payment().create(payment_data)

    if payment["status"] != 201:
        return jsonify({
            "error": "Erro ao criar pagamento",
            "detalhes": payment
        }), 500

    result = payment["response"]

    transaction = result.get("point_of_interaction", {}).get("transaction_data", {})

    pix_payload = transaction.get("qr_code")
    qr_base64 = transaction.get("qr_code_base64")

    if not pix_payload or not qr_base64:
        return jsonify({"error": "Pix não retornado"}), 500

    return jsonify({
        "pix_id": result["id"],
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": result["transaction_amount"]
    })

# ------------------ START ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
