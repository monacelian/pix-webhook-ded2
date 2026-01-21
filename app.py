from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago

# ----------------- CONFIGURAÇÃO -----------------
ACCESS_TOKEN = "APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780"
sdk = mercadopago.SDK(ACCESS_TOKEN)

app = Flask(__name__)
CORS(app)  # Permite requisições cross-origin

# ----------------- GERAR PIX -----------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # Criação de preferência (somente Pix)
    preference_data = {
        "items": [{"title": "Pagamento via DedMais Pix", "quantity": 1, "unit_price": 1.0}],
        "payer": {"email": email},
        "payment_methods": {
            "excluded_payment_types": [{"id": "ticket"}, {"id": "atm"}, {"id": "credit_card"}]
        },
        "back_urls": {"success": "https://www.google.com", "failure": "https://www.google.com"},
        "auto_return": "approved"
    }

    try:
        pref = sdk.preference().create(preference_data)
        link = pref["response"].get("init_point")

        if not link:
            return jsonify({"error": "Não foi possível gerar link Pix"}), 500

        return j
