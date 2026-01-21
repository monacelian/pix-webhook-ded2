import os
from flask import Flask, request, jsonify
from datetime import datetime
import psycopg2
import mercadopago

# ------------------ APP ------------------
app = Flask(__name__)

# ------------------ CONFIGURAÇÃO ------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# ------------------ FUNÇÕES DE BANCO ------------------
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id SERIAL PRIMARY KEY,
            payment_id BIGINT UNIQUE,
            email TEXT NOT NULL,
            valor NUMERIC NOT NULL,
            status TEXT NOT NULL,
            data_pagamento TIMESTAMP NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ------------------ ROTAS ------------------

@app.route("/")
def home():
    return "Servidor DED 2.0 PIX ONLINE 🚀"

@app.route("/teste_db")
def teste_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return "BANCO CONECTADO ✅"
    except Exception as e:
        return str(e), 500

@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    try:
        # ------------------ Criar pagamento Pix ------------------
        payment_data = {
            "transaction_amount": 1.0,  # valor de teste
            "description": "Pagamento Pix DedMais",
            "payment_method_id": "pix",
            "payer": {"email": email},
            "notification_url": WEBHOOK_URL
        }

        payment = mp.payment().create(payment_data)

        if payment["status"] != 201:
            return jsonify({"error": "Erro ao criar pagamento"}), 500

        result = payment["response"]
        pix_payload = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")
        qr_base64 = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64")

        if not pix_payload or not qr_base64:
            return jsonify({"error": "Não foi possível gerar Pix"}), 500

        # ------------------ Gravar no banco ------------------
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pagamentos (payment_id, email, valor, status, data_pagamento)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            result["id"],
            email,
            result["transaction_amount"],
            "pending",
            datetime.utcnow()
        ))
        conn.commit()
        cur.close()
        conn.close()

        # ------------------ Retornar dados ------------------
        return jsonify({
            "pix_id": result["id"],
            "pix_payload": pix_payload,
            "qr_base64": qr_base64,
            "valor": result["transaction_amount"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ START ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
