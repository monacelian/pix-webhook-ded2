from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import os
import psycopg2
from datetime import datetime

app = Flask(__name__)
CORS(app)  # permite que a extensão faça fetch

# ----------------- CONFIG -----------------
DATABASE_URL = os.environ.get("DATABASE_URL")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# ----------------- MERCADO PAGO -----------------
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# ----------------- BANCO DE DADOS -----------------
def get_db():
    return psycopg2.connect(DATABASE_URL)

# ----------------- GERAR PIX -----------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # Cria pagamento no Mercado Pago
    payment_data = {
        "transaction_amount": 1.0,
        "description": "Pagamento Pix DedMais",
        "payment_method_id": "pix",
        "payer": {"email": email},
    }

    payment = mp.payment().create(payment_data)
    if payment["status"] != 201:
        return jsonify({"error": "Erro ao criar pagamento"}), 500

    result = payment["response"]
    pix_payload = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")
    qr_base64 = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64")

    if not pix_payload or not qr_base64:
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

    # -------- SALVAR NO BANCO --------
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pagamentos (payment_id, email, valor, status, data_pagamento)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            str(result["id"]),
            email,
            result["transaction_amount"],
            "pending",
            datetime.utcnow()
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar no banco: {str(e)}"}), 500

    return jsonify({
        "payment_id": result["id"],
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": result["transaction_amount"]
    })

# ----------------- WEBHOOK -----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    payment_id = None

    # Extrair payment_id
    if "data" in data and "id" in data["data"]:
        payment_id = data["data"]["id"]
    elif request.args.get("id"):
        payment_id = request.args.get("id")

    if not payment_id:
        return "OK", 200

    # Consultar pagamento
    r = mp.payment().get(payment_id)
    p = r["response"]

    if p["status"] != "approved":
        return "OK", 200

    # Atualiza pagamento no banco
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE pagamentos
            SET status = %s
            WHERE payment_id = %s
        """, (
            "approved",
            str(payment_id)
        ))
        conn.commit()
        cur.close()
        conn.close()
    except:
        pass  # não interrompe o webhook

    return "OK", 200

# ----------------- START -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
