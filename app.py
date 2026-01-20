import os
from flask import Flask, request, jsonify
import mercadopago

app = Flask(__name__)

# Token vem da variável de ambiente
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

if not MP_ACCESS_TOKEN:
    raise Exception("MP_ACCESS_TOKEN não definido")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

@app.route("/")
def home():
    return "Servidor PIX + Webhook Mercado Pago OK"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook recebido:", data)

    payment_id = None

    if data and "data" in data and "id" in data["data"]:
        payment_id = data["data"]["id"]

    if not payment_id:
        payment_id = request.args.get("id")

    if not payment_id:
        return jsonify({"ignored": True}), 200

    payment = sdk.payment().get(payment_id)

    if payment["status"] != 200:
        return jsonify({"error": "payment_not_found"}), 200

    info = payment["response"]

    print("ID:", info["id"])
    print("Status:", info["status"])
    print("Valor:", info["transaction_amount"])
    print("Método:", info["payment_method_id"])

    if info["status"] == "approved" and info["payment_method_id"] == "bank_transfer":
        print("✅ PIX APROVADO")

        # 🔗 AQUI entra o DED 2.0
        # ex: liberar acesso / chamar API / registrar planilha

    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
