import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import psycopg2
from flask_cors import CORS

# ========================
# CONFIGURAÇÃO DO FLASK
# ========================
app = Flask(__name__)
CORS(app)  # habilita CORS para todas as rotas

# ========================
# VARIÁVEIS DE AMBIENTE
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

# Inicializa o banco ao subir o app
init_db()

# ========================
# ENDPOINT /VALIDAR
# ========================
@app.route("/validar", methods=["GET"])
def validar_email():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status, data_expiracao FROM pagamentos WHERE email = %s ORDER BY id DESC LIMIT 1", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row and row[0] == "approved":
        return jsonify({
            "ativo": True,
            "expira_em": row[1].isoformat()
        })
    else:
        return jsonify({"ativo": False})

# ========================
# ENDPOINT /GERAR_PIX
# ========================
@app.route("/gerar_pix", methods=["POST"])
def gerar_pix():
    data = request.json
    email = data.get("email")
    valor = float(data.get("valor", 1.0))  # default 1 real

    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # Cria pagamento Pix no Mercado Pago
    payload = {
        "transaction_amount": valor,
        "description": f"Assinatura DED 2.0 - {email}",
        "payment_method_id": "pix",
        "payer": {"email": email},
        "notification_url": WEBHOOK_URL
    }

    response = requests.post(
        "https://api.mercadopago.com/v1/payments",
        headers=MP_HEADERS,
        json=payload
    )

    if response.status_code != 201:
        return jsonify({"error": "Falha ao criar pagamento", "details": response.json()}), 400

    pagamento = response.json()

    # Salva pagamento no banco
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pagamentos (payment_id, email, status, valor, data_pagamento, data_expiracao)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        pagamento["id"],
        email,
        pagamento["status"],  # pending
        valor,
        datetime.utcnow(),
        datetime.utcnow() + timedelta(days=30)
    ))
    conn.commit()
    cur.close()
    conn.close()

    # Retorna QR code base64
    return jsonify({
        "link": pagamento["point_of_interaction"]["transaction_data"]["qr_code_base64"],
        "valor": valor,
        "status": pagamento["status"]
    })

# ========================
# ENDPOINT /WEBHOOK
# ========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    payment_id = data["data"]["id"]

    # Atualiza status do pagamento
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE pagamentos SET status = %s WHERE payment_id = %s", ("approved", payment_id))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})

# ========================
# RODAR O APP
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
