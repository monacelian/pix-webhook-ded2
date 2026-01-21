from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago

app = Flask(__name__)
CORS(app)

# Inicializa Mercado Pago com seu Access Token
mp = mercadopago.SDK("APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780")

@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,  # valor de teste 1 real
        "description": "Pagamento de teste",
        "payment_method_id": "pix",
        "payer": {"email": email},
    }

    try:
        payment_response = mp.payment().create(payment_data)
        payment = payment_response["response"]

        # Pega link do QR code
        qr_link_url = payment.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")

        return jsonify({
            "link_pix": qr_link_url or "",
            "valor": payment.get("transaction_amount", 1.0)
        })
    except Exception as e:
        print("Erro ao gerar Pix:", e)
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Recebi webhook:", data)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
