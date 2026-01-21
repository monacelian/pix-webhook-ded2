from flask import Flask, request, jsonify
import mercadopago
import qrcode
import base64
import io
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app = Flask(__name__)

sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email", "anonimo@dedmais.com")

    payment_data = {
        "transaction_amount": 1.0,
        "description": "Pagamento Pix DedMais",
        "payment_method_id": "pix",
        "payer": {
            "email": email
        }
    }

    result = sdk.payment().create(payment_data)
    payment = result["response"]

    pix_payload = payment["point_of_interaction"]["transaction_data"]["qr_code"]

    qr = qrcode.make(pix_payload)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")

    qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return jsonify({
        "pix_id": payment["id"],
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": 1
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

