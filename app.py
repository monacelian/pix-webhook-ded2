# app.py
from flask import Flask, request, jsonify
import mercadopago
import qrcode
import io
import threading

ACCESS_TOKEN = "APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780"
sdk = mercadopago.SDK(ACCESS_TOKEN)

app = Flask(__name__)

# Pagamentos pendentes
pagamentos_pendentes = {}

def criar_pix(titulo, valor, email_cliente):
    preference_data = {
        "items": [{"title": titulo, "quantity": 1, "unit_price": valor}],
        "payer": {"email": email_cliente},
        "payment_methods": {"excluded_payment_types": [{"id": "ticket"}, {"id": "atm"}, {"id": "credit_card"}]},
        "back_urls": {"success": "https://www.google.com/", "failure": "https://www.google.com/", "pending": "https://www.google.com/"},
        "auto_return": "approved"
    }

    pref = sdk.preference().create(preference_data)
    link = pref["response"].get("init_point")
    pix_id = pref["response"]["id"]

    # Gerar QR Code
    qr = qrcode.QRCode()
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)

    # Guardar pagamento pendente
    pagamentos_pendentes[pix_id] = {"status": "pending", "link": link, "valor": valor, "email": email_cliente}

    return pix_id, link

@app.route("/gerar_pix")
def gerar_pix_route():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    pix_id, link = criar_pix("Pagamento via DedMais Pix", 1.0, email)
    return jsonify({"pix_id": pix_id, "link_pix": link})

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

    if payment_id:
        try:
            resp = sdk.payment().get(payment_id)
            payment = resp["response"]
            print(f"Pagamento ID: {payment.get('id')} Status: {payment.get('status')}")
        except Exception as e:
            print("Erro ao consultar API:", e)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
