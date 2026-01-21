from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import os
import psycopg2
from datetime import datetime

app = Flask(__name__)
CORS(app)  # permite que a extensão faça fetch

# ------------------ CONFIG ------------------
DATABASE_URL = os.getenv("DATABASE_URL")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ------------------ MERCADO PAGO ------------------
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# ------------------ BANCO DE DADOS ------------------
def get_db():
    return psycopg2.connect(DATABASE_URL)

# ------------------ ROTAS ------------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,  # valor de teste
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

    # Salva no banco mesmo antes de receber Webhook
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pagamentos (id, email, valor, status, data_pagamento)
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
        print("Erro ao gravar no banco:", e)

    return jsonify({
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": result["transaction_amount"]
    })


# ------------------ WEBHOOK ------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    payment_id = None

    if "data" in data and "id" in data["data"]:
        payment_id = data["data"]["id"]
    elif request.args.get("id"):
        payment_id = request.args.get("id")

    if not payment_id:
        return "OK", 200

    # Consulta o pagamento no Mercado Pago
    import requests
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    r = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers)
    if r.status_code != 200:
        return "OK", 200

    pagamento = r.json()

    # Se não estiver aprovado, apenas ignora
    if pagamento["status"] != "approved":
        return "OK", 200

    # Atualiza status no banco
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE pagamentos
            SET status = %s, data_pagamento = %s
            WHERE id = %s
        """, ("approved", datetime.utcnow(), str(payment_id)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Erro ao atualizar pagamento:", e)

    return "OK", 200


# ------------------ HEALTHCHECK ------------------
@app.route("/")
def home():
    return "Servidor ONLINE - PIX + Webhook ✅"


# ------------------ START ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
