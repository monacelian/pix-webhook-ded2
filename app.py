import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import psycopg2
from flask_cors import CORS

# ========================
# Criar app e habilitar CORS
# ========================
app = Flask(__name__)
CORS(app)

# ========================
# Configurações
# ========================
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

MP_HEADERS = {
    "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# ========================
# Banco de dados
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

# ========================
# Endpoint para validar email
# ========================
@app.route("/validar", methods=["GET"])
def validar_email():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "email obrigatório"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status, data_expiracao FROM pagamentos WHERE email=%s ORDER BY id DESC LIMIT 1", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        status, data_expiracao = row
        ativo = status.lower() == "approved" and datetime.now() < data_expiracao
        return jsonify({
            "ativo": ativo,
            "expira_em": data_expiracao.isoformat() if ativo else None
        })
    else:
        return jsonify({"ativo": False})

# ========================
# Endpoint para gerar Pix (GET para extensão enxuta)
# ========================
@app.route("/gerar_pix", methods=["GET"])
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "email obrigatório"}), 400

    # Para teste, geramos um Pix fixo de 1 real
    valor = 1.00
    agora = datetime.now()
    expira = agora + timedelta(days=30)

    # Aqui você chamaria a API do Mercado Pago para criar o Pix
    # Exemplo simplificado de resposta simulada:
    payment_id = int(agora.timestamp())
    link_pix = f"https://www.mercadopago.com.br/pix/{payment_id}"  # link fictício

    # Salvar no banco
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pagamentos (payment_id, email, status, valor, data_pagamento, data_expiracao)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (payment_id, email, "pending", valor, agora, expira))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "payment_id": payment_id,
        "valor": valor,
        "link_pix": link_pix,
        "expira_em": expira.isoformat()
    })

# ========================
# Webhook do Mercado Pago (opcional)
# ========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    payment_id = data.get("data", {}).get("id")
    status = "approved"  # Exemplo simplificado

    if not payment_id:
        return "no data", 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE pagamentos SET status=%s WHERE payment_id=%s", (status, payment_id))
    conn.commit()
    cur.close()
    conn.close()

    return "ok", 200

# ========================
# Inicializar DB e rodar app
# ========================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)
