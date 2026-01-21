import os
import psycopg2
from flask import Flask, request, jsonify
from datetime import datetime
import mercadopago

from flask_cors import CORS
app = Flask(__name__)
CORS(app)

app = Flask(__name__)

# ========================
# CONFIGURAÇÕES
# ========================
DATABASE_URL = os.environ.get("DATABASE_URL")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# ========================
# BANCO DE DADOS
# ========================
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id SERIAL PRIMARY KEY,
            email TEXT,
            valor NUMERIC,
            status TEXT,
            data_pagamento TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ========================
# ROTAS
# ========================
@app.route("/")
def home():
    return "Servidor PIX ONLINE 🚀"

@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # Criar pagamento PIX no Mercado Pago
    payment_data = {
        "transaction_amount": 1.0,  # Valor de teste
        "description": "Pagamento DedMais",
        "payment_method_id": "pix",
        "payer": {"email": email}
    }

    payment = mp.payment().create(payment_data)
    if payment["status"] != 201:
        return jsonify({"error": "Erro ao criar pagamento"}), 500

    result = payment["response"]
    pix_payload = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")
    qr_base64 = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64")

    if not pix_payload or not qr_base64:
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

    # Salvar no banco
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pagamentos (email, valor, status, data_pagamento)
        VALUES (%s, %s, %s, %s)
    """, (
        email,
        result["transaction_amount"],
        "pending",
        datetime.utcnow()
    ))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": result["transaction_amount"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

