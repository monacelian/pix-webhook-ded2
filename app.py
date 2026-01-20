# app.py
from flask import Flask, request, jsonify
import mercadopago

app = Flask(__name__)

# Configurar o access token do Mercado Pago
mp = mercadopago.SDK("APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780")

# Endpoint para gerar pagamento Pix
@app.route("/validar")
def validar():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # Criar pagamento de teste
    payment_data = {
        "transaction_amount": 1.0,  # valor de teste 1 real
        "description": "Pagamento de teste",
        "payment_method_id": "pix",
        "payer": {"email": email}
    }

    payment_response = mp.payment().create(payment_data)
    if payment_response["status"] != 201:
        return jsonify({"error": payment_response}), 500

    # Retornar dados do Pix
    pix_info = payment_response["response"]["point_of_interaction"]["transaction_data"]
    return jsonify({
        "qr_code": pix_info.get("qr_code"),
        "qr_code_base64": pix_info.get("qr_code_base64")
    })

# Webhook para receber notificações de pagamento
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook recebido:", data)
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
