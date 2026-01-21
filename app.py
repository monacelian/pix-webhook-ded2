# servidor_pix_railway.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import qrcode
import io

# ----------------- CONFIGURAÇÃO -----------------
ACCESS_TOKEN = "APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780"
sdk = mercadopago.SDK(ACCESS_TOKEN)

app = Flask(__name__)
CORS(app)

# ----------------- PAGAMENTOS PENDENTES -----------------
pagamentos_pendentes = {}

# ----------------- GERAR PIX -----------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    try:
        preference_data = {
            "items": [{"title": "Pagamento via DedMais Pix", "quantity": 1, "unit_price": 1.0}],
            "payer": {"email": email},
            "payment_methods": {"excluded_payment_types": [{"id": "ticket"}, {"id": "atm"}, {"id": "credit_card"}]},
            "back_urls": {
                "success": "https://www.google.com/",
                "failure": "https://www.google.com/",
                "pending": "https://www.google.com/"
            },
            "auto_return": "approved"
        }

        pref = sdk.preference().create(preference_data)
        pref_resp = pref["response"]

        pix_payload = pref_resp.get("sandbox_init_point") or pref_resp.get("init_point")
        if not pix_payload:
            return jsonify({"error": "Não foi possível gerar Pix"}), 500

        # Gerar QR Code em Base64
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(pix_payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        qr_base64 = buf.getvalue().encode("base64").decode() if hasattr(buf.getvalue(), 'encode') else io.BytesIO(buf.getvalue()).getvalue().hex()

        # Guardar pagamento pendente
        pagamentos_pendentes[pref_resp["id"]] = {"status": "pending", "valor": 1.0, "email": email}

        return jsonify({
            "pix_payload": pix_payload,
            "qr_base64": qr_base64,
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

    payment_id = None
    if "data" in data and "id" in data["data"]:
        payment_id = data["data"]["id"]
    elif "resource" in data:
        payment_id = data["resource"].split("/")[-1]

    if payment_id:
        try:
            resp = sdk.payment().get(payment_id)
            payment = resp["response"]
            print(f"Pagamento ID: {payment.get('id')}")
            print(f"Status: {payment.get('status')}")
            print(f"Método: {payment.get('payment_type_id')}")
            print(f"Valor: {payment.get('transaction_amount')}")
            # Atualizar status do pagamento
            if payment.get("status") == "approved":
                for key, p in pagamentos_pendentes.items():
                    if p["email"] == payment.get("payer", {}).get("email"):
                        pagamentos_pendentes[key]["status"] = "paid"
        except Exception as e:
            print("Erro ao consultar API:", e)

    return "OK", 200

# ----------------- RUN -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
