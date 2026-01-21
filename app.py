# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import qrcode
import io
import base64
import os

app = Flask(__name__)
CORS(app)  # libera requisições cross-origin

# ⚠️ Coloque seu Access Token de produção do Mercado Pago
ACCESS_TOKEN = "APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780"
sdk = mercadopago.SDK(ACCESS_TOKEN)

# ----------------- GERAR PIX -----------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    try:
        preference_data = {
            "items": [{"title": "Pagamento DedMais Pix", "quantity": 1, "unit_price": 1.0}],
            "payer": {"email": email},
            "payment_methods": {"excluded_payment_types": [{"id": "ticket"}, {"id": "atm"}, {"id": "credit_card"}]},
            "back_urls": {"success": "https://www.google.com/", "failure": "https://www.google.com/", "pending": "https://www.google.com/"},
            "auto_return": "approved"
        }

        pref = sdk.preference().create(preference_data)
        link = pref["response"].get("init_point")

        # Gerar QR Code em Base64
        qr = qrcode.QRCode()
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        return jsonify({
            "qr_base64": qr_base64,
            "link_pix": link,
            "valor": 1.0
        })

    except Exception as e:
        print("Erro ao gerar Pix:", e)
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

# ----------------- WEBHOOK -----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Recebi webhook:", data)
    return "OK", 200

# ----------------- RUN -----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
