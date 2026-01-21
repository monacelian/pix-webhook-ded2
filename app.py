from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import os
import psycopg2
from datetime import datetime

# ------------------ APP ------------------
app = Flask(__name__)
CORS(app)

# ------------------ ENV ------------------
DATABASE_URL = os.getenv("DATABASE_URL")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

# ------------------ MERCADO PAGO ------------------
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# ------------------ DATABASE ------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ------------------ ROTAS ------------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")

    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # -------- MERCADO PAGO --------
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
        return jsonify({"error": "Erro ao criar pagamento"}), 500

    result = payment["response"]

    pix_payload = result.get("point_of_interaction", {}) \
                        .get("transaction_data", {}) \
                        .get("qr_code")

    qr_base64 = result.get("point_of_interaction", {}) \
                      .get("transaction_data", {}) \
                      .get("qr_code_base64")

    if not pix_payload or not qr_base64:
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

    payment_id = str(result["id"])
    valor = result["transaction_amount"]

    # -------- SALVAR NO BANCO --------
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO pagamentos (payment_id, email, status, valor, data_pagamento)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            payment_id,
            email,
            "pending",
            valor,
            datetime.utcnow()
        ))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("Erro banco:", e)
        return jsonify({"error": "Erro ao salvar pagamento"}), 500

    # -------- RESPOSTA --------
    return jsonify({
        "payment_id": payment_id,
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": valor
    })

# ------------------ START ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
