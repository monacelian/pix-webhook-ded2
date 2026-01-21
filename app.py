# gerar_pix_railway.py
from flask import Flask, request, jsonify
import mercadopago
import qrcode
import io

ACCESS_TOKEN = "APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780"
sdk = mercadopago.SDK(ACCESS_TOKEN)
app = Flask(__name__)

pagamentos_pendentes = {}

@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    try:
        # Criar preferência para pagamento Pix
        preference_data = {
            "items": [{"title": "Pagamento teste Pix", "quantity": 1, "unit_price": 1.0}],
            "payer": {"email": email},
            "payment_methods": {
                "excluded_payment_types": [{"id": "ticket"}, {"id": "atm"}, {"id": "credit_card"}]
            },
            "back_urls": {
                "success": "https://www.google.com/",
                "failure": "https://www.google.com/",
                "pending": "https://www.google.com/"
            },
            "auto_return": "approved"
        }

        pref = sdk.preference().create(preference_data)
        link = pref["response"].get("init_point")
        pix_id = pref["response"]["id"]

        pagamentos_pendentes[pix_id] = {"status": "pending", "link": link, "valor": 1.0, "email": email}

        return jsonify({"link_pix": link, "valor": 1.0})

    except Exception as e:
        print("Erro ao gerar Pix:", e)
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook recebido:", data)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
