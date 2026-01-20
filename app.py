import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import psycopg2

app = Flask(__name__)

# ========================
# CONFIGURAÇÕES
# ========================

MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

MP_HEADERS = {
    "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

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
            payment_id BIGINT UNIQUE,
            email TEXT,
            status TEXT,
            valor NUMERIC,
            data_pagamento TIMESTAMP,
            data_expiracao TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ========================
# GERAR PIX
# ========================

@app.route("/gerar_pix", methods=["POST"])
def gerar_pix():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"erro": "email obrigatório"}), 400

    payload = {
        "items": [
            {
                "title": "DED 2.0 - Acesso",
                "quantity": 1,
                "unit_price": 5
            }
        ],
        "payer": {
            "email": email
        },
        "payment_methods": {
            "excluded_payment_types": [{"id": "credit_card"}],
            "installments": 1
        },
        "notification_url": WEBHOOK_URL
    }

    r = requests.post(
        "https://api.mercadopago.com/checkout/preferences",
        json=payload,
        headers=MP_HEADERS
    )

    pref = r.json()

    return jsonify({
        "pref_id": pref["id"],
        "link": pref["init_point"]
    })

# ========================
# WEBHOOK MERCADO PAGO
# ========================

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
    r = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers=MP_HEADERS
    )

    if r.status_code != 200:
        return "OK", 200

    p = r.json()

    if p.get("status") != "approved":
        return "OK", 200

    email = p["payer"]["email"]
    valor = p["transaction_amount"]
    data_pagamento = datetime.utcnow()
    data_expiracao = data_pagamento + timedelta(days=30)

    conn = get_db()
    cur = conn.cursor()

    # Idempotência
    cur.execute(
        "SELECT 1 FROM pagamentos WHERE payment_id = %s",
        (payment_id,)
    )
    if cur.fetchone():
        cur.close()
        conn.close()
        return "OK", 200

    cur.execute("""
        INSERT INTO pagamentos
        (payment_id, email, status, valor, data_pagamento, data_expiracao)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        payment_id,
        email,
        "approved",
        valor,
        data_pagamento,
        data_expiracao
    ))

    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200

# ========================
# API PARA O DED 2.0
# ========================

@app.route("/validar", methods=["GET"])
def validar():
    email = request.args.get("email")

    if not email:
        return jsonify({"ativo": False})

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT data_expiracao
        FROM pagamentos
        WHERE email = %s
        AND data_expiracao > NOW()
        ORDER BY data_expiracao DESC
        LIMIT 1
    """, (email,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"ativo": False})

    return jsonify({
        "ativo": True,
        "expira_em": row[0].isoformat()
    })

# ========================
# HEALTHCHECK
# ========================

@app.route("/")
def home():
    return "DED 2.0 PIX API ONLINE 🚀"
